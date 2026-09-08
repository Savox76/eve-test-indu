"""Deterministic storage paths inside the application program directory."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from uuid import uuid4


DATA_DIRECTORY_NAME: Final = "data"
DATABASE_FILENAME: Final = "foundry.sqlite3"
BACKUP_DIRECTORY_NAME: Final = "backups"


class ProgramStorageError(RuntimeError):
    """Raised when the required program-folder storage cannot be used safely."""


@dataclass(frozen=True, slots=True)
class ProgramStorage:
    program_directory: Path
    data_directory: Path
    database_path: Path
    backup_directory: Path

    @property
    def relative_database_path(self) -> Path:
        return Path(DATA_DIRECTORY_NAME) / DATABASE_FILENAME


def resolve_program_storage(program_directory: Path) -> ProgramStorage:
    """Resolve the one allowed production database location without a fallback."""

    try:
        resolved_program_directory = program_directory.expanduser().resolve(strict=True)
    except OSError as error:
        raise ProgramStorageError("The program directory does not exist.") from error

    if not resolved_program_directory.is_dir():
        raise ProgramStorageError("The program path is not a directory.")

    data_directory = resolved_program_directory / DATA_DIRECTORY_NAME
    database_path = data_directory / DATABASE_FILENAME
    backup_directory = data_directory / BACKUP_DIRECTORY_NAME

    for path, label in (
        (data_directory, "data directory"),
        (database_path, "database"),
        (backup_directory, "backup directory"),
    ):
        if path.is_symlink():
            raise ProgramStorageError(
                f"The program-folder {label} must not redirect through a symbolic link."
            )

    if database_path.exists() and not database_path.is_file():
        raise ProgramStorageError("The database path is not a regular file.")

    return ProgramStorage(
        program_directory=resolved_program_directory,
        data_directory=data_directory,
        database_path=database_path,
        backup_directory=backup_directory,
    )


def prepare_program_storage(program_directory: Path) -> ProgramStorage:
    """Create and verify writable storage next to the application executable."""

    storage = resolve_program_storage(program_directory)
    try:
        storage.data_directory.mkdir(exist_ok=True)
        storage.backup_directory.mkdir(exist_ok=True)
    except OSError as error:
        raise ProgramStorageError(
            "The data directory could not be created inside the program directory."
        ) from error

    if storage.data_directory.is_symlink() or storage.backup_directory.is_symlink():
        raise ProgramStorageError(
            "Program-folder storage must not redirect through a symbolic link."
        )

    probe = storage.data_directory / f".foundry-write-test-{uuid4().hex}.tmp"
    try:
        with probe.open("xb") as stream:
            stream.write(b"New Eden Foundry storage check\n")
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        raise ProgramStorageError(
            "The program directory is not writable; no alternate database path was used."
        ) from error
    finally:
        try:
            probe.unlink(missing_ok=True)
        except OSError:
            pass

    return storage
