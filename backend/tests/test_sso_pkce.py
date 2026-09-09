from __future__ import annotations

import re
import time
import unittest
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlencode, urlsplit

from new_eden_foundry_backend.sso_pkce import (
    SSO_AUTHORIZATION_ENDPOINT,
    SsoPkceError,
    SsoPkceManager,
    generate_pkce_pair,
)
from new_eden_foundry_backend.sso_registration import (
    SSO_CALLBACK_PATH,
    load_bundled_sso_registration_profile,
)


class SsoPkceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = load_bundled_sso_registration_profile()
        self.manager = SsoPkceManager(self.profile, callback_port=0, timeout_seconds=2)

    def tearDown(self) -> None:
        self.manager.close()

    def test_generates_fresh_rfc7636_s256_values(self) -> None:
        first_verifier, first_challenge = generate_pkce_pair()
        second_verifier, second_challenge = generate_pkce_pair()

        token_pattern = re.compile(r"^[A-Za-z0-9_-]{43}$")
        self.assertRegex(first_verifier, token_pattern)
        self.assertRegex(first_challenge, token_pattern)
        self.assertNotEqual(first_verifier, second_verifier)
        self.assertNotEqual(first_challenge, second_challenge)

    def test_authorization_url_contains_exact_pkce_contract_and_selected_scopes(self) -> None:
        authorization_url, status = self.manager.start(["industry-core", "market"])
        parsed = urlsplit(authorization_url)
        query = parse_qs(parsed.query)

        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", SSO_AUTHORIZATION_ENDPOINT)
        self.assertEqual(query["response_type"], ["code"])
        self.assertEqual(query["client_id"], ["a8409de72d5b4cab9b0424819d0abdec"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertRegex(query["state"][0], r"^[A-Za-z0-9_-]{43}$")
        self.assertRegex(query["code_challenge"][0], r"^[A-Za-z0-9_-]{43}$")
        self.assertEqual(urlsplit(query["redirect_uri"][0]).path, SSO_CALLBACK_PATH)
        self.assertEqual(
            query["scope"][0].split(),
            [
                *self.profile.scope_packages["industry-core"],
                *self.profile.scope_packages["market"],
            ],
        )
        self.assertEqual(status["state"], "waiting")
        self.assertEqual(status["scopePackages"], ["industry-core", "market"])
        self.assertNotIn(query["state"][0], str(status))
        self.assertNotIn("codeVerifier", status)

    def test_listener_rejects_wrong_state_then_accepts_exact_callback_once(self) -> None:
        authorization_url, _ = self.manager.start(["industry-core"])
        query = parse_qs(urlsplit(authorization_url).query)
        callback_uri = query["redirect_uri"][0]
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        wrong_url = f"{callback_uri}?{urlencode({'code': 'synthetic-code', 'state': 'wrong'})}"
        with self.assertRaises(urllib.error.HTTPError) as rejected:
            opener.open(wrong_url, timeout=2)
        self.assertEqual(rejected.exception.code, 400)
        self.assertEqual(self.manager.status()["state"], "waiting")

        valid_url = f"{callback_uri}?{urlencode({'code': 'synthetic-code', 'state': query['state'][0]})}"
        with opener.open(valid_url, timeout=2) as response:
            document = response.read().decode("utf-8")
        self.assertEqual(response.status, 200)
        self.assertIn("EVE-Autorisierung empfangen", document)
        self.assertEqual(self.manager.status()["state"], "authorization-received")
        self.assertIsNone(self.manager._attempt.state_secret)  # noqa: SLF001
        self.assertIsNone(self.manager._attempt.code_verifier)  # noqa: SLF001

        result = self.manager.accept_callback(
            str(self.manager.status()["attemptId"]),
            urlencode({"code": "second-code", "state": query["state"][0]}),
        )
        self.assertEqual(result.status_code, 410)

    def test_cancel_clears_secrets_and_stops_waiting(self) -> None:
        self.manager.start(["industry-core"])

        status = self.manager.cancel()

        self.assertEqual(status["state"], "cancelled")
        self.assertIsNone(status["errorCode"])
        self.assertIsNone(self.manager._attempt.state_secret)  # noqa: SLF001
        self.assertIsNone(self.manager._attempt.code_verifier)  # noqa: SLF001

    def test_timeout_is_terminal_and_clears_secrets(self) -> None:
        manager = SsoPkceManager(self.profile, callback_port=0, timeout_seconds=0.05)
        self.addCleanup(manager.close)
        manager.start(["industry-core"])

        deadline = time.monotonic() + 2
        while manager.status()["state"] == "waiting" and time.monotonic() < deadline:
            time.sleep(0.01)

        status = manager.status()
        self.assertEqual(status["state"], "timed-out")
        self.assertEqual(status["errorCode"], "login-timeout")
        self.assertIsNone(manager._attempt.state_secret)  # noqa: SLF001
        self.assertIsNone(manager._attempt.code_verifier)  # noqa: SLF001

    def test_rejects_unknown_duplicate_and_empty_scope_packages(self) -> None:
        for packages in ([], ["unknown"], ["industry-core", "industry-core"]):
            with self.subTest(packages=packages):
                with self.assertRaisesRegex(SsoPkceError, "invalid-scope-packages"):
                    self.manager.start(packages)

    def test_matching_access_denied_callback_reports_sanitized_failure(self) -> None:
        authorization_url, status = self.manager.start(["industry-core"])
        state = parse_qs(urlsplit(authorization_url).query)["state"][0]

        result = self.manager.accept_callback(
            str(status["attemptId"]),
            urlencode({"error": "access_denied", "error_description": "private", "state": state}),
        )

        self.assertEqual(result.status_code, 400)
        self.assertEqual(self.manager.status()["state"], "failed")
        self.assertEqual(self.manager.status()["errorCode"], "authorization-denied")
        self.assertNotIn("private", str(self.manager.status()))


if __name__ == "__main__":
    unittest.main()
