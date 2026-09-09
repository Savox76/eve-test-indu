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
from pathlib import Path

from new_eden_foundry_backend.sidecar import (
    PROTOCOL_VERSION,
    StartupProtocolError,
    is_authorized,
    parse_startup_configuration,
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
            self.assertEqual(health["database"]["schemaVersion"], 5)
            self.assertEqual(health["database"]["location"], "data/foundry.sqlite3")
            self.assertIsNone(health["database"]["lastMigrationBackup"])
            self.assertEqual(health["data"]["state"], "empty")
            self.assertFalse(health["data"]["hasCachedData"])
            self.assertEqual(health["data"]["lastSyncStatus"], "never")
            self.assertIsNone(health["data"]["ageSeconds"])
            self.assertEqual(health["updater"]["channel"], "stable")
            self.assertEqual(health["updater"]["manifestState"], "verified")
            self.assertFalse(health["updater"]["publicDistribution"])
            self.assertEqual(health["ssoRegistration"]["state"], "registered")

            sso_login_url = f"{base_url}/sso/login"
            sso_status_request = urllib.request.Request(
                sso_login_url,
                headers={"Authorization": f"Bearer {SYNTHETIC_SESSION_TOKEN}"},
            )
            with opener.open(sso_status_request, timeout=3) as response:
                sso_status = json.loads(response.read())
            self.assertEqual(sso_status["state"], "idle")

            sso_start_request = urllib.request.Request(
                sso_login_url,
                data=json.dumps({"scopePackages": ["industry-core"]}).encode(),
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
            self.assertEqual(channel, "beta")

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
