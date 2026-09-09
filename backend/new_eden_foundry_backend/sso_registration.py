"""Validated public registration contract for EVE SSO.

This module contains no OAuth tokens and no client secret. The client ID is public,
but remains unset until EVE's developer portal has created the application.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from urllib.parse import urlsplit


SSO_REDIRECT_URI: Final = "http://127.0.0.1:17891/oauth/callback"
SSO_CALLBACK_HOST: Final = "127.0.0.1"
SSO_CALLBACK_PORT: Final = 17_891
SSO_CALLBACK_PATH: Final = "/oauth/callback"
RESOURCE_PATH: Final = (
    Path(__file__).resolve().parent / "resources" / "eve-sso-registration.json"
)
CLIENT_ID_PATTERN: Final = re.compile(r"^[A-Za-z0-9._~-]{8,128}$")
SCOPE_PATTERN: Final = re.compile(r"^esi-[a-z_]+\.[a-z_]+\.v[0-9]+$")

EXPECTED_SCOPE_PACKAGES: Final[dict[str, tuple[str, ...]]] = {
    "industry-core": (
        "esi-assets.read_assets.v1",
        "esi-characters.read_blueprints.v1",
        "esi-industry.read_character_jobs.v1",
        "esi-skills.read_skills.v1",
    ),
    "market": (
        "esi-markets.read_character_orders.v1",
        "esi-wallet.read_character_wallet.v1",
    ),
    "planetary-industry": ("esi-planets.manage_planets.v1",),
    "projects": ("esi-fittings.read_fittings.v1",),
    "private-structures": ("esi-universe.read_structures.v1",),
}


class SsoRegistrationError(ValueError):
    """Raised when the public EVE SSO registration contract is inconsistent."""


@dataclass(frozen=True, slots=True)
class DeveloperContact:
    name: str
    url: str


@dataclass(frozen=True, slots=True)
class SsoRegistrationProfile:
    application_name: str
    application_type: str
    client_id: str | None
    redirect_uri: str
    developer_contact: DeveloperContact
    scope_packages: dict[str, tuple[str, ...]]
    source_reviewed_at: str

    @property
    def is_registered(self) -> bool:
        return self.client_id is not None

    def as_status_payload(self) -> dict[str, object]:
        return {
            "state": "registered" if self.is_registered else "pending-client-id",
            "clientId": self.client_id,
            "redirectUri": self.redirect_uri,
            "scopePackages": sorted(self.scope_packages),
        }


def _object_without_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SsoRegistrationError("The SSO profile contains duplicate fields.")
        result[key] = value
    return result


def parse_sso_registration_profile(raw: bytes) -> SsoRegistrationProfile:
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_object_without_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SsoRegistrationError("The SSO profile is not valid UTF-8 JSON.") from error

    expected_fields = {
        "applicationName",
        "applicationType",
        "clientId",
        "redirectUri",
        "developerContact",
        "scopePackages",
        "sourceReviewedAt",
    }
    if not isinstance(payload, dict) or set(payload) != expected_fields:
        raise SsoRegistrationError("The SSO profile has unexpected fields.")

    if payload["applicationName"] != "New Eden Foundry":
        raise SsoRegistrationError("The SSO application name is invalid.")
    if payload["applicationType"] != "native-public-pkce":
        raise SsoRegistrationError("The SSO application type is invalid.")

    client_id = payload["clientId"]
    if client_id is not None and (
        not isinstance(client_id, str) or CLIENT_ID_PATTERN.fullmatch(client_id) is None
    ):
        raise SsoRegistrationError("The public SSO client ID is invalid.")

    redirect_uri = payload["redirectUri"]
    if redirect_uri != SSO_REDIRECT_URI:
        raise SsoRegistrationError("The SSO redirect URI differs from the fixed callback.")
    parsed_redirect = urlsplit(redirect_uri)
    if (
        parsed_redirect.scheme != "http"
        or parsed_redirect.hostname != SSO_CALLBACK_HOST
        or parsed_redirect.port != SSO_CALLBACK_PORT
        or parsed_redirect.path != SSO_CALLBACK_PATH
        or parsed_redirect.query
        or parsed_redirect.fragment
    ):
        raise SsoRegistrationError("The SSO redirect URI is not the approved loopback URI.")

    contact = payload["developerContact"]
    if not isinstance(contact, dict) or set(contact) != {"name", "url"}:
        raise SsoRegistrationError("The developer contact is invalid.")
    if contact["name"] != "Savox76":
        raise SsoRegistrationError("The developer contact name is invalid.")
    contact_url = contact["url"]
    parsed_contact = urlsplit(contact_url) if isinstance(contact_url, str) else None
    if (
        parsed_contact is None
        or parsed_contact.scheme != "https"
        or parsed_contact.hostname != "github.com"
        or not parsed_contact.path.startswith("/Savox76/eve-test-indu/")
    ):
        raise SsoRegistrationError("The developer contact URL is invalid.")

    raw_packages = payload["scopePackages"]
    if not isinstance(raw_packages, dict) or set(raw_packages) != set(EXPECTED_SCOPE_PACKAGES):
        raise SsoRegistrationError("The SSO scope packages differ from the approved set.")
    scope_packages: dict[str, tuple[str, ...]] = {}
    seen_scopes: set[str] = set()
    for package_name, expected_scopes in EXPECTED_SCOPE_PACKAGES.items():
        raw_scopes = raw_packages[package_name]
        if not isinstance(raw_scopes, list) or not all(
            isinstance(scope, str) for scope in raw_scopes
        ):
            raise SsoRegistrationError(f"Scope package {package_name!r} is invalid.")
        scopes = tuple(raw_scopes)
        if scopes != expected_scopes or any(
            SCOPE_PATTERN.fullmatch(scope) is None for scope in scopes
        ):
            raise SsoRegistrationError(f"Scope package {package_name!r} has drifted.")
        if seen_scopes.intersection(scopes):
            raise SsoRegistrationError("A scope occurs in more than one package.")
        seen_scopes.update(scopes)
        scope_packages[package_name] = scopes

    reviewed_at = payload["sourceReviewedAt"]
    if reviewed_at != "2026-09-09":
        raise SsoRegistrationError("The SSO source review date is invalid.")

    return SsoRegistrationProfile(
        application_name="New Eden Foundry",
        application_type="native-public-pkce",
        client_id=client_id,
        redirect_uri=redirect_uri,
        developer_contact=DeveloperContact(name=contact["name"], url=contact_url),
        scope_packages=scope_packages,
        source_reviewed_at=reviewed_at,
    )


def load_bundled_sso_registration_profile() -> SsoRegistrationProfile:
    return parse_sso_registration_profile(RESOURCE_PATH.read_bytes())
