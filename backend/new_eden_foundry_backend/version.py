"""Read the product version from the repository's single version source."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def project_version(package_path: Path | None = None) -> str:
    source = package_path or PROJECT_ROOT / "package.json"
    package = json.loads(source.read_text(encoding="utf-8"))
    version = package.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ValueError(f"No valid product version in {source}.")
    return version
