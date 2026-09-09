from __future__ import annotations

import sys
import unittest
import uuid

from new_eden_foundry_backend.token_vault import (
    MemoryCredentialStore,
    RefreshTokenVault,
    SERVICE_PREFIX,
    TokenVaultError,
    WindowsCredentialStore,
)


CHARACTER_ID = 2_112_345_678


class FailingCredentialStore(MemoryCredentialStore):
    def __init__(self) -> None:
        super().__init__()
        self.fail_active_write = False

    def write(self, target: str, value: str) -> None:
        if self.fail_active_write and target.endswith("/refresh"):
            raise TokenVaultError("credential-write-failed")
        super().write(target, value)


class RefreshTokenVaultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = FailingCredentialStore()
        self.vault = RefreshTokenVault(self.store)

    def test_stages_and_verifies_before_replacing_active_credential(self) -> None:
        self.vault.replace(CHARACTER_ID, "refresh-one")

        self.assertEqual(self.vault.read(CHARACTER_ID), "refresh-one")
        self.assertNotIn(
            f"{SERVICE_PREFIX}/{CHARACTER_ID}/refresh.pending",
            self.store.values,
        )

    def test_failed_commit_preserves_old_value_and_recovery_candidate(self) -> None:
        self.vault.replace(CHARACTER_ID, "refresh-old")
        candidate = self.vault.stage(CHARACTER_ID, "refresh-new")
        self.store.fail_active_write = True

        with self.assertRaisesRegex(TokenVaultError, "credential-write-failed"):
            self.vault.commit(candidate)

        self.assertEqual(
            self.store.values[f"{SERVICE_PREFIX}/{CHARACTER_ID}/refresh"],
            "refresh-old",
        )
        self.assertEqual(
            self.store.values[f"{SERVICE_PREFIX}/{CHARACTER_ID}/refresh.pending"],
            "refresh-new",
        )

        self.store.fail_active_write = False
        self.assertEqual(self.vault.read(CHARACTER_ID), "refresh-new")

    def test_rotation_rejects_a_stale_expected_token(self) -> None:
        self.vault.replace(CHARACTER_ID, "refresh-current")

        with self.assertRaisesRegex(TokenVaultError, "credential-rotation-conflict"):
            self.vault.rotate(CHARACTER_ID, "refresh-stale", "refresh-new")

        self.assertEqual(self.vault.read(CHARACTER_ID), "refresh-current")

    def test_discard_keeps_active_token(self) -> None:
        self.vault.replace(CHARACTER_ID, "refresh-active")
        candidate = self.vault.stage(CHARACTER_ID, "refresh-candidate")

        self.vault.discard(candidate)

        self.assertEqual(self.vault.read(CHARACTER_ID), "refresh-active")

    def test_delete_removes_active_and_recovery_slots(self) -> None:
        self.vault.replace(CHARACTER_ID, "refresh-active")
        self.vault.stage(CHARACTER_ID, "refresh-candidate")

        self.vault.delete(CHARACTER_ID)

        self.assertFalse(self.store.values)

    def test_secret_values_never_appear_in_candidate_or_error_text(self) -> None:
        candidate = self.vault.stage(CHARACTER_ID, "super-secret-refresh")

        self.assertNotIn("super-secret-refresh", repr(candidate))
        with self.assertRaises(TokenVaultError) as raised:
            self.vault.rotate(CHARACTER_ID, "another-secret", "new-secret")
        self.assertNotIn("secret", str(raised.exception))

    def test_invalid_values_are_rejected_before_storage(self) -> None:
        for character_id, token in ((0, "token"), (CHARACTER_ID, ""), (CHARACTER_ID, " x")):
            with self.subTest(character_id=character_id, token=token):
                with self.assertRaises(TokenVaultError):
                    self.vault.replace(character_id, token)
        self.assertFalse(self.store.values)


@unittest.skipUnless(sys.platform == "win32", "Windows Credential Manager test")
class WindowsCredentialStoreIntegrationTests(unittest.TestCase):
    def test_writes_reads_replaces_and_deletes_a_synthetic_credential(self) -> None:
        store = WindowsCredentialStore()
        target = f"{SERVICE_PREFIX}/test/{uuid.uuid4()}"
        self.addCleanup(store.delete, target)

        store.write(target, "synthetic-first")
        self.assertEqual(store.read(target), "synthetic-first")

        store.write(target, "synthetic-second")
        self.assertEqual(store.read(target), "synthetic-second")

        store.delete(target)
        self.assertIsNone(store.read(target))

if __name__ == "__main__":
    unittest.main()
