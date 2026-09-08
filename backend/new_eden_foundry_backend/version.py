"""Read the product version from the repository's single version source."""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _default_package_path() -> Path:
    candidates = [PROJECT_ROOT / "package.json"]
    if getattr(sys, "frozen", False):
        candidates.insert(0, Path(__file__).resolve().parents[1] / "package.json")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("The bundled product version source is missing.")


def project_version(package_path: Path | None = None) -> str:
    source = package_path or _default_package_path()
    package = json.loads(source.read_text(encoding="utf-8"))
    version = package.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ValueError(f"No valid product version in {source}.")
    return version
