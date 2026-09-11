from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from new_eden_foundry_backend.asset_delta import (
    AssetDeltaError,
    AssetDeltaQuery,
    build_asset_delta_payload,
    query_asset_deltas,
    validate_asset_delta_query,
)
from new_eden_foundry_backend.asset_sync import AssetSyncError, sync_character_assets
from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.esi_client import EsiClientError, EsiResponse
from new_eden_foundry_backend.sde import import_minimal_sde


CHARACTER_ID = 90_921_001
TYPE_ID = 99_021
SECOND_TYPE_ID = 99_022
STATION_ID = 60_921_001


def asset(
    item_id: int,
    *,
    type_id: int = TYPE_ID,
    quantity: int = 1,
    location_id: int = STATION_ID,
    location_flag: str = "SyntheticHangar",
) -> dict[str, object]:
    return {
        "item_id": item_id,
        "type_id": type_id,
        "location_id": location_id,
        "location_type": "station",
        "location_flag": location_flag,
        "quantity": quantity,
    }


class FakeClient:
    def __init__(self, rows: list[dict[str, object]], *, fail: bool = False) -> None:
        self.rows = rows
        self.fail = fail

    def get_json(self, path, *, query, character_id, required_scopes):
        if self.fail:
            raise EsiClientError("synthetic_network_failure", retryable=True)
        return EsiResponse(200, self.rows, {"x-pages": "1"}, False)


class AssetDeltaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "foundry.sqlite3"
        initialize_database(self.database_path)
        self.database = connect_database(self.database_path)
        self.database.execute(
            "INSERT INTO characters(character_id,name,alias) VALUES(?,?,?)",
            (CHARACTER_ID, "Synthetic Delta Pilot", "Delta Pilot"),
        )
        import_minimal_sde(
            self.database,
            build_number="asset-delta-fixture-1",
            groups=[{"group_id": 99_020, "name": "Synthetic Delta Group"}],
            types=[
                {"type_id": TYPE_ID, "group_id": 99_020, "name": "Synthetic Input"},
                {
                    "type_id": SECOND_TYPE_ID,
                    "group_id": 99_020,
                    "name": "Synthetic Output",
                },
            ],
            locations=[
                {
                    "location_id": STATION_ID,
                    "name": "Synthetic Delta Station",
                    "kind": "station",
                }
            ],
        )

    def tearDown(self) -> None:
        self.database.close()
        self.temporary_directory.cleanup()

    def delta_payloads(self) -> list[dict[str, object]]:
        rows = self.database.execute(
            "SELECT payload_json FROM cached_snapshots "
            "WHERE resource=? ORDER BY id",
            (f"asset_deltas:{CHARACTER_ID}",),
        ).fetchall()
        return [json.loads(str(row[0])) for row in rows]

    def test_first_complete_snapshot_creates_an_empty_baseline(self) -> None:
        result = sync_character_assets(
            self.database,
            FakeClient([asset(1, quantity=10)]),
            CHARACTER_ID,
        )

        payloads = self.delta_payloads()
        self.assertEqual(len(payloads), 1)
        baseline = payloads[0]
        self.assertTrue(baseline["baseline"])
        self.assertEqual(baseline["events"], [])
        self.assertEqual(baseline["summary"]["events"], 0)
        self.assertIsNone(baseline["previousAssetSnapshotId"])
        self.assertEqual(baseline["currentAssetSyncRunId"], result.sync_run_id)

    def test_complete_follow_up_records_added_removed_quantity_and_location(self) -> None:
        sync_character_assets(
            self.database,
            FakeClient(
                [
                    asset(1, quantity=10),
                    asset(2, type_id=SECOND_TYPE_ID, quantity=2),
                    asset(3, quantity=4),
                ]
            ),
            CHARACTER_ID,
        )
        sync_character_assets(
            self.database,
            FakeClient(
                [
                    asset(1, quantity=7),
                    asset(2, type_id=SECOND_TYPE_ID, quantity=2, location_flag="Output"),
                    asset(4, type_id=SECOND_TYPE_ID, quantity=5),
                ]
            ),
            CHARACTER_ID,
        )

        payload = self.delta_payloads()[-1]
        self.assertFalse(payload["baseline"])
        self.assertEqual(payload["summary"], {
            "events": 4,
            "added": 1,
            "removed": 1,
            "quantity": 1,
            "location": 1,
        })
        events = {event["itemId"]: event for event in payload["events"]}
        self.assertEqual(events[1]["changeTypes"], ["quantity"])
        self.assertEqual(events[1]["quantityDelta"], -3)
        self.assertEqual(events[1]["jobCorrelation"]["direction"], "outbound")
        self.assertEqual(events[2]["changeTypes"], ["location"])
        self.assertEqual(events[2]["locationFlagAfter"], "Output")
        self.assertEqual(events[3]["changeTypes"], ["removed"])
        self.assertEqual(events[4]["changeTypes"], ["added"])
        self.assertEqual(events[4]["jobCorrelation"]["key"], f"{CHARACTER_ID}:{SECOND_TYPE_ID}")
        self.assertTrue(all(len(event["eventId"]) == 64 for event in events.values()))

    def test_failed_or_invalid_follow_up_publishes_no_snapshot_or_delta(self) -> None:
        first = sync_character_assets(
            self.database,
            FakeClient([asset(1, quantity=10)]),
            CHARACTER_ID,
        )
        with self.assertRaises(EsiClientError):
            sync_character_assets(
                self.database,
                FakeClient([asset(1, quantity=9)], fail=True),
                CHARACTER_ID,
            )
        with self.assertRaises(AssetDeltaError):
            sync_character_assets(
                self.database,
                FakeClient([asset(1, type_id=SECOND_TYPE_ID, quantity=9)]),
                CHARACTER_ID,
            )

        self.assertEqual(len(self.delta_payloads()), 1)
        current = self.database.execute(
            "SELECT sync_run_id FROM cached_snapshots WHERE resource=? ORDER BY id DESC LIMIT 1",
            (f"character_assets:{CHARACTER_ID}",),
        ).fetchone()
        self.assertEqual(int(current[0]), first.sync_run_id)
        latest_runs = self.database.execute(
            "SELECT status,error_code FROM sync_runs ORDER BY id DESC LIMIT 2"
        ).fetchall()
        self.assertEqual(
            [(row[0], row[1]) for row in latest_runs],
            [("failed", "asset_item_identity_changed"), ("failed", "synthetic_network_failure")],
        )

    def test_query_is_bounded_searchable_filterable_and_job_ready(self) -> None:
        sync_character_assets(
            self.database,
            FakeClient([asset(1, quantity=10), asset(2, type_id=SECOND_TYPE_ID)]),
            CHARACTER_ID,
        )
        sync_character_assets(
            self.database,
            FakeClient([asset(1, quantity=6), asset(3, type_id=SECOND_TYPE_ID, quantity=8)]),
            CHARACTER_ID,
        )

        page = query_asset_deltas(
            self.database,
            AssetDeltaQuery("synthetic input", CHARACTER_ID, "quantity", 0, 1),
            now=datetime(2026, 9, 10, 18, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(page["total"], 1)
        self.assertEqual(len(page["items"]), 1)
        self.assertEqual(page["summary"], {
            "added": 0,
            "removed": 0,
            "quantity": 1,
            "location": 0,
        })
        event = page["items"][0]
        self.assertEqual(event["quantityDelta"], -4)
        self.assertEqual(event["ownerName"], "Delta Pilot")
        self.assertEqual(event["jobCorrelation"]["state"], "not-applicable")
        self.assertEqual(event["jobCorrelation"]["jobIds"], [])
        self.assertEqual(event["jobCorrelation"]["direction"], "outbound")
        self.assertEqual(page["limit"], 1)
        self.assertTrue(page["hasBaseline"])

    def test_deterministic_payload_and_strict_query_validation(self) -> None:
        before = {"characterId": CHARACTER_ID, "assets": [asset(1, quantity=3)]}
        after = {"characterId": CHARACTER_ID, "assets": [asset(1, quantity=5)]}
        arguments = {
            "character_id": CHARACTER_ID,
            "current_snapshot_id": 12,
            "current_sync_run_id": 22,
            "current_observed_at": "2026-09-10T11:00:00Z",
            "current_payload": after,
            "previous_snapshot_id": 11,
            "previous_sync_run_id": 21,
            "previous_observed_at": "2026-09-10T10:00:00Z",
            "previous_payload": before,
        }

        self.assertEqual(
            build_asset_delta_payload(**arguments),
            build_asset_delta_payload(**arguments),
        )
        with self.assertRaises(AssetDeltaError):
            validate_asset_delta_query(change_type="manufactured")
        with self.assertRaises(AssetDeltaError):
            validate_asset_delta_query(limit=201)

    def test_tampered_event_fingerprint_is_rejected_fail_closed(self) -> None:
        sync_character_assets(
            self.database,
            FakeClient([asset(1, quantity=3)]),
            CHARACTER_ID,
        )
        sync_character_assets(
            self.database,
            FakeClient([asset(1, quantity=5)]),
            CHARACTER_ID,
        )
        row = self.database.execute(
            "SELECT id,payload_json FROM cached_snapshots WHERE resource=? "
            "ORDER BY id DESC LIMIT 1",
            (f"asset_deltas:{CHARACTER_ID}",),
        ).fetchone()
        payload = json.loads(str(row[1]))
        original_id = payload["events"][0]["eventId"]
        payload["events"][0]["eventId"] = (
            ("b" if original_id[0] != "b" else "c") + original_id[1:]
        )
        self.database.execute(
            "UPDATE cached_snapshots SET payload_json=? WHERE id=?",
            (json.dumps(payload), int(row[0])),
        )

        with self.assertRaisesRegex(AssetDeltaError, "asset_delta_snapshot_invalid"):
            query_asset_deltas(self.database, AssetDeltaQuery())

    def test_ten_thousand_changes_return_only_the_bounded_window(self) -> None:
        sync_character_assets(
            self.database,
            FakeClient([asset(item_id, quantity=1) for item_id in range(1, 10_001)]),
            CHARACTER_ID,
        )
        sync_character_assets(
            self.database,
            FakeClient([asset(item_id, quantity=2) for item_id in range(1, 10_001)]),
            CHARACTER_ID,
        )

        page = query_asset_deltas(
            self.database,
            AssetDeltaQuery(offset=100, limit=50),
        )

        self.assertEqual(page["total"], 10_000)
        self.assertEqual(len(page["items"]), 50)
        self.assertEqual((page["offset"], page["limit"]), (100, 50))
        self.assertEqual(page["summary"]["quantity"], 10_000)


if __name__ == "__main__":
    unittest.main()
