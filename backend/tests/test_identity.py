from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.identity import (
    create_account_group,
    list_account_groups,
    list_characters,
    upsert_character,
)


class MultiCharacterIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "foundry.sqlite3"
        initialize_database(database_path)
        self.connection = connect_database(database_path)

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def test_multiple_local_accounts_and_characters_are_listed_together(self) -> None:
        industry_group = create_account_group(
            self.connection,
            "Industry Core",
            sort_order=1,
        )
        pi_group = create_account_group(self.connection, "PI Network", sort_order=2)

        upsert_character(
            self.connection,
            character_id=-9_900_000_001,
            name="Mara Venn",
            account_group_id=industry_group,
            scopes=("esi-assets.read_assets.v1", "esi-industry.read_character_jobs.v1"),
        )
        upsert_character(
            self.connection,
            character_id=-9_900_000_002,
            name="Elias Torv",
            account_group_id=industry_group,
            scopes=("esi-assets.read_assets.v1",),
        )
        upsert_character(
            self.connection,
            character_id=-9_900_000_003,
            name="Nera Sol",
            account_group_id=pi_group,
            scopes=("esi-planets.manage_planets.v1",),
        )

        groups = list_account_groups(self.connection)
        characters = list_characters(self.connection)

        self.assertEqual(
            [(group.label, group.character_count) for group in groups],
            [("Industry Core", 2), ("PI Network", 1)],
        )
        self.assertEqual([character.name for character in characters], ["Elias Torv", "Mara Venn", "Nera Sol"])
        self.assertEqual(characters[1].account_group_label, "Industry Core")
        self.assertEqual(
            characters[1].scopes,
            ("esi-assets.read_assets.v1", "esi-industry.read_character_jobs.v1"),
        )

    def test_reauthorization_updates_one_character_without_duplication(self) -> None:
        first_group = create_account_group(self.connection, "Industry Core")
        second_group = create_account_group(self.connection, "PI Network", sort_order=1)
        character_id = -9_900_000_004
        upsert_character(
            self.connection,
            character_id=character_id,
            name="Sera Nox",
            account_group_id=first_group,
            scopes=("scope.old",),
        )

        updated = upsert_character(
            self.connection,
            character_id=character_id,
            name="Sera Nox",
            account_group_id=second_group,
            scopes=("scope.new", "scope.new"),
            enabled=False,
        )

        self.assertEqual(len(list_characters(self.connection)), 1)
        self.assertEqual(updated.account_group_label, "PI Network")
        self.assertEqual(updated.scopes, ("scope.new",))
        self.assertFalse(updated.enabled)

    def test_deleting_local_group_keeps_character_authorization_record(self) -> None:
        group_id = create_account_group(self.connection, "Temporary Group")
        upsert_character(
            self.connection,
            character_id=-9_900_000_005,
            name="Ilan Kes",
            account_group_id=group_id,
        )

        self.connection.execute("DELETE FROM account_groups WHERE id = ?", (group_id,))

        character = list_characters(self.connection)[0]
        self.assertIsNone(character.account_group_id)
        self.assertIsNone(character.account_group_label)

    def test_deleting_character_removes_its_sync_history_and_snapshots(self) -> None:
        character_id = -9_900_000_007
        upsert_character(
            self.connection,
            character_id=character_id,
            name="Disposable Pilot",
            account_group_id=None,
        )
        cursor = self.connection.execute(
            """
            INSERT INTO sync_runs (
                source, status, started_at, completed_at, character_id
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                "synthetic-test",
                "completed",
                "2026-09-08T00:00:00Z",
                "2026-09-08T00:01:00Z",
                character_id,
            ),
        )
        self.connection.execute(
            """
            INSERT INTO cached_snapshots (
                sync_run_id, resource, payload_json, observed_at
            ) VALUES (?, ?, ?, ?)
            """,
            (
                cursor.lastrowid,
                "assets",
                "{}",
                "2026-09-08T00:01:00Z",
            ),
        )

        self.connection.execute(
            "DELETE FROM characters WHERE character_id = ?",
            (character_id,),
        )

        sync_count = self.connection.execute("SELECT COUNT(*) FROM sync_runs").fetchone()[0]
        snapshot_count = self.connection.execute(
            "SELECT COUNT(*) FROM cached_snapshots"
        ).fetchone()[0]
        self.assertEqual(sync_count, 0)
        self.assertEqual(snapshot_count, 0)

    def test_unknown_group_rolls_back_character_and_scope_changes(self) -> None:
        valid_group = create_account_group(self.connection, "Stable Group")
        character_id = -9_900_000_006
        upsert_character(
            self.connection,
            character_id=character_id,
            name="Stable Pilot",
            account_group_id=valid_group,
            scopes=("scope.stable",),
        )

        with self.assertRaises(sqlite3.IntegrityError):
            upsert_character(
                self.connection,
                character_id=character_id,
                name="Changed Too Early",
                account_group_id=999,
                scopes=("scope.synthetic",),
            )

        characters = list_characters(self.connection)
        self.assertEqual(len(characters), 1)
        self.assertEqual(characters[0].name, "Stable Pilot")
        self.assertEqual(characters[0].account_group_id, valid_group)
        self.assertEqual(characters[0].scopes, ("scope.stable",))


if __name__ == "__main__":
    unittest.main()
