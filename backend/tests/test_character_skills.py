from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from new_eden_foundry_backend.character_skill_sync import (
    CharacterSkillSyncError,
    sync_character_skills,
)
from new_eden_foundry_backend.character_skill_view import (
    CharacterSkillViewError,
    query_character_skills,
)
from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.esi_client import EsiClientError, EsiResponse


CHARACTER_ID = 90_000_001


class FakeClient:
    def __init__(self, payload, *, fail=False):
        self.payload = payload
        self.fail = fail
        self.calls = []

    def get_json(self, path, *, query=None, character_id, required_scopes):
        self.calls.append((path, query, character_id, required_scopes))
        if self.fail:
            raise EsiClientError("esi-network-unavailable", retryable=True)
        return EsiResponse(200, self.payload, {}, False)


def skill(skill_id, *, trained=5, active=5, skillpoints=256_000):
    return {
        "active_skill_level": active,
        "skill_id": skill_id,
        "skillpoints_in_skill": skillpoints,
        "trained_skill_level": trained,
    }


def payload(*skills, unallocated=0):
    return {
        "skills": list(skills),
        "total_sp": sum(item["skillpoints_in_skill"] for item in skills),
        "unallocated_sp": unallocated,
    }


class CharacterSkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "foundry.db"
        initialize_database(self.path)
        self.db = connect_database(self.path)
        self.db.execute(
            "INSERT INTO characters(character_id,name) VALUES(?,?)",
            (CHARACTER_ID, "Skill Pilot"),
        )

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_syncs_and_exposes_named_skill_levels_and_totals(self):
        client = FakeClient(payload(
            skill(33_550, trained=5, active=4, skillpoints=512_000),
            skill(33_851, trained=3, active=4, skillpoints=8_000),
            unallocated=12_500,
        ))
        result = sync_character_skills(self.db, client, CHARACTER_ID)
        self.assertEqual(
            (result.skills, result.total_sp, result.unallocated_sp, result.type_ids),
            (2, 520_000, 12_500, (33_550, 33_851)),
        )
        self.assertEqual(client.calls, [(
            f"/characters/{CHARACTER_ID}/skills/",
            None,
            CHARACTER_ID,
            ("esi-skills.read_skills.v1",),
        )])
        self.db.executemany(
            "INSERT INTO resolved_type_names(type_id,name) VALUES(?,?)",
            ((33_550, "Industry"), (33_851, "Advanced Industry")),
        )
        query = {
            "search": "industry",
            "ownerCharacterId": None,
            "trainedLevel": None,
            "activeState": None,
            "offset": 0,
            "limit": 100,
            "sortBy": "skill",
            "sortDirection": "asc",
        }
        page = query_character_skills(
            self.db, query, now=datetime(2026, 9, 11, tzinfo=timezone.utc)
        )
        self.assertEqual((page["total"], page["totalSp"], page["unallocatedSp"]), (2, 520_000, 12_500))
        self.assertEqual([item["skillName"] for item in page["items"]], ["Advanced Industry", "Industry"])
        self.assertEqual([item["activeState"] for item in page["items"]], ["boosted", "limited"])

    def test_query_filters_sorts_and_bounds_before_pagination(self):
        sync_character_skills(self.db, FakeClient(payload(
            skill(1, trained=1, active=1, skillpoints=250),
            skill(2, trained=3, active=3, skillpoints=8_000),
            skill(3, trained=3, active=2, skillpoints=45_255),
        )), CHARACTER_ID)
        self.db.executemany(
            "INSERT INTO resolved_type_names(type_id,name) VALUES(?,?)",
            ((1, "Alpha"), (2, "Beta"), (3, "Gamma")),
        )
        query = {
            "search": "",
            "ownerCharacterId": CHARACTER_ID,
            "trainedLevel": 3,
            "activeState": None,
            "offset": 1,
            "limit": 1,
            "sortBy": "skillpoints",
            "sortDirection": "asc",
        }
        page = query_character_skills(self.db, query)
        self.assertEqual((page["total"], len(page["items"]), page["items"][0]["skillName"]), (2, 1, "Gamma"))
        with self.assertRaises(CharacterSkillViewError):
            query_character_skills(self.db, {**query, "unexpected": True})

    def test_failed_followup_keeps_last_complete_snapshot(self):
        first = sync_character_skills(self.db, FakeClient(payload(skill(1, skillpoints=250))), CHARACTER_ID)
        with self.assertRaises(EsiClientError):
            sync_character_skills(self.db, FakeClient({}, fail=True), CHARACTER_ID)
        snapshots = self.db.execute(
            "SELECT COUNT(*) FROM cached_snapshots WHERE resource=?",
            (f"character_skills:{CHARACTER_ID}",),
        ).fetchone()[0]
        self.assertEqual(snapshots, 1)
        latest = self.db.execute(
            "SELECT status,error_code FROM sync_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(tuple(latest), ("failed", "esi-network-unavailable"))
        self.assertGreater(first.sync_run_id, 0)

    def test_invalid_or_duplicate_payload_publishes_nothing(self):
        invalid = payload(skill(1), skill(1))
        with self.assertRaises(CharacterSkillSyncError):
            sync_character_skills(self.db, FakeClient(invalid), CHARACTER_ID)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM cached_snapshots").fetchone()[0], 0)

        mismatched_total = payload(skill(2))
        mismatched_total["total_sp"] += 1
        with self.assertRaises(CharacterSkillSyncError):
            sync_character_skills(self.db, FakeClient(mismatched_total), CHARACTER_ID)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM cached_snapshots").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
