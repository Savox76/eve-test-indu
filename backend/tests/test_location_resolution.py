from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.esi_client import EsiClientError, EsiResponse
from new_eden_foundry_backend.location_resolution import (
    STRUCTURE_SCOPE,
    EsiLocationProvider,
    RootLocation,
    resolve_asset_locations,
    resolve_latest_character_asset_locations,
)
from new_eden_foundry_backend.sde import import_minimal_sde


# Endpoint-shaped but deliberately invented identifiers used only by synthetic fakes.
CHARACTER_ID = 90_999_001
SYSTEM_ID = 30_999_001
STATION_ID = 60_999_001
REMOTE_STATION_ID = 60_999_002
STRUCTURE_ID = 1_099_900_000_001
CONTAINER_TYPE_ID = 99_001
ITEM_TYPE_ID = 99_002


def asset(
    item_id: int,
    location_id: int,
    location_type: str,
    type_id: int = ITEM_TYPE_ID,
) -> dict[str, object]:
    return {
        "item_id": item_id,
        "type_id": type_id,
        "location_id": location_id,
        "location_type": location_type,
        "location_flag": "SyntheticHangar",
        "quantity": 1,
    }


class FakeLocationProvider:
    def __init__(self) -> None:
        self.station_calls: list[int] = []
        self.structure_calls: list[tuple[int, int]] = []

    def station(self, location_id: int) -> RootLocation:
        self.station_calls.append(location_id)
        return RootLocation(
            location_id,
            "station",
            "Synthetic Remote Station",
            solar_system_id=SYSTEM_ID,
        )

    def structure(self, location_id: int, character_id: int) -> RootLocation:
        self.structure_calls.append((location_id, character_id))
        return RootLocation(
            location_id,
            "structure",
            "Synthetic Industry Structure",
            solar_system_id=SYSTEM_ID,
            type_id=35_832,
        )


class FakeEsiClient:
    def __init__(self, result: EsiResponse | EsiClientError) -> None:
        self.result = result
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get_json(self, path: str, **kwargs: object) -> EsiResponse:
        self.calls.append((path, kwargs))
        if isinstance(self.result, EsiClientError):
            raise self.result
        return self.result


class LocationResolutionGoldenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = (
            Path(self.temporary_directory.name) / "foundry.sqlite3"
        )
        initialize_database(self.database_path)
        self.database = connect_database(self.database_path)
        self.database.execute(
            "INSERT INTO characters(character_id,name) VALUES(?,?)",
            (CHARACTER_ID, "Synthetic Locator"),
        )
        import_minimal_sde(
            self.database,
            build_number="synthetic-sde-location-golden-1",
            groups=[{"group_id": 99_000, "name": "Synthetic Asset Group"}],
            types=[
                {
                    "type_id": CONTAINER_TYPE_ID,
                    "group_id": 99_000,
                    "name": "Synthetic Freight Container",
                },
                {
                    "type_id": ITEM_TYPE_ID,
                    "group_id": 99_000,
                    "name": "Synthetic Component",
                },
            ],
            locations=[
                {
                    "location_id": SYSTEM_ID,
                    "name": "Synthetic System",
                    "kind": "solar_system",
                },
                {
                    "location_id": STATION_ID,
                    "parent_location_id": SYSTEM_ID,
                    "name": "Synthetic Station",
                    "kind": "station",
                },
            ],
        )

    def tearDown(self) -> None:
        self.database.close()
        self.temporary_directory.cleanup()

    def publish_asset_snapshot(
        self,
        assets: list[dict[str, object]],
        observed_at: str = "2026-09-10T08:00:00Z",
    ) -> int:
        cursor = self.database.execute(
            """
            INSERT INTO sync_runs(
                source,status,started_at,completed_at,data_timestamp,character_id
            ) VALUES('character_assets','completed',?,?,?,?)
            """,
            (observed_at, observed_at, observed_at, CHARACTER_ID),
        )
        run_id = int(cursor.lastrowid)
        payload = json.dumps(
            {
                "synthetic": True,
                "characterId": CHARACTER_ID,
                "pages": 1,
                "assets": assets,
            }
        )
        self.database.execute(
            """
            INSERT INTO cached_snapshots(
                sync_run_id,resource,payload_json,observed_at
            ) VALUES(?,?,?,?)
            """,
            (run_id, f"character_assets:{CHARACTER_ID}", payload, observed_at),
        )
        return run_id

    def test_station_and_nested_container_path_is_root_first(self) -> None:
        provider = FakeLocationProvider()
        locations = resolve_asset_locations(
            self.database,
            provider,
            CHARACTER_ID,
            [
                asset(9_900_001, STATION_ID, "station", CONTAINER_TYPE_ID),
                asset(9_900_002, 9_900_001, "item"),
            ],
        )

        self.assertEqual(locations[1].status, "resolved")
        self.assertEqual(
            [node.name for node in locations[1].path],
            [
                "Synthetic System",
                "Synthetic Station",
                "Synthetic Freight Container",
            ],
        )
        self.assertEqual(provider.station_calls, [])

    def test_station_provider_is_reused_for_shared_root(self) -> None:
        provider = FakeLocationProvider()
        locations = resolve_asset_locations(
            self.database,
            provider,
            CHARACTER_ID,
            [
                asset(9_900_011, REMOTE_STATION_ID, "station"),
                asset(9_900_012, REMOTE_STATION_ID, "station"),
            ],
        )

        self.assertEqual(provider.station_calls, [REMOTE_STATION_ID])
        self.assertEqual(
            [node.name for node in locations[0].path],
            ["Synthetic System", "Synthetic Remote Station"],
        )
        self.assertEqual(locations[0].path, locations[1].path)

    def test_structure_403_is_published_as_restricted_not_failed(self) -> None:
        self.database.execute(
            "INSERT INTO character_scopes(character_id,scope) VALUES(?,?)",
            (CHARACTER_ID, STRUCTURE_SCOPE),
        )
        self.publish_asset_snapshot(
            [asset(9_900_021, STRUCTURE_ID, "other")]
        )
        client = FakeEsiClient(
            EsiClientError("esi-request-rejected", status=403, retryable=False)
        )

        result = resolve_latest_character_asset_locations(
            self.database, client, CHARACTER_ID  # type: ignore[arg-type]
        )

        self.assertEqual((result.restricted, result.unresolved), (1, 0))
        snapshot = self.database.execute(
            "SELECT payload_json FROM cached_snapshots WHERE sync_run_id=?",
            (result.sync_run_id,),
        ).fetchone()
        payload = json.loads(snapshot[0])
        location = payload["locations"][0]
        self.assertEqual(location["status"], "restricted")
        self.assertEqual(location["errorCode"], "structure_forbidden")
        self.assertEqual(location["path"][-1]["kind"], "structure")
        self.assertEqual(
            client.calls,
            [
                (
                    f"/universe/structures/{STRUCTURE_ID}/",
                    {
                        "character_id": CHARACTER_ID,
                        "required_scopes": (STRUCTURE_SCOPE,),
                    },
                )
            ],
        )

    def test_missing_structure_scope_does_not_make_an_esi_request(self) -> None:
        provider = FakeLocationProvider()
        location = resolve_asset_locations(
            self.database,
            provider,
            CHARACTER_ID,
            [asset(9_900_031, STRUCTURE_ID, "item")],
        )[0]

        self.assertEqual(location.status, "restricted")
        self.assertEqual(location.error_code, "structure_scope_missing")
        self.assertEqual(provider.structure_calls, [])

    def test_container_cycle_is_marked_without_external_lookup(self) -> None:
        provider = FakeLocationProvider()
        locations = resolve_asset_locations(
            self.database,
            provider,
            CHARACTER_ID,
            [
                asset(9_900_041, 9_900_042, "item", CONTAINER_TYPE_ID),
                asset(9_900_042, 9_900_041, "item", CONTAINER_TYPE_ID),
            ],
        )

        self.assertEqual([value.status for value in locations], ["cycle", "cycle"])
        self.assertEqual(
            [node.location_id for node in locations[0].path],
            [9_900_041, 9_900_042, 9_900_041],
        )
        self.assertEqual(provider.station_calls, [])
        self.assertEqual(provider.structure_calls, [])

    def test_transient_failure_keeps_last_completed_location_snapshot(self) -> None:
        self.publish_asset_snapshot(
            [asset(9_900_051, REMOTE_STATION_ID, "station")]
        )
        good_client = FakeEsiClient(
            EsiResponse(
                200,
                {"name": "Synthetic Remote Station", "system_id": SYSTEM_ID},
                {},
                False,
            )
        )
        good = resolve_latest_character_asset_locations(
            self.database, good_client, CHARACTER_ID  # type: ignore[arg-type]
        )
        self.publish_asset_snapshot(
            [asset(9_900_052, REMOTE_STATION_ID + 1, "station")],
            "2026-09-10T09:00:00Z",
        )

        with self.assertRaises(EsiClientError):
            resolve_latest_character_asset_locations(
                self.database,
                FakeEsiClient(
                    EsiClientError("esi-network-unavailable", retryable=True)
                ),  # type: ignore[arg-type]
                CHARACTER_ID,
            )

        completed = self.database.execute(
            "SELECT COUNT(*) FROM cached_snapshots WHERE resource=?",
            (f"asset_locations:{CHARACTER_ID}",),
        ).fetchone()[0]
        last_run = self.database.execute(
            "SELECT status,error_code FROM sync_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(completed, 1)
        self.assertEqual(good.resolved, 1)
        self.assertEqual(tuple(last_run), ("failed", "esi-network-unavailable"))

    def test_esi_provider_maps_station_and_structure_payloads(self) -> None:
        station_client = FakeEsiClient(
            EsiResponse(
                200,
                {"name": "Synthetic Station", "system_id": SYSTEM_ID},
                {},
                False,
            )
        )
        structure_client = FakeEsiClient(
            EsiResponse(
                200,
                {
                    "name": "Synthetic Structure",
                    "solar_system_id": SYSTEM_ID,
                    "type_id": 35_832,
                },
                {},
                False,
            )
        )

        station = EsiLocationProvider(  # type: ignore[arg-type]
            station_client
        ).station(REMOTE_STATION_ID)
        structure = EsiLocationProvider(  # type: ignore[arg-type]
            structure_client
        ).structure(STRUCTURE_ID, CHARACTER_ID)

        self.assertEqual((station.name, station.solar_system_id), (
            "Synthetic Station",
            SYSTEM_ID,
        ))
        self.assertEqual(
            (structure.name, structure.solar_system_id, structure.type_id),
            ("Synthetic Structure", SYSTEM_ID, 35_832),
        )


if __name__ == "__main__":
    unittest.main()
