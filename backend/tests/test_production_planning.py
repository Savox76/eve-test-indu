from pathlib import Path
import json
import tempfile
import unittest
from datetime import datetime, timezone

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
        "marketHubId": "jita",
        "tradeCostMode": "manual",
        "salesCharacterId": None,
        "brokerFeeBasisPoints": None,
        "salesTaxBasisPoints": None,
        "analysisPlanId": 1,
        "includeBlueprintProfitability": False,
    }
    result.update(changes)
    return result


def plan_input(**changes: object) -> dict:
    result = {
        "planId": None,
        "ownerCharacterId": 7,
        "blueprintTypeId": 100,
        "blueprintItemId": None,
        "stepBlueprintAssignments": [],
        "facilityId": None,
        "materialLocationId": None,
        "facilityMaterialBonusBasisPoints": None,
        "facilityTimeBonusBasisPoints": None,
        "facilityTaxBasisPoints": None,
        "stepSupplyModes": [],
        "activity": "manufacturing",
        "productTypeId": 101,
        "targetQuantity": 3,
        "priority": 12,
        "note": "  main   goal  ",
    }
    result.update(changes)
    return result


def industry_job(**changes: object) -> dict:
    result = {
        "activity_id": 1,
        "blueprint_id": 8_001,
        "blueprint_location_id": 60_003_760,
        "blueprint_type_id": 100,
        "completed_character_id": None,
        "completed_date": None,
        "cost": 1_234.5,
        "duration": 1_000,
        "end_date": "2026-09-14T14:30:00Z",
        "facility_id": 60_003_760,
        "installer_id": 7,
        "job_id": 9_001,
        "licensed_runs": 0,
        "output_location_id": 60_003_760,
        "pause_date": None,
        "probability": 1.0,
        "product_type_id": 101,
        "runs": 2,
        "start_date": "2026-09-14T14:00:00Z",
        "station_id": 60_003_760,
        "status": "active",
        "successful_runs": None,
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

    def publish_assets(
        self,
        character_id: int,
        assets: list[dict[str, object]],
        observed_at: str,
        *,
        status: str = "completed",
    ) -> tuple[int, int]:
        run = self.db.execute(
            "INSERT INTO sync_runs(source,status,started_at,completed_at,data_timestamp,"
            "character_id) VALUES('character_assets',?,?,?,?,?)",
            (status, observed_at, observed_at, observed_at, character_id),
        )
        snapshot = self.db.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (
                int(run.lastrowid),
                f"character_assets:{character_id}",
                json.dumps({"characterId": character_id, "pages": 1, "assets": assets}),
                observed_at,
            ),
        )
        return int(snapshot.lastrowid), int(run.lastrowid)

    def publish_blueprints(
        self,
        character_id: int,
        blueprints: list[dict[str, object]],
        observed_at: str,
        *,
        status: str = "completed",
    ) -> tuple[int, int]:
        run = self.db.execute(
            "INSERT INTO sync_runs(source,status,started_at,completed_at,data_timestamp,"
            "character_id) VALUES('character_blueprints',?,?,?,?,?)",
            (status, observed_at, observed_at, observed_at, character_id),
        )
        snapshot = self.db.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (
                int(run.lastrowid),
                f"character_blueprints:{character_id}",
                json.dumps(
                    {
                        "characterId": character_id,
                        "pages": 1,
                        "blueprints": blueprints,
                    }
                ),
                observed_at,
            ),
        )
        return int(snapshot.lastrowid), int(run.lastrowid)

    def publish_skills(
        self,
        character_id: int,
        levels: dict[int, int],
        observed_at: str,
        *,
        status: str = "completed",
    ) -> tuple[int, int]:
        run = self.db.execute(
            "INSERT INTO sync_runs(source,status,started_at,completed_at,data_timestamp,"
            "character_id) VALUES('character_skills',?,?,?,?,?)",
            (status, observed_at, observed_at, observed_at, character_id),
        )
        skills = [
            {
                "active_skill_level": level,
                "skill_id": skill_id,
                "skillpoints_in_skill": (index + 1) * 1_000,
                "trained_skill_level": level,
            }
            for index, (skill_id, level) in enumerate(sorted(levels.items()))
        ]
        snapshot = self.db.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (
                int(run.lastrowid),
                f"character_skills:{character_id}",
                json.dumps(
                    {
                        "characterId": character_id,
                        "skills": skills,
                        "total_sp": sum(
                            int(skill["skillpoints_in_skill"]) for skill in skills
                        ),
                        "unallocated_sp": 0,
                    }
                ),
                observed_at,
            ),
        )
        return int(snapshot.lastrowid), int(run.lastrowid)

    def publish_standings(
        self,
        character_id: int,
        standings: list[dict[str, object]],
        observed_at: str,
    ) -> tuple[int, int]:
        run = self.db.execute(
            "INSERT INTO sync_runs(source,status,started_at,completed_at,data_timestamp,"
            "character_id) VALUES('character_standings','completed',?,?,?,?)",
            (observed_at, observed_at, observed_at, character_id),
        )
        snapshot = self.db.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (
                int(run.lastrowid),
                f"character_standings:{character_id}",
                json.dumps({"characterId": character_id, "standings": standings}),
                observed_at,
            ),
        )
        return int(snapshot.lastrowid), int(run.lastrowid)

    def publish_jobs(
        self,
        character_id: int,
        jobs: list[dict[str, object]],
        observed_at: str,
    ) -> tuple[int, int]:
        run = self.db.execute(
            "INSERT INTO sync_runs(source,status,started_at,completed_at,data_timestamp,"
            "character_id) VALUES('character_industry_jobs','completed',?,?,?,?)",
            (observed_at, observed_at, observed_at, character_id),
        )
        snapshot = self.db.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (
                int(run.lastrowid),
                f"character_industry_jobs:{character_id}",
                json.dumps(
                    {
                        "characterId": character_id,
                        "includeCompleted": True,
                        "jobs": jobs,
                    }
                ),
                observed_at,
            ),
        )
        return int(snapshot.lastrowid), int(run.lastrowid)

    def publish_facilities(self, observed_at: str) -> tuple[int, int]:
        run = self.db.execute(
            "INSERT INTO sync_runs(source,status,started_at,completed_at,data_timestamp) "
            "VALUES('industry_facilities','completed',?,?,?)",
            (observed_at, observed_at, observed_at),
        )
        snapshot = self.db.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,'industry_facilities',?,?)",
            (
                int(run.lastrowid),
                json.dumps(
                    {
                        "facilities": [
                            {
                                "facility_id": 60_003_760,
                                "owner_id": 1_000_001,
                                "region_id": 10_000_002,
                                "solar_system_id": 30_000_142,
                                "tax": None,
                                "type_id": 1_928,
                            }
                        ],
                        "names": [
                            {"category": "corporation", "id": 1_000_001, "name": "Synthetic Owner"},
                            {"category": "inventory_type", "id": 1_928, "name": "Synthetic Factory"},
                            {"category": "region", "id": 10_000_002, "name": "Synthetic Region"},
                            {"category": "solar_system", "id": 30_000_142, "name": "Synthetic System"},
                            {"category": "station", "id": 60_003_760, "name": "Synthetic Station"},
                        ],
                        "structures": [],
                        "prices": [
                            {"type_id": 111, "adjusted_price": 100.0, "average_price": 105.0},
                            {"type_id": 121, "adjusted_price": 20.0, "average_price": 22.0},
                            {"type_id": 900, "adjusted_price": 10.0, "average_price": 12.0},
                            {"type_id": 901, "adjusted_price": 2.0, "average_price": 2.5},
                        ],
                        "systems": [
                            {
                                "solar_system_id": 30_000_142,
                                "cost_indices": [
                                    {"activity": "manufacturing", "cost_index": 0.0125},
                                    {"activity": "reaction", "cost_index": 0.0042},
                                ],
                            }
                        ],
                    }
                ),
                observed_at,
            ),
        )
        return int(snapshot.lastrowid), int(run.lastrowid)

    def publish_market_prices(
        self,
        orders: list[dict[str, int]],
        requested_type_ids: list[int],
        *,
        hub_id: str = "jita",
    ) -> tuple[int, int]:
        observed_at = (
            datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
        source = f"market_prices:{hub_id}"
        run = self.db.execute(
            "INSERT INTO sync_runs(source,status,started_at,completed_at,data_timestamp) "
            "VALUES(?,'completed',?,?,?)",
            (source, observed_at, observed_at, observed_at),
        )
        snapshot = self.db.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (
                int(run.lastrowid),
                source,
                json.dumps(
                    {
                        "formatVersion": 1,
                        "hubId": hub_id,
                        "requestedTypeIds": sorted(requested_type_ids),
                        "pageCount": len(requested_type_ids),
                        "orders": sorted(
                            orders,
                            key=lambda order: (
                                order["typeId"],
                                order["priceCents"],
                                order["orderId"],
                            ),
                        ),
                    }
                ),
                observed_at,
            ),
        )
        return int(snapshot.lastrowid), int(run.lastrowid)

    def publish_locations(
        self,
        character_id: int,
        asset_snapshot_id: int,
        item_ids: list[int],
        observed_at: str,
    ) -> None:
        run = self.db.execute(
            "INSERT INTO sync_runs(source,status,started_at,completed_at,data_timestamp,"
            "character_id) VALUES('asset_locations','completed',?,?,?,?)",
            (observed_at, observed_at, observed_at, character_id),
        )
        locations = [
            {
                "itemId": item_id,
                "status": "resolved",
                "path": [
                    {
                        "locationId": 30_000_142,
                        "kind": "solar_system",
                        "name": "Synthetic System",
                        "access": "available",
                        "typeId": None,
                    },
                    {
                        "locationId": 60_003_760,
                        "kind": "station",
                        "name": "Synthetic Station",
                        "access": "available",
                        "typeId": None,
                    },
                ],
                "errorCode": None,
            }
            for item_id in item_ids
        ]
        self.db.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (
                int(run.lastrowid),
                f"asset_locations:{character_id}",
                json.dumps(
                    {
                        "characterId": character_id,
                        "assetSnapshotId": asset_snapshot_id,
                        "locations": locations,
                    }
                ),
                observed_at,
            ),
        )

    def publish_container_locations(
        self,
        character_id: int,
        asset_snapshot_id: int,
        container_id: int,
        item_ids: list[int],
        root_item_ids: list[int],
        observed_at: str,
        *,
        inventory_item_id: int | None = None,
        inventory_item_child_ids: list[int] | None = None,
    ) -> None:
        run = self.db.execute(
            "INSERT INTO sync_runs(source,status,started_at,completed_at,data_timestamp,"
            "character_id) VALUES('asset_locations','completed',?,?,?,?)",
            (observed_at, observed_at, observed_at, character_id),
        )
        root = [
            {
                "locationId": 30_000_142,
                "kind": "solar_system",
                "name": "Synthetic System",
                "access": "available",
                "typeId": None,
            },
            {
                "locationId": 60_003_760,
                "kind": "station",
                "name": "Synthetic Station",
                "access": "available",
                "typeId": None,
            },
        ]
        locations = [{
            "itemId": container_id,
            "status": "resolved",
            "path": root,
            "errorCode": None,
        }]
        locations.extend({
            "itemId": item_id,
            "status": "resolved",
            "path": root,
            "errorCode": None,
        } for item_id in root_item_ids)
        locations.extend({
            "itemId": item_id,
            "status": "resolved",
            "path": [*root, {
                "locationId": container_id,
                "kind": "container",
                "name": "Production Materials",
                "access": "available",
                "typeId": 1_001,
            }],
            "errorCode": None,
        } for item_id in item_ids)
        if inventory_item_id is not None:
            locations.append({
                "itemId": inventory_item_id,
                "status": "resolved",
                "path": root,
                "errorCode": None,
            })
            locations.extend({
                "itemId": item_id,
                "status": "resolved",
                "path": [*root, {
                    "locationId": inventory_item_id,
                    "kind": "inventory_item",
                    "name": "Synthetic Hauler",
                    "access": "available",
                    "typeId": 1_002,
                }],
                "errorCode": None,
            } for item_id in (inventory_item_child_ids or []))
        self.db.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (
                int(run.lastrowid),
                f"asset_locations:{character_id}",
                json.dumps({
                    "characterId": character_id,
                    "assetSnapshotId": asset_snapshot_id,
                    "locations": locations,
                }),
                observed_at,
            ),
        )

    def test_goal_persists_and_expands_shared_inputs_after_rounding(self) -> None:
        import_industry_sde(self.db, **bundle())
        saved = save_production_plan(self.db, plan_input())
        page = query_production_plans(self.db, query())

        self.assertTrue(saved["saved"])
        self.assertEqual(saved["note"], "main goal")
        self.assertEqual(page["buildNumber"], "synthetic-production-1")
        self.assertTrue(page["inventoryApplied"])
        self.assertTrue(page["reservationsApplied"])
        self.assertEqual(
            page["reservationRule"], "priority-desc-created-asc-plan-id-asc"
        )
        self.assertTrue(page["blueprintMaterialEfficiencyApplied"])
        self.assertEqual(
            page["materialEfficiencyRule"],
            "max-runs-ceil-base-runs-percent",
        )
        self.assertTrue(page["blueprintTimeEfficiencyApplied"])
        self.assertEqual(
            page["timeEfficiencyRule"],
            "max-one-ceil-base-runs-percent",
        )
        self.assertTrue(page["characterSkillTimeApplied"])
        self.assertEqual(
            page["characterSkillTimeRule"],
            "job-wide-ceil-industry-4-advanced-industry-3-reactions-4-active-levels",
        )
        self.assertTrue(page["facilityEvidenceApplied"])
        self.assertEqual(
            page["facilityEvidenceRule"],
            "assigned-blueprint-before-active-before-latest-owner-job",
        )
        self.assertFalse(page["remainingModifiersApplied"])
        self.assertTrue(page["purchaseListApplied"])
        self.assertEqual(
            page["purchaseListRule"], "selected-plan-conflict-free-shortage-by-type"
        )
        self.assertEqual(
            {
                key: page["purchaseList"][key]
                for key in (
                    "state",
                    "items",
                    "itemCount",
                    "totalQuantity",
                    "includedPlanCount",
                    "unresolvedPlanCount",
                    "omittedItemCount",
                    "pricingState",
                    "installationCostState",
                    "additionalCapitalNeedCents",
                )
            },
            {
                "state": "incomplete",
                "items": [],
                "itemCount": 0,
                "totalQuantity": 0,
                "includedPlanCount": 0,
                "unresolvedPlanCount": 1,
                "omittedItemCount": 0,
                "pricingState": "empty",
                "installationCostState": "not-applicable",
                "additionalCapitalNeedCents": None,
            },
        )
        self.assertEqual(page["purchaseList"]["marketHub"]["hubId"], "jita")
        self.assertEqual(
            [hub["hubId"] for hub in page["purchaseList"]["marketHubs"]],
            ["jita", "amarr", "dodixie", "hek", "rens"],
        )
        self.assertTrue(page["marketPricesApplied"])
        self.assertEqual(page["summary"]["ready"], 1)
        record = page["items"][0]
        self.assertEqual(record["state"], "ready")
        self.assertEqual(
            [(step["productTypeId"], step["requiredQuantity"], step["runs"], step["producedQuantity"])
             for step in record["steps"]],
            [(121, 23, 3, 30), (111, 6, 3, 6), (101, 3, 2, 4)],
        )
        self.assertEqual(
            {
                key: record["grossMaterials"][0][key]
                for key in ("typeId", "typeName", "quantity")
            },
            {"typeId": 900, "typeName": "Synthetic Mineral", "quantity": 27},
        )
        self.assertEqual(record["totalBaseTimeSeconds"], 290)
        self.assertEqual(record["totalBlueprintTimeSeconds"], 290)
        self.assertEqual(record["timeEfficiencySavingsSeconds"], 0)
        self.assertEqual(record["characterSkillState"], "snapshot-missing")
        self.assertIsNone(record["skillSnapshotId"])
        self.assertIsNone(record["skillSyncRunId"])
        self.assertIsNone(record["skillObservedAt"])
        self.assertIsNone(record["totalCharacterTimeSeconds"])
        self.assertIsNone(record["characterSkillTimeSavingsSeconds"])
        self.assertEqual(record["facilityState"], "missing")
        self.assertTrue(all(
            step["facilityEvidence"]["state"] == "job-snapshot-missing"
            for step in record["steps"]
        ))
        self.assertTrue(all(
            step["totalCharacterTimeSeconds"] is None
            and step["characterSkillTimeSavingsSeconds"] is None
            and not step["characterSkillTimeApplied"]
            and all(skill["activeLevel"] is None for skill in step["timeSkills"])
            for step in record["steps"]
        ))
        self.assertEqual(record["inventoryState"], "snapshot-missing")
        self.assertEqual(record["blueprintAssignmentState"], "snapshot-missing")
        self.assertEqual(record["appliedMaterialEfficiency"], 0)
        self.assertEqual(record["appliedTimeEfficiency"], 0)
        self.assertIsNone(record["assetSnapshotId"])
        self.assertEqual(
            record["grossMaterials"][0]["availabilityState"], "snapshot-missing"
        )
        self.assertIsNone(record["grossMaterials"][0]["availableQuantity"])
        self.assertIsNone(record["grossMaterials"][0]["reservedQuantity"])
        self.assertIsNone(
            record["grossMaterials"][0]["reservedByPriorPlansQuantity"]
        )
        self.assertIsNone(record["grossMaterials"][0]["remainingQuantity"])
        self.assertIsNone(record["grossMaterials"][0]["inventoryShortageQuantity"])
        self.assertIsNone(record["grossMaterials"][0]["reservationConflictQuantity"])
        self.assertIsNone(record["grossMaterials"][0]["missingQuantity"])
        self.assertEqual(record["grossMaterials"][0]["priorReservationCount"], 0)
        self.assertEqual(record["grossMaterials"][0]["priorReservations"], [])
        self.assertEqual(record["warnings"], [{
            "code": "alternative-recipe",
            "typeId": 121,
            "typeName": "Synthetic Plate",
            "selectedBlueprintTypeId": 120,
            "candidateCount": 2,
        }])

    def test_purchase_list_uses_only_the_selected_production_goal(self) -> None:
        import_industry_sde(self.db, **bundle())
        asset_snapshot, _ = self.publish_assets(
            7,
            [{
                "item_id": 7_001,
                "type_id": 900,
                "location_id": 60_003_760,
                "quantity": 10,
                "location_type": "station",
                "location_flag": "Hangar",
            }],
            "2026-09-16T10:00:00Z",
        )
        self.publish_locations(
            7, asset_snapshot, [7_001], "2026-09-16T10:01:00Z"
        )
        first = save_production_plan(
            self.db, plan_input(priority=100, note="First batch")
        )
        second = save_production_plan(
            self.db, plan_input(priority=50, note="Second batch")
        )
        market_snapshot, market_run = self.publish_market_prices(
            [
                {
                    "orderId": 1,
                    "typeId": 900,
                    "locationId": 60_003_760,
                    "systemId": 30_000_142,
                    "priceCents": 10_000,
                    "volumeRemain": 10,
                },
                {
                    "orderId": 2,
                    "typeId": 900,
                    "locationId": 60_003_760,
                    "systemId": 30_000_142,
                    "priceCents": 12_500,
                    "volumeRemain": 40,
                },
            ],
            [900],
        )

        page = query_production_plans(self.db, query())
        purchase = page["purchaseList"]
        self.assertEqual(purchase["state"], "ready")
        self.assertEqual(purchase["pricingState"], "ready")
        self.assertEqual(purchase["marketSnapshotId"], market_snapshot)
        self.assertEqual(purchase["marketSyncRunId"], market_run)
        self.assertEqual(purchase["totalPurchaseCostCents"], 187_500)
        self.assertEqual(purchase["installationCostState"], "unavailable")
        self.assertIsNone(purchase["additionalCapitalNeedCents"])
        self.assertEqual(
            purchase["items"],
            [{
                "typeId": 900,
                "typeName": "Synthetic Mineral",
                "quantity": 17,
                "inventoryShortageQuantity": 17,
                "reservationConflictQuantity": 0,
                "planCount": 1,
                "marketState": "ready",
                "coveredQuantity": 17,
                "uncoveredQuantity": 0,
                "usedOrderCount": 2,
                "lowestUnitPriceCents": 10_000,
                "weightedUnitPriceCents": 11_030,
                "purchaseCostCents": 187_500,
            }],
        )
        self.assertEqual(
            [item["planId"] for item in page["items"]],
            [first["planId"], second["planId"]],
        )
        self.assertEqual(page["analysisPlanId"], first["planId"])
        self.assertEqual(
            {item["planId"] for item in page["analysisPlans"]},
            {first["planId"], second["planId"]},
        )

        selected_second = query_production_plans(
            self.db, query(analysisPlanId=second["planId"])
        )["purchaseList"]
        self.assertEqual(selected_second["items"][0]["quantity"], 27)
        self.assertEqual(selected_second["items"][0]["planCount"], 1)
        self.assertEqual(selected_second["totalPurchaseCostCents"], 312_500)

        filtered = query_production_plans(self.db, query(search="first batch"))
        self.assertEqual(filtered["total"], 1)
        self.assertEqual(filtered["purchaseList"]["items"][0]["quantity"], 17)
        self.assertEqual(filtered["purchaseList"]["items"][0]["planCount"], 1)
        self.assertEqual(filtered["purchaseList"]["includedPlanCount"], 1)
        self.assertEqual(filtered["purchaseList"]["totalPurchaseCostCents"], 187_500)

    def test_selected_market_hub_never_falls_back_to_jita(self) -> None:
        import_industry_sde(self.db, **bundle())
        self.publish_assets(7, [], "2026-09-16T10:00:00Z")
        save_production_plan(self.db, plan_input())
        self.publish_market_prices(
            [{
                "orderId": 1,
                "typeId": 900,
                "locationId": 60_003_760,
                "systemId": 30_000_142,
                "priceCents": 100,
                "volumeRemain": 100,
            }],
            [900],
        )

        missing = query_production_plans(self.db, query(marketHubId="amarr"))[
            "purchaseList"
        ]
        self.assertEqual(missing["marketHub"]["hubId"], "amarr")
        self.assertEqual(missing["pricingState"], "snapshot-missing")
        self.assertEqual(missing["items"][0]["marketState"], "snapshot-missing")

        amarr_snapshot, _ = self.publish_market_prices(
            [{
                "orderId": 2,
                "typeId": 900,
                "locationId": 60_008_494,
                "systemId": 30_002_187,
                "priceCents": 200,
                "volumeRemain": 100,
            }],
            [900],
            hub_id="amarr",
        )
        priced = query_production_plans(self.db, query(marketHubId="amarr"))[
            "purchaseList"
        ]
        self.assertEqual(priced["marketSnapshotId"], amarr_snapshot)
        self.assertEqual(priced["pricingState"], "ready")
        self.assertEqual(priced["items"][0]["lowestUnitPriceCents"], 200)

    def inventory_query(self, **settings):
        return query(includeBlueprintProfitability=True, analysisPlanId=None,
                     brokerFeeBasisPoints=0, salesTaxBasisPoints=0,
                     inventoryAnalysis={"runs": 10, "offset": 0, "facilityId": 60_003_760,
                                        "facilityTaxBasisPoints": 0, "materialBonusBasisPoints": 0, **settings})

    def owned_blueprint(self, item_id=8001, **changes):
        return {"item_id": item_id, "type_id": 100, "quantity": -1,
                "material_efficiency": 10, "time_efficiency": 20, "runs": -1,
                "location_id": 60_003_760, "location_flag": "Hangar", **changes}

    def test_inventory_profitability_needs_no_goals_or_assets_and_buys_direct_inputs(self):
        import_industry_sde(self.db, **bundle())
        self.publish_facilities("2026-09-24T12:00:00Z")
        self.publish_blueprints(7, [self.owned_blueprint()], "2026-09-24T12:00:00Z")
        self.publish_market_prices([
            {"orderId": i + 1, "typeId": type_id, "locationId": 60_003_760,
             "systemId": 30_000_142, "priceCents": price, "volumeRemain": 10_000}
            for i, (type_id, price) in enumerate([(101, 100_000), (111, 1_000), (121, 500)])
        ], [101, 111, 121])
        before = self.db.total_changes
        result = query_production_plans(self.db, self.inventory_query())
        self.assertEqual(self.db.total_changes, before)
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["locationOptions"][0]["facilityId"], 60_003_760)
        comparison = result["blueprintProfitability"]
        self.assertEqual(comparison["inventory"]["total"], 1)
        self.assertEqual(comparison["marketTypeIds"], [101, 111, 121])
        item = comparison["items"][0]
        self.assertEqual(item["targetQuantity"], 20)
        self.assertEqual(item["appliedMaterialEfficiency"], 10)
        self.assertEqual(item["inventory"]["runs"], 10)
        jita = item["comparisons"][0]
        # Direct input purchase: ceil(3*10*.9)=27 frames, 36 plates.
        self.assertEqual(jita["materialReplacementCostCents"], 45_000)
        # EIV 3800 ISK; ceil(47.5) system + 152 SCC, no tax.
        self.assertEqual(jita["installationCostCents"], 20_000)
        self.assertEqual(jita["netProfitCents"], 1_935_000)
        self.assertEqual(item["bestHubId"], "jita")
        self.assertIsNone(item["comparisons"][1]["netProfitCents"])

    def test_inventory_copies_cap_runs_and_keep_exhausted_and_missing_recipes_visible(self):
        import_industry_sde(self.db, **bundle())
        self.publish_blueprints(7, [
            self.owned_blueprint(8001, quantity=-2, runs=3),
            self.owned_blueprint(8002, quantity=-2, runs=0),
            self.owned_blueprint(8003, type_id=999),
            self.owned_blueprint(8004, material_efficiency=0),
        ], "2026-09-24T12:00:00Z")
        result = query_production_plans(self.db, self.inventory_query())["blueprintProfitability"]
        rows = {r["blueprintItemId"]: r for r in result["items"]}
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[8001]["inventory"]["runs"], 3)
        self.assertEqual(rows[8001]["targetQuantity"], 6)
        self.assertEqual(rows[8002]["inventory"]["status"], "runs-exhausted")
        self.assertEqual(rows[8003]["inventory"]["status"], "recipe-missing")
        self.assertEqual(rows[8004]["appliedMaterialEfficiency"], 0)
        self.assertTrue(all(r["bestHubId"] is None for r in rows.values()))

    def test_inventory_pagination_covers_more_than_one_hundred_owned_blueprints(self):
        import_industry_sde(self.db, **bundle())
        self.publish_blueprints(7, [self.owned_blueprint(8000 + i) for i in range(131)], "2026-09-24T12:00:00Z")
        ids = []
        offset = 0
        while offset is not None:
            result = query_production_plans(self.db, self.inventory_query(offset=offset))["blueprintProfitability"]
            self.assertEqual(result["inventory"]["total"], 131)
            self.assertLessEqual(len(result["items"]), 25)
            self.assertEqual(result["omittedMarketTypeCount"], 0)
            ids.extend(item["blueprintItemId"] for item in result["items"])
            offset = result["inventory"]["nextOffset"]
        self.assertEqual(len(ids), 131)
        self.assertEqual(len(set(ids)), 131)

    def test_inventory_query_filters_owners_and_reports_missing_snapshots(self):
        import_industry_sde(self.db, **bundle())
        self.publish_blueprints(7, [self.owned_blueprint()], "2026-09-24T12:00:00Z")
        raw = self.inventory_query()
        self.db.execute("INSERT INTO characters(character_id,name) VALUES (8,'Other Synthetic Pilot')")
        raw["ownerCharacterId"] = 8
        result = query_production_plans(self.db, raw)["blueprintProfitability"]
        self.assertEqual(result["inventory"]["total"], 0)
        self.assertEqual(result["inventory"]["missingOwners"], 1)
        raw["ownerCharacterId"] = 7
        raw["search"] = "absent blueprint"
        self.assertEqual(query_production_plans(self.db, raw)["blueprintProfitability"]["inventory"]["total"], 0)

    def test_inventory_market_cache_keeps_other_pages_and_respects_empty_latest_orders(self):
        from new_eden_foundry_backend.market_prices import market_price_snapshot_for_types
        def order(order_id, type_id, price):
            return {"orderId": order_id, "typeId": type_id, "locationId": 60_003_760,
                    "systemId": 30_000_142, "priceCents": price, "volumeRemain": 100}
        old, _ = self.publish_market_prices([order(1, 101, 1000)], [101])
        self.db.execute("UPDATE cached_snapshots SET observed_at='2020-01-01T00:00:00Z' WHERE id=?", (old,))
        self.publish_market_prices([order(2, 111, 500)], [111])
        cached = market_price_snapshot_for_types(self.db, "jita", [101, 111])
        self.assertEqual(cached["requestedTypeIds"], {101, 111})
        self.assertEqual(cached["ordersByType"][101][0]["priceCents"], 1000)
        self.assertTrue(cached["stale"])
        self.assertEqual(cached["observedAt"], '2020-01-01T00:00:00Z')
        self.publish_market_prices([], [101])
        cached = market_price_snapshot_for_types(self.db, "jita", [101, 111])
        self.assertEqual(cached["ordersByType"][101], [])
        self.assertEqual(cached["ordersByType"][111][0]["priceCents"], 500)
        self.assertFalse(cached["stale"])
        self.assertIsNone(market_price_snapshot_for_types(self.db, "amarr", [101, 111]))

    def test_inventory_settings_reject_invalid_rates_runs_and_offsets(self):
        for changes in ({"runs": 0}, {"runs": True}, {"runs": 10_001}, {"offset": -1},
                        {"facilityId": 0}, {"facilityTaxBasisPoints": -1},
                        {"materialBonusBasisPoints": 5_001}):
            with self.subTest(changes=changes), self.assertRaises(ProductionPlanningError):
                validate_production_plan_query(self.inventory_query(**changes))

    def test_blueprint_profitability_compares_configured_goal_at_all_hubs(self) -> None:
        import_industry_sde(self.db, **bundle())
        asset_snapshot, _ = self.publish_assets(
            7,
            [{
                "item_id": 7_001,
                "type_id": 900,
                "location_id": 60_003_760,
                "quantity": 1,
                "location_type": "station",
                "location_flag": "Hangar",
            }],
            "2026-09-16T08:00:00Z",
        )
        self.publish_locations(
            7, asset_snapshot, [7_001], "2026-09-16T08:00:30Z"
        )
        self.publish_facilities("2026-09-16T08:01:00Z")
        saved = save_production_plan(
            self.db,
            plan_input(
                facilityId=60_003_760,
                facilityTaxBasisPoints=0,
            ),
        )
        hubs = [
            ("jita", 60_003_760, 30_000_142, 10_000),
            ("amarr", 60_008_494, 30_002_187, 12_000),
            ("dodixie", 60_011_866, 30_002_659, 9_000),
            ("hek", 60_005_686, 30_002_053, 8_000),
            ("rens", 60_004_588, 30_002_510, 7_000),
        ]
        for index, (hub_id, station_id, system_id, output_price) in enumerate(hubs):
            self.publish_market_prices(
                [
                    {
                        "orderId": index * 10 + 1,
                        "typeId": 101,
                        "locationId": station_id,
                        "systemId": system_id,
                        "priceCents": output_price,
                        "volumeRemain": 100,
                    },
                    {
                        "orderId": index * 10 + 2,
                        "typeId": 900,
                        "locationId": station_id,
                        "systemId": system_id,
                        "priceCents": 100,
                        "volumeRemain": 1_000,
                    },
                ],
                [101, 900],
                hub_id=hub_id,
            )

        page = query_production_plans(
            self.db,
            query(
                analysisPlanId=saved["planId"],
                includeBlueprintProfitability=True,
                brokerFeeBasisPoints=0,
                salesTaxBasisPoints=0,
            ),
        )
        comparison = page["blueprintProfitability"]
        self.assertTrue(page["blueprintProfitabilityApplied"])
        self.assertEqual(comparison["state"], "ready")
        self.assertEqual(comparison["itemCount"], 1)
        self.assertEqual(comparison["marketTypeIds"], [101, 900])
        self.assertEqual(comparison["items"][0]["planId"], saved["planId"])
        self.assertEqual(comparison["items"][0]["bestHubId"], "amarr")
        self.assertEqual(
            [item["hubId"] for item in comparison["items"][0]["comparisons"]],
            ["jita", "amarr", "dodixie", "hek", "rens"],
        )
        profits = {
            item["hubId"]: item["netProfitCents"]
            for item in comparison["items"][0]["comparisons"]
        }
        self.assertGreater(profits["amarr"], profits["jita"])
        self.assertGreater(profits["jita"], profits["rens"])

    def test_profitability_values_stock_at_full_replacement_cost(self) -> None:
        import_industry_sde(self.db, **bundle())
        asset_snapshot, _ = self.publish_assets(
            7,
            [{
                "item_id": 7_001,
                "type_id": 900,
                "location_id": 60_003_760,
                "quantity": 10,
                "location_type": "station",
                "location_flag": "Hangar",
            }],
            "2026-09-16T08:28:00Z",
        )
        self.publish_locations(
            7, asset_snapshot, [7_001], "2026-09-16T08:29:00Z"
        )
        self.publish_facilities("2026-09-16T08:30:00Z")
        save_production_plan(
            self.db,
            plan_input(
                facilityId=60_003_760,
                facilityTaxBasisPoints=100,
            ),
        )
        self.publish_market_prices(
            [
                {
                    "orderId": 1,
                    "typeId": 101,
                    "locationId": 60_003_760,
                    "systemId": 30_000_142,
                    "priceCents": 10_000,
                    "volumeRemain": 20,
                },
                {
                    "orderId": 2,
                    "typeId": 900,
                    "locationId": 60_003_760,
                    "systemId": 30_000_142,
                    "priceCents": 100,
                    "volumeRemain": 100,
                },
            ],
            [101, 900],
        )

        unconfigured = query_production_plans(self.db, query())["purchaseList"][
            "profitability"
        ]
        self.assertEqual(unconfigured["tradeCostState"], "unconfigured")
        self.assertIsNone(unconfigured["netProfitCents"])
        self.assertFalse(unconfigured["tradeFeesIncluded"])

        purchase = query_production_plans(
            self.db,
            query(brokerFeeBasisPoints=300, salesTaxBasisPoints=360),
        )["purchaseList"]
        profitability = purchase["profitability"]
        self.assertEqual(purchase["totalPurchaseCostCents"], 1_700)
        self.assertEqual(purchase["additionalCapitalNeedCents"], 10_500)
        self.assertEqual(profitability["state"], "ready")
        self.assertEqual(profitability["marketTypeIds"], [101, 900])
        self.assertEqual(profitability["marketTypeCount"], 2)
        self.assertEqual(profitability["materialItemCount"], 1)
        self.assertEqual(profitability["fullyPricedMaterialCount"], 1)
        self.assertEqual(profitability["grossRevenueCents"], 40_000)
        self.assertEqual(profitability["materialReplacementCostCents"], 2_700)
        self.assertEqual(profitability["installationCostCents"], 8_800)
        self.assertEqual(profitability["totalProductionCostCents"], 11_500)
        self.assertEqual(profitability["grossProfitCents"], 28_500)
        self.assertEqual(profitability["grossMarginBasisPoints"], 7_125)
        self.assertEqual(profitability["tradeCostState"], "ready")
        self.assertEqual(profitability["brokerFeeBasisPoints"], 300)
        self.assertEqual(profitability["salesTaxBasisPoints"], 360)
        self.assertEqual(profitability["effectiveBrokerFeeRate"], 300_000_000)
        self.assertEqual(profitability["effectiveSalesTaxRate"], 360_000_000)
        self.assertEqual(profitability["tradeRateScale"], 10_000_000_000)
        self.assertEqual(profitability["brokerFeeCents"], 1_200)
        self.assertEqual(profitability["salesTaxCents"], 1_440)
        self.assertEqual(profitability["totalTradeCostCents"], 2_640)
        self.assertEqual(profitability["netRevenueCents"], 37_360)
        self.assertEqual(profitability["netProfitCents"], 25_860)
        self.assertEqual(profitability["netMarginBasisPoints"], 6_465)
        self.assertTrue(profitability["tradeFeesIncluded"])
        self.assertEqual(
            profitability["items"],
            [{
                "typeId": 101,
                "typeName": "Synthetic Hull",
                "quantity": 4,
                "targetQuantity": 3,
                "surplusQuantity": 1,
                "planCount": 1,
                "marketState": "ready",
                "lowestSellUnitPriceCents": 10_000,
                "competingVolume": 20,
                "grossRevenueCents": 40_000,
            }],
        )

        automatic_query = query(
            tradeCostMode="automatic",
            salesCharacterId=7,
            brokerFeeBasisPoints=None,
            salesTaxBasisPoints=None,
        )
        missing_skills = query_production_plans(self.db, automatic_query)[
            "purchaseList"
        ]["profitability"]
        self.assertEqual(missing_skills["tradeCostState"], "skill-snapshot-missing")

        skill_snapshot, skill_run = self.publish_skills(
            7, {3446: 4, 16622: 5}, "2026-09-16T08:31:00Z"
        )
        missing_standings = query_production_plans(self.db, automatic_query)[
            "purchaseList"
        ]["profitability"]
        self.assertEqual(
            missing_standings["tradeCostState"], "standing-snapshot-missing"
        )
        standing_snapshot, standing_run = self.publish_standings(
            7,
            [
                {
                    "fromId": 500_001,
                    "fromType": "faction",
                    "standingMillionths": 5_000_000,
                },
                {
                    "fromId": 1_000_035,
                    "fromType": "npc_corp",
                    "standingMillionths": 4_000_000,
                },
            ],
            "2026-09-16T08:32:00Z",
        )
        automatic = query_production_plans(self.db, automatic_query)["purchaseList"][
            "profitability"
        ]
        self.assertEqual(automatic["tradeCostState"], "ready")
        self.assertEqual(automatic["tradeCostMode"], "automatic")
        self.assertEqual(automatic["salesCharacterName"], "Synthetic Pilot")
        self.assertEqual((automatic["brokerRelationsLevel"], automatic["accountingLevel"]), (4, 5))
        self.assertEqual(automatic["corporationStandingMillionths"], 4_000_000)
        self.assertEqual(automatic["factionStandingMillionths"], 5_000_000)
        self.assertEqual(automatic["effectiveBrokerFeeRate"], 157_000_000)
        self.assertEqual(automatic["effectiveSalesTaxRate"], 337_500_000)
        self.assertEqual((automatic["brokerFeeCents"], automatic["salesTaxCents"]), (628, 1_350))
        self.assertEqual((automatic["tradeSkillSnapshotId"], automatic["tradeSkillSyncRunId"]), (skill_snapshot, skill_run))
        self.assertEqual((automatic["standingSnapshotId"], automatic["standingSyncRunId"]), (standing_snapshot, standing_run))
        self.assertEqual(automatic["netRevenueCents"], 38_022)
        self.assertEqual(automatic["netProfitCents"], 26_522)
        self.assertTrue(query_production_plans(self.db, query())["profitabilityApplied"])

    def test_selected_container_and_stock_only_intermediate_skip_blueprint_step(self) -> None:
        import_industry_sde(self.db, **bundle())
        container_id = 7_000
        asset_snapshot, _ = self.publish_assets(
            7,
            [
                {"item_id": container_id, "type_id": 1_001, "location_id": 60_003_760,
                 "quantity": 1, "location_type": "station", "location_flag": "Hangar"},
                {"item_id": 7_001, "type_id": 111, "location_id": container_id,
                 "quantity": 4, "location_type": "item", "location_flag": "Unlocked"},
                {"item_id": 7_002, "type_id": 900, "location_id": container_id,
                 "quantity": 100, "location_type": "item", "location_flag": "Unlocked"},
                {"item_id": 7_003, "type_id": 111, "location_id": 60_003_760,
                 "quantity": 100, "location_type": "station", "location_flag": "Hangar"},
            ],
            "2026-09-15T10:00:00Z",
        )
        self.publish_container_locations(
            7, asset_snapshot, container_id, [7_001, 7_002], [7_003],
            "2026-09-15T10:01:00Z"
        )
        saved = save_production_plan(
            self.db,
            plan_input(
                facilityId=60_003_760,
                materialLocationId=container_id,
                stepSupplyModes=[{
                    "blueprintTypeId": 110,
                    "activity": "manufacturing",
                    "productTypeId": 111,
                    "supplyMode": "stock-only",
                }],
            ),
        )

        page = query_production_plans(self.db, query())
        record = page["items"][0]
        frame = next(item for item in record["grossMaterials"] if item["typeId"] == 111)
        decision = next(
            item for item in record["supplyDecisions"] if item["productTypeId"] == 111
        )

        self.assertEqual(saved["facilityId"], 60_003_760)
        self.assertEqual(saved["materialLocationId"], container_id)
        self.assertEqual(record["locationSelectionState"], "ready")
        self.assertEqual(record["facilityName"], "Synthetic Station")
        self.assertEqual(record["materialLocationName"], "Production Materials")
        self.assertEqual(record["facilityModifierState"], "unconfigured")
        self.assertIsNone(record["facilityMaterialBonusBasisPoints"])
        self.assertIsNone(record["facilityTimeBonusBasisPoints"])
        self.assertIsNone(record["totalFacilityTimeSeconds"])
        self.assertTrue(all(
            step["facilityModifierState"] == "unconfigured"
            and step["totalFacilityTimeSeconds"] is None
            for step in record["steps"]
        ))
        self.assertEqual(frame["quantity"], 6)
        self.assertEqual(frame["availableQuantity"], 4)
        self.assertEqual(frame["reservedQuantity"], 4)
        self.assertEqual(frame["missingQuantity"], 2)
        self.assertEqual(decision["supplyMode"], "stock-only")
        self.assertEqual(decision["stockUsedQuantity"], 4)
        self.assertEqual(decision["buildQuantity"], 0)
        self.assertFalse(decision["blueprintRequired"])
        self.assertNotIn(110, [step["blueprintTypeId"] for step in record["steps"]])
        root_material = next(
            material
            for step in record["steps"]
            for material in step["materials"]
            if material["typeId"] == 111
        )
        self.assertFalse(root_material["producedByPlan"])
        self.assertEqual(frame["excludedQuantity"], 100)
        self.assertEqual(frame["excludedLocations"][0]["ownerCharacterId"], 7)
        self.assertEqual(page["locationOptions"][0]["materialLocations"][1]["locationId"], container_id)
        self.assertTrue(page["supplyModesApplied"])
        self.assertEqual(page["supplyModeRule"], "stock-first-before-recursive-build")

    def test_station_source_excludes_ship_holds_from_material_inventory(self) -> None:
        import_industry_sde(self.db, **bundle())
        ship_id = 7_100
        asset_snapshot, _ = self.publish_assets(
            7,
            [
                {"item_id": 7_000, "type_id": 1_001,
                 "location_id": 60_003_760, "quantity": 1,
                 "location_type": "station", "location_flag": "Hangar"},
                {"item_id": ship_id, "type_id": 1_002,
                 "location_id": 60_003_760, "quantity": 1,
                 "location_type": "station", "location_flag": "Hangar"},
                {"item_id": 7_101, "type_id": 900, "location_id": ship_id,
                 "quantity": 500, "location_type": "item", "location_flag": "Cargo"},
                {"item_id": 7_102, "type_id": 900, "location_id": 60_003_760,
                 "quantity": 20, "location_type": "station", "location_flag": "Hangar"},
            ],
            "2026-09-15T10:10:00Z",
        )
        self.publish_container_locations(
            7,
            asset_snapshot,
            7_000,
            [],
            [7_102],
            "2026-09-15T10:11:00Z",
            inventory_item_id=ship_id,
            inventory_item_child_ids=[7_101],
        )
        save_production_plan(
            self.db,
            plan_input(
                facilityId=60_003_760,
                stepSupplyModes=[
                    {"blueprintTypeId": 110, "activity": "manufacturing",
                     "productTypeId": 111, "supplyMode": "build"},
                    {"blueprintTypeId": 120, "activity": "manufacturing",
                     "productTypeId": 121, "supplyMode": "build"},
                ],
            ),
        )

        page = query_production_plans(self.db, query())
        mineral = next(
            item for item in page["items"][0]["grossMaterials"]
            if item["typeId"] == 900
        )

        self.assertEqual(mineral["availableQuantity"], 20)
        self.assertEqual(mineral["excludedQuantity"], 500)
        self.assertEqual(
            [
                item["locationId"]
                for item in page["locationOptions"][0]["materialLocations"]
            ],
            [60_003_760],
        )

    def test_stock_first_builds_only_the_uncovered_intermediate_quantity(self) -> None:
        import_industry_sde(self.db, **bundle())
        asset_snapshot, _ = self.publish_assets(
            7,
            [{"item_id": 8_001, "type_id": 111, "location_id": 60_003_760,
              "quantity": 4, "location_type": "station", "location_flag": "Hangar"}],
            "2026-09-15T11:00:00Z",
        )
        self.publish_locations(7, asset_snapshot, [8_001], "2026-09-15T11:01:00Z")
        save_production_plan(self.db, plan_input())

        record = query_production_plans(self.db, query())["items"][0]
        frame_step = next(step for step in record["steps"] if step["productTypeId"] == 111)
        frame_decision = next(
            item for item in record["supplyDecisions"] if item["productTypeId"] == 111
        )

        self.assertEqual(frame_decision["supplyMode"], "stock-first")
        self.assertEqual(frame_decision["stockUsedQuantity"], 4)
        self.assertEqual(frame_decision["buildQuantity"], 2)
        self.assertEqual(frame_step["requiredQuantity"], 2)
        self.assertEqual(frame_step["runs"], 1)
        root_material = next(
            material
            for step in record["steps"]
            for material in step["materials"]
            if material["typeId"] == 111
        )
        self.assertTrue(root_material["producedByPlan"])

    def test_stock_only_parent_omits_inactive_descendants_without_zero_quantities(self) -> None:
        import_industry_sde(self.db, **bundle())
        self.db.execute(
            "DELETE FROM sde_blueprint_materials "
            "WHERE blueprint_type_id=100 AND material_type_id=121"
        )
        asset_snapshot, _ = self.publish_assets(
            7,
            [{"item_id": 8_101, "type_id": 111, "location_id": 60_003_760,
              "quantity": 6, "location_type": "station", "location_flag": "Hangar"}],
            "2026-09-15T12:00:00Z",
        )
        self.publish_locations(7, asset_snapshot, [8_101], "2026-09-15T12:01:00Z")
        self.publish_blueprints(
            7,
            [{"item_id": 9_101, "type_id": 120, "quantity": -1,
              "material_efficiency": 10, "time_efficiency": 20, "runs": -1,
              "location_id": 60_003_760, "location_flag": "Hangar"}],
            "2026-09-15T12:02:00Z",
        )
        save_production_plan(
            self.db,
            plan_input(stepBlueprintAssignments=[
                {"blueprintTypeId": 120, "activity": "manufacturing",
                 "productTypeId": 121, "blueprintItemId": 9_101},
            ], stepSupplyModes=[
                {"blueprintTypeId": 110, "activity": "manufacturing",
                 "productTypeId": 111, "supplyMode": "stock-only"},
                {"blueprintTypeId": 120, "activity": "manufacturing",
                 "productTypeId": 121, "supplyMode": "build"},
            ]),
        )

        record = query_production_plans(self.db, query())["items"][0]

        self.assertEqual(
            [(item["productTypeId"], item["requiredQuantity"])
             for item in record["supplyDecisions"]],
            [(111, 6)],
        )
        self.assertEqual(
            [step["productTypeId"] for step in record["steps"]],
            [101],
        )
        self.assertEqual(record["grossMaterials"][0]["typeId"], 111)
        self.assertEqual(
            self.db.execute(
                "SELECT COUNT(*) FROM production_plan_step_blueprints "
                "WHERE blueprint_item_id=9101"
            ).fetchone()[0],
            1,
        )

    def test_build_mode_ignores_available_intermediate_stock(self) -> None:
        import_industry_sde(self.db, **bundle())
        asset_snapshot, _ = self.publish_assets(
            7,
            [{"item_id": 8_201, "type_id": 111, "location_id": 60_003_760,
              "quantity": 100, "location_type": "station", "location_flag": "Hangar"}],
            "2026-09-15T13:00:00Z",
        )
        self.publish_locations(7, asset_snapshot, [8_201], "2026-09-15T13:01:00Z")
        save_production_plan(
            self.db,
            plan_input(stepSupplyModes=[{
                "blueprintTypeId": 110, "activity": "manufacturing",
                "productTypeId": 111, "supplyMode": "build",
            }]),
        )

        record = query_production_plans(self.db, query())["items"][0]
        decision = next(
            item for item in record["supplyDecisions"] if item["productTypeId"] == 111
        )
        step = next(item for item in record["steps"] if item["productTypeId"] == 111)

        self.assertEqual(decision["stockAvailableQuantity"], 100)
        self.assertEqual(decision["stockUsedQuantity"], 0)
        self.assertEqual(decision["buildQuantity"], 6)
        self.assertEqual(step["supplyMode"], "build")
        self.assertNotIn(111, [item["typeId"] for item in record["grossMaterials"]])

    def test_assigned_blueprint_me_changes_chain_with_exact_job_rounding(self) -> None:
        import_industry_sde(self.db, **bundle())
        snapshot_id, run_id = self.publish_blueprints(
            7,
            [
                {
                    "item_id": 1_001,
                    "type_id": 100,
                    "quantity": -2,
                    "material_efficiency": 10,
                    "time_efficiency": 20,
                    "runs": 10,
                    "location_id": 60_003_760,
                    "location_flag": "Hangar",
                },
                {
                    "item_id": 1_002,
                    "type_id": 100,
                    "quantity": -2,
                    "material_efficiency": 8,
                    "time_efficiency": 16,
                    "runs": 9,
                    "location_id": 60_003_760,
                    "location_flag": "Hangar",
                },
                {
                    "item_id": 1_003,
                    "type_id": 100,
                    "quantity": -1,
                    "material_efficiency": 5,
                    "time_efficiency": 10,
                    "runs": -1,
                    "location_id": 60_003_760,
                    "location_flag": "Hangar",
                },
            ],
            "2026-09-13T12:00:00Z",
        )
        saved = save_production_plan(
            self.db,
            plan_input(
                blueprintItemId=1_001,
                targetQuantity=20,
            ),
        )

        record = query_production_plans(self.db, query())["items"][0]

        self.assertEqual(saved["blueprintItemId"], 1_001)
        self.assertEqual(record["blueprintAssignmentState"], "ready")
        self.assertEqual(record["blueprintItemId"], 1_001)
        self.assertEqual(record["blueprintKind"], "copy")
        self.assertEqual(record["blueprintMaterialEfficiency"], 10)
        self.assertEqual(record["blueprintTimeEfficiency"], 20)
        self.assertEqual(record["blueprintRuns"], 10)
        self.assertEqual(record["appliedMaterialEfficiency"], 10)
        self.assertEqual(record["appliedTimeEfficiency"], 20)
        self.assertEqual(record["blueprintSnapshotId"], snapshot_id)
        self.assertEqual(record["blueprintSyncRunId"], run_id)
        self.assertEqual(record["blueprintObservedAt"], "2026-09-13T12:00:00Z")
        self.assertEqual(record["blueprintCandidateCount"], 3)
        self.assertEqual(
            [item["itemId"] for item in record["blueprintCandidates"]],
            [1_001, 1_003, 1_002],
        )
        self.assertFalse(record["blueprintCandidates"][2]["suitable"])
        self.assertEqual(
            record["blueprintCandidates"][2]["reason"], "runs-insufficient"
        )

        root = record["steps"][-1]
        self.assertEqual(root["blueprintTypeId"], 100)
        self.assertEqual(root["materialEfficiency"], 10)
        self.assertTrue(root["materialEfficiencyApplied"])
        self.assertEqual(root["timeEfficiency"], 20)
        self.assertTrue(root["timeEfficiencyApplied"])
        self.assertEqual(root["totalBaseTimeSeconds"], 1_000)
        self.assertEqual(root["totalBlueprintTimeSeconds"], 800)
        self.assertEqual(root["timeEfficiencySavingsSeconds"], 200)
        self.assertEqual(
            [
                (
                    material["typeId"],
                    material["quantityPerRun"],
                    material["unmodifiedGrossQuantity"],
                    material["grossQuantity"],
                    material["materialEfficiencySavings"],
                )
                for material in root["materials"]
            ],
            [(111, 3, 30, 27, 3), (121, 4, 40, 36, 4)],
        )
        self.assertEqual(
            {
                key: record["grossMaterials"][0][key]
                for key in (
                    "typeId",
                    "quantity",
                    "unmodifiedQuantity",
                    "materialEfficiencySavings",
                )
            },
            {
                "typeId": 900,
                "quantity": 120,
                "unmodifiedQuantity": 129,
                "materialEfficiencySavings": 9,
            },
        )
        self.assertEqual(
            [(step["productTypeId"], step["runs"]) for step in record["steps"]],
            [(121, 11), (111, 14), (101, 10)],
        )
        self.assertTrue(all(
            step["timeEfficiency"] == 0
            and not step["timeEfficiencyApplied"]
            and step["totalBlueprintTimeSeconds"] == step["totalBaseTimeSeconds"]
            and step["timeEfficiencySavingsSeconds"] == 0
            for step in record["steps"][:-1]
        ))
        self.assertEqual(record["totalBaseTimeSeconds"], 1_390)
        self.assertEqual(record["totalBlueprintTimeSeconds"], 1_190)
        self.assertEqual(record["timeEfficiencySavingsSeconds"], 200)

    def test_assigned_blueprint_te_uses_exact_complete_job_ceiling(self) -> None:
        source = bundle()
        source["blueprint_activities"][0]["time_seconds"] = 101
        import_industry_sde(self.db, **source)
        self.publish_blueprints(
            7,
            [{
                "item_id": 3_001,
                "type_id": 100,
                "quantity": -1,
                "material_efficiency": 0,
                "time_efficiency": 20,
                "runs": -1,
                "location_id": 60_003_760,
                "location_flag": "Hangar",
            }],
            "2026-09-14T10:00:00Z",
        )
        self.publish_skills(
            7,
            {3380: 5, 3388: 5, 45746: 3},
            "2026-09-14T10:01:00Z",
        )
        save_production_plan(
            self.db,
            plan_input(blueprintItemId=3_001, targetQuantity=3),
        )

        record = query_production_plans(self.db, query())["items"][0]
        root = record["steps"][-1]

        self.assertEqual(root["runs"], 2)
        self.assertEqual(root["totalBaseTimeSeconds"], 202)
        self.assertEqual(root["totalBlueprintTimeSeconds"], 162)
        self.assertEqual(root["timeEfficiencySavingsSeconds"], 40)
        self.assertEqual(record["totalBaseTimeSeconds"], 292)
        self.assertEqual(record["totalBlueprintTimeSeconds"], 252)
        self.assertEqual(record["timeEfficiencySavingsSeconds"], 40)
        self.assertEqual(root["totalCharacterTimeSeconds"], 110)
        self.assertEqual(root["characterSkillTimeSavingsSeconds"], 52)
        self.assertEqual(record["totalCharacterTimeSeconds"], 172)
        self.assertEqual(record["characterSkillTimeSavingsSeconds"], 80)

    def test_personal_blueprints_apply_me_and_te_to_every_assigned_chain_step(self) -> None:
        import_industry_sde(self.db, **bundle())
        self.publish_blueprints(
            7,
            [
                {
                    "item_id": 4_001,
                    "type_id": 100,
                    "quantity": -1,
                    "material_efficiency": 10,
                    "time_efficiency": 20,
                    "runs": -1,
                    "location_id": 60_003_760,
                    "location_flag": "Hangar",
                },
                {
                    "item_id": 4_002,
                    "type_id": 110,
                    "quantity": -2,
                    "material_efficiency": 10,
                    "time_efficiency": 20,
                    "runs": 14,
                    "location_id": 60_003_760,
                    "location_flag": "Hangar",
                },
                {
                    "item_id": 4_003,
                    "type_id": 120,
                    "quantity": -1,
                    "material_efficiency": 10,
                    "time_efficiency": 20,
                    "runs": -1,
                    "location_id": 60_003_760,
                    "location_flag": "Hangar",
                },
            ],
            "2026-09-14T15:00:00Z",
        )
        saved = save_production_plan(
            self.db,
            plan_input(
                blueprintItemId=4_001,
                targetQuantity=20,
                stepBlueprintAssignments=[
                    {
                        "blueprintTypeId": 110,
                        "activity": "manufacturing",
                        "productTypeId": 111,
                        "blueprintItemId": 4_002,
                    },
                    {
                        "blueprintTypeId": 120,
                        "activity": "manufacturing",
                        "productTypeId": 121,
                        "blueprintItemId": 4_003,
                    },
                ],
            ),
        )

        record = query_production_plans(self.db, query())["items"][0]

        self.assertEqual(
            [step["blueprintAssignment"]["blueprintItemId"] for step in record["steps"]],
            [4_003, 4_002, 4_001],
        )
        self.assertEqual(
            [(step["materialEfficiency"], step["timeEfficiency"]) for step in record["steps"]],
            [(10, 20), (10, 20), (10, 20)],
        )
        self.assertEqual(
            [(step["productTypeId"], step["runs"]) for step in record["steps"]],
            [(121, 10), (111, 14), (101, 10)],
        )
        self.assertEqual(record["grossMaterials"][0]["quantity"], 107)
        self.assertEqual(record["totalBaseTimeSeconds"], 1_380)
        self.assertEqual(record["totalBlueprintTimeSeconds"], 1_104)
        persisted = list(
            self.db.execute(
                "SELECT blueprint_item_id FROM production_plan_step_blueprints "
                "WHERE plan_id=? ORDER BY product_type_id",
                (saved["planId"],),
            )
        )
        self.assertEqual([int(row[0]) for row in persisted], [4_002, 4_003])

    def test_step_blueprint_assignments_reject_wrong_steps_runs_and_reuse(self) -> None:
        import_industry_sde(self.db, **bundle())
        self.publish_blueprints(
            7,
            [
                {
                    "item_id": 5_001,
                    "type_id": 110,
                    "quantity": -2,
                    "material_efficiency": 10,
                    "time_efficiency": 20,
                    "runs": 1,
                    "location_id": 60_003_760,
                    "location_flag": "Hangar",
                },
                {
                    "item_id": 5_002,
                    "type_id": 110,
                    "quantity": -1,
                    "material_efficiency": 8,
                    "time_efficiency": 16,
                    "runs": -1,
                    "location_id": 60_003_760,
                    "location_flag": "Hangar",
                },
            ],
            "2026-09-14T15:30:00Z",
        )
        with self.assertRaisesRegex(
            ProductionPlanningError, "production_blueprint_runs-insufficient"
        ):
            save_production_plan(
                self.db,
                plan_input(stepBlueprintAssignments=[{
                    "blueprintTypeId": 110,
                    "activity": "manufacturing",
                    "productTypeId": 111,
                    "blueprintItemId": 5_001,
                }]),
            )
        save_production_plan(
            self.db,
            plan_input(stepBlueprintAssignments=[{
                "blueprintTypeId": 110,
                "activity": "manufacturing",
                "productTypeId": 111,
                "blueprintItemId": 5_002,
            }]),
        )
        with self.assertRaisesRegex(
            ProductionPlanningError, "production_blueprint_already_assigned"
        ):
            save_production_plan(
                self.db,
                plan_input(stepBlueprintAssignments=[{
                    "blueprintTypeId": 110,
                    "activity": "manufacturing",
                    "productTypeId": 111,
                    "blueprintItemId": 5_002,
                }]),
            )
        with self.assertRaisesRegex(
            ProductionPlanningError, "production_blueprint_step_missing"
        ):
            save_production_plan(
                self.db,
                plan_input(stepBlueprintAssignments=[{
                    "blueprintTypeId": 110,
                    "activity": "manufacturing",
                    "productTypeId": 999,
                    "blueprintItemId": 5_001,
                }]),
            )
        with self.assertRaisesRegex(
            ProductionPlanningError, "production_plan_input_invalid"
        ):
            save_production_plan(
                self.db,
                plan_input(stepBlueprintAssignments=[{
                    "blueprintTypeId": 110,
                    "activity": "reaction",
                    "productTypeId": 111,
                    "blueprintItemId": 5_001,
                }]),
            )

    def test_personal_jobs_add_step_exact_facility_evidence_without_guessing_bonuses(self) -> None:
        import_industry_sde(self.db, **bundle())
        self.publish_blueprints(
            7,
            [{
                "item_id": 4_001,
                "type_id": 100,
                "quantity": -1,
                "material_efficiency": 10,
                "time_efficiency": 20,
                "runs": -1,
                "location_id": 60_003_760,
                "location_flag": "Hangar",
            }],
            "2026-09-14T13:00:00Z",
        )
        job_snapshot, job_run = self.publish_jobs(
            7,
            [
                industry_job(
                    blueprint_id=4_001,
                    job_id=9_000,
                    status="delivered",
                    completed_date="2026-09-14T14:31:00Z",
                ),
                industry_job(
                    blueprint_id=8_002,
                    job_id=9_001,
                    start_date="2026-09-14T15:00:00Z",
                    end_date="2026-09-14T15:30:00Z",
                ),
                industry_job(
                    blueprint_id=8_003,
                    blueprint_type_id=120,
                    product_type_id=121,
                    job_id=9_002,
                    start_date="2026-09-14T16:00:00Z",
                    end_date="2026-09-14T16:30:00Z",
                ),
            ],
            "2026-09-14T16:05:00Z",
        )
        save_production_plan(self.db, plan_input(blueprintItemId=4_001))

        without_facilities = query_production_plans(self.db, query())["items"][0]
        self.assertEqual(without_facilities["facilityState"], "missing")
        self.assertEqual(
            without_facilities["steps"][-1]["facilityEvidence"]["state"],
            "facility-snapshot-missing",
        )

        facility_snapshot, facility_run = self.publish_facilities(
            "2026-09-14T16:10:00Z"
        )
        record = query_production_plans(self.db, query())["items"][0]
        evidence_by_type = {
            step["blueprintTypeId"]: step["facilityEvidence"]
            for step in record["steps"]
        }

        self.assertEqual(record["facilityState"], "partial")
        self.assertEqual(evidence_by_type[110]["state"], "job-missing")
        self.assertEqual(evidence_by_type[120]["evidence"], "active-blueprint-type-job")
        root = evidence_by_type[100]
        self.assertEqual(root["state"], "ready")
        self.assertEqual(root["evidence"], "assigned-blueprint-job")
        self.assertEqual(root["jobId"], 9_000)
        self.assertEqual(root["jobStatus"], "delivered")
        self.assertEqual(root["facilityId"], 60_003_760)
        self.assertEqual(root["facilityName"], "Synthetic Station")
        self.assertEqual(root["facilityKind"], "station")
        self.assertEqual(root["facilityAccess"], "public")
        self.assertEqual(root["solarSystemName"], "Synthetic System")
        self.assertEqual(root["securityClass"], "unknown")
        self.assertEqual(root["systemCostIndex"], 0.0125)
        self.assertEqual((root["jobSnapshotId"], root["jobSyncRunId"]), (job_snapshot, job_run))
        self.assertEqual(
            (root["facilitySnapshotId"], root["facilitySyncRunId"]),
            (facility_snapshot, facility_run),
        )

    def test_explicit_facility_modifiers_apply_before_single_rounding(self) -> None:
        import_industry_sde(self.db, **bundle())
        asset_snapshot, _ = self.publish_assets(
            7,
            [{
                "item_id": 7_001,
                "type_id": 900,
                "location_id": 60_003_760,
                "quantity": 100,
                "location_type": "station",
                "location_flag": "Hangar",
            }],
            "2026-09-16T08:00:00Z",
        )
        self.publish_locations(
            7, asset_snapshot, [7_001], "2026-09-16T08:01:00Z"
        )
        self.publish_skills(
            7, {3380: 0, 3388: 0}, "2026-09-16T08:02:00Z"
        )

        saved = save_production_plan(
            self.db,
            plan_input(
                facilityId=60_003_760,
                facilityMaterialBonusBasisPoints=1_000,
                facilityTimeBonusBasisPoints=2_000,
            ),
        )
        page = query_production_plans(self.db, query())
        record = page["items"][0]

        self.assertEqual(saved["facilityMaterialBonusBasisPoints"], 1_000)
        self.assertEqual(saved["facilityTimeBonusBasisPoints"], 2_000)
        self.assertEqual(record["facilityModifierState"], "ready")
        self.assertEqual(record["facilityMaterialBonusBasisPoints"], 1_000)
        self.assertEqual(record["facilityTimeBonusBasisPoints"], 2_000)
        self.assertEqual(record["grossMaterials"][0]["quantity"], 25)
        self.assertEqual(record["grossMaterials"][0]["unmodifiedQuantity"], 27)
        self.assertEqual(record["grossMaterials"][0]["materialEfficiencySavings"], 2)
        self.assertEqual(record["totalCharacterTimeSeconds"], 290)
        self.assertEqual(record["totalFacilityTimeSeconds"], 232)
        self.assertEqual(record["facilityTimeSavingsSeconds"], 58)
        self.assertTrue(all(
            step["facilityModifierState"] == "ready"
            and step["facilityMaterialBonusBasisPoints"] == 1_000
            and step["facilityTimeBonusBasisPoints"] == 2_000
            and step["totalFacilityTimeSeconds"]
            == (step["totalCharacterTimeSeconds"] * 8 + 9) // 10
            for step in record["steps"]
        ))
        self.assertTrue(page["facilityModifiersApplied"])
        self.assertEqual(
            page["facilityModifierRule"],
            "explicit-basis-points-combined-before-single-ceil",
        )

    def test_installation_costs_include_system_tax_and_official_scc_surcharge(self) -> None:
        import_industry_sde(self.db, **bundle())
        asset_snapshot, _ = self.publish_assets(
            7,
            [{
                "item_id": 7_001,
                "type_id": 900,
                "location_id": 60_003_760,
                "quantity": 100,
                "location_type": "station",
                "location_flag": "Hangar",
            }],
            "2026-09-16T08:28:00Z",
        )
        self.publish_locations(
            7, asset_snapshot, [7_001], "2026-09-16T08:29:00Z"
        )
        price_snapshot, price_run = self.publish_facilities(
            "2026-09-16T08:30:00Z"
        )

        saved = save_production_plan(
            self.db,
            plan_input(
                facilityId=60_003_760,
                facilityTaxBasisPoints=100,
            ),
        )
        page = query_production_plans(self.db, query())
        record = page["items"][0]

        self.assertEqual(saved["facilityTaxBasisPoints"], 100)
        self.assertEqual(record["installationCostState"], "ready")
        self.assertEqual(record["estimatedItemValue"], 1_330)
        self.assertEqual(record["systemCost"], 18)
        self.assertEqual(record["facilityTax"], 15)
        self.assertEqual(record["sccSurcharge"], 55)
        self.assertEqual(record["estimatedInstallationCost"], 88)
        self.assertEqual(page["purchaseList"]["pricingState"], "empty")
        self.assertEqual(page["purchaseList"]["estimatedInstallationCost"], 88)
        self.assertEqual(page["purchaseList"]["additionalCapitalNeedCents"], 8_800)
        self.assertEqual(record["costedStepCount"], 3)
        self.assertEqual(record["uncostedStepCount"], 0)
        self.assertEqual(
            [step["installationCost"]["estimatedInstallationCost"] for step in record["steps"]],
            [5, 34, 49],
        )
        self.assertTrue(all(
            step["installationCost"]["state"] == "ready"
            and step["installationCost"]["facilityTaxBasisPoints"] == 100
            and step["installationCost"]["sccSurchargeBasisPoints"] == 400
            and step["installationCost"]["systemCostIndex"] == 0.0125
            and step["installationCost"]["priceSnapshotId"] == price_snapshot
            and step["installationCost"]["priceSyncRunId"] == price_run
            for step in record["steps"]
        ))
        self.assertTrue(page["installationCostsApplied"])
        self.assertEqual(
            page["installationCostRule"],
            "base-material-adjusted-price-times-runs-system-index-plus-explicit-tax-"
            "plus-scc-4-percent-ceil",
        )

        save_production_plan(
            self.db,
            plan_input(
                planId=saved["planId"],
                facilityId=60_003_760,
                facilityTaxBasisPoints=None,
            ),
        )
        unconfigured = query_production_plans(self.db, query())["items"][0]
        self.assertEqual(unconfigured["installationCostState"], "unconfigured")
        self.assertIsNone(unconfigured["estimatedInstallationCost"])
        self.assertTrue(all(
            step["installationCost"]["state"] == "unconfigured"
            for step in unconfigured["steps"]
        ))

    def test_facility_profile_does_not_cross_activity_boundaries(self) -> None:
        mixed_bundle = bundle()
        mixed_bundle["blueprint_activities"][0]["materials"].append(
            {"type_id": 201, "quantity": 1}
        )
        import_industry_sde(self.db, **mixed_bundle)
        asset_snapshot, _ = self.publish_assets(
            7,
            [{
                "item_id": 7_001,
                "type_id": 901,
                "location_id": 60_003_760,
                "quantity": 100,
                "location_type": "station",
                "location_flag": "Hangar",
            }],
            "2026-09-16T09:00:00Z",
        )
        self.publish_locations(
            7, asset_snapshot, [7_001], "2026-09-16T09:01:00Z"
        )
        self.publish_skills(
            7, {3380: 0, 3388: 0, 45746: 0}, "2026-09-16T09:02:00Z"
        )
        save_production_plan(
            self.db,
            plan_input(
                facilityId=60_003_760,
                facilityMaterialBonusBasisPoints=1_000,
                facilityTimeBonusBasisPoints=2_000,
            ),
        )

        record = query_production_plans(self.db, query())["items"][0]
        reaction = next(
            step for step in record["steps"] if step["activity"] == "reaction"
        )
        reaction_gas = next(
            material for material in reaction["materials"] if material["typeId"] == 901
        )

        self.assertEqual(record["facilityModifierState"], "ready")
        self.assertIsNone(record["totalFacilityTimeSeconds"])
        self.assertEqual(reaction["facilityModifierState"], "activity-mismatch")
        self.assertIsNone(reaction["facilityMaterialBonusBasisPoints"])
        self.assertIsNone(reaction["facilityTimeBonusBasisPoints"])
        self.assertIsNone(reaction["totalFacilityTimeSeconds"])
        self.assertEqual(reaction_gas["grossQuantity"], 100)
        self.assertTrue(any(
            step["facilityModifierState"] == "ready"
            and step["totalFacilityTimeSeconds"] is not None
            for step in record["steps"]
        ))

    def test_active_character_skills_apply_to_every_matching_step(self) -> None:
        import_industry_sde(self.db, **bundle())
        snapshot_id, run_id = self.publish_skills(
            7,
            {3380: 5, 3388: 5, 45746: 2},
            "2026-09-14T11:00:00Z",
        )
        save_production_plan(self.db, plan_input())

        record = query_production_plans(self.db, query())["items"][0]

        self.assertEqual(record["characterSkillState"], "ready")
        self.assertEqual(record["skillSnapshotId"], snapshot_id)
        self.assertEqual(record["skillSyncRunId"], run_id)
        self.assertEqual(record["skillObservedAt"], "2026-09-14T11:00:00Z")
        self.assertEqual(
            [step["totalCharacterTimeSeconds"] for step in record["steps"]],
            [21, 41, 136],
        )
        self.assertTrue(all(
            step["characterSkillTimeApplied"] for step in record["steps"]
        ))
        self.assertEqual(
            record["steps"][0]["timeSkills"],
            [
                {
                    "skillId": 3380,
                    "skillName": "Industry",
                    "activeLevel": 5,
                    "percentPerLevel": 4,
                },
                {
                    "skillId": 3388,
                    "skillName": "Advanced Industry",
                    "activeLevel": 5,
                    "percentPerLevel": 3,
                },
            ],
        )
        self.assertEqual(record["totalCharacterTimeSeconds"], 198)
        self.assertEqual(record["characterSkillTimeSavingsSeconds"], 92)

    def test_reactions_use_only_the_active_reactions_skill(self) -> None:
        import_industry_sde(self.db, **bundle())
        self.publish_skills(
            7,
            {3380: 5, 3388: 5, 45746: 5},
            "2026-09-14T11:30:00Z",
        )
        save_production_plan(
            self.db,
            plan_input(
                blueprintTypeId=200,
                activity="reaction",
                productTypeId=201,
                targetQuantity=200,
            ),
        )

        record = query_production_plans(self.db, query())["items"][0]
        step = record["steps"][0]

        self.assertEqual(step["timeSkills"], [{
            "skillId": 45746,
            "skillName": "Reactions",
            "activeLevel": 5,
            "percentPerLevel": 4,
        }])
        self.assertEqual(step["totalBlueprintTimeSeconds"], 60)
        self.assertEqual(step["totalCharacterTimeSeconds"], 48)
        self.assertEqual(step["characterSkillTimeSavingsSeconds"], 12)
        self.assertEqual(record["totalCharacterTimeSeconds"], 48)

    def test_newer_failed_skill_sync_does_not_replace_complete_evidence(self) -> None:
        import_industry_sde(self.db, **bundle())
        snapshot_id, run_id = self.publish_skills(
            7,
            {3380: 4, 3388: 2},
            "2026-09-14T12:00:00Z",
        )
        self.publish_skills(
            7,
            {3380: 5, 3388: 5},
            "2026-09-14T12:05:00Z",
            status="failed",
        )
        save_production_plan(self.db, plan_input())

        record = query_production_plans(self.db, query())["items"][0]

        self.assertEqual(record["skillSnapshotId"], snapshot_id)
        self.assertEqual(record["skillSyncRunId"], run_id)
        self.assertEqual(
            [skill["activeLevel"] for skill in record["steps"][0]["timeSkills"]],
            [4, 2],
        )

    def test_invalid_complete_skill_snapshot_fails_closed(self) -> None:
        import_industry_sde(self.db, **bundle())
        snapshot_id, _ = self.publish_skills(
            7,
            {3380: 5, 3388: 5},
            "2026-09-14T12:30:00Z",
        )
        save_production_plan(self.db, plan_input())
        self.db.execute(
            "UPDATE cached_snapshots SET payload_json=? WHERE id=?",
            (
                json.dumps({
                    "characterId": 7,
                    "skills": [{
                        "active_skill_level": 6,
                        "skill_id": 3380,
                        "skillpoints_in_skill": 1_000,
                        "trained_skill_level": 5,
                    }],
                    "total_sp": 1_000,
                    "unallocated_sp": 0,
                }),
                snapshot_id,
            ),
        )

        with self.assertRaisesRegex(
            ProductionPlanningError, "production_skill_snapshot_invalid"
        ):
            query_production_plans(self.db, query())

    def test_blueprint_assignment_states_and_duplicate_use_are_fail_closed(self) -> None:
        import_industry_sde(self.db, **bundle())
        blueprint = {
            "item_id": 2_001,
            "type_id": 100,
            "quantity": -2,
            "material_efficiency": 10,
            "time_efficiency": 20,
            "runs": 10,
            "location_id": 60_003_760,
            "location_flag": "Hangar",
        }
        self.publish_blueprints(7, [blueprint], "2026-09-13T12:00:00Z")
        first = save_production_plan(
            self.db,
            plan_input(blueprintItemId=2_001, targetQuantity=20),
        )
        with self.assertRaisesRegex(
            ProductionPlanningError, "production_blueprint_already_assigned"
        ):
            save_production_plan(
                self.db,
                plan_input(
                    blueprintItemId=2_001,
                    targetQuantity=2,
                    note="duplicate",
                ),
            )
        with self.assertRaisesRegex(
            ProductionPlanningError, "production_blueprint_runs-insufficient"
        ):
            save_production_plan(
                self.db,
                plan_input(
                    planId=first["planId"],
                    blueprintItemId=2_001,
                    targetQuantity=22,
                ),
            )

        changed = {**blueprint, "type_id": 110}
        self.publish_blueprints(7, [changed], "2026-09-13T13:00:00Z")
        mismatch = query_production_plans(self.db, query())["items"][0]
        self.assertEqual(mismatch["blueprintAssignmentState"], "type-mismatch")
        self.assertEqual(mismatch["appliedMaterialEfficiency"], 0)
        self.assertEqual(mismatch["grossMaterials"][0]["quantity"], 129)

        self.publish_blueprints(7, [], "2026-09-13T14:00:00Z")
        missing = query_production_plans(self.db, query())["items"][0]
        self.assertEqual(missing["blueprintAssignmentState"], "missing")
        self.assertEqual(missing["blueprintCandidateCount"], 0)

    def test_complete_asset_snapshots_expose_shortage_locations_and_other_owner_stock(self) -> None:
        import_industry_sde(self.db, **bundle())
        self.db.execute("INSERT INTO characters(character_id,name) VALUES (8,'Synthetic Hauler')")
        owner_snapshot, owner_run = self.publish_assets(
            7,
            [
                {
                    "item_id": 7_001,
                    "type_id": 900,
                    "location_id": 60_003_760,
                    "location_type": "station",
                    "location_flag": "Hangar",
                    "quantity": 20,
                },
                {
                    "item_id": 7_002,
                    "type_id": 900,
                    "location_id": 60_003_760,
                    "location_type": "station",
                    "location_flag": "Hangar",
                    "quantity": 3,
                },
            ],
            "2026-09-13T09:00:00Z",
        )
        self.publish_locations(
            7, owner_snapshot, [7_001, 7_002], "2026-09-13T09:01:00Z"
        )
        excluded_snapshot, _ = self.publish_assets(
            8,
            [
                {
                    "item_id": 8_001,
                    "type_id": 900,
                    "location_id": 60_003_760,
                    "location_type": "station",
                    "location_flag": "Hangar",
                    "quantity": 100,
                }
            ],
            "2026-09-13T08:00:00Z",
        )
        self.publish_locations(8, excluded_snapshot, [8_001], "2026-09-13T08:01:00Z")
        self.publish_assets(
            7,
            [
                {
                    "item_id": 7_999,
                    "type_id": 900,
                    "location_id": 60_003_760,
                    "location_type": "station",
                    "location_flag": "Hangar",
                    "quantity": 999,
                }
            ],
            "2026-09-13T10:00:00Z",
            status="failed",
        )
        save_production_plan(self.db, plan_input())

        record = query_production_plans(self.db, query())["items"][0]

        self.assertEqual(record["inventoryState"], "shortage")
        self.assertEqual(record["assetSnapshotId"], owner_snapshot)
        self.assertEqual(record["assetSyncRunId"], owner_run)
        self.assertEqual(record["assetObservedAt"], "2026-09-13T09:00:00Z")
        material = record["grossMaterials"][0]
        self.assertEqual(
            (
                material["quantity"],
                material["availableQuantity"],
                material["missingQuantity"],
                material["availabilityState"],
            ),
            (27, 23, 4, "shortage"),
        )
        self.assertEqual(material["availablePositionCount"], 2)
        self.assertEqual(material["availableLocationCount"], 1)
        self.assertEqual(material["availableLocations"][0]["quantity"], 23)
        self.assertEqual(material["reservedQuantity"], 23)
        self.assertEqual(material["reservedByPriorPlansQuantity"], 0)
        self.assertEqual(material["remainingQuantity"], 0)
        self.assertEqual(material["inventoryShortageQuantity"], 4)
        self.assertEqual(material["reservationConflictQuantity"], 0)
        self.assertEqual(material["priorReservationCount"], 0)
        self.assertEqual(material["priorReservations"], [])
        self.assertEqual(
            material["availableLocations"][0]["locationPath"],
            "Synthetic System / Synthetic Station",
        )
        self.assertEqual(material["excludedQuantity"], 100)
        self.assertEqual(material["excludedPositionCount"], 1)
        self.assertEqual(material["excludedLocationCount"], 1)
        self.assertEqual(material["excludedLocations"][0]["ownerCharacterId"], 8)

        save_production_plan(
            self.db,
            plan_input(planId=record["planId"], targetQuantity=1),
        )
        covered = query_production_plans(self.db, query())["items"][0]
        self.assertEqual(covered["inventoryState"], "covered")
        self.assertEqual(covered["grossMaterials"][0]["missingQuantity"], 0)
        self.assertEqual(covered["grossMaterials"][0]["reservedQuantity"], 18)
        self.assertEqual(covered["grossMaterials"][0]["remainingQuantity"], 5)

    def test_priority_reservations_prevent_cross_goal_double_use(self) -> None:
        import_industry_sde(self.db, **bundle())
        self.publish_assets(
            7,
            [
                {
                    "item_id": 7_001,
                    "type_id": 901,
                    "location_id": 60_003_760,
                    "location_type": "station",
                    "location_flag": "Hangar",
                    "quantity": 150,
                }
            ],
            "2026-09-13T10:00:00Z",
        )
        first = save_production_plan(
            self.db,
            plan_input(
                blueprintTypeId=200,
                activity="reaction",
                productTypeId=201,
                targetQuantity=200,
                priority=20,
                note="first",
            ),
        )
        second = save_production_plan(
            self.db,
            plan_input(
                blueprintTypeId=200,
                activity="reaction",
                productTypeId=201,
                targetQuantity=200,
                priority=10,
                note="second",
            ),
        )

        page = query_production_plans(self.db, query())
        records = {item["planId"]: item for item in page["items"]}
        first_material = records[first["planId"]]["grossMaterials"][0]
        second_material = records[second["planId"]]["grossMaterials"][0]

        self.assertEqual(
            (
                first_material["availableQuantity"],
                first_material["reservedByPriorPlansQuantity"],
                first_material["reservedQuantity"],
                first_material["remainingQuantity"],
                first_material["missingQuantity"],
            ),
            (150, 0, 100, 50, 0),
        )
        self.assertEqual(
            (
                second_material["availableQuantity"],
                second_material["reservedByPriorPlansQuantity"],
                second_material["reservedQuantity"],
                second_material["remainingQuantity"],
                second_material["inventoryShortageQuantity"],
                second_material["reservationConflictQuantity"],
                second_material["missingQuantity"],
            ),
            (150, 100, 50, 0, 0, 50, 50),
        )
        self.assertEqual(second_material["priorReservationCount"], 1)
        self.assertEqual(
            second_material["priorReservations"],
            [
                {
                    "planId": first["planId"],
                    "productTypeId": 201,
                    "productName": "Synthetic Composite",
                    "priority": 20,
                    "quantity": 100,
                    "createdAt": records[first["planId"]]["createdAt"],
                }
            ],
        )
        filtered = query_production_plans(self.db, query(search="second"))
        self.assertEqual(filtered["total"], 1)
        self.assertEqual(
            filtered["items"][0]["grossMaterials"][0]["priorReservations"][0][
                "planId"
            ],
            first["planId"],
        )

        save_production_plan(
            self.db,
            plan_input(
                planId=second["planId"],
                blueprintTypeId=200,
                activity="reaction",
                productTypeId=201,
                targetQuantity=200,
                priority=30,
                note="second",
            ),
        )
        reordered = {
            item["planId"]: item
            for item in query_production_plans(self.db, query())["items"]
        }
        self.assertEqual(
            reordered[second["planId"]]["grossMaterials"][0]["reservedQuantity"],
            100,
        )
        self.assertEqual(
            reordered[first["planId"]]["grossMaterials"][0][
                "reservationConflictQuantity"
            ],
            50,
        )
        self.assertEqual(
            reordered[first["planId"]]["grossMaterials"][0]["priorReservations"][
                0
            ]["planId"],
            second["planId"],
        )

        save_production_plan(
            self.db,
            plan_input(
                planId=second["planId"],
                blueprintTypeId=200,
                activity="reaction",
                productTypeId=201,
                targetQuantity=200,
                priority=20,
                note="second",
            ),
        )
        equal_priority_page = query_production_plans(self.db, query())
        self.assertEqual(
            [item["planId"] for item in equal_priority_page["items"]],
            [first["planId"], second["planId"]],
        )
        equal_priority = {
            item["planId"]: item for item in equal_priority_page["items"]
        }
        self.assertEqual(
            equal_priority[first["planId"]]["grossMaterials"][0][
                "reservedQuantity"
            ],
            100,
        )
        self.assertEqual(
            equal_priority[second["planId"]]["grossMaterials"][0][
                "reservationConflictQuantity"
            ],
            50,
        )

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
            query(marketHubId="unknown"),
            query(tradeCostMode="invented"),
            query(salesCharacterId=True),
            query(tradeCostMode="automatic", brokerFeeBasisPoints=300),
            query(brokerFeeBasisPoints=-1),
            query(salesTaxBasisPoints=10_001),
        ]
        for payload in invalid_queries:
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ProductionPlanningError, "production_plan_query_invalid"):
                    validate_production_plan_query(payload)
        with self.assertRaisesRegex(ProductionPlanningError, "production_plan_input_invalid"):
            validate_production_plan_input(plan_input(targetQuantity=0))
        with self.assertRaisesRegex(ProductionPlanningError, "production_plan_input_invalid"):
            validate_production_plan_input(plan_input(materialLocationId=7_000))
        with self.assertRaisesRegex(ProductionPlanningError, "production_plan_input_invalid"):
            validate_production_plan_input(
                plan_input(facilityMaterialBonusBasisPoints=100)
            )
        with self.assertRaisesRegex(ProductionPlanningError, "production_plan_input_invalid"):
            validate_production_plan_input(
                plan_input(
                    facilityId=60_003_760,
                    facilityMaterialBonusBasisPoints=5_001,
                    facilityTimeBonusBasisPoints=0,
                )
            )
        with self.assertRaisesRegex(ProductionPlanningError, "production_sde_unavailable"):
            save_production_plan(self.db, plan_input())
        import_industry_sde(self.db, **bundle())
        with self.assertRaisesRegex(
            ProductionPlanningError, "production_location_selection_invalid"
        ):
            save_production_plan(self.db, plan_input(facilityId=60_003_760))
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
