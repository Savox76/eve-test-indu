from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import new_eden_foundry_backend.database as database_module

from new_eden_foundry_backend.database import (
    BUSY_TIMEOUT_MILLISECONDS,
    DatabaseMigrationError,
    MIGRATIONS,
    SCHEMA_VERSION,
    connect_database,
    current_schema_version,
    initialize_database,
)
from new_eden_foundry_backend.recovery import (
    DatabaseBackupError,
    DatabaseRestoreError,
    create_migration_backup,
    prune_migration_backups,
    restore_database_backup,
    verify_database_backup,
)


class DatabaseFoundationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "foundry.sqlite3"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def create_database_at_version(self, target_version: int) -> None:
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
            for version, name, statements in MIGRATIONS:
                if version > target_version:
                    break
                for statement in statements:
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                    (version, name),
                )
                connection.execute(f"PRAGMA user_version = {version}")
            connection.execute("COMMIT")

    def test_initialization_applies_schema_and_required_pragmas(self) -> None:
        status = initialize_database(self.database_path)

        self.assertEqual(status.schema_version, SCHEMA_VERSION)
        self.assertEqual(status.journal_mode, "wal")
        self.assertTrue(status.foreign_keys)
        self.assertEqual(status.busy_timeout_ms, BUSY_TIMEOUT_MILLISECONDS)
        self.assertEqual(status.integrity, "ok")
        self.assertIsNone(status.last_migration_backup)

    def test_migration_is_idempotent(self) -> None:
        first = initialize_database(self.database_path)
        second = initialize_database(self.database_path)

        self.assertEqual(first, second)
        with closing(connect_database(self.database_path)) as connection:
            count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        self.assertEqual(count, SCHEMA_VERSION)

    def test_version_one_database_is_migrated_without_data_loss(self) -> None:
        self.create_database_at_version(1)
        with closing(connect_database(self.database_path)) as connection:
            connection.execute(
                "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
                ("preserved", "yes"),
            )

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
        self.assertTrue(
            {
                "account_groups",
                "characters",
                "character_scopes",
                "migration_backups",
            }
            <= tables
        )

    def test_existing_database_gets_a_verified_backup_before_migration(self) -> None:
        self.create_database_at_version(2)
        with closing(connect_database(self.database_path)) as connection:
            connection.execute(
                "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
                ("synthetic-upgrade", "preserved"),
            )

        status = initialize_database(self.database_path)

        backup_directory = self.database_path.parent / "backups"
        backups = list(backup_directory.glob("foundry-schema-*.sqlite3"))
        self.assertEqual(len(backups), 1)
        backup_path = backups[0]
        self.assertEqual(status.last_migration_backup, backup_path.name)

        with closing(connect_database(self.database_path)) as migrated:
            record = migrated.execute(
                """
                SELECT filename, source_schema_version, target_schema_version,
                       sha256, size_bytes
                FROM migration_backups
                """
            ).fetchone()
        self.assertEqual(record["filename"], backup_path.name)
        self.assertEqual(record["source_schema_version"], 2)
        self.assertEqual(record["target_schema_version"], SCHEMA_VERSION)
        self.assertEqual(record["size_bytes"], backup_path.stat().st_size)
        verify_database_backup(
            backup_path,
            expected_schema_version=2,
            expected_sha256=record["sha256"],
        )

        with closing(sqlite3.connect(backup_path)) as backup_connection:
            preserved = backup_connection.execute(
                "SELECT value FROM app_metadata WHERE key = ?",
                ("synthetic-upgrade",),
            ).fetchone()[0]
            backup_version = backup_connection.execute(
                "PRAGMA user_version"
            ).fetchone()[0]
            backup_journal = backup_connection.execute(
                "PRAGMA journal_mode"
            ).fetchone()[0]
        self.assertEqual(preserved, "preserved")
        self.assertEqual(backup_version, 2)
        self.assertEqual(backup_journal, "delete")

    def test_failed_migration_automatically_restores_the_verified_backup(self) -> None:
        initialize_database(self.database_path)
        with closing(connect_database(self.database_path)) as connection:
            connection.execute(
                "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
                ("recovery-marker", "before-failure"),
            )

        failing_migrations = MIGRATIONS + (
            (4, "synthetic_failure", ("CREATE TABLE broken (",)),
        )
        with (
            patch.object(database_module, "MIGRATIONS", failing_migrations),
            patch.object(database_module, "SCHEMA_VERSION", 4),
            self.assertRaisesRegex(DatabaseMigrationError, "backup was restored"),
        ):
            initialize_database(self.database_path)

        with closing(connect_database(self.database_path)) as restored:
            self.assertEqual(current_schema_version(restored), SCHEMA_VERSION)
            marker = restored.execute(
                "SELECT value FROM app_metadata WHERE key = ?",
                ("recovery-marker",),
            ).fetchone()[0]
            self.assertIsNone(
                restored.execute(
                    "SELECT 1 FROM sqlite_master WHERE name = 'broken'"
                ).fetchone()
            )
        self.assertEqual(marker, "before-failure")
        self.assertEqual(
            len(list((self.database_path.parent / "backups").glob("*.sqlite3"))),
            1,
        )

    def test_backup_failure_stops_migration_before_the_schema_changes(self) -> None:
        self.create_database_at_version(2)
        with closing(connect_database(self.database_path)) as connection:
            connection.execute(
                "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
                ("backup-failure-marker", "unchanged"),
            )

        with (
            patch.object(
                database_module,
                "create_migration_backup",
                side_effect=DatabaseBackupError("synthetic backup failure"),
            ),
            self.assertRaisesRegex(DatabaseBackupError, "synthetic backup failure"),
        ):
            initialize_database(self.database_path)

        with closing(connect_database(self.database_path)) as unchanged:
            self.assertEqual(current_schema_version(unchanged), 2)
            marker = unchanged.execute(
                "SELECT value FROM app_metadata WHERE key = ?",
                ("backup-failure-marker",),
            ).fetchone()[0]
            self.assertIsNone(
                unchanged.execute(
                    "SELECT 1 FROM sqlite_master WHERE name = 'migration_backups'"
                ).fetchone()
            )
        self.assertEqual(marker, "unchanged")

    def test_backup_retention_keeps_the_five_newest_snapshots(self) -> None:
        backup_directory = self.database_path.parent / "backups"
        backup_directory.mkdir()
        for index in range(7):
            path = backup_directory / (
                "foundry-schema-v0002-to-v0003-"
                f"20260909T12000{index}000000Z-{index:08x}.sqlite3"
            )
            path.write_bytes(f"synthetic-backup-{index}".encode())
        unrelated = backup_directory / "manual-note.txt"
        unrelated.write_text("keep", encoding="utf-8")

        prune_migration_backups(backup_directory)

        remaining = sorted(path.name for path in backup_directory.glob("*.sqlite3"))
        self.assertEqual(len(remaining), 5)
        self.assertTrue(all(f"12000{index}" in " ".join(remaining) for index in range(2, 7)))
        self.assertTrue(unrelated.is_file())

    def test_corrupt_backup_is_rejected_without_replacing_current_database(self) -> None:
        initialize_database(self.database_path)
        with closing(connect_database(self.database_path)) as connection:
            connection.execute(
                "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
                ("current-marker", "keep-current"),
            )
            backup = create_migration_backup(
                connection,
                self.database_path.parent / "backups",
                source_schema_version=SCHEMA_VERSION,
                target_schema_version=SCHEMA_VERSION + 1,
            )

        with backup.path.open("r+b") as stream:
            stream.seek(0)
            stream.write(b"not a sqlite database")

        with self.assertRaisesRegex(DatabaseRestoreError, "failed verification"):
            restore_database_backup(
                self.database_path,
                backup.path,
                expected_schema_version=SCHEMA_VERSION,
                expected_sha256=backup.sha256,
            )

        with closing(connect_database(self.database_path)) as current:
            marker = current.execute(
                "SELECT value FROM app_metadata WHERE key = ?",
                ("current-marker",),
            ).fetchone()[0]
        self.assertEqual(marker, "keep-current")

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
