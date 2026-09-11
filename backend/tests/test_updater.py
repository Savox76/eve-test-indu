from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.updater import (
    PUBLIC_RELEASES_URL,
    PublicReleaseCheckError,
    TEST_MANIFEST_PATH,
    TEST_MANIFEST_SIGNATURE_PATH,
    UpdateChannel,
    UpdateManifestError,
    check_public_releases,
    read_update_channel,
    set_update_channel,
    verify_bundled_test_manifest,
    verify_test_update_manifest,
)


def release(version: str, *, prerelease: bool = True, complete: bool = True) -> dict:
    names = [
        f"New.Eden.Foundry_{version}_x64-setup.exe",
        f"New.Eden.Foundry_{version}_x64-setup.exe.sha256",
        f"New.Eden.Foundry_{version}_x64-portable.zip",
        f"New.Eden.Foundry_{version}_x64-portable.zip.sha256",
    ]
    if not complete:
        names.pop()
    return {
        "tag_name": f"v{version}",
        "html_url": f"https://github.com/Savox76/eve-test-indu/releases/tag/v{version}",
        "draft": False,
        "prerelease": prerelease,
        "published_at": "2026-09-11T12:00:00Z",
        "assets": [{"name": name, "state": "uploaded"} for name in names],
    }


class UpdatePreferencesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "foundry.sqlite3"
        initialize_database(self.database_path)
        self.connection = connect_database(self.database_path)

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def test_stable_is_the_safe_default_and_channel_changes_persist(self) -> None:
        self.assertEqual(read_update_channel(self.connection), UpdateChannel.STABLE)

        selected = set_update_channel(self.connection, "beta")

        self.assertEqual(selected, UpdateChannel.BETA)
        self.assertEqual(read_update_channel(self.connection), UpdateChannel.BETA)

    def test_unsupported_channel_does_not_change_the_saved_preference(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported"):
            set_update_channel(self.connection, "nightly")

        self.assertEqual(read_update_channel(self.connection), UpdateChannel.STABLE)


class SignedTestManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = TEST_MANIFEST_PATH.read_bytes()
        self.signature = TEST_MANIFEST_SIGNATURE_PATH.read_text(encoding="ascii")

    def test_bundled_preview_manifest_has_a_valid_ed25519_signature(self) -> None:
        verified = verify_bundled_test_manifest()

        self.assertEqual(verified.channel, UpdateChannel.PREVIEW)
        self.assertEqual(verified.version, "0.0.4-preview.1")
        self.assertEqual(verified.target, "windows-x86_64")
        self.assertEqual(verified.url.split("/")[2], "updates.invalid")

    def test_tampered_manifest_is_rejected(self) -> None:
        payload = json.loads(self.manifest)
        payload["version"] = "0.0.4-preview.2"
        tampered = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()

        with self.assertRaisesRegex(UpdateManifestError, "signature is invalid"):
            verify_test_update_manifest(tampered, self.signature)

    def test_duplicate_manifest_fields_are_rejected_before_use(self) -> None:
        duplicated = self.manifest.replace(
            b'"version":',
            b'"version":"0.0.4-preview.1","version":',
            1,
        )

        with self.assertRaisesRegex(UpdateManifestError, "duplicate fields"):
            verify_test_update_manifest(duplicated, self.signature)

    def test_manifest_for_an_unrequested_channel_is_rejected(self) -> None:
        with self.assertRaisesRegex(UpdateManifestError, "requested channel"):
            verify_test_update_manifest(
                self.manifest,
                self.signature,
                expected_channel=UpdateChannel.STABLE,
            )

    def test_test_manifest_cannot_point_to_a_distributing_host(self) -> None:
        payload = json.loads(self.manifest)
        payload["platforms"]["windows-x86_64"]["url"] = (
            "https://github.com/Savox76/eve-test-indu/releases/download/test/update.exe"
        )
        changed = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()

        with self.assertRaisesRegex(UpdateManifestError, "cannot distribute"):
            verify_test_update_manifest(changed, self.signature)

    def test_malformed_test_manifest_url_is_rejected_cleanly(self) -> None:
        payload = json.loads(self.manifest)
        payload["platforms"]["windows-x86_64"]["url"] = "https://[invalid"
        changed = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()

        with self.assertRaisesRegex(UpdateManifestError, "URL is invalid"):
            verify_test_update_manifest(changed, self.signature)

    def test_malformed_signature_is_rejected(self) -> None:
        with self.assertRaisesRegex(UpdateManifestError, "base64"):
            verify_test_update_manifest(self.manifest, "not-a-signature")


class PublicReleaseNoticeTests(unittest.TestCase):
    @staticmethod
    def transport(releases: list[dict]):
        def load(url: str) -> bytes:
            if url != PUBLIC_RELEASES_URL:
                raise AssertionError("unexpected URL")
            return json.dumps(releases).encode()

        return load

    def test_preview_channel_reports_newest_complete_release(self) -> None:
        notice = check_public_releases(
            "preview",
            "0.0.5-preview.12",
            transport=self.transport([
                release("0.0.5-preview.12"),
                release("0.0.5-preview.13"),
                release("0.0.5-preview.14", complete=False),
            ]),
        )
        self.assertEqual(notice["state"], "available")
        self.assertEqual(notice["latestVersion"], "0.0.5-preview.13")
        self.assertFalse(notice["automaticInstall"])

    def test_stable_channel_ignores_prereleases(self) -> None:
        notice = check_public_releases(
            "stable",
            "0.0.4",
            transport=self.transport([
                release("0.0.5-preview.13"),
                release("0.0.4", prerelease=False),
            ]),
        )
        self.assertEqual(notice["state"], "current")
        self.assertEqual(notice["latestVersion"], "0.0.4")

    def test_untrusted_release_url_and_invalid_payload_are_ignored_or_rejected(self) -> None:
        wrong = release("0.0.5-preview.13")
        wrong["html_url"] = "https://example.invalid/release"
        notice = check_public_releases(
            "preview",
            "0.0.5-preview.12",
            transport=self.transport([wrong]),
        )
        self.assertEqual(notice["state"], "unavailable")
        with self.assertRaisesRegex(PublicReleaseCheckError, "response_invalid"):
            check_public_releases(
                "preview",
                "0.0.5-preview.12",
                transport=lambda _url: b"{}",
            )


if __name__ == "__main__":
    unittest.main()
