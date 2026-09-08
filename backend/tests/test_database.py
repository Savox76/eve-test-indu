from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from new_eden_foundry_backend.database import (
    BUSY_TIMEOUT_MILLISECONDS,
    MIGRATIONS,
    SCHEMA_VERSION,
    connect_database,
    initialize_database,
)


class DatabaseFoundationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "foundry.sqlite3"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_initialization_applies_schema_and_required_pragmas(self) -> None:
        status = initialize_database(self.database_path)

        self.assertEqual(status.schema_version, SCHEMA_VERSION)
        self.assertEqual(status.journal_mode, "wal")
        self.assertTrue(status.foreign_keys)
        self.assertEqual(status.busy_timeout_ms, BUSY_TIMEOUT_MILLISECONDS)
        self.assertEqual(status.integrity, "ok")

    def test_migration_is_idempotent(self) -> None:
        first = initialize_database(self.database_path)
        second = initialize_database(self.database_path)

        self.assertEqual(first, second)
        with closing(connect_database(self.database_path)) as connection:
            count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        self.assertEqual(count, SCHEMA_VERSION)

    def test_version_one_database_is_migrated_without_data_loss(self) -> None:
        with closing(connect_database(self.database_path)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                CREATE TABLE schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    applied_at TEXT NOT NULL DEFAULT (
                        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    )
                )
                """
            )
            version, name, statements = MIGRATIONS[0]
            for statement in statements:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                (version, name),
            )
            connection.execute("PRAGMA user_version = 1")
            connection.execute(
                "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
                ("preserved", "yes"),
            )
            connection.execute("COMMIT")

        status = initialize_database(self.database_path)

        self.assertEqual(status.schema_version, SCHEMA_VERSION)
        with closing(connect_database(self.database_path)) as connection:
            value = connection.execute(
                "SELECT value FROM app_metadata WHERE key = ?",
                ("preserved",),
            ).fetchone()[0]
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertEqual(value, "yes")
        self.assertTrue({"account_groups", "characters", "character_scopes"} <= tables)

    def test_foreign_keys_are_enforced_on_every_connection(self) -> None:
        initialize_database(self.database_path)

        with closing(connect_database(self.database_path)) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO cached_snapshots (
                        sync_run_id, resource, payload_json, observed_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (999, "assets", "{}", "2026-09-08T00:00:00Z"),
                )

    def test_sync_run_status_requires_a_consistent_completion_time(self) -> None:
        initialize_database(self.database_path)

        invalid_rows = (
            ("running", "2026-09-08T00:01:00Z"),
            ("completed", None),
        )
        with closing(connect_database(self.database_path)) as connection:
            for status, completed_at in invalid_rows:
                with self.subTest(status=status), self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        """
                        INSERT INTO sync_runs (
                            source, status, started_at, completed_at
                        ) VALUES (?, ?, ?, ?)
                        """,
                        ("synthetic-test", status, "2026-09-08T00:00:00Z", completed_at),
                    )

    def test_wal_reader_sees_committed_snapshot_during_write(self) -> None:
        initialize_database(self.database_path)

        with (
            closing(connect_database(self.database_path)) as writer,
            closing(connect_database(self.database_path)) as reader,
        ):
            writer.execute(
                "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
                ("generation", "committed"),
            )
            writer.execute("BEGIN IMMEDIATE")
            writer.execute(
                "UPDATE app_metadata SET value = ? WHERE key = ?",
                ("uncommitted", "generation"),
            )

            visible_value = reader.execute(
                "SELECT value FROM app_metadata WHERE key = ?",
                ("generation",),
            ).fetchone()[0]
            writer.execute("ROLLBACK")

        self.assertEqual(visible_value, "committed")


if __name__ == "__main__":
    unittest.main()
