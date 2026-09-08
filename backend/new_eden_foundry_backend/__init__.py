"""Local application core for New Eden Foundry."""

from .database import DatabaseStatus, initialize_database
from .identity import (
    AccountGroup,
    CharacterRecord,
    create_account_group,
    list_account_groups,
    list_characters,
    upsert_character,
)
from .storage import (
    ProgramStorage,
    ProgramStorageError,
    prepare_program_storage,
    resolve_program_storage,
)
from .version import project_version

__all__ = [
    "AccountGroup",
    "CharacterRecord",
    "DatabaseStatus",
    "ProgramStorage",
    "ProgramStorageError",
    "create_account_group",
    "initialize_database",
    "list_account_groups",
    "list_characters",
    "prepare_program_storage",
    "project_version",
    "resolve_program_storage",
    "upsert_character",
]
