#!/usr/bin/env python3
"""Validate repository rules that can be checked without project dependencies."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"

ACTION_REFERENCE = re.compile(
    r"^\s*-?\s*uses:\s*([^\s#]+)",
    flags=re.MULTILINE,
)
FULL_COMMIT_SHA = re.compile(r"^[^@]+@[0-9a-f]{40}$")
ARTIFACT_ACTION = re.compile(
    r"^actions/(?:upload|download)-artifact@",
    flags=re.IGNORECASE,
)

REQUIRED_RELEASE_HEADINGS = (
    "## Neu hinzugefügt",
    "## Geändert",
    "## Behobene Fehler",
    "## Bekannte Einschränkungen",
    "## Update und Datenbankmigration",
)

REQUIRED_ADRS = tuple(
    ROOT / "docs" / "adr" / name
    for name in (
        "0001-desktop-local-first.md",
        "0002-tauri-python-sidecar.md",
        "0003-sqlite-persistence.md",
        "0004-eve-sso-pkce.md",
        "0005-central-public-repository-and-releases.md",
        "0006-cache-first-sync.md",
        "0007-decimal-and-golden-tests.md",
        "0008-jita-first-market-adapters.md",
    )
)

REQUIRED_BACKEND_FILES = tuple(
    ROOT / path
    for path in (
        "backend/new_eden_foundry_backend/__main__.py",
        "backend/new_eden_foundry_backend/database.py",
        "backend/new_eden_foundry_backend/version.py",
        "backend/tests/test_database.py",
        "backend/tests/test_foundation_status.py",
    )
)

REQUIRED_SQLITE_MARKERS = (
    "PRAGMA foreign_keys = ON",
    "PRAGMA journal_mode = WAL",
    "PRAGMA busy_timeout",
    "PRAGMA quick_check",
    "PRAGMA foreign_key_check",
    "BEGIN IMMEDIATE",
)


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def check_workflows(errors: list[str]) -> None:
    workflows = sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))
    if not workflows:
        errors.append("No GitHub Actions workflow exists.")
        return

    for workflow in workflows:
        content = workflow.read_text(encoding="utf-8")
        for line_number, line in enumerate(content.splitlines(), start=1):
            stripped = line.lstrip()
            if not stripped.startswith("if: "):
                continue
            value = stripped.removeprefix("if: ")
            if ": " in value and not value.startswith(("'", '"')):
                errors.append(
                    f"{relative(workflow)}:{line_number} must quote an if expression "
                    "that contains a YAML colon."
                )

        for reference in ACTION_REFERENCE.findall(content):
            if reference.startswith("./"):
                continue
            if ARTIFACT_ACTION.match(reference):
                errors.append(
                    f"{relative(workflow)} uses forbidden Actions artifact transport: {reference}"
                )
            if not FULL_COMMIT_SHA.match(reference):
                errors.append(
                    f"{relative(workflow)} must pin action to a full commit SHA: {reference}"
                )

        if "gitleaks/gitleaks-action@" in content:
            expected = 'GITLEAKS_ENABLE_UPLOAD_ARTIFACT: "false"'
            if expected not in content:
                errors.append(
                    f"{relative(workflow)} must explicitly disable Gitleaks artifact upload."
                )

    release_workflow = WORKFLOW_DIR / "release.yml"
    if not release_workflow.is_file():
        errors.append("Missing generic Windows release workflow: .github/workflows/release.yml")
    else:
        release_content = release_workflow.read_text(encoding="utf-8")
        for marker in (
            "scripts/package_portable.ps1",
            "_x64-portable.zip",
            "Get-FileHash -Algorithm SHA256",
        ):
            if marker not in release_content:
                errors.append(
                    f"{relative(release_workflow)} is missing portable release marker: {marker}"
                )


def check_documentation(errors: list[str]) -> None:
    for adr in REQUIRED_ADRS:
        if not adr.is_file():
            errors.append(f"Missing required ADR: {relative(adr)}")

    synthetic_policy = ROOT / "docs" / "policies" / "synthetic-data.md"
    if not synthetic_policy.is_file():
        errors.append("Missing synthetic data policy.")

    releasing = ROOT / "docs" / "RELEASING.md"
    if not releasing.is_file():
        errors.append("Missing release rules.")
        return

    content = releasing.read_text(encoding="utf-8")
    for heading in REQUIRED_RELEASE_HEADINGS:
        if heading not in content:
            errors.append(f"docs/RELEASING.md is missing required heading: {heading}")

    portable_script = ROOT / "scripts" / "package_portable.ps1"
    portable_readme = ROOT / "docs" / "portable" / "README-DE-EN.txt"
    if not portable_script.is_file():
        errors.append("Missing portable packaging script.")
    if not portable_readme.is_file():
        errors.append("Missing portable package usage notes.")
    if "portable ZIP" not in content:
        errors.append("docs/RELEASING.md must require a portable ZIP.")


def check_application_release(errors: list[str]) -> None:
    package_path = ROOT / "package.json"
    if not package_path.is_file():
        return

    package = json.loads(package_path.read_text(encoding="utf-8"))
    version = package.get("version")
    if not isinstance(version, str) or not version:
        errors.append("package.json must define a non-empty version.")
        return

    tauri_config_path = ROOT / "src-tauri" / "tauri.conf.json"
    if not tauri_config_path.is_file():
        errors.append("Application package exists but src-tauri/tauri.conf.json is missing.")
    else:
        tauri_config = json.loads(tauri_config_path.read_text(encoding="utf-8"))
        if tauri_config.get("version") != "../package.json":
            errors.append("Tauri must read its application version from ../package.json.")

    cargo_path = ROOT / "src-tauri" / "Cargo.toml"
    if not cargo_path.is_file():
        errors.append("Application package exists but src-tauri/Cargo.toml is missing.")
    else:
        cargo = tomllib.loads(cargo_path.read_text(encoding="utf-8"))
        if cargo.get("package", {}).get("version") != version:
            errors.append("Cargo package version must match package.json.")

    release_notes_path = ROOT / "docs" / "releases" / f"v{version}.md"
    if not release_notes_path.is_file():
        errors.append(f"Missing release notes: {relative(release_notes_path)}")
    else:
        release_notes = release_notes_path.read_text(encoding="utf-8")
        for heading in REQUIRED_RELEASE_HEADINGS:
            if heading not in release_notes:
                errors.append(
                    f"{relative(release_notes_path)} is missing required heading: {heading}"
                )

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## {version}" not in changelog:
        errors.append(f"CHANGELOG.md has no section for {version}.")

    demo_source = ROOT / "frontend" / "src" / "demo.ts"
    if not demo_source.is_file() or "synthetic: true" not in demo_source.read_text(
        encoding="utf-8"
    ):
        errors.append("The versioned UI demo data must explicitly contain synthetic: true.")


def check_backend_foundation(errors: list[str]) -> None:
    for path in REQUIRED_BACKEND_FILES:
        if not path.is_file():
            errors.append(f"Missing backend foundation file: {relative(path)}")

    database_source = ROOT / "backend" / "new_eden_foundry_backend" / "database.py"
    if database_source.is_file():
        content = database_source.read_text(encoding="utf-8")
        for marker in REQUIRED_SQLITE_MARKERS:
            if marker not in content:
                errors.append(f"SQLite foundation is missing required marker: {marker}")

    package_path = ROOT / "package.json"
    if not package_path.is_file():
        return

    scripts = json.loads(package_path.read_text(encoding="utf-8")).get("scripts", {})
    for script in ("test:frontend", "test:backend", "check:backend"):
        if not isinstance(scripts.get(script), str) or not scripts[script].strip():
            errors.append(f"package.json must define the {script} script.")

    combined_test = scripts.get("test")
    if not isinstance(combined_test, str) or not all(
        script in combined_test for script in ("test:frontend", "test:backend")
    ):
        errors.append("The npm test script must run both frontend and backend tests.")


def main() -> int:
    errors: list[str] = []
    check_workflows(errors)
    check_documentation(errors)
    check_application_release(errors)
    check_backend_foundation(errors)

    if errors:
        print("Repository policy violations:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Repository policy checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
