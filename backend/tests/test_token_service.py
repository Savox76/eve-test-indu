from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from new_eden_foundry_backend.sso_tokens import VerifiedAuthorization, VerifiedCharacter
from new_eden_foundry_backend.token_service import CharacterTokenError, CharacterTokenService
from new_eden_foundry_backend.token_vault import MemoryCredentialStore, RefreshTokenVault


NOW = datetime(2026, 9, 9, 20, 0, tzinfo=timezone.utc)
CHARACTER_ID = 2_112_345_678
SCOPES = ("esi-assets.read_assets.v1",)


class SyntheticRefreshClient:
    def __init__(self, *, character_id: int = CHARACTER_ID) -> None:
        self.character_id = character_id
        self.calls: list[str] = []

    def refresh_and_validate(
        self,
        refresh_token: str,
        *,
        expected_character_id: int,
        expected_scopes: tuple[str, ...],
    ) -> VerifiedAuthorization:
        self.calls.append(refresh_token)
        if self.character_id != expected_character_id:
            from new_eden_foundry_backend.sso_tokens import SsoTokenError

            raise SsoTokenError("refresh-character-mismatch")
        return VerifiedAuthorization(
            character=VerifiedCharacter(
                self.character_id,
                "Synthetic Pilot",
                expected_scopes,
            ),
            access_token="access-new",
            refresh_token="refresh-new",
            expires_at=NOW + timedelta(minutes=20),
        )


class CharacterTokenServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vault = RefreshTokenVault(MemoryCredentialStore())
        self.vault.replace(CHARACTER_ID, "refresh-old")
        self.client = SyntheticRefreshClient()
        self.service = CharacterTokenService(
            self.vault,
            self.client,  # type: ignore[arg-type]
            utc_now=lambda: NOW,
        )

    def test_refreshes_once_and_atomically_rotates_the_persisted_token(self) -> None:
        first = self.service.access_token(CHARACTER_ID, SCOPES)
        second = self.service.access_token(CHARACTER_ID, SCOPES)

        self.assertEqual(first.token, "access-new")
        self.assertIs(first, second)
        self.assertEqual(self.client.calls, ["refresh-old"])
        self.assertEqual(self.vault.read(CHARACTER_ID), "refresh-new")
        self.assertNotIn("access-new", repr(first))

    def test_remembered_login_token_avoids_an_immediate_refresh(self) -> None:
        authorization = VerifiedAuthorization(
            character=VerifiedCharacter(CHARACTER_ID, "Synthetic Pilot", SCOPES),
            access_token="access-from-login",
            refresh_token="refresh-old",
            expires_at=NOW + timedelta(minutes=20),
        )
        self.service.remember(authorization)

        lease = self.service.access_token(CHARACTER_ID, SCOPES)

        self.assertEqual(lease.token, "access-from-login")
        self.assertFalse(self.client.calls)

    def test_cross_character_refresh_is_rejected_without_replacing_old_token(self) -> None:
        service = CharacterTokenService(
            self.vault,
            SyntheticRefreshClient(character_id=2_000_000_001),  # type: ignore[arg-type]
            utc_now=lambda: NOW,
        )

        with self.assertRaisesRegex(CharacterTokenError, "refresh-character-mismatch"):
            service.access_token(CHARACTER_ID, SCOPES)

        self.assertEqual(self.vault.read(CHARACTER_ID), "refresh-old")

    def test_missing_credential_is_explicit_and_contains_no_secret(self) -> None:
        self.vault.delete(CHARACTER_ID)

        with self.assertRaisesRegex(CharacterTokenError, "credential-missing") as raised:
            self.service.access_token(CHARACTER_ID, SCOPES)

        self.assertNotIn("refresh", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
