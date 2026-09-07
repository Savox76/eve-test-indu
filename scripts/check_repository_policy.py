#!/usr/bin/env python3
"""Validate repository rules that can be checked without project dependencies."""

from __future__ import annotations

import re
import sys
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


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def check_workflows(errors: list[str]) -> None:
    workflows = sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))
    if not workflows:
        errors.append("No GitHub Actions workflow exists.")
        return

    for workflow in workflows:
        content = workflow.read_text(encoding="utf-8")
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


def main() -> int:
    errors: list[str] = []
    check_workflows(errors)
    check_documentation(errors)

    if errors:
        print("Repository policy violations:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Repository policy checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
