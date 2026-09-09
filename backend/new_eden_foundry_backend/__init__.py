"""Local application core for New Eden Foundry."""

from .database import (
    DatabaseMigrationError,
    DatabaseSchemaError,
    DatabaseStatus,
    initialize_database,
)
from .identity import (
    AccountGroup,
    CharacterRecord,
    create_account_group,
    list_account_groups,
    list_characters,
    upsert_character,
)
from .recovery import (
    DatabaseBackupError,
    DatabaseRestoreError,
    MigrationBackup,
    create_migration_backup,
    restore_database_backup,
    verify_database_backup,
)
from .storage import (
    ProgramStorage,
    ProgramStorageError,
    prepare_program_storage,
    resolve_program_storage,
)
from .startup_state import StartupDataState, inspect_startup_data_state
from .updater import (
    UpdateChannel,
    UpdateManifestError,
    VerifiedUpdateManifest,
    read_update_channel,
    set_update_channel,
    verify_bundled_test_manifest,
    verify_test_update_manifest,
)
from .version import project_version

__all__ = [
    "AccountGroup",
    "CharacterRecord",
    "DatabaseBackupError",
    "DatabaseMigrationError",
    "DatabaseRestoreError",
    "DatabaseSchemaError",
    "DatabaseStatus",
    "MigrationBackup",
    "ProgramStorage",
    "ProgramStorageError",
    "StartupDataState",
    "UpdateChannel",
    "UpdateManifestError",
    "VerifiedUpdateManifest",
    "create_account_group",
    "create_migration_backup",
    "initialize_database",
    "inspect_startup_data_state",
    "list_account_groups",
    "list_characters",
    "prepare_program_storage",
    "project_version",
    "read_update_channel",
    "resolve_program_storage",
    "restore_database_backup",
    "set_update_channel",
    "upsert_character",
    "verify_database_backup",
    "verify_bundled_test_manifest",
    "verify_test_update_manifest",
]
