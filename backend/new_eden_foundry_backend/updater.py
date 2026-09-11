"""Local update preferences and offline verification for the updater skeleton."""

from __future__ import annotations

import base64
import binascii
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Callable, Final
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


TEST_MANIFEST_PUBLIC_KEY: Final = "RHyyKTAzmKGv9c7Rc5tnsHE3nhR2CnNECxYtHEg3cFI="
TEST_MANIFEST_MAX_BYTES: Final = 65_536
SEMANTIC_VERSION: Final = re.compile(
    r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
SHA256_HEX: Final = re.compile(r"^[0-9a-f]{64}$")
RESOURCE_DIRECTORY: Final = Path(__file__).resolve().parent / "resources"
TEST_MANIFEST_PATH: Final = RESOURCE_DIRECTORY / "update-test-manifest.json"
TEST_MANIFEST_SIGNATURE_PATH: Final = RESOURCE_DIRECTORY / "update-test-manifest.sig"
PUBLIC_RELEASES_URL: Final = (
    "https://api.github.com/repos/Savox76/eve-test-indu/releases?per_page=30"
)
PUBLIC_RELEASE_PAGE_PREFIX: Final = (
    "https://github.com/Savox76/eve-test-indu/releases/tag/v"
)
PUBLIC_RELEASE_MAX_BYTES: Final = 512_000


class UpdateChannel(StrEnum):
    STABLE = "stable"
    BETA = "beta"
    PREVIEW = "preview"


class UpdateManifestError(ValueError):
    """Raised when the bundled updater test manifest is invalid or untrusted."""


class PublicReleaseCheckError(ValueError):
    """Raised when the advisory public release feed is unavailable or invalid."""


@dataclass(frozen=True, slots=True)
class VerifiedUpdateManifest:
    channel: UpdateChannel
    version: str
    published_at: str
    target: str
    url: str
    sha256: str


def read_update_channel(connection: sqlite3.Connection) -> UpdateChannel:
    row = connection.execute(
        "SELECT value FROM app_settings WHERE key = 'update_channel'"
    ).fetchone()
    if row is None:
        raise RuntimeError("The local update-channel setting is missing.")
    try:
        return UpdateChannel(str(row[0]))
    except ValueError as error:
        raise RuntimeError("The local update-channel setting is invalid.") from error


def set_update_channel(
    connection: sqlite3.Connection,
    channel: UpdateChannel | str,
) -> UpdateChannel:
    try:
        selected = channel if isinstance(channel, UpdateChannel) else UpdateChannel(channel)
    except ValueError as error:
        raise ValueError("The update channel is unsupported.") from error

    cursor = connection.execute(
        """
        UPDATE app_settings
        SET value = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        WHERE key = 'update_channel'
        """,
        (selected.value,),
    )
    if cursor.rowcount != 1:
        raise RuntimeError("The local update-channel setting could not be stored.")
    return selected


def _object_without_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise UpdateManifestError("The update manifest contains duplicate fields.")
        result[key] = value
    return result


def _canonical_json(payload: dict[str, object]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _decode_base64(value: str, *, label: str, expected_size: int) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise UpdateManifestError(f"The {label} is not valid base64.") from error
    if len(decoded) != expected_size:
        raise UpdateManifestError(f"The {label} has an invalid size.")
    return decoded


def _parse_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise UpdateManifestError("The manifest publication time is invalid.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise UpdateManifestError("The manifest publication time is invalid.") from error
    if parsed.tzinfo is None or parsed.astimezone(UTC).utcoffset() is None:
        raise UpdateManifestError("The manifest publication time is invalid.")
    return value


def verify_test_update_manifest(
    manifest_bytes: bytes,
    signature_text: str,
    *,
    expected_channel: UpdateChannel = UpdateChannel.PREVIEW,
) -> VerifiedUpdateManifest:
    """Verify and strictly validate the non-distributing signed test manifest."""

    if not manifest_bytes or len(manifest_bytes) > TEST_MANIFEST_MAX_BYTES:
        raise UpdateManifestError("The update manifest has an invalid size.")
    try:
        payload = json.loads(
            manifest_bytes.decode("utf-8"),
            object_pairs_hook=_object_without_duplicates,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UpdateManifestError("The update manifest is not valid UTF-8 JSON.") from error
    if not isinstance(payload, dict) or set(payload) != {
        "schemaVersion",
        "channel",
        "version",
        "publishedAt",
        "platforms",
    }:
        raise UpdateManifestError("The update manifest has unexpected fields.")
    if isinstance(payload["schemaVersion"], bool) or payload["schemaVersion"] != 1:
        raise UpdateManifestError("The update manifest schema is unsupported.")

    try:
        channel = UpdateChannel(payload["channel"])
    except (TypeError, ValueError) as error:
        raise UpdateManifestError("The manifest update channel is unsupported.") from error
    if channel != expected_channel:
        raise UpdateManifestError("The manifest does not match the requested channel.")

    version = payload["version"]
    if not isinstance(version, str) or SEMANTIC_VERSION.fullmatch(version) is None:
        raise UpdateManifestError("The manifest version is not valid semantic versioning.")
    published_at = _parse_timestamp(payload["publishedAt"])

    platforms = payload["platforms"]
    if not isinstance(platforms, dict) or set(platforms) != {"windows-x86_64"}:
        raise UpdateManifestError("The test manifest target is unsupported.")
    target = platforms["windows-x86_64"]
    if not isinstance(target, dict) or set(target) != {"url", "sha256"}:
        raise UpdateManifestError("The test manifest target has unexpected fields.")
    url = target["url"]
    sha256 = target["sha256"]
    if not isinstance(url, str):
        raise UpdateManifestError("The test manifest URL is invalid.")
    try:
        parsed_url = urlsplit(url)
        hostname = parsed_url.hostname
    except ValueError as error:
        raise UpdateManifestError("The test manifest URL is invalid.") from error
    if (
        parsed_url.scheme != "https"
        or hostname != "updates.invalid"
        or parsed_url.username is not None
        or parsed_url.password is not None
        or not parsed_url.path.startswith("/new-eden-foundry/test/")
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise UpdateManifestError("The test manifest URL cannot distribute an update.")
    if not isinstance(sha256, str) or SHA256_HEX.fullmatch(sha256) is None:
        raise UpdateManifestError("The test manifest SHA-256 is invalid.")

    public_key = _decode_base64(
        TEST_MANIFEST_PUBLIC_KEY,
        label="trusted test public key",
        expected_size=32,
    )
    signature = _decode_base64(
        signature_text.strip(),
        label="test manifest signature",
        expected_size=64,
    )
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signature,
            _canonical_json(payload),
        )
    except (InvalidSignature, ValueError) as error:
        raise UpdateManifestError("The update manifest signature is invalid.") from error

    return VerifiedUpdateManifest(
        channel=channel,
        version=version,
        published_at=published_at,
        target="windows-x86_64",
        url=url,
        sha256=sha256,
    )


def verify_bundled_test_manifest() -> VerifiedUpdateManifest:
    try:
        manifest_bytes = TEST_MANIFEST_PATH.read_bytes()
        signature = TEST_MANIFEST_SIGNATURE_PATH.read_text(encoding="ascii")
    except (OSError, UnicodeError) as error:
        raise UpdateManifestError("The bundled updater test manifest is missing.") from error
    return verify_test_update_manifest(manifest_bytes, signature)


def _version_key(value: str) -> tuple[int, int, int, int, tuple[tuple[int, int | str], ...]]:
    if SEMANTIC_VERSION.fullmatch(value) is None:
        raise PublicReleaseCheckError("public_release_version_invalid")
    core, separator, prerelease = value.partition("-")
    major, minor, patch = (int(part) for part in core.split("."))
    if not separator:
        return major, minor, patch, 1, ()
    identifiers: list[tuple[int, int | str]] = []
    for identifier in prerelease.split("."):
        identifiers.append(
            (0, int(identifier)) if identifier.isdigit() else (1, identifier.casefold())
        )
    return major, minor, patch, 0, tuple(identifiers)


def _download_public_release_feed(url: str) -> bytes:
    if url != PUBLIC_RELEASES_URL:
        raise PublicReleaseCheckError("public_release_url_invalid")
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "New-Eden-Foundry-Update-Notice",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=5) as response:  # noqa: S310 - fixed HTTPS origin
            content_type = response.headers.get_content_type()
            if response.status != 200 or content_type != "application/json":
                raise PublicReleaseCheckError("public_release_response_invalid")
            payload = response.read(PUBLIC_RELEASE_MAX_BYTES + 1)
    except PublicReleaseCheckError:
        raise
    except Exception as error:
        raise PublicReleaseCheckError("public_release_unavailable") from error
    if not payload or len(payload) > PUBLIC_RELEASE_MAX_BYTES:
        raise PublicReleaseCheckError("public_release_response_invalid")
    return payload


def _release_assets_are_complete(release: Mapping[str, object], version: str) -> bool:
    assets = release.get("assets")
    if not isinstance(assets, list) or len(assets) > 20:
        return False
    names = {
        asset.get("name")
        for asset in assets
        if isinstance(asset, dict)
        and asset.get("state") == "uploaded"
        and isinstance(asset.get("name"), str)
    }
    installer = f"New.Eden.Foundry_{version}_x64-setup.exe"
    portable = f"New.Eden.Foundry_{version}_x64-portable.zip"
    return {installer, f"{installer}.sha256", portable, f"{portable}.sha256"} <= names


def check_public_releases(
    channel: UpdateChannel | str,
    current_version: str,
    *,
    transport: Callable[[str], bytes] | None = None,
) -> dict[str, object]:
    """Read-only release notice; it never downloads or applies application packages."""

    try:
        selected_channel = channel if isinstance(channel, UpdateChannel) else UpdateChannel(channel)
    except ValueError as error:
        raise PublicReleaseCheckError("public_release_channel_invalid") from error
    current_key = _version_key(current_version)
    try:
        payload = json.loads((transport or _download_public_release_feed)(PUBLIC_RELEASES_URL))
    except PublicReleaseCheckError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
        raise PublicReleaseCheckError("public_release_response_invalid") from error
    if not isinstance(payload, list) or len(payload) > 30:
        raise PublicReleaseCheckError("public_release_response_invalid")
    candidates: list[tuple[tuple[int, int, int, int, tuple[tuple[int, int | str], ...]], str, str, str]] = []
    for release in payload:
        if not isinstance(release, dict) or release.get("draft") is not False:
            continue
        tag = release.get("tag_name")
        prerelease = release.get("prerelease")
        published_at = release.get("published_at")
        if (
            not isinstance(tag, str)
            or not tag.startswith("v")
            or not isinstance(prerelease, bool)
            or not isinstance(published_at, str)
        ):
            continue
        version = tag[1:]
        try:
            version_key = _version_key(version)
            _parse_timestamp(published_at)
        except (PublicReleaseCheckError, UpdateManifestError):
            continue
        expected_page = f"{PUBLIC_RELEASE_PAGE_PREFIX}{version}"
        if release.get("html_url") != expected_page or not _release_assets_are_complete(release, version):
            continue
        allowed = (
            selected_channel == UpdateChannel.PREVIEW
            or selected_channel == UpdateChannel.STABLE
            and not prerelease
            or selected_channel == UpdateChannel.BETA
            and (not prerelease or "-beta" in version)
        )
        if allowed:
            candidates.append((version_key, version, expected_page, published_at))
    if not candidates:
        return {
            "state": "unavailable",
            "channel": selected_channel.value,
            "currentVersion": current_version,
            "latestVersion": None,
            "releaseUrl": None,
            "publishedAt": None,
            "automaticInstall": False,
        }
    latest_key, latest_version, release_url, published_at = max(candidates, key=lambda item: item[0])
    return {
        "state": "available" if latest_key > current_key else "current",
        "channel": selected_channel.value,
        "currentVersion": current_version,
        "latestVersion": latest_version,
        "releaseUrl": release_url,
        "publishedAt": published_at,
        "automaticInstall": False,
    }
