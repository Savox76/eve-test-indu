from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from new_eden_foundry_backend.asset_view import (
    AssetQuery,
    AssetViewError,
    export_assets_csv,
    query_assets,
    validate_asset_query,
)
from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.sde import import_minimal_sde


CHARACTER_ID = 90_888_001
SECOND_CHARACTER_ID = 90_888_002
TYPE_ID = 98_001
SECOND_TYPE_ID = 98_002
SYSTEM_ID = 30_888_001
STATION_ID = 60_888_001


def asset(item_id: int, type_id: int = TYPE_ID, quantity: int = 1) -> dict[str, object]:
    return {
        "item_id": item_id,
        "type_id": type_id,
        "location_id": STATION_ID,
        "location_type": "station",
        "location_flag": "SyntheticHangar",
        "quantity": quantity,
    }


class AssetViewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.database_path = self.root / "foundry.sqlite3"
        initialize_database(self.database_path)
        self.database = connect_database(self.database_path)
        self.database.execute(
            "INSERT INTO characters(character_id,name,alias) VALUES(?,?,?)",
            (CHARACTER_ID, "Synthetic Builder", "Builder"),
        )
        self.database.execute(
            "INSERT INTO characters(character_id,name) VALUES(?,?)",
            (SECOND_CHARACTER_ID, "Synthetic Hauler"),
        )
        import_minimal_sde(
            self.database,
            build_number="asset-view-fixture-1",
            groups=[{"group_id": 98_000, "name": "Synthetic Group"}],
            types=[
                {"type_id": TYPE_ID, "group_id": 98_000, "name": "Synthetic Component"},
                {"type_id": SECOND_TYPE_ID, "group_id": 98_000, "name": "=Formula Material"},
            ],
            locations=[
                {"location_id": SYSTEM_ID, "name": "Synthetic System", "kind": "solar_system"}
            ],
        )

    def tearDown(self) -> None:
        self.database.close()
        self.temporary_directory.cleanup()

    def publish_assets(
        self,
        character_id: int,
        rows: list[dict[str, object]],
        observed_at: str,
    ) -> int:
        run = self.database.execute(
            """
            INSERT INTO sync_runs(
                source,status,started_at,completed_at,data_timestamp,character_id
            ) VALUES('character_assets','completed',?,?,?,?)
            """,
            (observed_at, observed_at, observed_at, character_id),
        )
        snapshot = self.database.execute(
            """
            INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at)
            VALUES(?,?,?,?)
            """,
            (
                int(run.lastrowid),
                f"character_assets:{character_id}",
                json.dumps({"characterId": character_id, "pages": 1, "assets": rows}),
                observed_at,
            ),
        )
        return int(snapshot.lastrowid)

    def publish_locations(
        self,
        character_id: int,
        asset_snapshot_id: int,
        rows: list[dict[str, object]],
        observed_at: str,
    ) -> None:
        run = self.database.execute(
            """
            INSERT INTO sync_runs(
                source,status,started_at,completed_at,data_timestamp,character_id
            ) VALUES('asset_locations','completed',?,?,?,?)
            """,
            (observed_at, observed_at, observed_at, character_id),
        )
        self.database.execute(
            """
            INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at)
            VALUES(?,?,?,?)
            """,
            (
                int(run.lastrowid),
                f"asset_locations:{character_id}",
                json.dumps(
                    {
                        "characterId": character_id,
                        "assetSnapshotId": asset_snapshot_id,
                        "locations": rows,
                    }
                ),
                observed_at,
            ),
        )

    @staticmethod
    def resolved_location(item_id: int, status: str = "resolved") -> dict[str, object]:
        return {
            "itemId": item_id,
            "status": status,
            "path": [
                {
                    "locationId": SYSTEM_ID,
                    "kind": "solar_system",
                    "name": "Synthetic System",
                    "access": "available",
                    "typeId": None,
                },
                {
                    "locationId": STATION_ID,
                    "kind": "station",
                    "name": "Synthetic Station",
                    "access": "available" if status == "resolved" else "restricted",
                    "typeId": None,
                },
            ],
            "errorCode": None if status == "resolved" else "synthetic_restricted",
        }

    def test_joined_view_exposes_owner_location_quantity_and_age(self) -> None:
        first = self.publish_assets(
            CHARACTER_ID,
            [asset(9_800_001, quantity=17), asset(9_800_002, SECOND_TYPE_ID, 4)],
            "2026-09-10T10:00:00Z",
        )
        self.publish_locations(
            CHARACTER_ID,
            first,
            [
                self.resolved_location(9_800_001),
                self.resolved_location(9_800_002, "restricted"),
            ],
            "2026-09-10T10:01:00Z",
        )
        self.publish_assets(
            SECOND_CHARACTER_ID,
            [asset(9_800_003, quantity=2)],
            "2026-09-10T09:30:00Z",
        )

        result = query_assets(
            self.database,
            AssetQuery(),
            now=datetime(2026, 9, 10, 11, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(result["total"], 3)
        self.assertEqual(result["quantityTotal"], 23)
        self.assertEqual(result["observedAt"], "2026-09-10T09:30:00Z")
        self.assertEqual(result["ageSeconds"], 5_400)
        self.assertEqual(
            result["owners"],
            [
                {"characterId": CHARACTER_ID, "name": "Builder"},
                {"characterId": SECOND_CHARACTER_ID, "name": "Synthetic Hauler"},
            ],
        )
        component = next(row for row in result["items"] if row["itemId"] == 9_800_001)
        self.assertEqual(component["typeName"], "Synthetic Component")
        self.assertEqual(component["ownerName"], "Builder")
        self.assertEqual(component["quantity"], 17)
        self.assertEqual(
            component["locationPath"],
            "Synthetic System / Synthetic Station",
        )
        self.assertEqual(component["locationStatus"], "resolved")
        self.assertEqual(component["ageSeconds"], 3_600)
        pending = next(row for row in result["items"] if row["itemId"] == 9_800_003)
        self.assertEqual((pending["locationStatus"], pending["locationPath"]), ("pending", ""))

    def test_search_owner_and_location_filters_compose(self) -> None:
        snapshot = self.publish_assets(
            CHARACTER_ID,
            [asset(9_800_011), asset(9_800_012, SECOND_TYPE_ID)],
            "2026-09-10T10:00:00Z",
        )
        self.publish_locations(
            CHARACTER_ID,
            snapshot,
            [
                self.resolved_location(9_800_011),
                self.resolved_location(9_800_012, "restricted"),
            ],
            "2026-09-10T10:01:00Z",
        )

        result = query_assets(
            self.database,
            AssetQuery("formula station", CHARACTER_ID, "restricted"),
            now=datetime(2026, 9, 10, 11, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["itemId"], 9_800_012)
        self.assertEqual(result["items"][0]["locationStatus"], "restricted")

    def test_sorting_is_applied_before_the_bounded_page(self) -> None:
        self.publish_assets(
            CHARACTER_ID,
            [
                asset(9_800_101, quantity=9),
                asset(9_800_102, SECOND_TYPE_ID, 2),
                asset(9_800_103, quantity=5),
            ],
            "2026-09-10T10:00:00Z",
        )

        ascending = query_assets(
            self.database,
            AssetQuery(offset=0, limit=2, sort_by="quantity", sort_direction="asc"),
        )
        descending = query_assets(
            self.database,
            AssetQuery(offset=0, limit=2, sort_by="quantity", sort_direction="desc"),
        )

        self.assertEqual([2, 5], [row["quantity"] for row in ascending["items"]])
        self.assertEqual([9, 5], [row["quantity"] for row in descending["items"]])
        with self.assertRaisesRegex(AssetViewError, "asset_query_invalid"):
            validate_asset_query(sort_by="unknown")

    def test_new_asset_snapshot_never_uses_paths_from_an_older_snapshot(self) -> None:
        old = self.publish_assets(
            CHARACTER_ID,
            [asset(9_800_021)],
            "2026-09-10T09:00:00Z",
        )
        self.publish_locations(
            CHARACTER_ID,
            old,
            [self.resolved_location(9_800_021)],
            "2026-09-10T09:01:00Z",
        )
        self.publish_assets(
            CHARACTER_ID,
            [asset(9_800_022)],
            "2026-09-10T10:00:00Z",
        )

        result = query_assets(self.database, AssetQuery())

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["itemId"], 9_800_022)
        self.assertEqual(result["items"][0]["locationStatus"], "pending")

    def test_matching_location_snapshot_must_cover_exactly_the_asset_snapshot(self) -> None:
        snapshot = self.publish_assets(
            CHARACTER_ID,
            [asset(9_800_025), asset(9_800_026)],
            "2026-09-10T10:00:00Z",
        )
        self.publish_locations(
            CHARACTER_ID,
            snapshot,
            [self.resolved_location(9_800_025)],
            "2026-09-10T10:01:00Z",
        )

        with self.assertRaisesRegex(AssetViewError, "asset_location_snapshot_invalid"):
            query_assets(self.database, AssetQuery())

    def test_one_hundred_thousand_rows_return_only_the_bounded_window(self) -> None:
        self.publish_assets(
            CHARACTER_ID,
            [asset(10_000_000 + index, quantity=index % 13) for index in range(100_000)],
            "2026-09-10T10:00:00Z",
        )

        result = query_assets(
            self.database,
            AssetQuery(offset=99_900, limit=100),
            now=datetime(2026, 9, 10, 11, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(result["total"], 100_000)
        self.assertEqual(len(result["items"]), 100)
        self.assertEqual(result["offset"], 99_900)
        self.assertLess(len(json.dumps(result)), 100_000)
        with self.assertRaisesRegex(AssetViewError, "asset_query_invalid"):
            validate_asset_query(limit=201)

    def test_csv_export_is_filtered_atomic_and_formula_safe(self) -> None:
        snapshot = self.publish_assets(
            CHARACTER_ID,
            [asset(9_800_031, SECOND_TYPE_ID, 8), asset(9_800_032, TYPE_ID, 3)],
            "2026-09-10T10:00:00Z",
        )
        self.publish_locations(
            CHARACTER_ID,
            snapshot,
            [self.resolved_location(9_800_031), self.resolved_location(9_800_032)],
            "2026-09-10T10:01:00Z",
        )
        export_directory = self.root / "data" / "exports"

        exported = export_assets_csv(
            self.database,
            AssetQuery(search="formula"),
            export_directory,
            now=datetime(2026, 9, 10, 11, 2, 3, tzinfo=timezone.utc),
        )

        self.assertEqual(exported.rows, 1)
        self.assertEqual(exported.filename, "assets-20260910-110203.csv")
        self.assertEqual(exported.relative_path, "data/exports/assets-20260910-110203.csv")
        self.assertEqual(list(export_directory.glob(".*.tmp")), [])
        with (export_directory / exported.filename).open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows[0]["type_name"], "'=Formula Material")
        self.assertEqual(rows[0]["quantity"], "8")

    def test_invalid_query_and_corrupt_complete_snapshot_fail_closed(self) -> None:
        with self.assertRaisesRegex(AssetViewError, "asset_query_invalid"):
            validate_asset_query(search="x" * 121)
        with self.assertRaisesRegex(AssetViewError, "asset_query_invalid"):
            validate_asset_query(location_status="secret")
        self.publish_assets(
            CHARACTER_ID,
            [{"item_id": True}],
            "2026-09-10T10:00:00Z",
        )
        with self.assertRaisesRegex(AssetViewError, "asset_snapshot_invalid"):
            query_assets(self.database, AssetQuery())


if __name__ == "__main__":
    unittest.main()
