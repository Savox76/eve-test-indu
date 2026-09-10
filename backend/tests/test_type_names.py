from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.esi_client import EsiResponse
from new_eden_foundry_backend.type_names import (
    TYPE_NAME_BATCH_SIZE,
    TypeNameResolutionError,
    resolve_type_names,
)


class FakeClient:
    def __init__(self, malformed: bool = False) -> None:
        self.calls: list[list[int]] = []
        self.malformed = malformed

    def post_json(self, path: str, payload: object) -> EsiResponse:
        self.assert_path = path
        ids = list(payload)  # type: ignore[arg-type]
        self.calls.append(ids)
        rows = [
            {"id": type_id, "name": f"Item {type_id}", "category": "inventory_type"}
            for type_id in ids
        ]
        if self.malformed:
            rows[0]["category"] = "character"
        return EsiResponse(200, rows, {}, False)


class TypeNameResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "foundry.sqlite3"
        initialize_database(self.database_path)
        self.database = connect_database(self.database_path)

    def tearDown(self) -> None:
        self.database.close()
        self.temporary_directory.cleanup()

    def test_resolves_unknown_ids_in_bounded_batches_and_reuses_cache(self) -> None:
        client = FakeClient()
        ids = list(range(1, TYPE_NAME_BATCH_SIZE + 2))

        self.assertEqual(len(ids), resolve_type_names(self.database, client, ids))
        self.assertEqual([TYPE_NAME_BATCH_SIZE, 1], [len(call) for call in client.calls])
        self.assertEqual("/universe/names/", client.assert_path)
        self.assertEqual(0, resolve_type_names(self.database, client, reversed(ids)))
        self.assertEqual(2, len(client.calls))
        stored = self.database.execute(
            "SELECT name FROM resolved_type_names WHERE type_id=?", (34,)
        ).fetchone()
        self.assertEqual("Item 34", stored[0])

    def test_rejects_wrong_categories_without_persisting_partial_names(self) -> None:
        client = FakeClient(malformed=True)
        with self.assertRaisesRegex(TypeNameResolutionError, "type_name_payload_invalid"):
            resolve_type_names(self.database, client, [34])
        count = self.database.execute("SELECT count(*) FROM resolved_type_names").fetchone()
        self.assertEqual(0, count[0])


if __name__ == "__main__":
    unittest.main()
