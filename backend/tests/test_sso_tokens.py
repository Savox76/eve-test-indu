from __future__ import annotations

import base64
import json
import unittest
from datetime import datetime, timezone
from typing import cast

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from new_eden_foundry_backend.sso_tokens import (
    EveSsoClient,
    SSO_METADATA_ENDPOINT,
    SsoTokenError,
    validate_access_token,
)


CLIENT_ID = "synthetic-client-id"
NOW = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)
SCOPES = ("esi-assets.read_assets.v1", "esi-industry.read_character_jobs.v1")


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


class JwtFixture:
    def __init__(self) -> None:
        self.private_key = rsa.generate_private_key(public_exponent=65_537, key_size=2_048)
        numbers = self.private_key.public_key().public_numbers()
        self.jwk = {
            "kty": "RSA",
            "kid": "synthetic-key",
            "use": "sig",
            "alg": "RS256",
            "n": _base64url(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")),
            "e": _base64url(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")),
        }

    def token(self, claim_overrides: dict[str, object] | None = None) -> str:
        header = {"alg": "RS256", "kid": "synthetic-key", "typ": "JWT"}
        claims: dict[str, object] = {
            "iss": "https://login.eveonline.com/",
            "aud": [CLIENT_ID, "EVE Online"],
            "exp": int(NOW.timestamp()) + 1_200,
            "iat": int(NOW.timestamp()) - 5,
            "sub": "CHARACTER:EVE:2112345678",
            "name": "Synthetic Pilot",
            "scp": list(SCOPES),
        }
        claims.update(claim_overrides or {})
        encoded_header = _base64url(json.dumps(header, separators=(",", ":")).encode())
        encoded_claims = _base64url(json.dumps(claims, separators=(",", ":")).encode())
        signing_input = f"{encoded_header}.{encoded_claims}".encode("ascii")
        signature = self.private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        return f"{signing_input.decode('ascii')}.{_base64url(signature)}"


class AccessTokenValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = JwtFixture()

    def validate(self, token: str):  # type: ignore[no-untyped-def]
        return validate_access_token(
            token,
            jwks={"keys": [self.fixture.jwk]},
            client_id=CLIENT_ID,
            expected_scopes=SCOPES,
            now=NOW,
        )

    def test_accepts_signed_eve_identity_and_returns_no_tokens(self) -> None:
        identity = self.validate(self.fixture.token())

        self.assertEqual(identity.character_id, 2_112_345_678)
        self.assertEqual(identity.name, "Synthetic Pilot")
        self.assertEqual(identity.scopes, tuple(sorted(SCOPES)))
        self.assertNotIn("token", str(identity).casefold())

    def test_rejects_wrong_signature(self) -> None:
        token = self.fixture.token()
        other_fixture = JwtFixture()

        with self.assertRaisesRegex(SsoTokenError, "jwt-signature-invalid"):
            validate_access_token(
                token,
                jwks={"keys": [other_fixture.jwk]},
                client_id=CLIENT_ID,
                expected_scopes=SCOPES,
                now=NOW,
            )

    def test_rejects_invalid_identity_and_security_claims(self) -> None:
        invalid_claims = (
            {"iss": "https://login.invalid/"},
            {"aud": [CLIENT_ID]},
            {"aud": ["another-client", "EVE Online"]},
            {"exp": int(NOW.timestamp()) - 31},
            {"sub": "ACCOUNT:EVE:2112345678"},
            {"sub": "CHARACTER:EVE:0"},
            {"name": ""},
            {"scp": [SCOPES[0]]},
        )
        for overrides in invalid_claims:
            with self.subTest(overrides=overrides):
                with self.assertRaises(SsoTokenError):
                    self.validate(self.fixture.token(overrides))


class TokenExchangeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = JwtFixture()
        self.calls: list[tuple[str, str, dict[str, str] | None]] = []

    def requester(self, method, url, form, _headers):  # type: ignore[no-untyped-def]
        self.calls.append((method, url, dict(form) if form is not None else None))
        if url == SSO_METADATA_ENDPOINT:
            return {
                "issuer": "https://login.eveonline.com/",
                "authorization_endpoint": "https://login.eveonline.com/v2/oauth/authorize",
                "token_endpoint": "https://login.eveonline.com/v2/oauth/token",
                "jwks_uri": "https://login.eveonline.com/oauth/jwks",
            }
        if url.endswith("/v2/oauth/token"):
            return {
                "access_token": self.fixture.token(),
                "refresh_token": "synthetic-refresh-token",
                "expires_in": 1_200,
                "token_type": "Bearer",
            }
        if url.endswith("/oauth/jwks"):
            return {"keys": [self.fixture.jwk]}
        raise AssertionError(f"Unexpected URL: {url}")

    def test_exchanges_pkce_code_via_metadata_and_returns_verified_identity(self) -> None:
        client = EveSsoClient(
            CLIENT_ID,
            request_json=self.requester,
            utc_now=lambda: NOW,
        )
        identity = client.exchange_and_validate("synthetic-code", "v" * 43, SCOPES)

        self.assertEqual(identity.name, "Synthetic Pilot")
        self.assertEqual([call[0] for call in self.calls], ["GET", "POST", "GET"])
        token_form = cast(dict[str, str], self.calls[1][2])
        self.assertEqual(token_form["grant_type"], "authorization_code")
        self.assertEqual(token_form["client_id"], CLIENT_ID)
        self.assertEqual(token_form["code_verifier"], "v" * 43)
        self.assertNotIn("client_secret", token_form)

    def test_rejects_metadata_endpoint_outside_eve_sso(self) -> None:
        def malicious_requester(method, url, form, headers):  # type: ignore[no-untyped-def]
            payload = dict(self.requester(method, url, form, headers))
            if url == SSO_METADATA_ENDPOINT:
                payload["jwks_uri"] = "https://login.invalid/keys"
            return payload

        client = EveSsoClient(CLIENT_ID, request_json=malicious_requester)

        with self.assertRaisesRegex(SsoTokenError, "sso-metadata-invalid"):
            client.exchange_and_validate("synthetic-code", "v" * 43, SCOPES)

    def test_sanitizes_remote_token_failure(self) -> None:
        def failing_requester(method, url, form, headers):  # type: ignore[no-untyped-def]
            if url.endswith("/v2/oauth/token"):
                raise SsoTokenError("private-upstream-detail")
            return self.requester(method, url, form, headers)

        client = EveSsoClient(CLIENT_ID, request_json=failing_requester)

        with self.assertRaisesRegex(SsoTokenError, "token-exchange-failed") as raised:
            client.exchange_and_validate("synthetic-code", "v" * 43, SCOPES)
        self.assertNotIn("private-upstream-detail", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
