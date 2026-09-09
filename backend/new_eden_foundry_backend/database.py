"""Versioned SQLite foundation for the local application core."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .recovery import (
    DatabaseRestoreError,
    MigrationBackup,
    create_migration_backup,
    prune_migration_backups,
    restore_database_backup,
)


BUSY_TIMEOUT_MILLISECONDS: Final = 5_000
SCHEMA_VERSION: Final = 5

MIGRATIONS: Final = (
    (
        1,
        "initial_local_core",
        (
            """
            CREATE TABLE app_metadata (
                key TEXT PRIMARY KEY NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
            )
            """,
            """
            CREATE TABLE sync_runs (
                id INTEGER PRIMARY KEY,
                source TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN ('running', 'completed', 'failed', 'cancelled')
                ),
                started_at TEXT NOT NULL,
                completed_at TEXT,
                data_timestamp TEXT,
                error_code TEXT,
                CHECK (
                    (status = 'running' AND completed_at IS NULL)
                    OR (status <> 'running' AND completed_at IS NOT NULL)
                )
            )
            """,
            """
            CREATE TABLE cached_snapshots (
                id INTEGER PRIMARY KEY,
                sync_run_id INTEGER NOT NULL
                    REFERENCES sync_runs(id) ON DELETE CASCADE,
                resource TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                UNIQUE (sync_run_id, resource)
            )
            """,
        ),
    ),
    (
        2,
        "multi_character_identity",
        (
            """
            CREATE TABLE account_groups (
                id INTEGER PRIMARY KEY,
                label TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK (
                    length(trim(label)) BETWEEN 1 AND 80
                ),
                sort_order INTEGER NOT NULL DEFAULT 0 CHECK (sort_order >= 0),
                created_at TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                updated_at TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
            )
            """,
            """
            CREATE TABLE characters (
                character_id INTEGER PRIMARY KEY CHECK (character_id <> 0),
                account_group_id INTEGER
                    REFERENCES account_groups(id) ON DELETE SET NULL,
                name TEXT NOT NULL CHECK (
                    length(trim(name)) BETWEEN 1 AND 100
                ),
                enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
                connected_at TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                updated_at TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
            )
            """,
            """
            CREATE TABLE character_scopes (
                character_id INTEGER NOT NULL
                    REFERENCES characters(character_id) ON DELETE CASCADE,
                scope TEXT NOT NULL CHECK (
                    length(trim(scope)) BETWEEN 1 AND 200
                ),
                PRIMARY KEY (character_id, scope)
            )
            """,
            """
            ALTER TABLE sync_runs
                ADD COLUMN character_id INTEGER
                    REFERENCES characters(character_id) ON DELETE CASCADE
            """,
            """
            CREATE INDEX idx_characters_account_group
                ON characters(account_group_id, name COLLATE NOCASE)
            """,
            """
            CREATE INDEX idx_sync_runs_character
                ON sync_runs(character_id, started_at DESC)
            """,
        ),
    ),
    (
        3,
        "migration_backup_history",
        (
            """
            CREATE TABLE migration_backups (
                id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL UNIQUE CHECK (
                    length(filename) BETWEEN 1 AND 255
                    AND instr(filename, '/') = 0
                    AND instr(filename, char(92)) = 0
                ),
                source_schema_version INTEGER NOT NULL CHECK (
                    source_schema_version >= 0
                ),
                target_schema_version INTEGER NOT NULL CHECK (
                    target_schema_version > source_schema_version
                ),
                sha256 TEXT NOT NULL CHECK (
                    length(sha256) = 64
                    AND sha256 NOT GLOB '*[^0-9a-f]*'
                ),
                size_bytes INTEGER NOT NULL CHECK (size_bytes > 0),
                created_at TEXT NOT NULL
            )
            """,
            """
            CREATE INDEX idx_migration_backups_created
                ON migration_backups(created_at DESC)
            """,
        ),
    ),
    (
        4,
        "cache_freshness_metadata",
        (
            """
            ALTER TABLE cached_snapshots
                ADD COLUMN expires_at TEXT
            """,
            """
            CREATE INDEX idx_cached_snapshots_resource_observed
                ON cached_snapshots(resource, observed_at DESC)
            """,
        ),
    ),
    (
        5,
        "local_update_preferences",
        (
            """
            CREATE TABLE app_settings (
                key TEXT PRIMARY KEY NOT NULL CHECK (
                    length(trim(key)) BETWEEN 1 AND 80
                ),
                value TEXT NOT NULL CHECK (length(value) <= 2000),
                updated_at TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
            )
            """,
            """
            INSERT INTO app_settings (key, value)
                VALUES ('update_channel', 'stable')
            """,
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class DatabaseStatus:
    schema_version: int
    journal_mode: str
    foreign_keys: bool
    busy_timeout_ms: int
    integrity: str
    last_migration_backup: str | None


class DatabaseSchemaError(RuntimeError):
    """Raised when migration history is incomplete or incompatible."""


class DatabaseMigrationError(RuntimeError):
    """Raised when migration fails after recovery was attempted."""


def _validate_migration_definitions() -> None:
    versions = [version for version, _name, _statements in MIGRATIONS]
    if versions != list(range(1, SCHEMA_VERSION + 1)):
        raise DatabaseSchemaError(
            "Application migration definitions are incomplete or out of order."
        )
    names = [name for _version, name, _statements in MIGRATIONS]
    if len(names) != len(set(names)):
        raise DatabaseSchemaError("Application migration names must be unique.")


def connect_database(path: Path) -> sqlite3.Connection:
    """Open and configure one production-style SQLite connection."""

    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        path,
        timeout=BUSY_TIMEOUT_MILLISECONDS / 1_000,
        isolation_level=None,
    )
    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")
    journal_mode = str(connection.execute("PRAGMA journal_mode = WAL").fetchone()[0])
    connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MILLISECONDS}")

    if journal_mode.lower() != "wal":
        connection.close()
        raise RuntimeError(f"SQLite refused WAL mode and returned {journal_mode!r}.")
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        connection.close()
        raise RuntimeError("SQLite foreign-key enforcement could not be enabled.")
    if connection.execute("PRAGMA busy_timeout").fetchone()[0] != BUSY_TIMEOUT_MILLISECONDS:
        connection.close()
        raise RuntimeError("SQLite busy timeout could not be configured.")

    return connection


def current_schema_version(connection: sqlite3.Connection) -> int:
    """Validate and return the schema version recorded by the database."""

    _validate_migration_definitions()
    user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    migration_table = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = 'schema_migrations'
        """
    ).fetchone()
    if migration_table is None:
        if user_version != 0:
            raise DatabaseSchemaError(
                "The database has a user version but no migration history."
            )
        return 0

    applied_rows = list(
        connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        )
    )
    versions = [int(row[0]) for row in applied_rows]
    expected_versions = list(range(1, len(versions) + 1))
    if versions != expected_versions:
        raise DatabaseSchemaError("The database migration history has gaps.")

    recorded_version = versions[-1] if versions else 0
    if recorded_version != user_version:
        raise DatabaseSchemaError(
            "The database migration history and user version disagree."
        )
    if recorded_version > SCHEMA_VERSION:
        raise DatabaseSchemaError(
            "The database was created by a newer application version."
        )

    migration_names = {version: name for version, name, _statements in MIGRATIONS}
    for row in applied_rows:
        version = int(row[0])
        if migration_names.get(version) != str(row[1]):
            raise DatabaseSchemaError(
                f"Migration {version} does not match this application build."
            )
    return recorded_version


def apply_migrations(
    connection: sqlite3.Connection,
    *,
    backup: MigrationBackup | None = None,
) -> None:
    """Apply every pending forward migration in one explicit transaction."""

    applied_version = current_schema_version(connection)
    if backup is not None and (
        backup.source_schema_version != applied_version
        or backup.target_schema_version != SCHEMA_VERSION
        or applied_version >= SCHEMA_VERSION
    ):
        raise DatabaseSchemaError(
            "The migration backup does not match the pending schema change."
        )
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
            )
            """
        )
        for version, name, statements in MIGRATIONS:
            if version <= applied_version:
                continue
            for statement in statements:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                (version, name),
            )
            connection.execute(f"PRAGMA user_version = {version}")

        if backup is not None:
            connection.execute(
                """
                INSERT INTO migration_backups (
                    filename,
                    source_schema_version,
                    target_schema_version,
                    sha256,
                    size_bytes,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    backup.filename,
                    backup.source_schema_version,
                    backup.target_schema_version,
                    backup.sha256,
                    backup.size_bytes,
                    backup.created_at,
                ),
            )

        connection.execute("COMMIT")
    except BaseException:
        connection.execute("ROLLBACK")
        raise


def inspect_database(connection: sqlite3.Connection) -> DatabaseStatus:
    """Return verified connection and schema properties."""

    quick_check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
    foreign_key_violations = list(connection.execute("PRAGMA foreign_key_check"))
    if quick_check.lower() != "ok":
        raise RuntimeError(f"SQLite quick_check failed: {quick_check}")
    if foreign_key_violations:
        raise RuntimeError("SQLite foreign_key_check reported violations.")

    schema_version = current_schema_version(connection)
    backup_row = connection.execute(
        """
        SELECT filename
        FROM migration_backups
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """
    ).fetchone()
    return DatabaseStatus(
        schema_version=schema_version,
        journal_mode=str(connection.execute("PRAGMA journal_mode").fetchone()[0]),
        foreign_keys=bool(connection.execute("PRAGMA foreign_keys").fetchone()[0]),
        busy_timeout_ms=int(connection.execute("PRAGMA busy_timeout").fetchone()[0]),
        integrity=quick_check.lower(),
        last_migration_backup=(
            str(backup_row["filename"]) if backup_row is not None else None
        ),
    )


def initialize_database(
    path: Path,
    backup_directory: Path | None = None,
) -> DatabaseStatus:
    """Create or safely migrate a local database, then verify and close it."""

    resolved_path = path.expanduser().resolve()
    database_preexisted = resolved_path.is_file() and resolved_path.stat().st_size > 0
    resolved_backup_directory = (
        backup_directory.expanduser()
        if backup_directory is not None
        else resolved_path.parent / "backups"
    )
    connection: sqlite3.Connection | None = connect_database(resolved_path)
    backup: MigrationBackup | None = None
    try:
        source_schema_version = current_schema_version(connection)
        if database_preexisted and source_schema_version < SCHEMA_VERSION:
            backup = create_migration_backup(
                connection,
                resolved_backup_directory,
                source_schema_version=source_schema_version,
                target_schema_version=SCHEMA_VERSION,
            )
            prune_migration_backups(
                resolved_backup_directory,
                preserve=(backup.path,),
            )

        try:
            apply_migrations(connection, backup=backup)
            status = inspect_database(connection)
            if status.schema_version != SCHEMA_VERSION:
                raise DatabaseSchemaError(
                    f"Expected schema version {SCHEMA_VERSION}, "
                    f"got {status.schema_version}."
                )
            return status
        except Exception as migration_error:
            if backup is None:
                raise

            connection.close()
            connection = None
            try:
                restore_database_backup(
                    resolved_path,
                    backup.path,
                    expected_schema_version=backup.source_schema_version,
                    expected_sha256=backup.sha256,
                )
            except DatabaseRestoreError as restore_error:
                raise DatabaseMigrationError(
                    "Database migration and automatic restoration both failed; "
                    "the verified backup was retained."
                ) from restore_error
            raise DatabaseMigrationError(
                "Database migration failed; the pre-migration backup was restored."
            ) from migration_error
    finally:
        if connection is not None:
            connection.close()
