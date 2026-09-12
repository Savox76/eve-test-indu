from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from new_eden_foundry_backend.blueprint_sync import BlueprintSyncError, sync_character_blueprints
from new_eden_foundry_backend.blueprint_view import BlueprintViewError, query_blueprints
from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.esi_client import EsiClientError, EsiResponse


class FakeClient:
    def __init__(self, pages, fail_page=None):
        self.pages, self.fail_page, self.last_scope = pages, fail_page, None

    def get_json(self, path, *, query, character_id, required_scopes):
        page = query["page"]
        self.last_scope = required_scopes
        if page == self.fail_page:
            raise EsiClientError("esi-network-unavailable", retryable=True)
        return EsiResponse(200, self.pages[page - 1], {"x-pages": str(len(self.pages))}, False)


def blueprint(item_id, type_id=681, *, quantity=-1, runs=-1, me=10, te=20):
    return {
        "item_id": item_id, "type_id": type_id, "location_id": 60_003_760,
        "location_flag": "Hangar", "quantity": quantity,
        "material_efficiency": me, "time_efficiency": te, "runs": runs,
    }


class BlueprintTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "foundry.db"
        initialize_database(self.path)
        self.db = connect_database(self.path)
        self.db.execute("INSERT INTO characters(character_id,name) VALUES(90000001,'Alpha')")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_syncs_all_pages_and_exposes_bpo_bpc_read_model(self):
        client = FakeClient([
            [blueprint(1, 681), blueprint(3, 683, quantity=4)],
            [blueprint(2, 682, quantity=-2, runs=7, me=4, te=8)],
        ])
        result = sync_character_blueprints(self.db, client, 90000001)
        self.assertEqual((result.pages, result.blueprints, result.type_ids), (2, 3, (681, 682, 683)))
        self.assertEqual(client.last_scope, ("esi-characters.read_blueprints.v1",))
        self.db.execute("INSERT INTO resolved_type_names(type_id,name) VALUES(681,'Bantam Blueprint')")
        query = {"search": "", "ownerCharacterId": None, "kind": None, "offset": 0,
                 "limit": 100, "sortBy": "type", "sortDirection": "asc"}
        page = query_blueprints(self.db, query, now=datetime(2026, 9, 10, tzinfo=timezone.utc))
        self.assertEqual(page["total"], 3)
        self.assertEqual(page["items"][0]["typeName"], "Bantam Blueprint")
        self.assertEqual({item["kind"] for item in page["items"]}, {"original", "copy"})
        self.assertEqual(next(item for item in page["items"] if item["itemId"] == 3)["kind"], "original")
        self.assertEqual(next(item for item in page["items"] if item["kind"] == "copy")["runs"], 7)

    def test_rejects_blueprint_quantity_values_outside_esi_semantics(self):
        for item_id, quantity in enumerate((0, -3, 9_007_199_254_740_992), start=10):
            with self.subTest(quantity=quantity), self.assertRaises(BlueprintSyncError):
                sync_character_blueprints(
                    self.db,
                    FakeClient([[blueprint(item_id, quantity=quantity)]]),
                    90000001,
                )

    def test_failed_followup_keeps_last_complete_snapshot(self):
        first = sync_character_blueprints(self.db, FakeClient([[blueprint(10)]]), 90000001)
        with self.assertRaises(EsiClientError):
            sync_character_blueprints(self.db, FakeClient([[blueprint(20)], [blueprint(21)]], fail_page=2), 90000001)
        snapshots = self.db.execute("SELECT COUNT(*) FROM cached_snapshots WHERE resource='character_blueprints:90000001'").fetchone()[0]
        self.assertEqual(snapshots, 1)
        latest = self.db.execute("SELECT status,error_code FROM sync_runs ORDER BY id DESC LIMIT 1").fetchone()
        self.assertEqual(tuple(latest), ("failed", "esi-network-unavailable"))
        self.assertGreater(first.sync_run_id, 0)

    def test_query_is_strict_filtered_sorted_and_bounded(self):
        sync_character_blueprints(self.db, FakeClient([[
            blueprint(1, 700, quantity=-2, runs=2), blueprint(2, 600), blueprint(3, 800)
        ]]), 90000001)
        for type_id, name in [(600, "Alpha Blueprint"), (700, "Beta Blueprint"), (800, "Gamma Blueprint")]:
            self.db.execute("INSERT INTO resolved_type_names(type_id,name) VALUES(?,?)", (type_id, name))
        query = {"search": "blueprint", "ownerCharacterId": 90000001, "kind": None,
                 "offset": 1, "limit": 1, "sortBy": "type", "sortDirection": "asc"}
        page = query_blueprints(self.db, query)
        self.assertEqual((page["total"], len(page["items"]), page["items"][0]["typeName"]), (3, 1, "Beta Blueprint"))
        with self.assertRaises(BlueprintViewError):
            query_blueprints(self.db, {**query, "unexpected": True})

    def test_invalid_or_duplicate_payload_publishes_nothing(self):
        with self.assertRaises(BlueprintSyncError):
            sync_character_blueprints(self.db, FakeClient([[blueprint(1), blueprint(1)]]), 90000001)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM cached_snapshots").fetchone()[0], 0)

    def test_lists_enabled_character_without_snapshot_and_hides_disabled_cache(self):
        second_character_id = 90000002
        self.db.execute(
            "INSERT INTO characters(character_id,name) VALUES(?,?)",
            (second_character_id, "Beta"),
        )
        sync_character_blueprints(
            self.db,
            FakeClient([[blueprint(30)]]),
            90000001,
        )

        query = {"search": "", "ownerCharacterId": None, "kind": None, "offset": 0,
                 "limit": 100, "sortBy": "type", "sortDirection": "asc"}
        page = query_blueprints(self.db, query)
        self.assertEqual(
            page["owners"],
            [
                {"characterId": 90000001, "name": "Alpha"},
                {"characterId": second_character_id, "name": "Beta"},
            ],
        )

        self.db.execute("UPDATE characters SET enabled=0 WHERE character_id=90000001")
        page = query_blueprints(self.db, query)
        self.assertEqual(page["total"], 0)
        self.assertEqual(
            page["owners"],
            [{"characterId": second_character_id, "name": "Beta"}],
        )


if __name__ == "__main__":
    unittest.main()
