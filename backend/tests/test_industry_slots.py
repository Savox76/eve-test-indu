from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from new_eden_foundry_backend.blueprint_sync import sync_character_blueprints
from new_eden_foundry_backend.character_skill_sync import sync_character_skills
from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.identity import upsert_character
from new_eden_foundry_backend.industry_job_sync import sync_character_industry_jobs
from new_eden_foundry_backend.industry_slots import (
    IndustrySlotError,
    query_industry_slots,
)
from new_eden_foundry_backend.production_planning import save_production_plan
from new_eden_foundry_backend.research_planning import save_research_plan
from new_eden_foundry_backend.sde import import_industry_sde


CHARACTER_ID = 90_000_201
SECOND_CHARACTER_ID = 90_000_202


class Response:
    def __init__(self, payload):
        self.payload = payload
        self.headers = {}


class StaticClient:
    def __init__(self, payload):
        self.payload = payload

    def get_json(self, _path, **_kwargs):
        return Response(self.payload)


def skill_payload():
    levels = (
        (3387, 4),
        (24625, 2),
        (45748, 3),
        (45749, 1),
        (3406, 3),
        (24624, 2),
    )
    return {
        "skills": [
            {
                "active_skill_level": level,
                "skill_id": skill_id,
                "skillpoints_in_skill": 100 * (index + 1),
                "trained_skill_level": level,
            }
            for index, (skill_id, level) in enumerate(levels)
        ],
        "total_sp": 2_100,
    }


def blueprint(item_id):
    return {
        "item_id": item_id,
        "type_id": 6_001,
        "location_id": 60_000_001,
        "location_flag": "Hangar",
        "quantity": -1,
        "time_efficiency": 8,
        "material_efficiency": 4,
        "runs": -1,
    }


def job(job_id, activity_id, status="active", *, blueprint_id=None, end_date=None):
    return {
        "activity_id": activity_id,
        "blueprint_id": blueprint_id or 70_000 + job_id,
        "blueprint_location_id": 60_000_001,
        "blueprint_type_id": 6_001,
        "cost": 1_000.0,
        "duration": 3_600,
        "end_date": end_date or f"2026-09-11T{12 + job_id % 4:02d}:00:00Z",
        "facility_id": 60_000_001,
        "installer_id": CHARACTER_ID,
        "job_id": job_id,
        "output_location_id": 60_000_001,
        "runs": 1,
        "start_date": "2026-09-11T10:00:00Z",
        "station_id": 60_000_001,
        "status": status,
    }


def query(**overrides):
    value = {"ownerCharacterId": None, "offset": 0, "limit": 100}
    value.update(overrides)
    return value


class IndustrySlotTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "foundry.sqlite3"
        initialize_database(self.database_path)
        self.db = connect_database(self.database_path)
        upsert_character(
            self.db,
            character_id=CHARACTER_ID,
            name="Slot Pilot",
            account_group_id=None,
            scopes=(),
        )
        upsert_character(
            self.db,
            character_id=SECOND_CHARACTER_ID,
            name="No Snapshot Pilot",
            account_group_id=None,
            scopes=(),
        )

    def tearDown(self):
        self.db.close()
        self.temporary_directory.cleanup()

    def sync_sources(self):
        sync_character_skills(self.db, StaticClient(skill_payload()), CHARACTER_ID)
        sync_character_blueprints(
            self.db,
            StaticClient([blueprint(7_001), blueprint(7_002), blueprint(7_003)]),
            CHARACTER_ID,
        )
        sync_character_industry_jobs(
            self.db,
            StaticClient(
                [
                    job(8_001, 1, end_date="2026-09-11T12:00:00Z"),
                    job(8_002, 1, "ready"),
                    job(8_003, 9),
                    job(8_004, 5),
                    job(8_005, 4, blueprint_id=7_001),
                ]
            ),
            CHARACTER_ID,
        )
        for item_id in (7_001, 7_002, 7_003):
            save_research_plan(
                self.db,
                {
                    "ownerCharacterId": CHARACTER_ID,
                    "blueprintItemId": item_id,
                    "nextActivity": "material",
                    "targetMaterialEfficiency": 10,
                    "targetTimeEfficiency": 20,
                    "priority": 50,
                    "note": None,
                },
            )
        sync_character_blueprints(
            self.db,
            StaticClient([blueprint(7_001), blueprint(7_002)]),
            CHARACTER_ID,
        )

    def test_combines_real_capacity_occupancy_and_research_queue(self):
        self.sync_sources()
        import_industry_sde(
            self.db,
            build_number="synthetic-slot-production-1",
            groups=[{"group_id": 1, "name": "Synthetic industry"}],
            types=[
                {"type_id": 6_001, "group_id": 1, "name": "Synthetic Blueprint"},
                {"type_id": 6_002, "group_id": 1, "name": "Synthetic Product"},
                {"type_id": 6_003, "group_id": 1, "name": "Synthetic Material"},
            ],
            locations=[
                {
                    "location_id": 30_000_142,
                    "name": "Synthetic System",
                    "kind": "solar_system",
                }
            ],
            blueprint_activities=[
                {
                    "blueprint_type_id": 6_001,
                    "activity": activity,
                    "time_seconds": 60,
                    "products": [{"type_id": 6_002, "quantity": 1}],
                    "materials": [{"type_id": 6_003, "quantity": 2}],
                }
                for activity in ("manufacturing", "reaction")
            ],
        )
        for activity in ("manufacturing", "reaction"):
            save_production_plan(
                self.db,
                {
                    "planId": None,
                    "ownerCharacterId": CHARACTER_ID,
                    "blueprintTypeId": 6_001,
                    "activity": activity,
                    "productTypeId": 6_002,
                    "targetQuantity": 1,
                    "priority": 50,
                    "note": None,
                },
            )
        page = query_industry_slots(
            self.db,
            query(ownerCharacterId=CHARACTER_ID),
            now=datetime(2026, 9, 11, 11, tzinfo=timezone.utc),
        )

        self.assertEqual(page["total"], 1)
        self.assertEqual(len(page["owners"]), 2)
        record = page["items"][0]
        activities = {item["activity"]: item for item in record["activities"]}
        self.assertEqual(
            (activities["manufacturing"]["capacity"], activities["manufacturing"]["occupied"]),
            (7, 2),
        )
        self.assertEqual(
            (activities["reactions"]["capacity"], activities["reactions"]["available"]),
            (5, 4),
        )
        self.assertEqual(
            (activities["science"]["capacity"], activities["science"]["occupied"]),
            (6, 2),
        )
        self.assertEqual(
            (
                activities["science"]["runningPlans"],
                activities["science"]["queuedPlans"],
                activities["science"]["blockedPlans"],
            ),
            (1, 1, 1),
        )
        self.assertEqual(activities["manufacturing"]["readyJobs"], 1)
        self.assertEqual(activities["manufacturing"]["runningPlans"], 1)
        self.assertEqual(activities["reactions"]["runningPlans"], 1)
        self.assertEqual(
            activities["manufacturing"]["nextJobEndDate"],
            "2026-09-11T12:00:00Z",
        )
        self.assertGreater(record["skillSnapshotId"], 0)
        self.assertGreater(record["jobSnapshotId"], 0)

    def test_missing_snapshots_remain_unknown_instead_of_zero(self):
        page = query_industry_slots(self.db, query(ownerCharacterId=SECOND_CHARACTER_ID))
        activity = page["items"][0]["activities"][0]

        self.assertIsNone(activity["capacity"])
        self.assertIsNone(activity["occupied"])
        self.assertIsNone(activity["available"])
        self.assertEqual(activity["utilizationState"], "unknown")
        self.assertIsNone(page["items"][0]["observedAt"])

    def test_skill_capacity_and_job_occupancy_are_independently_evidenced(self):
        sync_character_skills(self.db, StaticClient(skill_payload()), CHARACTER_ID)
        page = query_industry_slots(self.db, query(ownerCharacterId=CHARACTER_ID))
        manufacturing = page["items"][0]["activities"][0]

        self.assertEqual(manufacturing["capacity"], 7)
        self.assertIsNone(manufacturing["occupied"])
        self.assertIsNone(manufacturing["available"])
        self.assertEqual(manufacturing["utilizationState"], "unknown")

    def test_query_is_strict_and_bounded(self):
        with self.assertRaisesRegex(IndustrySlotError, "industry_slot_query_invalid"):
            query_industry_slots(self.db, {**query(), "extra": True})
        with self.assertRaisesRegex(IndustrySlotError, "industry_slot_query_invalid"):
            query_industry_slots(self.db, query(limit=201))


if __name__ == "__main__":
    unittest.main()
