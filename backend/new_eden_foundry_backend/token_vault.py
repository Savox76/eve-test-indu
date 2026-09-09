"""Windows Credential Manager storage for character-bound EVE refresh tokens."""

from __future__ import annotations

import ctypes
import secrets
import sys
import threading
from dataclasses import dataclass
from typing import Final, Protocol


SERVICE_PREFIX: Final = "NewEdenFoundry/EVE"
MAXIMUM_REFRESH_TOKEN_BYTES: Final = 2_400
ERROR_NOT_FOUND: Final = 1_168
CRED_TYPE_GENERIC: Final = 1
CRED_PERSIST_LOCAL_MACHINE: Final = 2


class TokenVaultError(RuntimeError):
    """Expose a bounded error code without ever including credential contents."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class CredentialStore(Protocol):
    """Minimal replace-capable secret store used by the transactional vault."""

    backend_name: str

    def read(self, target: str) -> str | None: ...

    def write(self, target: str, value: str) -> None: ...

    def delete(self, target: str) -> None: ...


class UnavailableCredentialStore:
    """Fail closed when Windows Credential Manager is not available."""

    backend_name = "unavailable"

    @staticmethod
    def _raise() -> None:
        raise TokenVaultError("credential-store-unavailable")

    def read(self, target: str) -> str | None:
        del target
        self._raise()

    def write(self, target: str, value: str) -> None:
        del target, value
        self._raise()

    def delete(self, target: str) -> None:
        del target
        self._raise()


class MemoryCredentialStore:
    """Deterministic test double; never selected by the production factory."""

    backend_name = "memory-test-double"

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def read(self, target: str) -> str | None:
        return self.values.get(target)

    def write(self, target: str, value: str) -> None:
        self.values[target] = value

    def delete(self, target: str) -> None:
        self.values.pop(target, None)


class WindowsCredentialStore:
    """Store generic credentials in the current Windows user's credential set."""

    backend_name = "windows-credential-manager"

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise TokenVaultError("credential-store-unavailable")

        from ctypes import wintypes

        class Credential(ctypes.Structure):
            _fields_ = [
                ("Flags", wintypes.DWORD),
                ("Type", wintypes.DWORD),
                ("TargetName", wintypes.LPWSTR),
                ("Comment", wintypes.LPWSTR),
                ("LastWritten", wintypes.FILETIME),
                ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", wintypes.DWORD),
                ("AttributeCount", wintypes.DWORD),
                ("Attributes", ctypes.c_void_p),
                ("TargetAlias", wintypes.LPWSTR),
                ("UserName", wintypes.LPWSTR),
            ]

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        advapi32.CredWriteW.argtypes = [ctypes.POINTER(Credential), wintypes.DWORD]
        advapi32.CredWriteW.restype = wintypes.BOOL
        advapi32.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(Credential)),
        ]
        advapi32.CredReadW.restype = wintypes.BOOL
        advapi32.CredDeleteW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
        ]
        advapi32.CredDeleteW.restype = wintypes.BOOL
        advapi32.CredFree.argtypes = [ctypes.c_void_p]
        advapi32.CredFree.restype = None
        self._credential_type = Credential
        self._advapi32 = advapi32

    def read(self, target: str) -> str | None:
        pointer = ctypes.POINTER(self._credential_type)()
        if not self._advapi32.CredReadW(
            target,
            CRED_TYPE_GENERIC,
            0,
            ctypes.byref(pointer),
        ):
            error_code = ctypes.get_last_error()
            if error_code == ERROR_NOT_FOUND:
                return None
            raise TokenVaultError("credential-read-failed")
        try:
            credential = pointer.contents
            raw = ctypes.string_at(
                credential.CredentialBlob,
                credential.CredentialBlobSize,
            )
            return raw.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as error:
            raise TokenVaultError("credential-read-failed") from error
        finally:
            self._advapi32.CredFree(pointer)

    def write(self, target: str, value: str) -> None:
        encoded = value.encode("utf-8")
        buffer = (ctypes.c_ubyte * len(encoded)).from_buffer_copy(encoded)
        credential = self._credential_type()
        credential.Flags = 0
        credential.Type = CRED_TYPE_GENERIC
        credential.TargetName = target
        credential.Comment = "New Eden Foundry EVE refresh token"
        credential.CredentialBlobSize = len(encoded)
        credential.CredentialBlob = ctypes.cast(
            buffer,
            ctypes.POINTER(ctypes.c_ubyte),
        )
        credential.Persist = CRED_PERSIST_LOCAL_MACHINE
        credential.AttributeCount = 0
        credential.Attributes = None
        credential.TargetAlias = None
        credential.UserName = "New Eden Foundry"
        if not self._advapi32.CredWriteW(ctypes.byref(credential), 0):
            raise TokenVaultError("credential-write-failed")

    def delete(self, target: str) -> None:
        if self._advapi32.CredDeleteW(target, CRED_TYPE_GENERIC, 0):
            return
        if ctypes.get_last_error() != ERROR_NOT_FOUND:
            raise TokenVaultError("credential-delete-failed")


@dataclass(frozen=True, slots=True, repr=False)
class StagedRefreshToken:
    """Opaque candidate that can be committed without exposing its value in repr."""

    character_id: int
    _value: str

    def __repr__(self) -> str:
        return f"StagedRefreshToken(character_id={self.character_id}, value=<redacted>)"


class RefreshTokenVault:
    """Two-slot vault that keeps the last usable token until replacement is durable."""

    def __init__(self, store: CredentialStore) -> None:
        self._store = store
        self._lock = threading.RLock()

    @property
    def backend_name(self) -> str:
        return self._store.backend_name

    @staticmethod
    def _validate_character_id(character_id: int) -> int:
        if isinstance(character_id, bool) or not isinstance(character_id, int) or character_id <= 0:
            raise TokenVaultError("credential-character-invalid")
        return character_id

    @staticmethod
    def _validate_token(value: str) -> str:
        if (
            not isinstance(value, str)
            or not value
            or value.strip() != value
            or "\x00" in value
            or len(value.encode("utf-8")) > MAXIMUM_REFRESH_TOKEN_BYTES
        ):
            raise TokenVaultError("credential-token-invalid")
        return value

    @classmethod
    def _active_target(cls, character_id: int) -> str:
        return f"{SERVICE_PREFIX}/{cls._validate_character_id(character_id)}/refresh"

    @classmethod
    def _staging_target(cls, character_id: int) -> str:
        return f"{SERVICE_PREFIX}/{cls._validate_character_id(character_id)}/refresh.pending"

    def stage(self, character_id: int, refresh_token: str) -> StagedRefreshToken:
        """Write and verify a candidate without touching the currently active value."""

        character_id = self._validate_character_id(character_id)
        refresh_token = self._validate_token(refresh_token)
        with self._lock:
            target = self._staging_target(character_id)
            self._store.write(target, refresh_token)
            persisted = self._store.read(target)
            if persisted is None or not secrets.compare_digest(persisted, refresh_token):
                raise TokenVaultError("credential-stage-verification-failed")
            return StagedRefreshToken(character_id, refresh_token)

    def commit(self, candidate: StagedRefreshToken) -> None:
        """Replace the active credential only after the staged value is verified."""

        if not isinstance(candidate, StagedRefreshToken):
            raise TokenVaultError("credential-candidate-invalid")
        with self._lock:
            staging_target = self._staging_target(candidate.character_id)
            active_target = self._active_target(candidate.character_id)
            staged = self._store.read(staging_target)
            if staged is None or not secrets.compare_digest(staged, candidate._value):
                raise TokenVaultError("credential-stage-missing")
            self._store.write(active_target, candidate._value)
            active = self._store.read(active_target)
            if active is None or not secrets.compare_digest(active, candidate._value):
                raise TokenVaultError("credential-commit-verification-failed")
            self._store.delete(staging_target)

    def discard(self, candidate: StagedRefreshToken) -> None:
        """Remove only the matching uncommitted candidate; preserve the active token."""

        if not isinstance(candidate, StagedRefreshToken):
            return
        with self._lock:
            target = self._staging_target(candidate.character_id)
            staged = self._store.read(target)
            if staged is not None and secrets.compare_digest(staged, candidate._value):
                self._store.delete(target)

    def replace(self, character_id: int, refresh_token: str) -> None:
        candidate = self.stage(character_id, refresh_token)
        self.commit(candidate)

    def rotate(self, character_id: int, old_token: str, new_token: str) -> None:
        """Compare-and-replace one token so concurrent refreshes cannot clobber it."""

        old_token = self._validate_token(old_token)
        with self._lock:
            current = self.read(character_id)
            if current is None or not secrets.compare_digest(current, old_token):
                raise TokenVaultError("credential-rotation-conflict")
            candidate = self.stage(character_id, new_token)
            self.commit(candidate)

    def read(self, character_id: int) -> str | None:
        """Recover a durable staged token before returning the active credential."""

        with self._lock:
            staging_target = self._staging_target(character_id)
            staged = self._store.read(staging_target)
            if staged is not None:
                staged = self._validate_token(staged)
                candidate = StagedRefreshToken(character_id, staged)
                self.commit(candidate)
            active = self._store.read(self._active_target(character_id))
            return self._validate_token(active) if active is not None else None

    def contains(self, character_id: int) -> bool:
        return self.read(character_id) is not None

    def delete(self, character_id: int) -> None:
        """Remove active and recovery slots for a character."""

        with self._lock:
            self._store.delete(self._staging_target(character_id))
            self._store.delete(self._active_target(character_id))


def create_system_refresh_token_vault() -> RefreshTokenVault:
    """Return the Windows credential vault or a fail-closed unsupported backend."""

    try:
        store: CredentialStore = WindowsCredentialStore()
    except TokenVaultError:
        store = UnavailableCredentialStore()
    return RefreshTokenVault(store)
