from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from new_eden_foundry_backend.__main__ import main
from new_eden_foundry_backend.version import PROJECT_ROOT, project_version


class FoundationStatusTests(unittest.TestCase):
    def test_backend_uses_package_json_as_version_source(self) -> None:
        package = json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8"))

        self.assertEqual(project_version(), package["version"])

    def test_self_check_reports_verified_database_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "self-check.sqlite3"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(["--database", str(database_path)])

        result = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["state"], "foundation-ready")
        self.assertEqual(result["database"]["integrity"], "ok")
        self.assertEqual(result["database"]["schema_version"], 5)
        self.assertIsNone(result["database"]["last_migration_backup"])
        self.assertEqual(result["data"]["state"], "empty")
        self.assertFalse(result["data"]["hasCachedData"])
        self.assertEqual(result["updater"]["channel"], "stable")
        self.assertEqual(result["updater"]["manifest_state"], "verified")
        self.assertEqual(result["updater"]["test_manifest_version"], "0.0.4-preview.1")
        self.assertFalse(result["updater"]["public_distribution"])


if __name__ == "__main__":
    unittest.main()
