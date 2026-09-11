from pathlib import Path
import tempfile
import unittest

from new_eden_foundry_backend.database import SCHEMA_VERSION, connect_database, initialize_database
from new_eden_foundry_backend.sde import (
    SdeImportError,
    SdeQueryError,
    current_sde_blueprint_activity_build,
    current_sde_build,
    import_industry_sde,
    import_minimal_sde,
    query_blueprint_activities,
    validate_blueprint_activity_query,
)


def synthetic_industry_bundle(*, build_number: str = "synthetic-sde-2026-09-11.1") -> dict:
    return {
        "build_number": build_number,
        "groups": [{"group_id": 1, "name": "Synthetic industry types"}],
        "types": [
            {"type_id": 100, "group_id": 1, "name": "Synthetic Rifter Blueprint"},
            {"type_id": 101, "group_id": 1, "name": "Synthetic Rifter"},
            {"type_id": 102, "group_id": 1, "name": "Synthetic Tritanium"},
            {"type_id": 103, "group_id": 1, "name": "Synthetic Pyerite"},
            {"type_id": 200, "group_id": 1, "name": "Synthetic Reaction Formula"},
            {"type_id": 201, "group_id": 1, "name": "Synthetic Composite"},
            {"type_id": 202, "group_id": 1, "name": "Synthetic Gas"},
        ],
        "locations": [
            {"location_id": 30000142, "name": "Synthetic Jita", "kind": "solar_system",
             "security_status": 0.9}
        ],
        "blueprint_activities": [
            {
                "blueprint_type_id": 100,
                "activity": "manufacturing",
                "time_seconds": 6_000,
                "products": [{"type_id": 101, "quantity": 1}],
                "materials": [
                    {"type_id": 102, "quantity": 2_850},
                    {"type_id": 103, "quantity": 650},
                ],
            },
            {
                "blueprint_type_id": 200,
                "activity": "reaction",
                "time_seconds": 10_800,
                "products": [{"type_id": 201, "quantity": 200}],
                "materials": [{"type_id": 202, "quantity": 100}],
            },
        ],
    }


def query_payload(**changes: object) -> dict:
    payload = {
        "blueprintTypeIds": [],
        "productTypeIds": [],
        "activities": [],
        "offset": 0,
        "limit": 100,
    }
    payload.update(changes)
    return payload


class SdeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "foundry.db"
        initialize_database(self.path)
        self.db = connect_database(self.path)

    def tearDown(self) -> None:
        self.db.close()
        self.temp.cleanup()

    def test_minimal_import_remains_rebuildable_without_app_migration(self) -> None:
        self.assertEqual(SCHEMA_VERSION, 9)
        result = import_minimal_sde(
            self.db,
            build_number="synthetic-sde-minimal-1",
            groups=[{"group_id": 25, "name": "Synthetic Frigate"}],
            types=[{"type_id": 587, "group_id": 25, "name": "Synthetic Rifter"}],
            locations=[
                {"location_id": 30000142, "name": "Synthetic Jita", "kind": "solar_system"}
            ],
        )
        names = {
            row[0]
            for row in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        self.assertTrue(
            {
                "sde_groups",
                "sde_types",
                "sde_locations",
                "sde_blueprint_activities",
                "sde_blueprint_products",
                "sde_blueprint_materials",
            }
            <= names
        )
        self.assertEqual(result.blueprint_activities, 0)
        self.assertIsNone(current_sde_blueprint_activity_build(self.db))
        self.assertEqual(self.db.execute("PRAGMA user_version").fetchone()[0], SCHEMA_VERSION)

    def test_industry_import_and_query_preserve_exact_sde_values(self) -> None:
        bundle = synthetic_industry_bundle()
        result = import_industry_sde(self.db, **bundle)

        self.assertEqual(result.blueprint_activities, 2)
        self.assertEqual(result.products, 2)
        self.assertEqual(result.materials, 3)
        self.assertEqual(current_sde_build(self.db), bundle["build_number"])
        self.assertEqual(
            current_sde_blueprint_activity_build(self.db), bundle["build_number"]
        )
        self.assertEqual(
            self.db.execute(
                "SELECT security_status FROM sde_locations WHERE location_id=30000142"
            ).fetchone()[0],
            0.9,
        )

        page = query_blueprint_activities(
            self.db,
            query_payload(productTypeIds=[101], activities=["manufacturing"]),
        )
        self.assertEqual(page["buildNumber"], bundle["build_number"])
        self.assertEqual(page["total"], 1)
        self.assertEqual(
            page["items"],
            [
                {
                    "blueprintTypeId": 100,
                    "blueprintName": "Synthetic Rifter Blueprint",
                    "activity": "manufacturing",
                    "baseTimeSeconds": 6_000,
                    "products": [
                        {"typeId": 101, "typeName": "Synthetic Rifter", "quantity": 1}
                    ],
                    "materials": [
                        {
                            "typeId": 103,
                            "typeName": "Synthetic Pyerite",
                            "quantity": 650,
                        },
                        {
                            "typeId": 102,
                            "typeName": "Synthetic Tritanium",
                            "quantity": 2_850,
                        },
                    ],
                }
            ],
        )

    def test_invalid_activity_cannot_replace_previous_build(self) -> None:
        first = synthetic_industry_bundle()
        import_industry_sde(self.db, **first)
        broken = synthetic_industry_bundle(build_number="synthetic-sde-broken")
        broken["blueprint_activities"][0]["materials"][0]["type_id"] = 999_999

        with self.assertRaisesRegex(SdeImportError, "unknown_material_type"):
            import_industry_sde(self.db, **broken)

        self.assertEqual(current_sde_build(self.db), first["build_number"])
        self.assertEqual(
            current_sde_blueprint_activity_build(self.db), first["build_number"]
        )
        self.assertEqual(
            self.db.execute(
                "SELECT time_seconds FROM sde_blueprint_activities "
                "WHERE blueprint_type_id=100 AND activity='manufacturing'"
            ).fetchone()[0],
            6_000,
        )

    def test_invalid_security_status_cannot_replace_previous_build(self) -> None:
        first = synthetic_industry_bundle()
        import_industry_sde(self.db, **first)
        broken = synthetic_industry_bundle(build_number="synthetic-sde-broken-security")
        broken["locations"][0]["security_status"] = 1.5

        with self.assertRaisesRegex(SdeImportError, "invalid_location_security_status"):
            import_industry_sde(self.db, **broken)

        self.assertEqual(current_sde_build(self.db), first["build_number"])
        self.assertEqual(
            self.db.execute(
                "SELECT security_status FROM sde_locations WHERE location_id=30000142"
            ).fetchone()[0],
            0.9,
        )

    def test_database_failure_rolls_back_reference_and_activity_tables(self) -> None:
        first = synthetic_industry_bundle()
        import_industry_sde(self.db, **first)
        self.db.execute(
            "CREATE TRIGGER synthetic_abort_activity BEFORE INSERT ON sde_blueprint_activities "
            "WHEN NEW.blueprint_type_id=100 BEGIN SELECT RAISE(ABORT,'synthetic failure'); END"
        )
        self.db.commit()
        replacement = synthetic_industry_bundle(build_number="synthetic-sde-replacement")
        replacement["types"][0]["name"] = "Replacement Blueprint"
        replacement["blueprint_activities"][0]["time_seconds"] = 7_200

        with self.assertRaisesRegex(SdeImportError, "atomic_sde_import_failed"):
            import_industry_sde(self.db, **replacement)

        self.assertEqual(current_sde_build(self.db), first["build_number"])
        self.assertEqual(
            self.db.execute("SELECT name FROM sde_types WHERE type_id=100").fetchone()[0],
            "Synthetic Rifter Blueprint",
        )
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM sde_blueprint_materials").fetchone()[0],
            3,
        )

    def test_minimal_reimport_clears_activity_data_and_its_build_marker(self) -> None:
        import_industry_sde(self.db, **synthetic_industry_bundle())
        import_minimal_sde(
            self.db,
            build_number="synthetic-sde-minimal-2",
            groups=[{"group_id": 25, "name": "Synthetic Frigate"}],
            types=[{"type_id": 587, "group_id": 25, "name": "Synthetic Rifter"}],
            locations=[
                {"location_id": 30000142, "name": "Synthetic Jita", "kind": "solar_system"}
            ],
        )
        self.assertEqual(current_sde_build(self.db), "synthetic-sde-minimal-2")
        self.assertIsNone(current_sde_blueprint_activity_build(self.db))
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM sde_blueprint_activities").fetchone()[0], 0
        )
        self.assertIsNone(query_blueprint_activities(self.db, query_payload())["buildNumber"])

    def test_activity_contract_rejects_unsupported_empty_and_duplicate_values(self) -> None:
        unsupported = synthetic_industry_bundle()
        unsupported["blueprint_activities"][0]["activity"] = "invention"
        empty = synthetic_industry_bundle()
        empty["blueprint_activities"][0]["products"] = []
        duplicate = synthetic_industry_bundle()
        duplicate["blueprint_activities"][0]["materials"].append(
            {"type_id": 102, "quantity": 1}
        )
        cases = [
            (unsupported, "unsupported_blueprint_activity"),
            (empty, "blueprint_activity_must_have_products_and_materials"),
            (duplicate, "duplicate_blueprint_material"),
        ]

        for bundle, error_code in cases:
            with self.subTest(error_code=error_code):
                with self.assertRaisesRegex(SdeImportError, error_code):
                    import_industry_sde(self.db, **bundle)
        self.assertIsNone(current_sde_build(self.db))

    def test_query_validation_is_strict_and_bounded(self) -> None:
        invalid = [
            {},
            query_payload(limit=201),
            query_payload(offset=-1),
            query_payload(activities=["copying"]),
            query_payload(activities=["reaction", "reaction"]),
            query_payload(productTypeIds=[101, 101]),
            query_payload(blueprintTypeIds=[True]),
        ]
        for payload in invalid:
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(
                    SdeQueryError, "sde_blueprint_activity_query_invalid"
                ):
                    validate_blueprint_activity_query(payload)

    def test_query_never_transfers_more_than_two_hundred_activities(self) -> None:
        bundle = synthetic_industry_bundle()
        bundle["types"] = [
            {"type_id": 1, "group_id": 1, "name": "Synthetic common product"},
            {"type_id": 2, "group_id": 1, "name": "Synthetic common material"},
            *[
                {
                    "type_id": 1_000 + index,
                    "group_id": 1,
                    "name": f"Synthetic Blueprint {index:03d}",
                }
                for index in range(205)
            ],
        ]
        bundle["blueprint_activities"] = [
            {
                "blueprint_type_id": 1_000 + index,
                "activity": "manufacturing",
                "time_seconds": 60 + index,
                "products": [{"type_id": 1, "quantity": 1}],
                "materials": [{"type_id": 2, "quantity": index + 1}],
            }
            for index in range(205)
        ]
        import_industry_sde(self.db, **bundle)

        page = query_blueprint_activities(self.db, query_payload(limit=200))
        self.assertEqual(page["total"], 205)
        self.assertEqual(len(page["items"]), 200)


if __name__ == "__main__":
    unittest.main()
