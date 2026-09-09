from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from new_eden_foundry_backend.appearance import (
    FontScale,
    appearance_payload,
    read_font_scale,
    set_font_scale,
)
from new_eden_foundry_backend.database import connect_database, initialize_database


class AppearancePreferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "foundry.sqlite3"
        initialize_database(database_path)
        self.connection = connect_database(database_path)

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def test_existing_database_defaults_to_normal_without_migration(self) -> None:
        self.assertEqual(read_font_scale(self.connection), FontScale.NORMAL)

    def test_persists_each_bounded_font_scale_stage(self) -> None:
        for font_scale in FontScale:
            with self.subTest(font_scale=font_scale):
                saved = set_font_scale(self.connection, font_scale.value)
                self.assertEqual(saved, font_scale)
                self.assertEqual(read_font_scale(self.connection), font_scale)
                self.assertEqual(appearance_payload(saved), {"fontScale": font_scale.value})

    def test_rejects_unknown_or_non_text_scale(self) -> None:
        for value in ("giant", "", None, 1):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    set_font_scale(self.connection, value)


if __name__ == "__main__":
    unittest.main()
