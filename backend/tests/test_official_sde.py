from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.official_sde import install_bundled_industry_sde


class OfficialSdeTests(unittest.TestCase):
    def test_bundled_subset_installs_once_and_populates_production_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database_path = root / "foundry.sqlite3"
            resource_path = root / "official-industry-sde.json.gz"
            initialize_database(database_path)
            payload = {
                "build_number": "official-test-1",
                "groups": [{"group_id": 1, "name": "Blueprint group"}],
                "types": [
                    {"type_id": 10, "group_id": 1, "name": "Test Blueprint"},
                    {"type_id": 11, "group_id": 1, "name": "Test Product"},
                    {"type_id": 12, "group_id": 1, "name": "Test Material"},
                ],
                "locations": [
                    {"location_id": 30, "parent_location_id": None, "name": "Test Region", "kind": "region"}
                ],
                "blueprint_activities": [
                    {
                        "blueprint_type_id": 10,
                        "activity": "manufacturing",
                        "time_seconds": 60,
                        "products": [{"type_id": 11, "quantity": 1}],
                        "materials": [{"type_id": 12, "quantity": 2}],
                    }
                ],
            }
            with gzip.open(resource_path, "wt", encoding="utf-8") as stream:
                json.dump(payload, stream)
            connection = connect_database(database_path)
            try:
                result = install_bundled_industry_sde(connection, resource_path)
                self.assertIsNotNone(result)
                self.assertEqual(result.build_number, "official-test-1")
                self.assertEqual(result.blueprint_activities, 1)
                self.assertIsNone(install_bundled_industry_sde(connection, resource_path))
                self.assertEqual(
                    connection.execute("SELECT count(*) FROM sde_blueprint_products").fetchone()[0],
                    1,
                )
            finally:
                connection.close()

    def test_same_build_refreshes_new_security_data_without_touching_user_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database_path = root / "foundry.sqlite3"
            resource_path = root / "official-industry-sde.json.gz"
            initialize_database(database_path)
            payload = {
                "build_number": "official-test-security",
                "groups": [{"group_id": 1, "name": "Blueprint group"}],
                "types": [
                    {"type_id": 10, "group_id": 1, "name": "Test Blueprint"},
                    {"type_id": 11, "group_id": 1, "name": "Test Product"},
                    {"type_id": 12, "group_id": 1, "name": "Test Material"},
                ],
                "locations": [
                    {
                        "location_id": 30,
                        "parent_location_id": None,
                        "name": "Test System",
                        "kind": "solar_system",
                    }
                ],
                "blueprint_activities": [
                    {
                        "blueprint_type_id": 10,
                        "activity": "manufacturing",
                        "time_seconds": 60,
                        "products": [{"type_id": 11, "quantity": 1}],
                        "materials": [{"type_id": 12, "quantity": 2}],
                    }
                ],
            }
            with gzip.open(resource_path, "wt", encoding="utf-8") as stream:
                json.dump(payload, stream)
            connection = connect_database(database_path)
            try:
                connection.execute(
                    "INSERT INTO characters(character_id,name) VALUES(90000001,'Existing Pilot')"
                )
                first = install_bundled_industry_sde(connection, resource_path)
                self.assertIsNotNone(first)
                connection.execute(
                    "INSERT INTO production_plans(owner_character_id,blueprint_type_id,activity,"
                    "product_type_id,target_quantity,priority,note) "
                    "VALUES(90000001,10,'manufacturing',11,3,50,'Existing plan')"
                )
                self.assertIsNone(
                    connection.execute(
                        "SELECT security_status FROM sde_locations WHERE location_id=30"
                    ).fetchone()[0]
                )

                payload["locations"][0]["security_status"] = 0.9
                with gzip.open(resource_path, "wt", encoding="utf-8") as stream:
                    json.dump(payload, stream)
                refreshed = install_bundled_industry_sde(connection, resource_path)

                self.assertIsNotNone(refreshed)
                self.assertEqual(refreshed.build_number, "official-test-security")
                self.assertEqual(
                    connection.execute(
                        "SELECT security_status FROM sde_locations WHERE location_id=30"
                    ).fetchone()[0],
                    0.9,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT name FROM characters WHERE character_id=90000001"
                    ).fetchone()[0],
                    "Existing Pilot",
                )
                plan = connection.execute(
                    "SELECT target_quantity,note FROM production_plans"
                ).fetchone()
                self.assertEqual((plan[0], plan[1]), (3, "Existing plan"))
                self.assertIsNone(install_bundled_industry_sde(connection, resource_path))
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
