"""Versioned SQLite foundation for the local application core."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Final


BUSY_TIMEOUT_MILLISECONDS: Final = 5_000
SCHEMA_VERSION: Final = 2

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
)


@dataclass(frozen=True, slots=True)
class DatabaseStatus:
    schema_version: int
    journal_mode: str
    foreign_keys: bool
    busy_timeout_ms: int
    integrity: str


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


def apply_migrations(connection: sqlite3.Connection) -> None:
    """Apply every pending forward migration in one explicit transaction."""

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
        applied = {
            int(row["version"])
            for row in connection.execute("SELECT version FROM schema_migrations")
        }

        for version, name, statements in MIGRATIONS:
            if version in applied:
                continue
            for statement in statements:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                (version, name),
            )
            connection.execute(f"PRAGMA user_version = {version}")

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

    schema_row = connection.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
    ).fetchone()
    return DatabaseStatus(
        schema_version=int(schema_row[0]),
        journal_mode=str(connection.execute("PRAGMA journal_mode").fetchone()[0]),
        foreign_keys=bool(connection.execute("PRAGMA foreign_keys").fetchone()[0]),
        busy_timeout_ms=int(connection.execute("PRAGMA busy_timeout").fetchone()[0]),
        integrity=quick_check.lower(),
    )


def initialize_database(path: Path) -> DatabaseStatus:
    """Create, migrate and verify a local database, then close it cleanly."""

    connection = connect_database(path)
    try:
        apply_migrations(connection)
        status = inspect_database(connection)
        if status.schema_version != SCHEMA_VERSION:
            raise RuntimeError(
                f"Expected schema version {SCHEMA_VERSION}, got {status.schema_version}."
            )
        return status
    finally:
        connection.close()
