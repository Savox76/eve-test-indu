from pathlib import Path
import json
import tempfile
import unittest

from new_eden_foundry_backend.asset_sync import AssetSyncError, sync_character_assets
from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.esi_client import EsiResponse, EsiClientError


class FakeClient:
    def __init__(self, pages, fail_page=None): self.pages, self.fail_page = pages, fail_page
    def get_json(self, path, *, query, character_id, required_scopes):
        page = query["page"]
        self.last_scope = required_scopes
        if page == self.fail_page: raise EsiClientError("esi-network-unavailable", retryable=True)
        return EsiResponse(200, self.pages[page-1], {"x-pages": str(len(self.pages))}, False)


def asset(item_id, type_id=34):
    return {"item_id":item_id,"type_id":type_id,"location_id":60003760,"location_type":"station","location_flag":"Hangar","quantity":1}


class AssetSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.path=Path(self.temp.name)/"foundry.db"; initialize_database(self.path); self.db=connect_database(self.path)
        self.db.execute("INSERT INTO characters(character_id,name) VALUES(90000001,'Alpha')")
    def tearDown(self): self.db.close(); self.temp.cleanup()

    def test_reads_all_pages_and_publishes_one_completed_snapshot(self):
        client=FakeClient([[asset(1)],[asset(2),asset(3)]])
        result=sync_character_assets(self.db,client,90000001)
        self.assertEqual((result.pages,result.assets),(2,3))
        run=self.db.execute("SELECT status,error_code FROM sync_runs WHERE id=?",(result.sync_run_id,)).fetchone(); self.assertEqual(run[0],"completed"); self.assertIsNone(run[1])
        snap=self.db.execute("SELECT payload_json FROM cached_snapshots WHERE sync_run_id=?",(result.sync_run_id,)).fetchone(); payload=json.loads(snap[0]); self.assertEqual([a["item_id"] for a in payload["assets"]],[1,2,3])
        self.assertEqual(client.last_scope,("esi-assets.read_assets.v1",))

    def test_failed_page_never_publishes_partial_snapshot(self):
        good=sync_character_assets(self.db,FakeClient([[asset(10)]]),90000001)
        with self.assertRaises(EsiClientError): sync_character_assets(self.db,FakeClient([[asset(20)],[asset(21)]],fail_page=2),90000001)
        completed=self.db.execute("SELECT COUNT(*) FROM cached_snapshots").fetchone()[0]; self.assertEqual(completed,1)
        latest=self.db.execute("SELECT status,error_code FROM sync_runs ORDER BY id DESC LIMIT 1").fetchone(); self.assertEqual(latest[0],"failed"); self.assertEqual(latest[1],"esi-network-unavailable")
        old=json.loads(self.db.execute("SELECT payload_json FROM cached_snapshots WHERE sync_run_id=?",(good.sync_run_id,)).fetchone()[0]); self.assertEqual(old["assets"][0]["item_id"],10)

    def test_duplicate_items_across_pages_reject_whole_run(self):
        with self.assertRaises(AssetSyncError): sync_character_assets(self.db,FakeClient([[asset(1)],[asset(1)]]),90000001)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM cached_snapshots").fetchone()[0],0)


if __name__ == "__main__": unittest.main()
