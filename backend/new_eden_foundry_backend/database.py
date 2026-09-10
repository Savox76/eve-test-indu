"""Versioned SQLite foundation for the local application core."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .recovery import DatabaseRestoreError, MigrationBackup, create_migration_backup, prune_migration_backups, restore_database_backup

BUSY_TIMEOUT_MILLISECONDS: Final = 5_000
SCHEMA_VERSION: Final = 7

# Migrations are deliberately append-only. Earlier statements are kept byte-for-byte compatible.
MIGRATIONS: Final = (
(1,"initial_local_core",("""CREATE TABLE app_metadata (key TEXT PRIMARY KEY NOT NULL,value TEXT NOT NULL,updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')))""","""CREATE TABLE sync_runs (id INTEGER PRIMARY KEY,source TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('running','completed','failed','cancelled')),started_at TEXT NOT NULL,completed_at TEXT,data_timestamp TEXT,error_code TEXT,CHECK((status='running' AND completed_at IS NULL) OR (status<>'running' AND completed_at IS NOT NULL)))""","""CREATE TABLE cached_snapshots (id INTEGER PRIMARY KEY,sync_run_id INTEGER NOT NULL REFERENCES sync_runs(id) ON DELETE CASCADE,resource TEXT NOT NULL,payload_json TEXT NOT NULL,observed_at TEXT NOT NULL,UNIQUE(sync_run_id,resource))""")),
(2,"multi_character_identity",("""CREATE TABLE account_groups (id INTEGER PRIMARY KEY,label TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK(length(trim(label)) BETWEEN 1 AND 80),sort_order INTEGER NOT NULL DEFAULT 0 CHECK(sort_order>=0),created_at TEXT NOT NULL DEFAULT(strftime('%Y-%m-%dT%H:%M:%fZ','now')),updated_at TEXT NOT NULL DEFAULT(strftime('%Y-%m-%dT%H:%M:%fZ','now')))""","""CREATE TABLE characters (character_id INTEGER PRIMARY KEY CHECK(character_id<>0),account_group_id INTEGER REFERENCES account_groups(id) ON DELETE SET NULL,name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 100),enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN(0,1)),connected_at TEXT NOT NULL DEFAULT(strftime('%Y-%m-%dT%H:%M:%fZ','now')),updated_at TEXT NOT NULL DEFAULT(strftime('%Y-%m-%dT%H:%M:%fZ','now')))""","""CREATE TABLE character_scopes (character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,scope TEXT NOT NULL CHECK(length(trim(scope)) BETWEEN 1 AND 200),PRIMARY KEY(character_id,scope))""","ALTER TABLE sync_runs ADD COLUMN character_id INTEGER REFERENCES characters(character_id) ON DELETE CASCADE","CREATE INDEX idx_characters_account_group ON characters(account_group_id,name COLLATE NOCASE)","CREATE INDEX idx_sync_runs_character ON sync_runs(character_id,started_at DESC)")),
(3,"migration_backup_history",("""CREATE TABLE migration_backups (id INTEGER PRIMARY KEY,filename TEXT NOT NULL UNIQUE CHECK(length(filename) BETWEEN 1 AND 255 AND instr(filename,'/')=0 AND instr(filename,char(92))=0),source_schema_version INTEGER NOT NULL CHECK(source_schema_version>=0),target_schema_version INTEGER NOT NULL CHECK(target_schema_version>source_schema_version),sha256 TEXT NOT NULL CHECK(length(sha256)=64 AND sha256 NOT GLOB '*[^0-9a-f]*'),size_bytes INTEGER NOT NULL CHECK(size_bytes>0),created_at TEXT NOT NULL)""","CREATE INDEX idx_migration_backups_created ON migration_backups(created_at DESC)")),
(4,"cache_freshness_metadata",("ALTER TABLE cached_snapshots ADD COLUMN expires_at TEXT","CREATE INDEX idx_cached_snapshots_resource_observed ON cached_snapshots(resource,observed_at DESC)")),
(5,"local_update_preferences",("""CREATE TABLE app_settings (key TEXT PRIMARY KEY NOT NULL CHECK(length(trim(key)) BETWEEN 1 AND 80),value TEXT NOT NULL CHECK(length(value)<=2000),updated_at TEXT NOT NULL DEFAULT(strftime('%Y-%m-%dT%H:%M:%fZ','now')))""","INSERT INTO app_settings(key,value) VALUES('update_channel','stable')")),
(6,"character_aliases",("ALTER TABLE characters ADD COLUMN alias TEXT CHECK(alias IS NULL OR length(trim(alias)) BETWEEN 1 AND 80)",)),
(7,"minimal_sde",(
"CREATE TABLE sde_groups (group_id INTEGER PRIMARY KEY CHECK(group_id>0),name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 200))",
"CREATE TABLE sde_types (type_id INTEGER PRIMARY KEY CHECK(type_id>0),group_id INTEGER NOT NULL REFERENCES sde_groups(group_id) ON DELETE RESTRICT,name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 200))",
"CREATE INDEX idx_sde_types_group_name ON sde_types(group_id,name COLLATE NOCASE)",
"CREATE TABLE sde_locations (location_id INTEGER PRIMARY KEY CHECK(location_id>0),parent_location_id TEXT,name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 200),kind TEXT NOT NULL CHECK(length(trim(kind)) BETWEEN 1 AND 40))",
"CREATE INDEX idx_sde_locations_name ON sde_locations(name COLLATE NOCASE)",
)),)

@dataclass(frozen=True, slots=True)
class DatabaseStatus:
    schema_version:int; journal_mode:str; foreign_keys:bool; busy_timeout_ms:int; integrity:str; last_migration_backup:str|None
class DatabaseSchemaError(RuntimeError): pass
class DatabaseMigrationError(RuntimeError): pass

def _validate_migration_definitions():
    versions=[v for v,_,_ in MIGRATIONS]
    if versions!=list(range(1,SCHEMA_VERSION+1)): raise DatabaseSchemaError("Application migration definitions are incomplete or out of order.")
    names=[n for _,n,_ in MIGRATIONS]
    if len(names)!=len(set(names)): raise DatabaseSchemaError("Application migration names must be unique.")

def connect_database(path:Path)->sqlite3.Connection:
    path=path.expanduser().resolve(); path.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(path,timeout=BUSY_TIMEOUT_MILLISECONDS/1000,isolation_level=None); c.row_factory=sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON"); journal=str(c.execute("PRAGMA journal_mode=WAL").fetchone()[0]); c.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MILLISECONDS}")
    if journal.lower()!='wal' or c.execute("PRAGMA foreign_keys").fetchone()[0]!=1 or c.execute("PRAGMA busy_timeout").fetchone()[0]!=BUSY_TIMEOUT_MILLISECONDS: c.close(); raise RuntimeError("SQLite production settings unavailable.")
    return c

def current_schema_version(c):
    _validate_migration_definitions(); uv=int(c.execute("PRAGMA user_version").fetchone()[0]); exists=c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'").fetchone()
    if exists is None:
        if uv!=0: raise DatabaseSchemaError("The database has a user version but no migration history.")
        return 0
    rows=list(c.execute("SELECT version,name FROM schema_migrations ORDER BY version")); versions=[int(r[0]) for r in rows]
    if versions!=list(range(1,len(versions)+1)): raise DatabaseSchemaError("The database migration history has gaps.")
    rv=versions[-1] if versions else 0
    if rv!=uv or rv>SCHEMA_VERSION: raise DatabaseSchemaError("The database migration history is incompatible.")
    names={v:n for v,n,_ in MIGRATIONS}
    if any(names.get(int(r[0]))!=str(r[1]) for r in rows): raise DatabaseSchemaError("Migration history does not match this application build.")
    return rv

def apply_migrations(c,*,backup:MigrationBackup|None=None):
    applied=current_schema_version(c)
    if backup is not None and (backup.source_schema_version!=applied or backup.target_schema_version!=SCHEMA_VERSION or applied>=SCHEMA_VERSION): raise DatabaseSchemaError("The migration backup does not match the pending schema change.")
    c.execute("BEGIN IMMEDIATE")
    try:
        c.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,applied_at TEXT NOT NULL DEFAULT(strftime('%Y-%m-%dT%H:%M:%fZ','now')))")
        for version,name,statements in MIGRATIONS:
            if version<=applied: continue
            for statement in statements: c.execute(statement)
            c.execute("INSERT INTO schema_migrations(version,name) VALUES(?,?)",(version,name)); c.execute(f"PRAGMA user_version={version}")
        if backup is not None: c.execute("INSERT INTO migration_backups(filename,source_schema_version,target_schema_version,sha256,size_bytes,created_at) VALUES(?,?,?,?,?,?)",(backup.filename,backup.source_schema_version,backup.target_schema_version,backup.sha256,backup.size_bytes,backup.created_at))
        c.execute("COMMIT")
    except BaseException: c.execute("ROLLBACK"); raise

def inspect_database(c):
    quick=str(c.execute("PRAGMA quick_check").fetchone()[0]); violations=list(c.execute("PRAGMA foreign_key_check"))
    if quick.lower()!='ok' or violations: raise RuntimeError("SQLite integrity check failed.")
    row=c.execute("SELECT filename FROM migration_backups ORDER BY created_at DESC,id DESC LIMIT 1").fetchone()
    return DatabaseStatus(current_schema_version(c),str(c.execute("PRAGMA journal_mode").fetchone()[0]),bool(c.execute("PRAGMA foreign_keys").fetchone()[0]),int(c.execute("PRAGMA busy_timeout").fetchone()[0]),quick.lower(),str(row['filename']) if row else None)

def initialize_database(path:Path,backup_directory:Path|None=None):
    resolved=path.expanduser().resolve(); pre=resolved.is_file() and resolved.stat().st_size>0; backup_dir=backup_directory.expanduser() if backup_directory else resolved.parent/'backups'; c=connect_database(resolved); backup=None
    try:
        source=current_schema_version(c)
        if pre and source<SCHEMA_VERSION:
            backup=create_migration_backup(c,backup_dir,source_schema_version=source,target_schema_version=SCHEMA_VERSION); prune_migration_backups(backup_dir,preserve=(backup.path,))
        try:
            apply_migrations(c,backup=backup); status=inspect_database(c)
            if status.schema_version!=SCHEMA_VERSION: raise DatabaseSchemaError("Unexpected schema version.")
            return status
        except Exception as migration_error:
            if backup is None: raise
            c.close(); c=None
            try: restore_database_backup(resolved,backup.path,expected_schema_version=backup.source_schema_version,expected_sha256=backup.sha256)
            except DatabaseRestoreError as restore_error: raise DatabaseMigrationError("Database migration and automatic restoration both failed; the verified backup was retained.") from restore_error
            raise DatabaseMigrationError("Database migration failed; the pre-migration backup was restored.") from migration_error
    finally:
        if c is not None: c.close()
