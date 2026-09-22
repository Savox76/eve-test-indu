from pathlib import Path
import tempfile
import unittest

from new_eden_foundry_backend.character_standing_sync import (
    CHARACTER_STANDING_SCOPE,
    CharacterStandingSyncError,
    sync_character_standings,
    validate_character_standings,
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


class CharacterStandingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "foundry.db"
        initialize_database(self.path)
        self.db = connect_database(self.path)
        self.db.execute(
            "INSERT INTO characters(character_id,name) VALUES(?,?)",
            (CHARACTER_ID, "Trade Pilot"),
        )

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_syncs_normalized_fixed_point_standings(self):
        client = FakeClient([
            {"from_id": 500_001, "from_type": "faction", "standing": 1.2345678},
            {"from_id": 1_000_035, "from_type": "npc_corp", "standing": -2.5},
        ])
        result = sync_character_standings(self.db, client, CHARACTER_ID)
        self.assertEqual((result.standings, result.character_id), (2, CHARACTER_ID))
        self.assertEqual(client.calls, [(
            f"/characters/{CHARACTER_ID}/standings/",
            None,
            CHARACTER_ID,
            (CHARACTER_STANDING_SCOPE,),
        )])
        row = self.db.execute(
            "SELECT payload_json FROM cached_snapshots WHERE resource=?",
            (f"character_standings:{CHARACTER_ID}",),
        ).fetchone()
        self.assertIn('"standingMillionths":1234568', row[0])
        self.assertIn('"standingMillionths":-2500000', row[0])

    def test_failed_followup_preserves_latest_complete_snapshot(self):
        sync_character_standings(self.db, FakeClient([]), CHARACTER_ID)
        with self.assertRaises(EsiClientError):
            sync_character_standings(self.db, FakeClient([], fail=True), CHARACTER_ID)
        self.assertEqual(
            self.db.execute(
                "SELECT COUNT(*) FROM cached_snapshots WHERE resource=?",
                (f"character_standings:{CHARACTER_ID}",),
            ).fetchone()[0],
            1,
        )
        self.assertEqual(
            tuple(self.db.execute(
                "SELECT status,error_code FROM sync_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()),
            ("failed", "esi-network-unavailable"),
        )

    def test_rejects_invalid_duplicate_or_non_finite_payloads(self):
        invalid_payloads = (
            [{"from_id": 1, "from_type": "player", "standing": 0}],
            [
                {"from_id": 1, "from_type": "faction", "standing": 0},
                {"from_id": 1, "from_type": "faction", "standing": 1},
            ],
            [{"from_id": 1, "from_type": "faction", "standing": float("nan")}],
            [{"from_id": 1, "from_type": "faction", "standing": 10.000001}],
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(CharacterStandingSyncError):
                    validate_character_standings(payload)


if __name__ == "__main__":
    unittest.main()
