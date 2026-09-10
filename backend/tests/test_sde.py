from pathlib import Path
import tempfile
import unittest

from new_eden_foundry_backend.database import connect_database, initialize_database, SCHEMA_VERSION
from new_eden_foundry_backend.sde import import_minimal_sde, current_sde_build, SdeImportError


class MinimalSdeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "foundry.db"
        initialize_database(self.path)
        self.db = connect_database(self.path)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_import_bootstraps_derived_tables_without_app_migration(self):
        self.assertEqual(SCHEMA_VERSION, 7)
        import_minimal_sde(
            self.db,
            build_number="sde-2026-09-10.1",
            groups=[{"group_id": 25, "name": "Frigate"}],
            types=[{"type_id": 587, "group_id": 25, "name": "Rifter"}],
            locations=[{"location_id": 30000142, "name": "Jita", "kind": "solar_system"}],
        )
        names = {r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"sde_groups", "sde_types", "sde_locations"} <= names)

    def test_import_replaces_build_atomically(self):
        result = import_minimal_sde(
            self.db,
            build_number="sde-2026-09-10.1",
            groups=[{"group_id": 25, "name": "Frigate"}],
            types=[{"type_id": 587, "group_id": 25, "name": "Rifter"}],
            locations=[{"location_id": 30000142, "name": "Jita", "kind": "solar_system"}],
        )
        self.assertEqual(result.types, 1)
        self.assertEqual(current_sde_build(self.db), "sde-2026-09-10.1")
        self.assertEqual(self.db.execute("SELECT name FROM sde_types").fetchone()[0], "Rifter")

        with self.assertRaises(SdeImportError):
            import_minimal_sde(
                self.db,
                build_number="broken",
                groups=[{"group_id": 26, "name": "Cruiser"}],
                types=[{"type_id": 621, "group_id": 999, "name": "Caracal"}],
                locations=[{"location_id": 30000142, "name": "Jita", "kind": "solar_system"}],
            )
        self.assertEqual(current_sde_build(self.db), "sde-2026-09-10.1")
        self.assertEqual(self.db.execute("SELECT name FROM sde_types").fetchone()[0], "Rifter")


if __name__ == "__main__":
    unittest.main()
