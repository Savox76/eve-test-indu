from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from new_eden_foundry_backend.blueprint_sync import sync_character_blueprints
from new_eden_foundry_backend.character_skill_sync import sync_character_skills
from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.identity import upsert_character
from new_eden_foundry_backend.industry_job_sync import sync_character_industry_jobs
from new_eden_foundry_backend.research_planning import (
    ResearchPlanningError,
    delete_research_plan,
    query_research_plans,
    save_research_plan,
)


CHARACTER_ID = 90_000_101


class Response:
    def __init__(self, payload, headers=None):
        self.payload = payload
        self.headers = headers or {}


class StaticClient:
    def __init__(self, payload):
        self.payload = payload

    def get_json(self, _path, **_kwargs):
        return Response(self.payload)


def blueprint(item_id=7_001, type_id=6_001, *, quantity=-1, me=4, te=8):
    return {
        "item_id": item_id,
        "type_id": type_id,
        "location_id": 60_000_001,
        "location_flag": "Hangar",
        "quantity": quantity,
        "time_efficiency": te,
        "material_efficiency": me,
        "runs": -1 if quantity == -1 else 10,
    }


def skills(*, laboratory=3, advanced=2, research=4, metallurgy=5):
    levels = ((3403, research), (3406, laboratory), (3409, metallurgy), (24624, advanced))
    records = [
        {
            "active_skill_level": level,
            "skill_id": skill_id,
            "skillpoints_in_skill": 100 * (index + 1),
            "trained_skill_level": level,
        }
        for index, (skill_id, level) in enumerate(levels)
    ]
    return {"skills": records, "total_sp": sum(item["skillpoints_in_skill"] for item in records)}


def job(job_id=8_001, *, blueprint_id=7_001, activity_id=4, status="active"):
    return {
        "activity_id": activity_id,
        "blueprint_id": blueprint_id,
        "blueprint_location_id": 60_000_001,
        "blueprint_type_id": 6_001,
        "cost": 125_000.5,
        "duration": 7_200,
        "end_date": "2026-09-11T14:00:00Z",
        "facility_id": 60_000_001,
        "installer_id": CHARACTER_ID,
        "job_id": job_id,
        "output_location_id": 60_000_001,
        "runs": 1,
        "start_date": "2026-09-11T12:00:00Z",
        "station_id": 60_000_001,
        "status": status,
    }


def query(**overrides):
    value = {
        "search": "",
        "ownerCharacterId": None,
        "state": None,
        "plannedOnly": False,
        "includeMaxed": False,
        "offset": 0,
        "limit": 100,
        "sortBy": "priority",
        "sortDirection": "desc",
    }
    value.update(overrides)
    return value


def plan(**overrides):
    value = {
        "ownerCharacterId": CHARACTER_ID,
        "blueprintItemId": 7_001,
        "nextActivity": "material",
        "targetMaterialEfficiency": 10,
        "targetTimeEfficiency": 20,
        "priority": 50,
        "note": "  Capital component first  ",
    }
    value.update(overrides)
    return value


class ResearchPlanningTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "foundry.sqlite3"
        initialize_database(self.database_path)
        self.db = connect_database(self.database_path)
        upsert_character(
            self.db,
            character_id=CHARACTER_ID,
            name="Research Pilot",
            account_group_id=None,
            scopes=(),
        )
        self.db.execute(
            "INSERT INTO resolved_type_names(type_id,name) VALUES(6001,'Synthetic Cruiser Blueprint')"
        )

    def tearDown(self):
        self.db.close()
        self.temporary_directory.cleanup()

    def sync_sources(self, *, blueprints=None, skill_payload=None, jobs=None):
        sync_character_blueprints(
            self.db,
            StaticClient([blueprint()] if blueprints is None else blueprints),
            CHARACTER_ID,
        )
        if skill_payload is not False:
            sync_character_skills(
                self.db,
                StaticClient(skills() if skill_payload is None else skill_payload),
                CHARACTER_ID,
            )
        sync_character_industry_jobs(
            self.db,
            StaticClient([] if jobs is None else jobs),
            CHARACTER_ID,
        )

    def test_saved_plan_reports_targets_skills_slots_and_source_ids(self):
        self.sync_sources()
        saved = save_research_plan(self.db, plan())
        page = query_research_plans(
            self.db,
            query(plannedOnly=True),
            now=datetime(2026, 9, 11, 13, tzinfo=timezone.utc),
        )

        self.assertTrue(saved["saved"])
        self.assertEqual(saved["note"], "Capital component first")
        self.assertEqual(page["total"], 1)
        self.assertFalse(page["estimatesAvailable"])
        self.assertEqual(page["summary"]["ready"], 1)
        record = page["items"][0]
        self.assertEqual(record["state"], "ready")
        self.assertEqual(record["blueprintName"], "Synthetic Cruiser Blueprint")
        self.assertEqual((record["currentMaterialEfficiency"], record["targetMaterialEfficiency"]), (4, 10))
        self.assertEqual((record["currentTimeEfficiency"], record["targetTimeEfficiency"]), (8, 20))
        self.assertEqual((record["slotCapacity"], record["slotsUsed"], record["slotsAvailable"]), (6, 0, 6))
        self.assertEqual((record["researchLevel"], record["metallurgyLevel"]), (4, 5))
        self.assertGreater(record["blueprintSnapshotId"], 0)
        self.assertGreater(record["skillSnapshotId"], 0)
        self.assertGreater(record["jobSnapshotId"], 0)

    def test_active_research_job_is_running_and_uses_observed_job_values(self):
        self.sync_sources(jobs=[job()])
        save_research_plan(self.db, plan())
        record = query_research_plans(self.db, query())["items"][0]

        self.assertEqual(record["state"], "running")
        self.assertEqual(record["activeJobId"], 8_001)
        self.assertEqual(record["activeJobActivity"], "material")
        self.assertEqual(record["activeJobCost"], 125_000.5)
        self.assertEqual(record["facilityId"], 60_000_001)
        self.assertEqual(record["facilityEvidence"], "active-job")
        self.assertIsNone(record["facilityName"])

    def test_full_science_slot_capacity_queues_a_plan(self):
        self.sync_sources(
            skill_payload=skills(laboratory=0, advanced=0),
            jobs=[job(8_002, blueprint_id=9_999, activity_id=5)],
        )
        save_research_plan(self.db, plan())
        record = query_research_plans(self.db, query())["items"][0]

        self.assertEqual(record["state"], "queued")
        self.assertEqual((record["slotCapacity"], record["slotsUsed"], record["slotsAvailable"]), (1, 1, 0))

    def test_plan_without_skill_snapshot_is_unverified(self):
        self.sync_sources(skill_payload=False)
        save_research_plan(self.db, plan())
        record = query_research_plans(self.db, query())["items"][0]

        self.assertEqual(record["state"], "unverified")
        self.assertIsNone(record["slotCapacity"])
        self.assertIsNone(record["skillSnapshotId"])

    def test_stacked_originals_are_plannable_and_maxed_bpos_are_hidden_by_default(self):
        self.sync_sources(blueprints=[blueprint(quantity=3, me=10, te=20)])

        self.assertEqual(query_research_plans(self.db, query())["total"], 0)
        visible = query_research_plans(self.db, query(includeMaxed=True))
        self.assertEqual(visible["total"], 1)
        self.assertTrue(visible["items"][0]["blueprintPresent"])

    def test_disappeared_blueprint_keeps_saved_plan_and_can_be_deleted(self):
        self.sync_sources()
        save_research_plan(self.db, plan())
        sync_character_blueprints(self.db, StaticClient([]), CHARACTER_ID)

        record = query_research_plans(self.db, query(plannedOnly=True))["items"][0]
        self.assertEqual(record["state"], "missing")
        self.assertFalse(record["blueprintPresent"])
        deleted = delete_research_plan(
            self.db,
            {"ownerCharacterId": CHARACTER_ID, "blueprintItemId": 7_001},
        )
        self.assertTrue(deleted["deleted"])
        self.assertEqual(query_research_plans(self.db, query(plannedOnly=True))["total"], 0)

    def test_invalid_target_bpc_and_query_fail_closed(self):
        self.sync_sources()
        with self.assertRaisesRegex(ResearchPlanningError, "research_target_below_current"):
            save_research_plan(self.db, plan(targetMaterialEfficiency=3))
        with self.assertRaisesRegex(ResearchPlanningError, "research_plan_invalid"):
            save_research_plan(self.db, plan(nextActivity="copying"))
        with self.assertRaisesRegex(ResearchPlanningError, "research_query_invalid"):
            query_research_plans(self.db, {**query(), "extra": True})

        sync_character_blueprints(
            self.db,
            StaticClient([blueprint(item_id=7_002, quantity=-2)]),
            CHARACTER_ID,
        )
        with self.assertRaisesRegex(ResearchPlanningError, "research_blueprint_not_found"):
            save_research_plan(self.db, plan(blueprintItemId=7_002))

    def test_plan_rows_are_removed_with_the_character(self):
        self.sync_sources()
        save_research_plan(self.db, plan())
        self.db.execute("DELETE FROM characters WHERE character_id=?", (CHARACTER_ID,))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM research_plans").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
