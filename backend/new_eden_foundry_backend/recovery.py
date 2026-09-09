"""Consistent SQLite migration backups and verified restoration."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Iterable
from uuid import uuid4


MAX_MIGRATION_BACKUPS: Final = 5
BACKUP_FILENAME_PATTERN: Final = re.compile(
    r"^foundry-schema-v\d{4}-to-v\d{4}-"
    r"\d{8}T\d{12}Z-[0-9a-f]{8}\.sqlite3$"
)


class DatabaseBackupError(RuntimeError):
    """Raised when a migration backup cannot be created or verified."""


class DatabaseRestoreError(RuntimeError):
    """Raised when a verified backup cannot safely replace a database."""


@dataclass(frozen=True, slots=True)
class MigrationBackup:
    path: Path
    source_schema_version: int
    target_schema_version: int
    created_at: str
    sha256: str
    size_bytes: int

    @property
    def filename(self) -> str:
        return self.path.name


def _schema_version(connection: sqlite3.Connection) -> int:
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
            raise DatabaseBackupError(
                "The database has a user version but no migration history."
            )
        return 0

    migration_versions = [
        int(row[0])
        for row in connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        )
    ]
    if migration_versions != list(range(1, len(migration_versions) + 1)):
        raise DatabaseBackupError("The database migration history has gaps.")
    migration_version = migration_versions[-1] if migration_versions else 0
    if migration_version != user_version:
        raise DatabaseBackupError(
            "The database migration history and user version disagree."
        )
    return migration_version


def _verify_connection(
    connection: sqlite3.Connection,
    *,
    expected_schema_version: int,
) -> None:
    quick_check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
    if quick_check.lower() != "ok":
        raise DatabaseBackupError(f"SQLite quick_check failed: {quick_check}")
    if list(connection.execute("PRAGMA foreign_key_check")):
        raise DatabaseBackupError("SQLite foreign_key_check reported violations.")
    actual_schema_version = _schema_version(connection)
    if actual_schema_version != expected_schema_version:
        raise DatabaseBackupError(
            "The database image has an unexpected schema version: "
            f"expected {expected_schema_version}, got {actual_schema_version}."
        )


def _open_read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(
        f"{path.resolve(strict=True).as_uri()}?mode=ro",
        uri=True,
        isolation_level=None,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _flush_file(path: Path) -> None:
    with path.open("r+b") as stream:
        os.fsync(stream.fileno())


def _temporary_database(directory: Path, prefix: str) -> Path:
    descriptor, raw_path = tempfile.mkstemp(
        prefix=prefix,
        suffix=".tmp",
        dir=directory,
    )
    os.close(descriptor)
    return Path(raw_path)


def _copy_database(
    source: sqlite3.Connection,
    destination_path: Path,
    *,
    expected_schema_version: int,
) -> None:
    destination = sqlite3.connect(destination_path, isolation_level=None)
    try:
        source.backup(destination)
        journal_mode = str(
            destination.execute("PRAGMA journal_mode = DELETE").fetchone()[0]
        )
        if journal_mode.lower() != "delete":
            raise DatabaseBackupError(
                "The standalone database image could not leave WAL mode."
            )
        _verify_connection(
            destination,
            expected_schema_version=expected_schema_version,
        )
    finally:
        destination.close()
    _flush_file(destination_path)


def create_migration_backup(
    source: sqlite3.Connection,
    backup_directory: Path,
    *,
    source_schema_version: int,
    target_schema_version: int,
) -> MigrationBackup:
    """Create, verify and atomically publish one pre-migration snapshot."""

    if source_schema_version >= target_schema_version:
        raise DatabaseBackupError(
            "A migration backup requires a newer target schema version."
        )
    if source.in_transaction:
        raise DatabaseBackupError(
            "A migration backup cannot start inside an active transaction."
        )
    if backup_directory.is_symlink():
        raise DatabaseBackupError("The backup directory must not be a symbolic link.")

    try:
        backup_directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise DatabaseBackupError("The backup directory could not be created.") from error
    if not backup_directory.is_dir() or backup_directory.is_symlink():
        raise DatabaseBackupError("The backup path is not a regular directory.")

    created = datetime.now(UTC)
    created_at = created.isoformat(timespec="microseconds").replace("+00:00", "Z")
    timestamp = created.strftime("%Y%m%dT%H%M%S%fZ")
    final_path = backup_directory / (
        f"foundry-schema-v{source_schema_version:04d}-"
        f"to-v{target_schema_version:04d}-{timestamp}-{uuid4().hex[:8]}.sqlite3"
    )
    temporary_path = _temporary_database(backup_directory, ".foundry-backup-")

    try:
        _copy_database(
            source,
            temporary_path,
            expected_schema_version=source_schema_version,
        )
        checksum = _sha256(temporary_path)
        size_bytes = temporary_path.stat().st_size
        if final_path.exists() or final_path.is_symlink():
            raise DatabaseBackupError("The generated backup path already exists.")
        os.replace(temporary_path, final_path)
    except DatabaseBackupError:
        raise
    except (OSError, sqlite3.Error) as error:
        raise DatabaseBackupError(
            "The pre-migration database backup could not be completed."
        ) from error
    finally:
        temporary_path.unlink(missing_ok=True)

    return MigrationBackup(
        path=final_path,
        source_schema_version=source_schema_version,
        target_schema_version=target_schema_version,
        created_at=created_at,
        sha256=checksum,
        size_bytes=size_bytes,
    )


def prune_migration_backups(
    backup_directory: Path,
    *,
    keep: int = MAX_MIGRATION_BACKUPS,
    preserve: Iterable[Path] = (),
) -> None:
    """Keep the newest verified-looking migration backup filenames."""

    if keep < 1:
        raise ValueError("At least one migration backup must be retained.")
    preserved = {path.resolve() for path in preserve}
    candidates: list[Path] = []
    try:
        for path in backup_directory.iterdir():
            if not BACKUP_FILENAME_PATTERN.fullmatch(path.name):
                continue
            if path.is_symlink() or not path.is_file():
                raise DatabaseBackupError(
                    "A migration backup path is not a regular file."
                )
            candidates.append(path)
    except OSError as error:
        raise DatabaseBackupError("Migration backups could not be listed.") from error

    candidates.sort(key=lambda path: path.name, reverse=True)
    retained = {path.resolve() for path in candidates[:keep]} | preserved
    try:
        for path in candidates:
            if path.resolve() not in retained:
                path.unlink()
    except OSError as error:
        raise DatabaseBackupError("An expired migration backup could not be removed.") from error


def verify_database_backup(
    backup_path: Path,
    *,
    expected_schema_version: int,
    expected_sha256: str | None = None,
) -> None:
    """Verify checksum, SQLite integrity and schema version without modifying a backup."""

    if backup_path.is_symlink() or not backup_path.is_file():
        raise DatabaseBackupError("The selected backup is not a regular file.")
    if expected_sha256 is not None and _sha256(backup_path) != expected_sha256:
        raise DatabaseBackupError("The selected backup checksum does not match.")

    try:
        connection = _open_read_only(backup_path)
        try:
            _verify_connection(
                connection,
                expected_schema_version=expected_schema_version,
            )
        finally:
            connection.close()
    except DatabaseBackupError:
        raise
    except (OSError, sqlite3.Error) as error:
        raise DatabaseBackupError("The selected backup is not a valid database.") from error


def _settle_existing_database(database_path: Path) -> None:
    sidecars = tuple(
        Path(f"{database_path}{suffix}") for suffix in ("-wal", "-shm", "-journal")
    )
    if not database_path.exists() or not any(path.exists() for path in sidecars):
        return

    try:
        connection = sqlite3.connect(database_path, timeout=5, isolation_level=None)
        try:
            checkpoint = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            if checkpoint is not None and int(checkpoint[0]) != 0:
                raise DatabaseRestoreError(
                    "The current database is still in use and cannot be restored."
                )
        finally:
            connection.close()
    except DatabaseRestoreError:
        raise
    except sqlite3.Error as error:
        raise DatabaseRestoreError(
            "The current database journal could not be settled safely."
        ) from error

    if any(path.exists() for path in sidecars):
        raise DatabaseRestoreError(
            "The current database still has active journal files."
        )


def restore_database_backup(
    database_path: Path,
    backup_path: Path,
    *,
    expected_schema_version: int,
    expected_sha256: str | None = None,
) -> None:
    """Verify a backup and atomically restore it while the application is stopped."""

    database_path = database_path.expanduser()
    backup_path = backup_path.expanduser()
    if database_path.is_symlink():
        raise DatabaseRestoreError("The database path must not be a symbolic link.")
    database_path = database_path.resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        verify_database_backup(
            backup_path,
            expected_schema_version=expected_schema_version,
            expected_sha256=expected_sha256,
        )
    except DatabaseBackupError as error:
        raise DatabaseRestoreError("The selected backup failed verification.") from error

    temporary_path = _temporary_database(database_path.parent, ".foundry-restore-")
    try:
        with backup_path.open("rb") as source, temporary_path.open("wb") as destination:
            shutil.copyfileobj(source, destination, length=1024 * 1024)
            destination.flush()
            os.fsync(destination.fileno())
        verify_database_backup(
            temporary_path,
            expected_schema_version=expected_schema_version,
            expected_sha256=expected_sha256,
        )
        _settle_existing_database(database_path)
        os.replace(temporary_path, database_path)
    except DatabaseRestoreError:
        raise
    except (OSError, sqlite3.Error, DatabaseBackupError) as error:
        raise DatabaseRestoreError("The database backup could not be restored.") from error
    finally:
        temporary_path.unlink(missing_ok=True)

    try:
        verify_database_backup(
            database_path,
            expected_schema_version=expected_schema_version,
            expected_sha256=expected_sha256,
        )
    except DatabaseBackupError as error:
        raise DatabaseRestoreError(
            "The restored database failed its final verification."
        ) from error
