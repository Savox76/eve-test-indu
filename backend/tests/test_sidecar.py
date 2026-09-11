from __future__ import annotations

import contextlib
import json
import queue
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from new_eden_foundry_backend.sidecar import (
    PROTOCOL_VERSION,
    StartupProtocolError,
    delete_character_completely,
    is_authorized,
    managed_character_payload,
    parse_startup_configuration,
    store_verified_authorization,
    store_verified_character,
)
from new_eden_foundry_backend.sso_registration import load_bundled_sso_registration_profile
from new_eden_foundry_backend.sso_tokens import VerifiedAuthorization, VerifiedCharacter
from new_eden_foundry_backend.token_vault import (
    MemoryCredentialStore,
    RefreshTokenVault,
    TokenVaultError,
)


SYNTHETIC_SESSION_TOKEN = "a" * 64


class SidecarProtocolTests(unittest.TestCase):
    def test_startup_configuration_requires_absolute_program_directory(self) -> None:
        with self.assertRaisesRegex(StartupProtocolError, "absolute"):
            parse_startup_configuration(
                json.dumps(
                    {
                        "protocol": PROTOCOL_VERSION,
                        "sessionToken": SYNTHETIC_SESSION_TOKEN,
                        "programDirectory": "relative/program",
                    }
                )
            )

    def test_startup_configuration_rejects_unknown_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(StartupProtocolError, "unexpected fields"):
                parse_startup_configuration(
                    json.dumps(
                        {
                            "protocol": PROTOCOL_VERSION,
                            "sessionToken": SYNTHETIC_SESSION_TOKEN,
                            "programDirectory": str(Path(temporary_directory).resolve()),
                            "extra": "not-accepted",
                        }
                    )
                )

    def test_authorization_uses_the_exact_bearer_token(self) -> None:
        self.assertTrue(is_authorized(f"Bearer {SYNTHETIC_SESSION_TOKEN}", SYNTHETIC_SESSION_TOKEN))
        self.assertFalse(is_authorized(None, SYNTHETIC_SESSION_TOKEN))
        self.assertFalse(is_authorized("Bearer wrong", SYNTHETIC_SESSION_TOKEN))
        self.assertFalse(is_authorized(SYNTHETIC_SESSION_TOKEN, SYNTHETIC_SESSION_TOKEN))

    def test_verified_character_is_persisted_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "foundry.sqlite3"
            from new_eden_foundry_backend.database import initialize_database

            initialize_database(database_path)
            identity = VerifiedCharacter(
                2_112_345_678,
                "Synthetic Pilot",
                ("esi-assets.read_assets.v1",),
            )
            store_verified_character(database_path, identity)
            store_verified_character(database_path, identity)

            with contextlib.closing(sqlite3.connect(database_path)) as connection:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM characters").fetchone()[0],
                    1,
                )

    def test_verified_authorization_commits_identity_and_refresh_token(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "foundry.sqlite3"
            from new_eden_foundry_backend.database import initialize_database

            initialize_database(database_path)
            vault = RefreshTokenVault(MemoryCredentialStore())
            authorization = VerifiedAuthorization(
                character=VerifiedCharacter(
                    2_112_345_679,
                    "Stored Pilot",
                    ("esi-assets.read_assets.v1",),
                ),
                access_token="synthetic-access-token",
                refresh_token="synthetic-refresh-token",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
            )

            store_verified_authorization(database_path, vault, authorization)

            self.assertEqual(
                vault.read(authorization.character.character_id),
                "synthetic-refresh-token",
            )
            with contextlib.closing(sqlite3.connect(database_path)) as connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT name FROM characters WHERE character_id = ?",
                        (authorization.character.character_id,),
                    ).fetchone()[0],
                    "Stored Pilot",
                )

    def test_identity_failure_discards_the_staged_refresh_token(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "uninitialized.sqlite3"
            store = MemoryCredentialStore()
            vault = RefreshTokenVault(store)
            authorization = VerifiedAuthorization(
                character=VerifiedCharacter(
                    2_112_345_680,
                    "Rejected Pilot",
                    ("esi-assets.read_assets.v1",),
                ),
                access_token="synthetic-access-token",
                refresh_token="synthetic-refresh-token",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
            )

            with self.assertRaises(sqlite3.OperationalError):
                store_verified_authorization(database_path, vault, authorization)

            self.assertFalse(store.values)


    def test_managed_character_payload_reports_scope_and_credential_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "foundry.sqlite3"
            from new_eden_foundry_backend.database import (
                connect_database,
                initialize_database,
            )
            from new_eden_foundry_backend.identity import (
                list_characters,
                upsert_character,
            )

            initialize_database(database_path)
            with contextlib.closing(connect_database(database_path)) as connection:
                upsert_character(
                    connection,
                    character_id=2_112_345_681,
                    name="Scope Pilot",
                    account_group_id=None,
                    scopes=("esi-assets.read_assets.v1",),
                )
                character = list_characters(connection)[0]
            vault = RefreshTokenVault(MemoryCredentialStore())
            profile = load_bundled_sso_registration_profile()

            missing = managed_character_payload(character, profile, vault)
            self.assertEqual(missing["credentialState"], "missing")
            self.assertEqual(
                missing["scopePackages"][0],
                {
                    "id": "industry-core",
                    "status": "partial",
                    "grantedCount": 1,
                    "requiredCount": 4,
                },
            )
            self.assertTrue(
                all(
                    package["status"] == "missing"
                    for package in missing["scopePackages"][1:]
                )
            )

            vault.replace(2_112_345_681, "synthetic-refresh-token")
            stored = managed_character_payload(character, profile, vault)
            self.assertEqual(stored["credentialState"], "stored")

    def test_complete_character_delete_removes_credential_and_database_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "foundry.sqlite3"
            from new_eden_foundry_backend.database import (
                connect_database,
                initialize_database,
            )
            from new_eden_foundry_backend.identity import upsert_character

            initialize_database(database_path)
            character_id = 2_112_345_682
            with contextlib.closing(connect_database(database_path)) as connection:
                upsert_character(
                    connection,
                    character_id=character_id,
                    name="Delete Pilot",
                    account_group_id=None,
                    scopes=("esi-assets.read_assets.v1",),
                )
                sync = connection.execute(
                    """
                    INSERT INTO sync_runs (
                        source, status, started_at, completed_at, character_id
                    ) VALUES (?, 'completed', ?, ?, ?)
                    """,
                    (
                        "synthetic-delete-test",
                        "2026-09-09T12:00:00Z",
                        "2026-09-09T12:01:00Z",
                        character_id,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO cached_snapshots (
                        sync_run_id, resource, payload_json, observed_at
                    ) VALUES (?, 'assets', '{}', ?)
                    """,
                    (sync.lastrowid, "2026-09-09T12:01:00Z"),
                )
                facility_sync = connection.execute(
                    """
                    INSERT INTO sync_runs (
                        source, status, started_at, completed_at
                    ) VALUES ('industry_facilities', 'completed', ?, ?)
                    """,
                    ("2026-09-09T12:00:00Z", "2026-09-09T12:01:00Z"),
                )
                connection.execute(
                    """
                    INSERT INTO cached_snapshots (
                        sync_run_id, resource, payload_json, observed_at
                    ) VALUES (?, 'industry_facilities', '{}', ?)
                    """,
                    (facility_sync.lastrowid, "2026-09-09T12:01:00Z"),
                )
                connection.commit()
            vault = RefreshTokenVault(MemoryCredentialStore())
            vault.replace(character_id, "synthetic-refresh-token")

            self.assertTrue(
                delete_character_completely(database_path, vault, character_id)
            )
            self.assertIsNone(vault.read(character_id))
            with contextlib.closing(sqlite3.connect(database_path)) as connection:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM characters").fetchone()[0],
                    0,
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM sync_runs").fetchone()[0],
                    0,
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM cached_snapshots").fetchone()[0],
                    0,
                )

    def test_credential_delete_failure_rolls_back_database_delete(self) -> None:
        class DeleteFailingStore(MemoryCredentialStore):
            def delete(self, target: str) -> None:
                del target
                raise TokenVaultError("credential-delete-failed")

        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "foundry.sqlite3"
            from new_eden_foundry_backend.database import (
                connect_database,
                initialize_database,
            )
            from new_eden_foundry_backend.identity import upsert_character

            initialize_database(database_path)
            character_id = 2_112_345_683
            with contextlib.closing(connect_database(database_path)) as connection:
                upsert_character(
                    connection,
                    character_id=character_id,
                    name="Rollback Pilot",
                    account_group_id=None,
                    scopes=("esi-assets.read_assets.v1",),
                )
            vault = RefreshTokenVault(DeleteFailingStore())

            with self.assertRaisesRegex(TokenVaultError, "credential-delete-failed"):
                delete_character_completely(database_path, vault, character_id)

            with contextlib.closing(sqlite3.connect(database_path)) as connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM characters WHERE character_id = ?",
                        (character_id,),
                    ).fetchone()[0],
                    1,
                )


class SidecarIntegrationTests(unittest.TestCase):
    def test_loopback_health_requires_token_and_shutdown_is_clean(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            program_directory = Path(temporary_directory).resolve()
            process = subprocess.Popen(
                [sys.executable, "-m", "new_eden_foundry_backend.sidecar"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
            self.addCleanup(self._close_process_streams, process)
            self.addCleanup(self._stop_process, process)
            assert process.stdin is not None
            assert process.stdout is not None
            assert process.stderr is not None

            process.stdin.write(
                json.dumps(
                    {
                        "protocol": PROTOCOL_VERSION,
                        "sessionToken": SYNTHETIC_SESSION_TOKEN,
                        "programDirectory": str(program_directory),
                    }
                )
                + "\n"
            )
            process.stdin.flush()

            ready_line = self._read_line_with_timeout(process.stdout, timeout=12)
            ready = json.loads(ready_line)
            self.assertEqual(ready["event"], "ready")
            self.assertEqual(ready["host"], "127.0.0.1")
            self.assertGreater(ready["port"], 0)
            self.assertEqual(ready["database"]["location"], "data/foundry.sqlite3")
            self.assertEqual(ready["data"]["state"], "empty")
            self.assertEqual(ready["updater"]["channel"], "stable")
            self.assertEqual(ready["updater"]["manifestState"], "verified")
            self.assertFalse(ready["updater"]["publicDistribution"])
            self.assertEqual(ready["appearance"], {"fontScale": "normal"})
            self.assertEqual(ready["esiClient"]["state"], "ready")
            self.assertEqual(
                ready["esiClient"]["compatibilityDate"],
                "2026-09-09",
            )
            expected_backend = (
                "windows-credential-manager" if sys.platform == "win32" else "unavailable"
            )
            self.assertEqual(ready["credentials"]["backend"], expected_backend)
            self.assertEqual(
                ready["credentials"]["state"],
                "available" if sys.platform == "win32" else "unavailable",
            )
            self.assertEqual(ready["ssoRegistration"]["state"], "registered")
            self.assertEqual(
                ready["ssoRegistration"]["clientId"],
                "a8409de72d5b4cab9b0424819d0abdec",
            )
            self.assertEqual(
                ready["ssoRegistration"]["redirectUri"],
                "http://127.0.0.1:17891/oauth/callback",
            )
            self.assertNotIn(SYNTHETIC_SESSION_TOKEN, ready_line)

            base_url = f"http://127.0.0.1:{ready['port']}"
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            self._wait_until_serving(opener, base_url)

            with self.assertRaises(urllib.error.HTTPError) as missing_auth:
                opener.open(f"{base_url}/health", timeout=3)
            self.assertEqual(missing_auth.exception.code, 401)

            wrong_request = urllib.request.Request(
                f"{base_url}/health",
                headers={"Authorization": "Bearer wrong"},
            )
            with self.assertRaises(urllib.error.HTTPError) as wrong_auth:
                opener.open(wrong_request, timeout=3)
            self.assertEqual(wrong_auth.exception.code, 401)

            valid_request = urllib.request.Request(
                f"{base_url}/health",
                headers={"Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}"},
            )
            with opener.open(valid_request, timeout=3) as response:
                health = json.loads(response.read())
            self.assertEqual(health["state"], "ready")
            self.assertEqual(health["database"]["schemaVersion"], 8)
            self.assertEqual(health["database"]["location"], "data/foundry.sqlite3")
            self.assertIsNone(health["database"]["lastMigrationBackup"])
            self.assertEqual(health["data"]["state"], "empty")
            self.assertFalse(health["data"]["hasCachedData"])
            self.assertEqual(health["data"]["lastSyncStatus"], "never")
            self.assertIsNone(health["data"]["ageSeconds"])
            self.assertEqual(health["updater"]["channel"], "stable")
            self.assertEqual(health["updater"]["manifestState"], "verified")
            self.assertFalse(health["updater"]["publicDistribution"])
            self.assertEqual(health["appearance"], {"fontScale": "normal"})
            self.assertEqual(health["characters"], {"connected": 0})
            self.assertEqual(health["esiClient"]["state"], "ready")
            self.assertEqual(health["esiClient"]["compatibilityDate"], "2026-09-09")
            self.assertEqual(health["esiClient"]["cachedResources"], 0)
            self.assertEqual(health["credentials"], ready["credentials"])
            self.assertEqual(health["ssoRegistration"]["state"], "registered")

            sso_login_url = f"{base_url}/sso/login"
            sso_status_request = urllib.request.Request(
                sso_login_url,
                headers={"Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}"},
            )
            with opener.open(sso_status_request, timeout=3) as response:
                sso_status = json.loads(response.read())
            self.assertEqual(sso_status["state"], "idle")
            self.assertIsNone(sso_status["character"])

            characters_request = urllib.request.Request(
                f"{base_url}/characters",
                headers={"Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}"},
            )
            with opener.open(characters_request, timeout=3) as response:
                characters = json.loads(response.read())
            self.assertEqual(characters, {"characters": []})

            asset_query_request = urllib.request.Request(
                f"{base_url}/assets/query",
                data=json.dumps(
                    {
                        "search": "",
                        "ownerCharacterId": None,
                        "locationStatus": None,
                        "offset": 0,
                        "limit": 100,
                        "sortBy": "type",
                        "sortDirection": "asc",
                    }
                ).encode(),
                method="POST",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(asset_query_request, timeout=3) as response:
                asset_page = json.loads(response.read())
            self.assertEqual(asset_page["items"], [])
            self.assertEqual(asset_page["total"], 0)
            self.assertEqual(asset_page["limit"], 100)

            asset_sync_request = urllib.request.Request(
                f"{base_url}/assets/sync",
                data=b"{}",
                method="POST",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(asset_sync_request, timeout=3) as response:
                asset_sync = json.loads(response.read())
            self.assertEqual(
                asset_sync,
                {"characters": [], "completed": 0, "failed": 0, "assets": 0},
            )

            delta_query_request = urllib.request.Request(
                f"{base_url}/assets/deltas/query",
                data=json.dumps(
                    {
                        "search": "",
                        "ownerCharacterId": None,
                        "changeType": None,
                        "offset": 0,
                        "limit": 50,
                    }
                ).encode(),
                method="POST",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(delta_query_request, timeout=3) as response:
                delta_page = json.loads(response.read())
            self.assertEqual(delta_page["items"], [])
            self.assertEqual(delta_page["total"], 0)
            self.assertEqual(delta_page["limit"], 50)
            self.assertFalse(delta_page["hasBaseline"])

            blueprint_query_request = urllib.request.Request(
                f"{base_url}/blueprints/query",
                data=json.dumps({
                    "search": "", "ownerCharacterId": None, "kind": None,
                    "offset": 0, "limit": 100, "sortBy": "type", "sortDirection": "asc",
                }).encode(),
                method="POST",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(blueprint_query_request, timeout=3) as response:
                blueprint_page = json.loads(response.read())
            self.assertEqual(blueprint_page["items"], [])
            self.assertEqual(blueprint_page["total"], 0)
            self.assertEqual(blueprint_page["limit"], 100)

            blueprint_sync_request = urllib.request.Request(
                f"{base_url}/blueprints/sync", data=b"{}", method="POST",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(blueprint_sync_request, timeout=3) as response:
                blueprint_sync = json.loads(response.read())
            self.assertEqual(blueprint_sync, {"characters": [], "completed": 0, "failed": 0, "blueprints": 0})

            industry_job_query_request = urllib.request.Request(
                f"{base_url}/industry-jobs/query",
                data=json.dumps({
                    "search": "", "ownerCharacterId": None, "status": None,
                    "activityId": None, "correlation": None, "offset": 0,
                    "limit": 100, "sortBy": "end", "sortDirection": "desc",
                }).encode(),
                method="POST",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(industry_job_query_request, timeout=3) as response:
                industry_job_page = json.loads(response.read())
            self.assertEqual(industry_job_page["items"], [])
            self.assertEqual(industry_job_page["total"], 0)
            self.assertEqual(industry_job_page["activeTotal"], 0)
            self.assertEqual(industry_job_page["limit"], 100)

            industry_job_sync_request = urllib.request.Request(
                f"{base_url}/industry-jobs/sync", data=b"{}", method="POST",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(industry_job_sync_request, timeout=3) as response:
                industry_job_sync = json.loads(response.read())
            self.assertEqual(industry_job_sync, {
                "characters": [], "completed": 0, "failed": 0, "jobs": 0,
                "active": 0, "completedJobs": 0,
            })

            industry_facility_query_request = urllib.request.Request(
                f"{base_url}/industry-facilities/query",
                data=json.dumps({
                    "search": "", "kind": None, "access": None,
                    "activity": "manufacturing", "usedOnly": False,
                    "offset": 0, "limit": 100, "sortBy": "facility",
                    "sortDirection": "asc",
                }).encode(),
                method="POST",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(industry_facility_query_request, timeout=3) as response:
                industry_facility_page = json.loads(response.read())
            self.assertEqual(industry_facility_page["items"], [])
            self.assertEqual(industry_facility_page["total"], 0)
            self.assertEqual(industry_facility_page["activity"], "manufacturing")
            self.assertEqual(industry_facility_page["limit"], 100)

            industry_slot_query_request = urllib.request.Request(
                f"{base_url}/industry-slots/query",
                data=json.dumps({
                    "ownerCharacterId": None, "offset": 0, "limit": 100,
                }).encode(),
                method="POST",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(industry_slot_query_request, timeout=3) as response:
                industry_slot_page = json.loads(response.read())
            self.assertEqual(industry_slot_page["items"], [])
            self.assertEqual(industry_slot_page["total"], 0)
            self.assertEqual(industry_slot_page["limit"], 100)
            self.assertEqual(
                industry_slot_page["activities"],
                ["manufacturing", "reactions", "science"],
            )

            research_query_request = urllib.request.Request(
                f"{base_url}/research-plans/query",
                data=json.dumps({
                    "search": "", "ownerCharacterId": None, "state": None,
                    "plannedOnly": False, "offset": 0, "limit": 100,
                    "sortBy": "priority", "sortDirection": "desc",
                }).encode(),
                method="POST",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(research_query_request, timeout=3) as response:
                research_page = json.loads(response.read())
            self.assertEqual(research_page["items"], [])
            self.assertEqual(research_page["total"], 0)
            self.assertEqual(research_page["limit"], 100)
            self.assertFalse(research_page["estimatesAvailable"])

            character_skill_query_request = urllib.request.Request(
                f"{base_url}/skills/query",
                data=json.dumps({
                    "search": "", "ownerCharacterId": None, "trainedLevel": None,
                    "activeState": None, "offset": 0, "limit": 100,
                    "sortBy": "skill", "sortDirection": "asc",
                }).encode(),
                method="POST",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(character_skill_query_request, timeout=3) as response:
                character_skill_page = json.loads(response.read())
            self.assertEqual(character_skill_page["items"], [])
            self.assertEqual(character_skill_page["total"], 0)
            self.assertEqual(character_skill_page["totalSp"], 0)
            self.assertEqual(character_skill_page["levels"], [0, 1, 2, 3, 4, 5])

            character_skill_sync_request = urllib.request.Request(
                f"{base_url}/skills/sync", data=b"{}", method="POST",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(character_skill_sync_request, timeout=3) as response:
                character_skill_sync = json.loads(response.read())
            self.assertEqual(character_skill_sync, {
                "characters": [], "completed": 0, "failed": 0, "skills": 0,
                "totalSp": 0, "unallocatedSp": 0,
            })

            asset_export_request = urllib.request.Request(
                f"{base_url}/assets/export",
                data=json.dumps(
                    {
                        "search": "",
                        "ownerCharacterId": None,
                        "locationStatus": None,
                        "sortBy": "type",
                        "sortDirection": "asc",
                    }
                ).encode(),
                method="POST",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(asset_export_request, timeout=3) as response:
                asset_export = json.loads(response.read())
            self.assertEqual(asset_export["rows"], 0)
            self.assertTrue(asset_export["filename"].startswith("assets-"))
            self.assertEqual(
                asset_export["relativePath"],
                f"data/exports/{asset_export['filename']}",
            )
            self.assertTrue(
                (program_directory / asset_export["relativePath"]).is_file()
            )

            sso_start_request = urllib.request.Request(
                sso_login_url,
                data=json.dumps({"scopePackages": [
                    "industry-core", "market", "planetary-industry", "projects", "private-structures"
                ]}).encode(),
                method="POST",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(sso_start_request, timeout=3) as response:
                sso_start = json.loads(response.read())
            self.assertEqual(sso_start["status"]["state"], "waiting")
            self.assertTrue(sso_start["authorizationUrl"].startswith(
                "https://login.eveonline.com/v2/oauth/authorize?"
            ))
            self.assertNotIn("codeVerifier", json.dumps(sso_start))

            sso_cancel_request = urllib.request.Request(
                sso_login_url,
                method="DELETE",
                headers={"Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}"},
            )
            with opener.open(sso_cancel_request, timeout=3) as response:
                sso_cancelled = json.loads(response.read())
            self.assertEqual(sso_cancelled["state"], "cancelled")

            update_settings_url = f"{base_url}/settings/update"
            put_request = urllib.request.Request(
                update_settings_url,
                data=json.dumps({"channel": "beta"}).encode(),
                method="PUT",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(put_request, timeout=3) as response:
                update_settings = json.loads(response.read())
            self.assertEqual(update_settings["channel"], "beta")
            self.assertEqual(update_settings["manifestState"], "verified")
            self.assertFalse(update_settings["publicDistribution"])

            with opener.open(valid_request, timeout=3) as response:
                updated_health = json.loads(response.read())
            self.assertEqual(updated_health["updater"]["channel"], "beta")

            appearance_url = f"{base_url}/settings/appearance"
            appearance_request = urllib.request.Request(
                appearance_url,
                data=json.dumps({"fontScale": "very-large"}).encode(),
                method="PUT",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with opener.open(appearance_request, timeout=3) as response:
                appearance = json.loads(response.read())
            self.assertEqual(appearance, {"fontScale": "very-large"})

            invalid_request = urllib.request.Request(
                update_settings_url,
                data=json.dumps({"channel": "nightly"}).encode(),
                method="PUT",
                headers={
                    "Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            with self.assertRaises(urllib.error.HTTPError) as invalid_channel:
                opener.open(invalid_request, timeout=3)
            self.assertEqual(invalid_channel.exception.code, 422)

            database_path = program_directory / "data" / "foundry.sqlite3"
            self.assertTrue(database_path.is_file())
            with contextlib.closing(sqlite3.connect(database_path)) as connection:
                self.assertEqual(connection.execute("PRAGMA quick_check").fetchone()[0], "ok")
                channel = connection.execute(
                    "SELECT value FROM app_settings WHERE key = 'update_channel'"
                ).fetchone()[0]
                font_scale = connection.execute(
                    "SELECT value FROM app_settings WHERE key = 'font_scale'"
                ).fetchone()[0]
            self.assertEqual(channel, "beta")
            self.assertEqual(font_scale, "very-large")

            process.stdin.write('{"command":"shutdown"}\n')
            process.stdin.flush()
            self.assertEqual(process.wait(timeout=10), 0)
            remaining_output = process.stdout.read()
            error_output = process.stderr.read()
            self.assertNotIn(SYNTHETIC_SESSION_TOKEN, remaining_output)
            self.assertNotIn(SYNTHETIC_SESSION_TOKEN, error_output)

    @staticmethod
    def _read_line_with_timeout(stream, timeout: float) -> str:  # type: ignore[no-untyped-def]
        result: queue.Queue[str] = queue.Queue(maxsize=1)
        reader = threading.Thread(target=lambda: result.put(stream.readline()), daemon=True)
        reader.start()
        try:
            line = result.get(timeout=timeout)
        except queue.Empty as error:
            raise AssertionError("The sidecar did not emit a readiness line in time.") from error
        if not line:
            raise AssertionError("The sidecar exited before reporting readiness.")
        return line

    @staticmethod
    def _wait_until_serving(
        opener: urllib.request.OpenerDirector,
        base_url: str,
    ) -> None:
        deadline = time.monotonic() + 8
        request = urllib.request.Request(
            f"{base_url}/health",
            headers={"Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}"},
        )
        while time.monotonic() < deadline:
            try:
                with opener.open(request, timeout=1) as response:
                    if response.status == 200:
                        return
            except (OSError, urllib.error.URLError):
                time.sleep(0.05)
        raise AssertionError("The loopback health endpoint did not become available.")

    @staticmethod
    def _stop_process(process: subprocess.Popen[str]) -> None:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)

    @staticmethod
    def _close_process_streams(process: subprocess.Popen[str]) -> None:
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None and not stream.closed:
                stream.close()


if __name__ == "__main__":
    unittest.main()
