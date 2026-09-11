from pathlib import Path
import tempfile
import unittest

from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.production_planning import (
    ProductionPlanningError,
    delete_production_plan,
    query_production_catalog,
    query_production_plans,
    resolve_production_plan,
    save_production_plan,
    validate_production_plan_input,
    validate_production_plan_query,
)
from new_eden_foundry_backend.sde import import_industry_sde


def bundle() -> dict:
    return {
        "build_number": "synthetic-production-1",
        "groups": [{"group_id": 1, "name": "Synthetic production"}],
        "types": [
            {"type_id": 100, "group_id": 1, "name": "Synthetic Hull Blueprint"},
            {"type_id": 101, "group_id": 1, "name": "Synthetic Hull"},
            {"type_id": 110, "group_id": 1, "name": "Synthetic Frame Blueprint"},
            {"type_id": 111, "group_id": 1, "name": "Synthetic Frame"},
            {"type_id": 120, "group_id": 1, "name": "Synthetic Plate Blueprint"},
            {"type_id": 121, "group_id": 1, "name": "Synthetic Plate"},
            {"type_id": 130, "group_id": 1, "name": "Synthetic Alternate Plate Blueprint"},
            {"type_id": 200, "group_id": 1, "name": "Synthetic Reaction Formula"},
            {"type_id": 201, "group_id": 1, "name": "Synthetic Composite"},
            {"type_id": 900, "group_id": 1, "name": "Synthetic Mineral"},
            {"type_id": 901, "group_id": 1, "name": "Synthetic Gas"},
        ],
        "locations": [
            {"location_id": 30000142, "name": "Synthetic System", "kind": "solar_system"}
        ],
        "blueprint_activities": [
            {
                "blueprint_type_id": 100,
                "activity": "manufacturing",
                "time_seconds": 100,
                "products": [{"type_id": 101, "quantity": 2}],
                "materials": [
                    {"type_id": 111, "quantity": 3},
                    {"type_id": 121, "quantity": 4},
                ],
            },
            {
                "blueprint_type_id": 110,
                "activity": "manufacturing",
                "time_seconds": 20,
                "products": [{"type_id": 111, "quantity": 2}],
                "materials": [
                    {"type_id": 121, "quantity": 5},
                    {"type_id": 900, "quantity": 7},
                ],
            },
            {
                "blueprint_type_id": 120,
                "activity": "manufacturing",
                "time_seconds": 10,
                "products": [{"type_id": 121, "quantity": 10}],
                "materials": [{"type_id": 900, "quantity": 2}],
            },
            {
                "blueprint_type_id": 130,
                "activity": "manufacturing",
                "time_seconds": 30,
                "products": [{"type_id": 121, "quantity": 20}],
                "materials": [{"type_id": 900, "quantity": 3}],
            },
            {
                "blueprint_type_id": 200,
                "activity": "reaction",
                "time_seconds": 60,
                "products": [{"type_id": 201, "quantity": 200}],
                "materials": [{"type_id": 901, "quantity": 100}],
            },
        ],
    }


def query(**changes: object) -> dict:
    result = {
        "search": "",
        "ownerCharacterId": None,
        "activity": None,
        "state": None,
        "offset": 0,
        "limit": 50,
        "sortBy": "priority",
        "sortDirection": "desc",
    }
    result.update(changes)
    return result


def plan_input(**changes: object) -> dict:
    result = {
        "planId": None,
        "ownerCharacterId": 7,
        "blueprintTypeId": 100,
        "activity": "manufacturing",
        "productTypeId": 101,
        "targetQuantity": 3,
        "priority": 12,
        "note": "  main   goal  ",
    }
    result.update(changes)
    return result


class ProductionPlanningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        path = Path(self.temp.name) / "foundry.db"
        initialize_database(path)
        self.db = connect_database(path)
        self.db.execute("INSERT INTO characters(character_id,name) VALUES (7,'Synthetic Pilot')")

    def tearDown(self) -> None:
        self.db.close()
        self.temp.cleanup()

    def test_goal_persists_and_expands_shared_inputs_after_rounding(self) -> None:
        import_industry_sde(self.db, **bundle())
        saved = save_production_plan(self.db, plan_input())
        page = query_production_plans(self.db, query())

        self.assertTrue(saved["saved"])
        self.assertEqual(saved["note"], "main goal")
        self.assertEqual(page["buildNumber"], "synthetic-production-1")
        self.assertFalse(page["inventoryApplied"])
        self.assertFalse(page["modifiersApplied"])
        self.assertEqual(page["summary"]["ready"], 1)
        record = page["items"][0]
        self.assertEqual(record["state"], "ready")
        self.assertEqual(
            [(step["productTypeId"], step["requiredQuantity"], step["runs"], step["producedQuantity"])
             for step in record["steps"]],
            [(121, 23, 3, 30), (111, 6, 3, 6), (101, 3, 2, 4)],
        )
        self.assertEqual(record["grossMaterials"], [
            {"typeId": 900, "typeName": "Synthetic Mineral", "quantity": 27}
        ])
        self.assertEqual(record["totalBaseTimeSeconds"], 290)
        self.assertEqual(record["warnings"], [{
            "code": "alternative-recipe",
            "typeId": 121,
            "typeName": "Synthetic Plate",
            "selectedBlueprintTypeId": 120,
            "candidateCount": 2,
        }])

    def test_reaction_catalog_query_and_plan_update_are_bounded(self) -> None:
        import_industry_sde(self.db, **bundle())
        catalog = query_production_catalog(
            self.db,
            {"search": "composite", "activity": "reaction", "offset": 0, "limit": 10},
        )
        self.assertEqual(catalog["total"], 1)
        self.assertEqual(catalog["items"][0]["productTypeId"], 201)
        saved = save_production_plan(
            self.db,
            plan_input(
                blueprintTypeId=200,
                activity="reaction",
                productTypeId=201,
                targetQuantity=201,
            ),
        )
        updated = save_production_plan(
            self.db,
            plan_input(
                planId=saved["planId"],
                blueprintTypeId=200,
                activity="reaction",
                productTypeId=201,
                targetQuantity=400,
                priority=99,
                note=None,
            ),
        )
        self.assertEqual(updated["planId"], saved["planId"])
        record = query_production_plans(
            self.db, query(activity="reaction", search="pilot")
        )["items"][0]
        self.assertEqual(record["steps"][0]["runs"], 2)
        self.assertEqual(record["grossMaterials"][0]["quantity"], 200)

    def test_plans_survive_sde_removal_and_expose_missing_source(self) -> None:
        import_industry_sde(self.db, **bundle())
        save_production_plan(self.db, plan_input())
        self.db.execute("DELETE FROM app_metadata WHERE key='sde_blueprint_activity_build_number'")
        page = query_production_plans(self.db, query(state="sde-unavailable"))
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["items"][0]["state"], "sde-unavailable")
        self.assertEqual(page["items"][0]["steps"], [])

    def test_cycle_is_detected_and_cannot_be_persisted(self) -> None:
        cyclic = bundle()
        cyclic["blueprint_activities"][2]["materials"] = [{"type_id": 111, "quantity": 1}]
        import_industry_sde(self.db, **cyclic)
        resolution = resolve_production_plan(self.db, {
            "blueprint_type_id": 100,
            "activity": "manufacturing",
            "product_type_id": 101,
            "target_quantity": 1,
        })
        self.assertEqual(resolution["state"], "cycle")
        self.assertEqual(resolution["cycleTypeIds"], [111, 121])
        with self.assertRaisesRegex(ProductionPlanningError, "production_plan_cycle"):
            save_production_plan(self.db, plan_input())

    def test_invalid_contracts_missing_recipe_and_delete_are_fail_closed(self) -> None:
        invalid_queries = [
            {},
            query(limit=101),
            query(state="invented"),
            query(sortBy="quantity"),
            query(ownerCharacterId=True),
        ]
        for payload in invalid_queries:
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ProductionPlanningError, "production_plan_query_invalid"):
                    validate_production_plan_query(payload)
        with self.assertRaisesRegex(ProductionPlanningError, "production_plan_input_invalid"):
            validate_production_plan_input(plan_input(targetQuantity=0))
        with self.assertRaisesRegex(ProductionPlanningError, "production_sde_unavailable"):
            save_production_plan(self.db, plan_input())
        import_industry_sde(self.db, **bundle())
        with self.assertRaisesRegex(ProductionPlanningError, "production_recipe_missing"):
            save_production_plan(self.db, plan_input(productTypeId=900))
        saved = save_production_plan(self.db, plan_input())
        self.assertEqual(delete_production_plan(self.db, {"planId": saved["planId"]}), {
            "deleted": True, "planId": saved["planId"]
        })
        with self.assertRaisesRegex(ProductionPlanningError, "production_plan_missing"):
            delete_production_plan(self.db, {"planId": saved["planId"]})


if __name__ == "__main__":
    unittest.main()
