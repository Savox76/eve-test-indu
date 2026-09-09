"""Process-local access-token leases backed by atomically rotated refresh tokens."""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .sso_tokens import EveSsoClient, SsoTokenError, VerifiedAuthorization
from .token_vault import RefreshTokenVault, TokenVaultError


class CharacterTokenError(RuntimeError):
    """Bounded token lifecycle error safe to surface without token material."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True, repr=False)
class AccessTokenLease:
    character_id: int
    token: str
    scopes: tuple[str, ...]
    expires_at: datetime

    def __repr__(self) -> str:
        return (
            "AccessTokenLease("
            f"character_id={self.character_id}, token=<redacted>, "
            f"scopes={len(self.scopes)}, expires_at={self.expires_at.isoformat()})"
        )


class CharacterTokenService:
    """Keep access tokens in memory and rotate persisted refresh tokens on demand."""

    def __init__(
        self,
        vault: RefreshTokenVault,
        sso_client: EveSsoClient,
        *,
        utc_now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        refresh_margin: timedelta = timedelta(seconds=60),
    ) -> None:
        if refresh_margin < timedelta(0):
            raise ValueError("The access-token refresh margin must not be negative.")
        self._vault = vault
        self._sso_client = sso_client
        self._utc_now = utc_now
        self._refresh_margin = refresh_margin
        self._leases: dict[int, AccessTokenLease] = {}
        self._lock = threading.RLock()

    def remember(self, authorization: VerifiedAuthorization) -> AccessTokenLease:
        """Cache a validated access token in memory; never persist it."""

        lease = AccessTokenLease(
            character_id=authorization.character.character_id,
            token=authorization.access_token,
            scopes=authorization.character.scopes,
            expires_at=authorization.expires_at,
        )
        with self._lock:
            self._leases[lease.character_id] = lease
        return lease

    def access_token(
        self,
        character_id: int,
        expected_scopes: Sequence[str],
    ) -> AccessTokenLease:
        """Return a valid lease, refreshing and rotating its credential if needed."""

        normalized_scopes = tuple(sorted(set(expected_scopes)))
        if (
            isinstance(character_id, bool)
            or not isinstance(character_id, int)
            or character_id <= 0
            or not normalized_scopes
        ):
            raise CharacterTokenError("access-token-request-invalid")
        with self._lock:
            current = self._leases.get(character_id)
            if (
                current is not None
                and self._utc_now() + self._refresh_margin < current.expires_at
                and set(normalized_scopes).issubset(current.scopes)
            ):
                return current
            try:
                previous_refresh_token = self._vault.read(character_id)
            except TokenVaultError as error:
                raise CharacterTokenError(error.code) from error
            if previous_refresh_token is None:
                raise CharacterTokenError("credential-missing")
            try:
                authorization = self._sso_client.refresh_and_validate(
                    previous_refresh_token,
                    expected_character_id=character_id,
                    expected_scopes=normalized_scopes,
                )
                self._vault.rotate(
                    character_id,
                    previous_refresh_token,
                    authorization.refresh_token,
                )
            except (SsoTokenError, TokenVaultError) as error:
                raise CharacterTokenError(error.code) from error
            return self.remember(authorization)

    def forget(self, character_id: int) -> None:
        with self._lock:
            self._leases.pop(character_id, None)

