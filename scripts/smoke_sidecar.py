#!/usr/bin/env python3
"""Exercise a frozen sidecar exactly as the Tauri parent process does."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import queue
import secrets
import sqlite3
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import TextIO


SYNTHETIC_MIGRATION_MARKER = "portable-smoke-preserved"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    return parser


def read_line_with_timeout(stream: TextIO, timeout: float) -> str:
    result: queue.Queue[str] = queue.Queue(maxsize=1)
    reader = threading.Thread(target=lambda: result.put(stream.readline()), daemon=True)
    reader.start()
    try:
        line = result.get(timeout=timeout)
    except queue.Empty as error:
        raise RuntimeError("Sidecar readiness timed out.") from error
    if not line:
        raise RuntimeError("Sidecar exited before reporting readiness.")
    return line


def wait_for_health(
    opener: urllib.request.OpenerDirector,
    url: str,
    token: str,
) -> dict[str, object]:
    deadline = time.monotonic() + 12
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
    )
    while time.monotonic() < deadline:
        try:
            with opener.open(request, timeout=1) as response:
                return json.loads(response.read())
        except (OSError, urllib.error.URLError):
            time.sleep(0.05)
    raise RuntimeError("Sidecar health did not become available.")


def expect_unauthorized(
    opener: urllib.request.OpenerDirector,
    url: str,
    authorization: str | None,
) -> None:
    headers = {} if authorization is None else {"Authorization": authorization}
    request = urllib.request.Request(url, headers=headers)
    try:
        opener.open(request, timeout=3)
    except urllib.error.HTTPError as error:
        if error.code == 401:
            return
        raise RuntimeError(f"Expected HTTP 401, received {error.code}.") from error
    raise RuntimeError("An unauthenticated sidecar request was accepted.")


def seed_previous_release_database(program_directory: Path) -> Path:
    data_directory = program_directory / "data"
    data_directory.mkdir()
    database_path = data_directory / "foundry.sqlite3"
    with contextlib.closing(sqlite3.connect(database_path)) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
            );
            CREATE TABLE app_metadata (
                key TEXT PRIMARY KEY NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
            );
            CREATE TABLE account_groups (
                id INTEGER PRIMARY KEY,
                label TEXT NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE characters (
                character_id INTEGER PRIMARY KEY,
                account_group_id INTEGER REFERENCES account_groups(id) ON DELETE SET NULL,
                name TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                connected_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE character_scopes (
                character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
                scope TEXT NOT NULL,
                PRIMARY KEY (character_id, scope)
            );
            CREATE TABLE sync_runs (
                id INTEGER PRIMARY KEY,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                data_timestamp TEXT,
                error_code TEXT,
                character_id INTEGER REFERENCES characters(character_id) ON DELETE CASCADE
            );
            CREATE TABLE cached_snapshots (
                id INTEGER PRIMARY KEY,
                sync_run_id INTEGER NOT NULL REFERENCES sync_runs(id) ON DELETE CASCADE,
                resource TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                expires_at TEXT,
                UNIQUE (sync_run_id, resource)
            );
            CREATE TABLE migration_backups (
                id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL UNIQUE,
                source_schema_version INTEGER NOT NULL,
                target_schema_version INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE app_settings (
                key TEXT PRIMARY KEY NOT NULL CHECK (
                    length(trim(key)) BETWEEN 1 AND 80
                ),
                value TEXT NOT NULL CHECK (length(value) <= 2000),
                updated_at TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
            );
            INSERT INTO app_settings (key, value)
                VALUES ('update_channel', 'stable');
            INSERT INTO schema_migrations (version, name)
                VALUES (1, 'initial_local_core');
            INSERT INTO schema_migrations (version, name)
                VALUES (2, 'multi_character_identity');
            INSERT INTO schema_migrations (version, name)
                VALUES (3, 'migration_backup_history');
            INSERT INTO schema_migrations (version, name)
                VALUES (4, 'cache_freshness_metadata');
            INSERT INTO schema_migrations (version, name)
                VALUES (5, 'local_update_preferences');
            INSERT INTO app_metadata (key, value)
                VALUES ('smoke-marker', 'portable-smoke-preserved');
            INSERT INTO sync_runs (source, status, started_at)
                VALUES ('frozen-interrupted-recovery-smoke', 'running',
                        '2026-09-12T12:00:00Z');
            PRAGMA user_version = 5;
            """
        )
        connection.commit()
    return database_path


def main() -> int:
    arguments = build_parser().parse_args()
    executable = arguments.executable.resolve(strict=True)
    token = secrets.token_hex(32)

    with tempfile.TemporaryDirectory(prefix="new-eden-foundry-sidecar-") as temporary_directory:
        program_directory = Path(temporary_directory).resolve()
        database_path = seed_previous_release_database(program_directory)
        process = subprocess.Popen(
            [str(executable)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None
        try:
            process.stdin.write(
                json.dumps(
                    {
                        "protocol": 1,
                        "sessionToken": token,
                        "programDirectory": str(program_directory),
                    }
                )
                + "\n"
            )
            process.stdin.flush()
            ready_line = read_line_with_timeout(process.stdout, 20)
            ready = json.loads(ready_line)
            if ready.get("event") != "ready" or ready.get("host") != "127.0.0.1":
                raise RuntimeError(f"Unexpected readiness payload: {ready!r}")
            if ready.get("appearance") != {"fontScale": "normal"}:
                raise RuntimeError("The packaged default font scale is invalid.")
            if ready.get("esiClient", {}).get("compatibilityDate") != "2026-09-09":
                raise RuntimeError("The packaged ESI compatibility date is invalid.")
            if ready.get("esiClient", {}).get("state") != "ready":
                raise RuntimeError("The packaged ESI circuit must start ready.")
            if token in ready_line:
                raise RuntimeError("The readiness payload exposed the session token.")

            health_url = f"http://127.0.0.1:{int(ready['port'])}/health"
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            health = wait_for_health(opener, health_url, token)
            expect_unauthorized(opener, health_url, None)
            expect_unauthorized(opener, health_url, "Bearer incorrect")

            database = health.get("database")
            if not isinstance(database, dict) or database.get("location") != "data/foundry.sqlite3":
                raise RuntimeError("The sidecar reported an unexpected database location.")
            if database.get("schemaVersion") != 9 or database.get("integrity") != "ok":
                raise RuntimeError("The sidecar database health is invalid.")
            if health.get("esiClient", {}).get("compatibilityDate") != "2026-09-09":
                raise RuntimeError("The health response omitted the ESI compatibility date.")
            data_state = health.get("data")
            if not isinstance(data_state, dict) or data_state.get("state") != "empty":
                raise RuntimeError("The sidecar did not report the empty cache-first state.")
            updater = health.get("updater")
            if (
                not isinstance(updater, dict)
                or updater.get("channel") != "stable"
                or updater.get("manifestState") != "verified"
                or updater.get("publicDistribution") is not False
            ):
                raise RuntimeError("The signed updater skeleton is not ready or safely disabled.")
            sso_registration = health.get("ssoRegistration")
            if (
                not isinstance(sso_registration, dict)
                or sso_registration.get("state") != "registered"
                or sso_registration.get("clientId")
                != "a8409de72d5b4cab9b0424819d0abdec"
                or sso_registration.get("redirectUri")
                != "http://127.0.0.1:17891/oauth/callback"
            ):
                raise RuntimeError("The packaged SSO registration profile is invalid.")
            if health.get("appearance") != {"fontScale": "normal"}:
                raise RuntimeError("The packaged appearance health is invalid.")
            if health.get("characters") != {"connected": 0}:
                raise RuntimeError("The packaged character health is invalid.")

            characters_request = urllib.request.Request(
                f"http://127.0.0.1:{int(ready['port'])}/characters",
                headers={"Authorization": f"Bearer {token}"},
            )
            with opener.open(characters_request, timeout=3) as response:
                characters = json.loads(response.read())
            if characters != {"characters": []}:
                raise RuntimeError("The packaged character roster is invalid.")

            industry_job_query = urllib.request.Request(
                f"http://127.0.0.1:{int(ready['port'])}/industry-jobs/query",
                data=json.dumps({
                    "search": "", "ownerCharacterId": None, "status": None,
                    "activityId": None, "correlation": None, "offset": 0,
                    "limit": 100, "sortBy": "end", "sortDirection": "desc",
                }).encode("utf-8"),
                method="POST",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(industry_job_query, timeout=3) as response:
                industry_job_page = json.loads(response.read())
            if (
                industry_job_page.get("items") != []
                or industry_job_page.get("total") != 0
                or industry_job_page.get("activeTotal") != 0
            ):
                raise RuntimeError("The packaged industry-job query is invalid.")

            industry_job_sync = urllib.request.Request(
                f"http://127.0.0.1:{int(ready['port'])}/industry-jobs/sync",
                data=b"{}",
                method="POST",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(industry_job_sync, timeout=3) as response:
                industry_job_result = json.loads(response.read())
            if industry_job_result != {
                "characters": [], "completed": 0, "failed": 0, "jobs": 0,
                "active": 0, "completedJobs": 0,
            }:
                raise RuntimeError("The packaged industry-job sync is invalid.")

            production_catalog_request = urllib.request.Request(
                f"http://127.0.0.1:{int(ready['port'])}/production-plans/catalog",
                data=json.dumps({
                    "search": "", "activity": None, "offset": 0, "limit": 50,
                }).encode("utf-8"),
                method="POST",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(production_catalog_request, timeout=3) as response:
                production_catalog = json.loads(response.read())
            if (
                len(production_catalog.get("items", [])) != 50
                or production_catalog.get("total", 0) < 4_000
                or production_catalog.get("buildNumber") != "3503375"
            ):
                raise RuntimeError("The packaged production catalog is invalid.")

            production_plan_request = urllib.request.Request(
                f"http://127.0.0.1:{int(ready['port'])}/production-plans/query",
                data=json.dumps({
                    "search": "", "ownerCharacterId": None, "activity": None,
                    "state": None, "offset": 0, "limit": 50,
                    "sortBy": "priority", "sortDirection": "desc",
                }).encode("utf-8"),
                method="POST",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(production_plan_request, timeout=3) as response:
                production_plans = json.loads(response.read())
            if (
                production_plans.get("items") != []
                or production_plans.get("total") != 0
                or production_plans.get("inventoryApplied") is not False
                or production_plans.get("modifiersApplied") is not False
            ):
                raise RuntimeError("The packaged production-plan query is invalid.")

            sso_login_url = f"http://127.0.0.1:{int(ready['port'])}/sso/login"
            sso_status_request = urllib.request.Request(
                sso_login_url,
                headers={"Authorization": f"Bearer {token}"},
            )
            with opener.open(sso_status_request, timeout=3) as response:
                sso_status = json.loads(response.read())
            if sso_status.get("state") != "idle":
                raise RuntimeError("The packaged PKCE login did not start idle.")
            if sso_status.get("character") is not None:
                raise RuntimeError("The idle PKCE login exposed a character.")

            sso_start_request = urllib.request.Request(
                sso_login_url,
                data=json.dumps({
                    "scopePackages": [
                        "industry-core",
                        "market",
                        "planetary-industry",
                        "projects",
                        "private-structures",
                    ]
                }).encode("utf-8"),
                method="POST",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(sso_start_request, timeout=3) as response:
                sso_start = json.loads(response.read())
            if (
                sso_start.get("status", {}).get("state") != "waiting"
                or not str(sso_start.get("authorizationUrl", "")).startswith(
                    "https://login.eveonline.com/v2/oauth/authorize?"
                )
                or "codeVerifier" in json.dumps(sso_start)
                or sso_start.get("status", {}).get("character") is not None
            ):
                raise RuntimeError("The packaged PKCE login response is invalid.")

            sso_cancel_request = urllib.request.Request(
                sso_login_url,
                method="DELETE",
                headers={"Authorization": f"Bearer {token}"},
            )
            with opener.open(sso_cancel_request, timeout=3) as response:
                sso_cancelled = json.loads(response.read())
            if sso_cancelled.get("state") != "cancelled":
                raise RuntimeError("The packaged PKCE login could not be cancelled.")
            backup_name = database.get("lastMigrationBackup")
            if not isinstance(backup_name, str) or not backup_name.startswith(
                "foundry-schema-v0005-to-v0009-"
            ):
                raise RuntimeError("The packaged migration did not report its backup.")

            update_request = urllib.request.Request(
                f"http://127.0.0.1:{int(ready['port'])}/settings/update",
                data=json.dumps({"channel": "preview"}).encode("utf-8"),
                method="PUT",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(update_request, timeout=3) as response:
                update_settings = json.loads(response.read())
            if (
                update_settings.get("channel") != "preview"
                or update_settings.get("manifestState") != "verified"
                or update_settings.get("publicDistribution") is not False
            ):
                raise RuntimeError("The packaged update-channel preference is invalid.")

            appearance_request = urllib.request.Request(
                f"http://127.0.0.1:{int(ready['port'])}/settings/appearance",
                data=json.dumps({"fontScale": "very-large"}).encode("utf-8"),
                method="PUT",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(appearance_request, timeout=3) as response:
                appearance = json.loads(response.read())
            if appearance != {"fontScale": "very-large"}:
                raise RuntimeError("The packaged font-scale preference is invalid.")

            if not database_path.is_file():
                raise RuntimeError("The database was not created inside the program directory.")
            with contextlib.closing(sqlite3.connect(database_path)) as connection:
                if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise RuntimeError("The created SQLite database failed quick_check.")
                if connection.execute("PRAGMA user_version").fetchone()[0] != 9:
                    raise RuntimeError("The packaged sidecar did not migrate to schema 9.")
                marker = connection.execute(
                    "SELECT value FROM app_metadata WHERE key = 'smoke-marker'"
                ).fetchone()[0]
                update_channel = connection.execute(
                    "SELECT value FROM app_settings WHERE key = 'update_channel'"
                ).fetchone()[0]
                font_scale = connection.execute(
                    "SELECT value FROM app_settings WHERE key = 'font_scale'"
                ).fetchone()[0]
                character_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(characters)")
                }
                backup_record = connection.execute(
                    "SELECT filename, sha256 FROM migration_backups"
                ).fetchone()
                recovered_run = connection.execute(
                    "SELECT status, completed_at, error_code FROM sync_runs "
                    "WHERE source='frozen-interrupted-recovery-smoke'"
                ).fetchone()
            if (
                marker != SYNTHETIC_MIGRATION_MARKER
                or update_channel != "preview"
                or font_scale != "very-large"
                or "alias" not in character_columns
                or backup_record[0] != backup_name
                or recovered_run[0] != "cancelled"
                or recovered_run[1] is None
                or recovered_run[2] != "sidecar-interrupted"
            ):
                raise RuntimeError(
                    "The packaged migration or interrupted-sync recovery is invalid."
                )

            backup_path = program_directory / "data" / "backups" / backup_name
            if not backup_path.is_file():
                raise RuntimeError("The packaged migration backup was not created.")
            checksum = hashlib.sha256(backup_path.read_bytes()).hexdigest()
            if checksum != backup_record[1]:
                raise RuntimeError("The packaged migration backup checksum is invalid.")
            with contextlib.closing(sqlite3.connect(backup_path)) as backup_connection:
                if backup_connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise RuntimeError("The packaged migration backup failed quick_check.")
                if backup_connection.execute("PRAGMA user_version").fetchone()[0] != 5:
                    raise RuntimeError("The packaged backup does not contain schema 5.")
                backup_marker = backup_connection.execute(
                    "SELECT value FROM app_metadata WHERE key = 'smoke-marker'"
                ).fetchone()[0]
            if backup_marker != SYNTHETIC_MIGRATION_MARKER:
                raise RuntimeError("The packaged backup did not preserve source data.")

            process.stdin.write('{"command":"shutdown"}\n')
            process.stdin.flush()
            exit_code = process.wait(timeout=30)
            remaining_output = process.stdout.read()
            error_output = process.stderr.read()
            if exit_code != 0:
                raise RuntimeError(f"The sidecar exited with code {exit_code}: {error_output}")
            if token in remaining_output or token in error_output:
                raise RuntimeError("Sidecar output exposed the session token.")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()

    print(
        "Frozen sidecar handshake, signed updater skeleton, PKCE start/cancel, character "
        "roster, industry-job and production endpoints, ESI policy, font scale, migration backup, database "
        "location, interrupted-sync recovery and shutdown verified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
