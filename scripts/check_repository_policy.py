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
        "0009-multi-character-scopes-and-local-account-groups.md",
        "0010-program-folder-storage.md",
        "0011-signed-update-channel-skeleton.md",
        "0012-fixed-eve-sso-registration-profile.md",
    )
)

REQUIRED_BACKEND_FILES = tuple(
    ROOT / path
    for path in (
        "backend/new_eden_foundry_backend/__main__.py",
        "backend/new_eden_foundry_backend/appearance.py",
        "backend/new_eden_foundry_backend/database.py",
        "backend/new_eden_foundry_backend/identity.py",
        "backend/new_eden_foundry_backend/recovery.py",
        "backend/new_eden_foundry_backend/sidecar.py",
        "backend/new_eden_foundry_backend/storage.py",
        "backend/new_eden_foundry_backend/startup_state.py",
        "backend/new_eden_foundry_backend/sso_registration.py",
        "backend/new_eden_foundry_backend/sso_pkce.py",
        "backend/new_eden_foundry_backend/sso_tokens.py",
        "backend/new_eden_foundry_backend/token_vault.py",
        "backend/new_eden_foundry_backend/token_service.py",
        "backend/new_eden_foundry_backend/updater.py",
        "backend/new_eden_foundry_backend/version.py",
        "backend/new_eden_foundry_backend/resources/update-test-manifest.json",
        "backend/new_eden_foundry_backend/resources/update-test-manifest.sig",
        "backend/new_eden_foundry_backend/resources/eve-sso-registration.json",
        "backend/requirements-build.txt",
        "backend/requirements-runtime.txt",
        "backend/sidecar_entry.py",
        "backend/tests/test_database.py",
        "backend/tests/test_appearance.py",
        "backend/tests/test_foundation_status.py",
        "backend/tests/test_identity.py",
        "backend/tests/test_sidecar.py",
        "backend/tests/test_storage.py",
        "backend/tests/test_startup_state.py",
        "backend/tests/test_sso_registration.py",
        "backend/tests/test_sso_pkce.py",
        "backend/tests/test_sso_tokens.py",
        "backend/tests/test_token_vault.py",
        "backend/tests/test_token_service.py",
        "backend/tests/test_updater.py",
        "scripts/build_sidecar.py",
        "scripts/prepare_release_files.ps1",
        "scripts/smoke_sidecar.py",
    )
)

REQUIRED_SQLITE_MARKERS = (
    "PRAGMA foreign_keys = ON",
    "PRAGMA journal_mode = WAL",
    "PRAGMA busy_timeout",
    "PRAGMA quick_check",
    "PRAGMA foreign_key_check",
    "BEGIN IMMEDIATE",
    "CREATE TABLE account_groups",
    "CREATE TABLE characters",
    "CREATE TABLE character_scopes",
    "CREATE TABLE migration_backups",
    "ADD COLUMN expires_at",
    "CREATE TABLE app_settings",
    "VALUES ('update_channel', 'stable')",
    "ADD COLUMN alias",
)

REQUIRED_RECOVERY_MARKERS = (
    "source.backup(destination)",
    "PRAGMA journal_mode = DELETE",
    "PRAGMA quick_check",
    "PRAGMA foreign_key_check",
    "MAX_MIGRATION_BACKUPS: Final = 5",
    "os.replace(temporary_path, database_path)",
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
            "scripts/prepare_release_files.ps1",
            "scripts/build_sidecar.py",
            "scripts/smoke_sidecar.py",
            "requirements-build.txt",
            "gh release",
        ):
            if marker not in release_content:
                errors.append(
                    f"{relative(release_workflow)} is missing portable release marker: {marker}"
                )

    release_file_script = ROOT / "scripts" / "prepare_release_files.ps1"
    if release_file_script.is_file():
        release_file_content = release_file_script.read_text(encoding="utf-8")
        for marker in (
            "New.Eden.Foundry_${Version}_x64-setup.exe",
            "New.Eden.Foundry_${Version}_x64-portable.zip",
            "Get-FileHash -Algorithm SHA256",
            "$($package.Name)",
        ):
            if marker not in release_file_content:
                errors.append(
                    f"{relative(release_file_script)} is missing release file marker: {marker}"
                )


def check_documentation(errors: list[str]) -> None:
    for adr in REQUIRED_ADRS:
        if not adr.is_file():
            errors.append(f"Missing required ADR: {relative(adr)}")

    synthetic_policy = ROOT / "docs" / "policies" / "synthetic-data.md"
    if not synthetic_policy.is_file():
        errors.append("Missing synthetic data policy.")

    sso_documentation = ROOT / "docs" / "sso-registration.md"
    if not sso_documentation.is_file():
        errors.append("Missing binding EVE SSO registration documentation.")
    else:
        sso_content = sso_documentation.read_text(encoding="utf-8")
        for marker in (
            "http://127.0.0.1:17891/oauth/callback",
            "Savox76",
            "esi-assets.read_assets.v1",
            "esi-planets.manage_planets.v1",
            "a8409de72d5b4cab9b0424819d0abdec",
        ):
            if marker not in sso_content:
                errors.append(f"SSO registration documentation is missing marker: {marker}")

    pkce_documentation = ROOT / "docs" / "sso-pkce-login.md"
    if not pkce_documentation.is_file():
        errors.append("Missing EVE SSO PKCE operating documentation.")
    else:
        pkce_content = pkce_documentation.read_text(encoding="utf-8")
        for marker in (
            "http://127.0.0.1:17891/oauth/callback",
            "Drei-Minuten-Timeout",
            "exchanging",
            "connected",
            "Paket 14",
        ):
            if marker not in pkce_content:
                errors.append(f"SSO PKCE documentation is missing marker: {marker}")

    token_documentation = ROOT / "docs" / "token-security.md"
    if not token_documentation.is_file():
        errors.append("Missing EVE token storage and rotation documentation.")
    else:
        token_content = token_documentation.read_text(encoding="utf-8")
        for marker in (
            "Windows-Anmeldespeicher",
            "refresh.pending",
            "Access Tokens bleiben ausschließlich im Speicher",
            "keinen Rückfall auf Dateien, SQLite oder Klartext",
        ):
            if marker not in token_content:
                errors.append(f"Token security documentation is missing marker: {marker}")

    character_documentation = ROOT / "docs" / "character-management.md"
    if not character_documentation.is_file():
        errors.append("Missing character-management operating documentation.")
    else:
        character_content = character_documentation.read_text(encoding="utf-8")
        for marker in (
            "**Alias:**",
            "Credential-Status",
            "Scopepaket-Status",
            "zweistufig",
            "rollt der Sidecar die SQLite-Änderung zurück",
        ):
            if marker not in character_content:
                errors.append(
                    f"Character-management documentation is missing marker: {marker}"
                )

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
    for marker in ("foundry-sidecar.exe", "data", "Programmordner"):
        if marker not in content:
            errors.append(f"docs/RELEASING.md is missing program-folder marker: {marker}")


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

    app_source = ROOT / "frontend" / "src" / "App.tsx"
    if app_source.is_file():
        app_content = app_source.read_text(encoding="utf-8")
        for marker in (f'footerVersion: "v{version}"', 'creatorLabel: "Erstellt von"', "Savoxmedia"):
            if marker not in app_content:
                errors.append(f"The UI is missing required release marker: {marker}")
        for forbidden in ("Lokaler Betreiber", "operatorName", "operatorRole"):
            if forbidden in app_content:
                errors.append(f"The UI contains a forbidden creator/profile marker: {forbidden}")


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

    storage_source = ROOT / "backend" / "new_eden_foundry_backend" / "storage.py"
    if storage_source.is_file():
        storage_content = storage_source.read_text(encoding="utf-8")
        for marker in ('DATA_DIRECTORY_NAME: Final = "data"', 'DATABASE_FILENAME: Final = "foundry.sqlite3"', "no alternate database path"):
            if marker not in storage_content:
                errors.append(f"Program-folder storage is missing required marker: {marker}")

    recovery_source = ROOT / "backend" / "new_eden_foundry_backend" / "recovery.py"
    if recovery_source.is_file():
        recovery_content = recovery_source.read_text(encoding="utf-8")
        for marker in REQUIRED_RECOVERY_MARKERS:
            if marker not in recovery_content:
                errors.append(f"Migration recovery is missing required marker: {marker}")

    sidecar_source = ROOT / "backend" / "new_eden_foundry_backend" / "sidecar.py"
    if sidecar_source.is_file():
        sidecar_content = sidecar_source.read_text(encoding="utf-8")
        for marker in (
            'LOOPBACK_HOST: Final = "127.0.0.1"',
            "secrets.compare_digest",
            'listener.bind((LOOPBACK_HOST, 0))',
            'app.put("/settings/update")',
            'app.put("/settings/appearance")',
            'app.get("/characters")',
            'app.patch("/characters/{character_id}")',
            'app.delete("/characters/{character_id}")',
            'app.get("/account-groups")',
            "delete_character_completely",
            '"publicDistribution": False',
            "verify_bundled_test_manifest",
        ):
            if marker not in sidecar_content:
                errors.append(f"Sidecar security is missing required marker: {marker}")

    updater_source = ROOT / "backend" / "new_eden_foundry_backend" / "updater.py"
    if updater_source.is_file():
        updater_content = updater_source.read_text(encoding="utf-8")
        for marker in (
            "Ed25519PublicKey",
            'hostname != "updates.invalid"',
            "TEST_MANIFEST_MAX_BYTES",
            "object_pairs_hook=_object_without_duplicates",
        ):
            if marker not in updater_content:
                errors.append(f"Updater skeleton is missing required marker: {marker}")
        if "PRIVATE_KEY" in updater_content:
            errors.append("Updater skeleton must not contain a private signing key.")

    sso_source = ROOT / "backend" / "new_eden_foundry_backend" / "sso_registration.py"
    if sso_source.is_file():
        sso_content = sso_source.read_text(encoding="utf-8")
        for marker in (
            'SSO_REDIRECT_URI: Final = "http://127.0.0.1:17891/oauth/callback"',
            "EXPECTED_SCOPE_PACKAGES",
            "registered",
            "Savox76",
        ):
            if marker not in sso_content:
                errors.append(f"SSO registration profile is missing marker: {marker}")
        if "client_secret" in sso_content.lower():
            errors.append("The SSO registration module must not contain a client secret.")

    sso_profile = (
        ROOT
        / "backend"
        / "new_eden_foundry_backend"
        / "resources"
        / "eve-sso-registration.json"
    )
    if sso_profile.is_file():
        profile = json.loads(sso_profile.read_text(encoding="utf-8"))
        if profile.get("clientId") != "a8409de72d5b4cab9b0424819d0abdec":
            errors.append("The bundled public EVE SSO client ID has drifted.")

    sso_pkce_source = ROOT / "backend" / "new_eden_foundry_backend" / "sso_pkce.py"
    if sso_pkce_source.is_file():
        pkce_content = sso_pkce_source.read_text(encoding="utf-8")
        for marker in (
            'SSO_AUTHORIZATION_ENDPOINT: Final = "https://login.eveonline.com/v2/oauth/authorize"',
            "secrets.token_bytes(32)",
            "code_challenge_method",
            "secrets.compare_digest",
            '"timed-out"',
            "server.shutdown()",
        ):
            if marker not in pkce_content:
                errors.append(f"SSO PKCE implementation is missing marker: {marker}")
        if "client_secret" in pkce_content.lower():
            errors.append("The SSO PKCE implementation must not contain a client secret field.")

    sso_token_source = ROOT / "backend" / "new_eden_foundry_backend" / "sso_tokens.py"
    if sso_token_source.is_file():
        token_content = sso_token_source.read_text(encoding="utf-8")
        for marker in (
            "SSO_METADATA_ENDPOINT",
            "RS256",
            "EXPECTED_EVE_AUDIENCE",
            "jwt-signature-invalid",
            "CHARACTER:EVE:",
            "_RejectRedirects",
        ):
            if marker not in token_content:
                errors.append(f"SSO token validation is missing required marker: {marker}")
        if "client_secret" in token_content.lower():
            errors.append("The SSO token implementation must not contain a client secret field.")

    sidecar_build = ROOT / "scripts" / "build_sidecar.py"
    if sidecar_build.is_file() and "SSO_REGISTRATION_PROFILE" not in sidecar_build.read_text(
        encoding="utf-8"
    ):
        errors.append("The frozen sidecar must include the SSO registration profile.")

    sidecar_smoke = ROOT / "scripts" / "smoke_sidecar.py"
    if sidecar_smoke.is_file():
        smoke_content = sidecar_smoke.read_text(encoding="utf-8")
        for marker in (
            "registered",
            "a8409de72d5b4cab9b0424819d0abdec",
            "PKCE start/cancel",
        ):
            if marker not in smoke_content:
                errors.append(
                    f"The frozen sidecar smoke test is missing SSO marker: {marker}"
                )

    runtime_requirements = ROOT / "backend" / "requirements-runtime.txt"
    if runtime_requirements.is_file() and "cryptography==50.0.1" not in runtime_requirements.read_text(
        encoding="utf-8"
    ):
        errors.append("Runtime requirements must pin the cryptographic validation dependency.")

    tauri_source = ROOT / "src-tauri" / "src" / "lib.rs"
    if tauri_source.is_file():
        tauri_content = tauri_source.read_text(encoding="utf-8")
        for marker in (
            "tauri_plugin_single_instance::init",
            "std::env::current_exe",
            "foundry-sidecar.exe",
            "sessionToken",
            "set_update_channel",
            "set_font_scale",
            "list_eve_characters",
            "list_account_groups",
            "update_eve_character",
            "delete_eve_character",
            "create_account_group",
            "rename_account_group",
            "delete_account_group",
            "start_eve_sso",
            "eve_sso_status",
            "cancel_eve_sso",
            "EVE_SSO_AUTHORIZATION_ENDPOINT",
            "SIDECAR_REQUEST_TIMEOUT",
        ):
            if marker not in tauri_content:
                errors.append(f"Tauri runtime is missing required marker: {marker}")

    portable_script = ROOT / "scripts" / "package_portable.ps1"
    if portable_script.is_file() and "foundry-sidecar.exe" not in portable_script.read_text(encoding="utf-8"):
        errors.append("The portable package must contain foundry-sidecar.exe.")

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
