from datetime import datetime, timezone
from pathlib import Path
import json
import tempfile
import unittest

from new_eden_foundry_backend.asset_delta import (
    AssetDeltaQuery,
    build_asset_delta_payload,
    query_asset_deltas,
)
from new_eden_foundry_backend.blueprint_sync import sync_character_blueprints
from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.esi_client import EsiClientError, EsiResponse
from new_eden_foundry_backend.industry_job_sync import (
    IndustryJobSyncError,
    sync_character_industry_jobs,
)
from new_eden_foundry_backend.industry_job_evidence import correlate_asset_event
from new_eden_foundry_backend.industry_job_view import (
    IndustryJobViewError,
    query_industry_jobs,
)


CHARACTER_ID = 90_000_001


class FakeClient:
    def __init__(self, payload, *, fail=False):
        self.payload = payload
        self.fail = fail
        self.calls = []

    def get_json(self, path, *, query, character_id, required_scopes):
        self.calls.append((path, query, character_id, required_scopes))
        if self.fail:
            raise EsiClientError("esi-network-unavailable", retryable=True)
        return EsiResponse(200, self.payload, {}, False)


class BlueprintClient:
    def get_json(self, path, *, query, character_id, required_scopes):
        del path, query, character_id, required_scopes
        return EsiResponse(200, [{
            "item_id": 7_001,
            "type_id": 6_001,
            "location_id": 60_000_001,
            "location_flag": "Hangar",
            "quantity": -1,
            "time_efficiency": 20,
            "material_efficiency": 10,
            "runs": -1,
        }], {"x-pages": "1"}, False)


def job(job_id=8_001, *, status="delivered", product_type_id=6_002):
    return {
        "activity_id": 1,
        "blueprint_id": 7_001,
        "blueprint_location_id": 60_000_001,
        "blueprint_type_id": 6_001,
        "completed_character_id": CHARACTER_ID,
        "completed_date": "2026-09-10T11:00:00Z" if status == "delivered" else None,
        "cost": 1234.5,
        "duration": 3600,
        "end_date": "2026-09-10T11:00:00Z",
        "facility_id": 60_000_001,
        "installer_id": CHARACTER_ID,
        "job_id": job_id,
        "licensed_runs": 0,
        "output_location_id": 60_000_001,
        "pause_date": None,
        "probability": 1.0,
        "product_type_id": product_type_id,
        "runs": 2,
        "start_date": "2026-09-10T10:00:00Z",
        "station_id": 60_000_001,
        "status": status,
        "successful_runs": 2 if status == "delivered" else None,
    }


def asset(item_id, type_id, quantity):
    return {
        "item_id": item_id,
        "type_id": type_id,
        "quantity": quantity,
        "location_id": 60_000_001,
        "location_type": "station",
        "location_flag": "Hangar",
    }


class IndustryJobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "foundry.db"
        initialize_database(self.path)
        self.db = connect_database(self.path)
        self.db.execute(
            "INSERT INTO characters(character_id,name) VALUES(?,?)",
            (CHARACTER_ID, "Industry Pilot"),
        )

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def _insert_asset_delta(self):
        previous_payload = {"characterId": CHARACTER_ID, "pages": 1, "assets": []}
        current_payload = {
            "characterId": CHARACTER_ID,
            "pages": 1,
            "assets": [asset(9_001, 6_002, 2)],
        }
        run = self.db.execute(
            "INSERT INTO sync_runs(source,status,started_at,completed_at,data_timestamp,character_id) "
            "VALUES('character_assets','completed',?,?,?,?)",
            (
                "2026-09-10T10:59:00Z",
                "2026-09-10T11:01:00Z",
                "2026-09-10T11:01:00Z",
                CHARACTER_ID,
            ),
        )
        previous = self.db.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (run.lastrowid, "synthetic_previous_assets", "{}", "2026-09-10T10:59:00Z"),
        )
        current = self.db.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (run.lastrowid, "synthetic_current_assets", "{}", "2026-09-10T11:01:00Z"),
        )
        payload = build_asset_delta_payload(
            character_id=CHARACTER_ID,
            previous_snapshot_id=int(previous.lastrowid),
            previous_sync_run_id=int(run.lastrowid),
            previous_observed_at="2026-09-10T10:59:00Z",
            previous_payload=previous_payload,
            current_snapshot_id=int(current.lastrowid),
            current_sync_run_id=int(run.lastrowid),
            current_observed_at="2026-09-10T11:01:00Z",
            current_payload=current_payload,
        )
        self.db.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (
                run.lastrowid,
                f"asset_deltas:{CHARACTER_ID}",
                json.dumps(payload, separators=(",", ":"), sort_keys=True),
                "2026-09-10T11:01:00Z",
            ),
        )
        self.db.commit()

    def test_syncs_completed_jobs_and_exposes_traceable_correlations(self):
        sync_character_blueprints(self.db, BlueprintClient(), CHARACTER_ID)
        self._insert_asset_delta()
        client = FakeClient([job()])
        result = sync_character_industry_jobs(self.db, client, CHARACTER_ID)
        self.assertEqual((result.jobs, result.active, result.completed), (1, 0, 1))
        self.assertEqual(result.type_ids, (6_001, 6_002))
        self.assertEqual(client.calls[0], (
            f"/characters/{CHARACTER_ID}/industry/jobs/",
            {"include_completed": "true"},
            CHARACTER_ID,
            ("esi-industry.read_character_jobs.v1",),
        ))

        query = {
            "search": "industry pilot",
            "ownerCharacterId": None,
            "status": "delivered",
            "activityId": 1,
            "correlation": "linked",
            "offset": 0,
            "limit": 100,
            "sortBy": "end",
            "sortDirection": "desc",
        }
        page = query_industry_jobs(
            self.db, query, now=datetime(2026, 9, 10, 12, tzinfo=timezone.utc)
        )
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["activeTotal"], 0)
        record = page["items"][0]
        self.assertEqual(record["blueprintCorrelation"]["state"], "current")
        self.assertEqual(record["assetCorrelation"]["state"], "linked")
        self.assertTrue(record["assetCorrelation"]["locationMatched"])
        self.assertEqual(record["correlationState"], "linked")

        delta_page = query_asset_deltas(
            self.db,
            AssetDeltaQuery(),
            now=datetime(2026, 9, 10, 12, tzinfo=timezone.utc),
        )
        self.assertEqual(delta_page["items"][0]["jobCorrelation"]["state"], "linked")
        self.assertEqual(delta_page["items"][0]["jobCorrelation"]["jobIds"], [8_001])

    def test_lists_enabled_character_without_snapshot_and_hides_disabled_jobs(self):
        second_character_id = 90_000_002
        self.db.execute(
            "INSERT INTO characters(character_id,name) VALUES(?,?)",
            (second_character_id, "Second Pilot"),
        )
        sync_character_industry_jobs(
            self.db,
            FakeClient([job(status="active")]),
            CHARACTER_ID,
        )
        query = {
            "search": "", "ownerCharacterId": None, "status": None,
            "activityId": None, "correlation": None, "offset": 0, "limit": 100,
            "sortBy": "start", "sortDirection": "asc",
        }

        page = query_industry_jobs(self.db, query)
        self.assertEqual(
            page["owners"],
            [
                {"characterId": CHARACTER_ID, "name": "Industry Pilot"},
                {"characterId": second_character_id, "name": "Second Pilot"},
            ],
        )

        self.db.execute(
            "UPDATE characters SET enabled=0 WHERE character_id=?",
            (CHARACTER_ID,),
        )
        page = query_industry_jobs(self.db, query)
        self.assertEqual(page["total"], 0)
        self.assertEqual(
            page["owners"],
            [{"characterId": second_character_id, "name": "Second Pilot"}],
        )

    def test_active_jobs_are_pending_and_query_is_strict_and_bounded(self):
        active = job(8_002, status="active")
        active["successful_runs"] = None
        active["completed_date"] = None
        sync_character_industry_jobs(self.db, FakeClient([active]), CHARACTER_ID)
        query = {
            "search": "",
            "ownerCharacterId": CHARACTER_ID,
            "status": None,
            "activityId": None,
            "correlation": "pending",
            "offset": 0,
            "limit": 1,
            "sortBy": "start",
            "sortDirection": "asc",
        }
        page = query_industry_jobs(self.db, query)
        self.assertEqual((page["total"], len(page["items"])), (1, 1))
        self.assertEqual(page["activeTotal"], 1)
        self.assertEqual(page["items"][0]["assetCorrelation"]["state"], "pending")
        with self.assertRaises(IndustryJobViewError):
            query_industry_jobs(self.db, {**query, "unexpected": True})

    def test_failed_followup_keeps_last_complete_job_snapshot(self):
        first = sync_character_industry_jobs(self.db, FakeClient([job()]), CHARACTER_ID)
        with self.assertRaises(EsiClientError):
            sync_character_industry_jobs(self.db, FakeClient([], fail=True), CHARACTER_ID)
        snapshots = self.db.execute(
            "SELECT COUNT(*) FROM cached_snapshots WHERE resource=?",
            (f"character_industry_jobs:{CHARACTER_ID}",),
        ).fetchone()[0]
        self.assertEqual(snapshots, 1)
        latest = self.db.execute(
            "SELECT status,error_code FROM sync_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(tuple(latest), ("failed", "esi-network-unavailable"))
        self.assertGreater(first.sync_run_id, 0)

    def test_invalid_or_duplicate_jobs_publish_nothing(self):
        duplicate = [job(), job()]
        with self.assertRaises(IndustryJobSyncError):
            sync_character_industry_jobs(self.db, FakeClient(duplicate), CHARACTER_ID)
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM cached_snapshots").fetchone()[0], 0
        )

    def test_multiple_matching_jobs_remain_ambiguous_unless_location_disambiguates(self):
        first = job(8_001)
        second = job(8_002)
        second["output_location_id"] = 60_000_002
        snapshots = {CHARACTER_ID: {"jobs": [first, second]}}
        ambiguous = correlate_asset_event(
            snapshots,
            character_id=CHARACTER_ID,
            type_id=6_002,
            direction="inbound",
            window_start="2026-09-10T10:59:00Z",
            window_end="2026-09-10T11:01:00Z",
            location_id_after=60_000_003,
        )
        self.assertEqual(ambiguous["state"], "ambiguous")
        self.assertEqual(ambiguous["jobIds"], [8_001, 8_002])

        linked = correlate_asset_event(
            snapshots,
            character_id=CHARACTER_ID,
            type_id=6_002,
            direction="inbound",
            window_start="2026-09-10T10:59:00Z",
            window_end="2026-09-10T11:01:00Z",
            location_id_after=60_000_002,
        )
        self.assertEqual(linked["state"], "linked")
        self.assertEqual(linked["jobIds"], [8_002])
        self.assertTrue(linked["locationMatched"])


if __name__ == "__main__":
    unittest.main()
