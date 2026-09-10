from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from new_eden_foundry_backend.storage import (
    ProgramStorageError,
    prepare_program_storage,
    resolve_program_storage,
)


class ProgramStorageTests(unittest.TestCase):
    def test_database_and_backups_resolve_inside_program_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            program_directory = Path(temporary_directory).resolve()

            storage = prepare_program_storage(program_directory)

            self.assertEqual(
                storage.database_path,
                program_directory / "data" / "foundry.sqlite3",
            )
            self.assertEqual(
                storage.backup_directory,
                program_directory / "data" / "backups",
            )
            self.assertEqual(
                storage.export_directory,
                program_directory / "data" / "exports",
            )
            self.assertEqual(storage.relative_database_path.as_posix(), "data/foundry.sqlite3")
            self.assertTrue(storage.data_directory.is_dir())
            self.assertTrue(storage.backup_directory.is_dir())
            self.assertTrue(storage.export_directory.is_dir())
            self.assertEqual(list(storage.data_directory.glob(".foundry-write-test-*")), [])

    def test_missing_program_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing = Path(temporary_directory) / "missing"

            with self.assertRaisesRegex(ProgramStorageError, "does not exist"):
                resolve_program_storage(missing)

    def test_unwritable_program_storage_has_no_silent_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            program_directory = Path(temporary_directory)
            original_open = Path.open

            def reject_probe(path: Path, *args: object, **kwargs: object):
                if path.name.startswith(".foundry-write-test-"):
                    raise PermissionError("synthetic permission failure")
                return original_open(path, *args, **kwargs)

            with patch.object(Path, "open", autospec=True, side_effect=reject_probe):
                with self.assertRaisesRegex(ProgramStorageError, "no alternate database path"):
                    prepare_program_storage(program_directory)

            self.assertFalse((program_directory / "foundry.sqlite3").exists())

    def test_database_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            program_directory = root / "program"
            external_directory = root / "external"
            program_directory.mkdir()
            external_directory.mkdir()
            data_directory = program_directory / "data"
            data_directory.mkdir()
            target = external_directory / "outside.sqlite3"
            target.touch()

            try:
                (data_directory / "foundry.sqlite3").symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Symbolic links are unavailable in this environment.")

            with self.assertRaisesRegex(ProgramStorageError, "symbolic link"):
                resolve_program_storage(program_directory)


if __name__ == "__main__":
    unittest.main()
