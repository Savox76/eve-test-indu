#!/usr/bin/env python3
"""Build the target-specific Python sidecar used by the Tauri package."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
ENTRY_POINT = BACKEND / "sidecar_entry.py"
PACKAGE_JSON = ROOT / "package.json"
UPDATE_TEST_MANIFEST = (
    BACKEND / "new_eden_foundry_backend" / "resources" / "update-test-manifest.json"
)
UPDATE_TEST_SIGNATURE = UPDATE_TEST_MANIFEST.with_suffix(".sig")
SSO_REGISTRATION_PROFILE = (
    BACKEND / "new_eden_foundry_backend" / "resources" / "eve-sso-registration.json"
)
OFFICIAL_INDUSTRY_SDE = (
    BACKEND / "new_eden_foundry_backend" / "resources" / "official-industry-sde.json.gz"
)
OFFICIAL_SDE_SOURCE = (
    BACKEND / "new_eden_foundry_backend" / "resources" / "official-sde-source.json"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-triple", required=True)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    target_triple = arguments.target_triple.strip()
    if not target_triple or any(character.isspace() for character in target_triple):
        raise ValueError("The Rust target triple is invalid.")

    work_directory = ROOT / "build" / "sidecar"
    dist_directory = work_directory / "dist"
    spec_directory = work_directory / "spec"
    executable_suffix = ".exe" if os.name == "nt" else ""
    built_executable = dist_directory / f"foundry-sidecar{executable_suffix}"
    target_executable = (
        ROOT
        / "src-tauri"
        / "binaries"
        / f"foundry-sidecar-{target_triple}{executable_suffix}"
    )

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--noupx",
        "--name",
        "foundry-sidecar",
        "--paths",
        str(BACKEND),
        "--add-data",
        f"{PACKAGE_JSON}{os.pathsep}.",
        "--add-data",
        (
            f"{UPDATE_TEST_MANIFEST}{os.pathsep}"
            "new_eden_foundry_backend/resources"
        ),
        "--add-data",
        (
            f"{UPDATE_TEST_SIGNATURE}{os.pathsep}"
            "new_eden_foundry_backend/resources"
        ),
        "--add-data",
        (
            f"{SSO_REGISTRATION_PROFILE}{os.pathsep}"
            "new_eden_foundry_backend/resources"
        ),
        "--add-data",
        (
            f"{OFFICIAL_INDUSTRY_SDE}{os.pathsep}"
            "new_eden_foundry_backend/resources"
        ),
        "--add-data",
        (
            f"{OFFICIAL_SDE_SOURCE}{os.pathsep}"
            "new_eden_foundry_backend/resources"
        ),
        "--collect-submodules",
        "uvicorn",
        "--distpath",
        str(dist_directory),
        "--workpath",
        str(work_directory / "work"),
        "--specpath",
        str(spec_directory),
        str(ENTRY_POINT),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    if not built_executable.is_file():
        raise FileNotFoundError(f"PyInstaller did not create {built_executable}.")

    target_executable.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built_executable, target_executable)
    print(
        json.dumps(
            {
                "source": str(built_executable.relative_to(ROOT)),
                "target": str(target_executable.relative_to(ROOT)),
                "bytes": target_executable.stat().st_size,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
