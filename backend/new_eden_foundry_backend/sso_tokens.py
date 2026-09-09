"""EVE SSO token exchange and strict access-token identity validation."""

from __future__ import annotations

import base64
import binascii
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Final

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa


SSO_METADATA_ENDPOINT: Final = (
    "https://login.eveonline.com/.well-known/oauth-authorization-server"
)
EXPECTED_EVE_AUDIENCE: Final = "EVE Online"
ACCEPTED_EVE_ISSUERS: Final = frozenset(
    {
        "https://login.eveonline.com",
        "https://login.eveonline.com/",
        "login.eveonline.com",
    }
)
HTTP_TIMEOUT_SECONDS: Final = 8.0
METADATA_CACHE_SECONDS: Final = 300.0
MAXIMUM_JSON_BYTES: Final = 262_144
MAXIMUM_ACCESS_TOKEN_LENGTH: Final = 32_768
MAXIMUM_REFRESH_TOKEN_LENGTH: Final = 2_400
MAXIMUM_AUTHORIZATION_CODE_LENGTH: Final = 4_096
MAXIMUM_CODE_VERIFIER_LENGTH: Final = 128
JWT_CLOCK_SKEW_SECONDS: Final = 30
CHARACTER_SUBJECT = re.compile(r"^CHARACTER:EVE:([1-9][0-9]*)$")
PKCE_VALUE = re.compile(r"^[A-Za-z0-9_-]{43,128}$")


class SsoTokenError(RuntimeError):
    """Expose only a bounded public error code for an SSO validation failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class EveSsoMetadata:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str


@dataclass(frozen=True, slots=True)
class VerifiedCharacter:
    character_id: int
    name: str
    scopes: tuple[str, ...]

    def as_api_payload(self) -> dict[str, object]:
        return {
            "characterId": self.character_id,
            "name": self.name,
            "scopes": list(self.scopes),
        }


@dataclass(frozen=True, slots=True, repr=False)
class VerifiedAuthorization:
    """Validated identity plus process-local OAuth credentials.

    This object must stay inside the Python sidecar. Its representation is
    deliberately redacted so an accidental exception or debug line cannot
    disclose either token.
    """

    character: VerifiedCharacter
    access_token: str
    refresh_token: str
    expires_at: datetime

    def __repr__(self) -> str:
        return (
            "VerifiedAuthorization("
            f"character_id={self.character.character_id}, "
            "access_token=<redacted>, refresh_token=<redacted>, "
            f"expires_at={self.expires_at.isoformat()})"
        )


JsonRequester = Callable[
    [str, str, Mapping[str, str] | None, Mapping[str, str]],
    Mapping[str, object],
]


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def _trusted_sso_url(value: object) -> str:
    if not isinstance(value, str) or len(value) > 2_048:
        raise SsoTokenError("sso-metadata-invalid")
    parsed = urllib.parse.urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "login.eveonline.com"
        or parsed.port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or not parsed.path.startswith("/")
        or parsed.query
        or parsed.fragment
    ):
        raise SsoTokenError("sso-metadata-invalid")
    return value


def _default_json_request(
    method: str,
    url: str,
    form: Mapping[str, str] | None,
    headers: Mapping[str, str],
) -> Mapping[str, object]:
    data = urllib.parse.urlencode(form).encode("ascii") if form is not None else None
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "New-Eden-Foundry/SSO",
        **headers,
    }
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers=request_headers,
    )
    try:
        opener = urllib.request.build_opener(_RejectRedirects())
        with opener.open(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise SsoTokenError("sso-http-failed")
            content_type = response.headers.get_content_type()
            if content_type not in {"application/json", "text/json"}:
                raise SsoTokenError("sso-response-invalid")
            payload = response.read(MAXIMUM_JSON_BYTES + 1)
    except SsoTokenError:
        raise
    except (OSError, TimeoutError, urllib.error.URLError) as error:
        raise SsoTokenError("sso-http-failed") from error
    if len(payload) > MAXIMUM_JSON_BYTES:
        raise SsoTokenError("sso-response-invalid")
    try:
        decoded = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SsoTokenError("sso-response-invalid") from error
    if not isinstance(decoded, dict):
        raise SsoTokenError("sso-response-invalid")
    return decoded


def _base64url_decode(value: object, *, error_code: str) -> bytes:
    if (
        not isinstance(value, str)
        or not value
        or "=" in value
        or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for character in value)
    ):
        raise SsoTokenError(error_code)
    padding_length = (-len(value)) % 4
    try:
        return base64.urlsafe_b64decode(value + ("=" * padding_length))
    except (ValueError, binascii.Error) as error:
        raise SsoTokenError(error_code) from error


def _json_segment(value: str) -> Mapping[str, object]:
    try:
        decoded = json.loads(_base64url_decode(value, error_code="jwt-malformed"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SsoTokenError("jwt-malformed") from error
    if not isinstance(decoded, dict):
        raise SsoTokenError("jwt-malformed")
    return decoded


def _integer_claim(claims: Mapping[str, object], name: str) -> int:
    value = claims.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
        raise SsoTokenError("jwt-claims-invalid")
    return int(value)


def _validate_scopes(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise SsoTokenError("jwt-claims-invalid")
    if any(
        not isinstance(scope, str)
        or not 1 <= len(scope) <= 200
        or scope.strip() != scope
        for scope in value
    ):
        raise SsoTokenError("jwt-claims-invalid")
    scopes = tuple(sorted(set(value)))
    if len(scopes) != len(value):
        raise SsoTokenError("jwt-claims-invalid")
    return scopes


def validate_access_token(
    token: str,
    *,
    jwks: Mapping[str, object],
    client_id: str,
    expected_scopes: Sequence[str],
    now: datetime | None = None,
) -> VerifiedCharacter:
    """Verify signature and every identity-bearing claim before trusting a character."""

    if not isinstance(token, str) or not 1 <= len(token) <= MAXIMUM_ACCESS_TOKEN_LENGTH:
        raise SsoTokenError("jwt-malformed")
    segments = token.split(".")
    if len(segments) != 3:
        raise SsoTokenError("jwt-malformed")
    header = _json_segment(segments[0])
    claims = _json_segment(segments[1])
    signature = _base64url_decode(segments[2], error_code="jwt-malformed")

    algorithm = header.get("alg")
    key_id = header.get("kid")
    if (
        algorithm != "RS256"
        or not isinstance(key_id, str)
        or not key_id
        or len(key_id) > 256
        or "crit" in header
    ):
        raise SsoTokenError("jwt-header-invalid")

    keys = jwks.get("keys")
    if not isinstance(keys, list) or not keys:
        raise SsoTokenError("jwks-invalid")
    matches = [
        key
        for key in keys
        if isinstance(key, dict)
        and key.get("kid") == key_id
        and key.get("kty") == "RSA"
        and key.get("alg", "RS256") == "RS256"
        and key.get("use", "sig") == "sig"
    ]
    if len(matches) != 1:
        raise SsoTokenError("jwt-key-not-found")
    key = matches[0]
    modulus = int.from_bytes(_base64url_decode(key.get("n"), error_code="jwks-invalid"), "big")
    exponent = int.from_bytes(_base64url_decode(key.get("e"), error_code="jwks-invalid"), "big")
    if modulus.bit_length() < 2_048 or exponent < 3:
        raise SsoTokenError("jwks-invalid")
    try:
        public_key = rsa.RSAPublicNumbers(exponent, modulus).public_key()
        public_key.verify(
            signature,
            f"{segments[0]}.{segments[1]}".encode("ascii"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except (InvalidSignature, ValueError) as error:
        raise SsoTokenError("jwt-signature-invalid") from error

    if claims.get("iss") not in ACCEPTED_EVE_ISSUERS:
        raise SsoTokenError("jwt-claims-invalid")
    audience = claims.get("aud")
    if (
        not isinstance(audience, list)
        or any(not isinstance(item, str) for item in audience)
        or not {client_id, EXPECTED_EVE_AUDIENCE}.issubset(set(audience))
    ):
        raise SsoTokenError("jwt-claims-invalid")

    current_time = int((now or datetime.now(timezone.utc)).timestamp())
    if _integer_claim(claims, "exp") <= current_time - JWT_CLOCK_SKEW_SECONDS:
        raise SsoTokenError("jwt-expired")
    if "nbf" in claims and _integer_claim(claims, "nbf") > current_time + JWT_CLOCK_SKEW_SECONDS:
        raise SsoTokenError("jwt-claims-invalid")
    if "iat" in claims and _integer_claim(claims, "iat") > current_time + JWT_CLOCK_SKEW_SECONDS:
        raise SsoTokenError("jwt-claims-invalid")

    subject = claims.get("sub")
    subject_match = CHARACTER_SUBJECT.fullmatch(subject) if isinstance(subject, str) else None
    name = claims.get("name")
    if subject_match is None or not isinstance(name, str):
        raise SsoTokenError("jwt-identity-invalid")
    normalized_name = name.strip()
    if not 1 <= len(normalized_name) <= 100:
        raise SsoTokenError("jwt-identity-invalid")
    character_id = int(subject_match.group(1))
    if character_id > 9_007_199_254_740_991:
        raise SsoTokenError("jwt-identity-invalid")

    scopes = _validate_scopes(claims.get("scp"))
    normalized_expected = tuple(sorted(set(expected_scopes)))
    if not normalized_expected or not set(normalized_expected).issubset(scopes):
        raise SsoTokenError("jwt-scopes-missing")
    return VerifiedCharacter(character_id, normalized_name, scopes)


class EveSsoClient:
    """Exchange or refresh OAuth credentials and validate their EVE identity."""

    def __init__(
        self,
        client_id: str,
        *,
        request_json: JsonRequester = _default_json_request,
        monotonic: Callable[[], float] = time.monotonic,
        utc_now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if not isinstance(client_id, str) or not client_id.strip():
            raise ValueError("A public EVE SSO client ID is required.")
        self._client_id = client_id
        self._request_json = request_json
        self._monotonic = monotonic
        self._utc_now = utc_now
        self._metadata: EveSsoMetadata | None = None
        self._metadata_expires_at = 0.0
        self._lock = threading.Lock()

    def _load_metadata(self) -> EveSsoMetadata:
        with self._lock:
            now = self._monotonic()
            if self._metadata is not None and now < self._metadata_expires_at:
                return self._metadata
            try:
                payload = self._request_json("GET", SSO_METADATA_ENDPOINT, None, {})
            except SsoTokenError as error:
                raise SsoTokenError("sso-metadata-unavailable") from error
            issuer = payload.get("issuer")
            if issuer not in ACCEPTED_EVE_ISSUERS:
                raise SsoTokenError("sso-metadata-invalid")
            metadata = EveSsoMetadata(
                issuer=str(issuer),
                authorization_endpoint=_trusted_sso_url(payload.get("authorization_endpoint")),
                token_endpoint=_trusted_sso_url(payload.get("token_endpoint")),
                jwks_uri=_trusted_sso_url(payload.get("jwks_uri")),
            )
            self._metadata = metadata
            self._metadata_expires_at = now + METADATA_CACHE_SECONDS
            return metadata

    def exchange_and_validate(
        self,
        authorization_code: str,
        code_verifier: str,
        expected_scopes: Sequence[str],
    ) -> VerifiedAuthorization:
        if (
            not isinstance(authorization_code, str)
            or not 1 <= len(authorization_code) <= MAXIMUM_AUTHORIZATION_CODE_LENGTH
            or not PKCE_VALUE.fullmatch(code_verifier)
        ):
            raise SsoTokenError("token-request-invalid")
        metadata = self._load_metadata()
        try:
            token_payload = self._request_json(
                "POST",
                metadata.token_endpoint,
                {
                    "grant_type": "authorization_code",
                    "code": authorization_code,
                    "client_id": self._client_id,
                    "code_verifier": code_verifier,
                },
                {"Content-Type": "application/x-www-form-urlencoded"},
            )
        except SsoTokenError as error:
            raise SsoTokenError("token-exchange-failed") from error

        return self._validate_token_response(
            token_payload,
            metadata=metadata,
            expected_scopes=expected_scopes,
        )

    def refresh_and_validate(
        self,
        refresh_token: str,
        *,
        expected_character_id: int,
        expected_scopes: Sequence[str],
    ) -> VerifiedAuthorization:
        """Use a stored refresh token and reject cross-character responses."""

        if (
            not isinstance(refresh_token, str)
            or not 1 <= len(refresh_token.encode("utf-8")) <= MAXIMUM_REFRESH_TOKEN_LENGTH
            or refresh_token.strip() != refresh_token
            or "\x00" in refresh_token
            or isinstance(expected_character_id, bool)
            or not isinstance(expected_character_id, int)
            or expected_character_id <= 0
        ):
            raise SsoTokenError("refresh-request-invalid")
        metadata = self._load_metadata()
        try:
            token_payload = self._request_json(
                "POST",
                metadata.token_endpoint,
                {
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self._client_id,
                },
                {"Content-Type": "application/x-www-form-urlencoded"},
            )
        except SsoTokenError as error:
            raise SsoTokenError("refresh-exchange-failed") from error
        authorization = self._validate_token_response(
            token_payload,
            metadata=metadata,
            expected_scopes=expected_scopes,
        )
        if authorization.character.character_id != expected_character_id:
            raise SsoTokenError("refresh-character-mismatch")
        return authorization

    def _validate_token_response(
        self,
        token_payload: Mapping[str, object],
        *,
        metadata: EveSsoMetadata,
        expected_scopes: Sequence[str],
    ) -> VerifiedAuthorization:
        access_token = token_payload.get("access_token")
        refresh_token = token_payload.get("refresh_token")
        expires_in = token_payload.get("expires_in")
        token_type = token_payload.get("token_type")
        if (
            not isinstance(access_token, str)
            or not 1 <= len(access_token) <= MAXIMUM_ACCESS_TOKEN_LENGTH
            or not isinstance(refresh_token, str)
            or not 1 <= len(refresh_token.encode("utf-8")) <= MAXIMUM_REFRESH_TOKEN_LENGTH
            or refresh_token.strip() != refresh_token
            or "\x00" in refresh_token
            or isinstance(expires_in, bool)
            or not isinstance(expires_in, int)
            or not 1 <= expires_in <= 86_400
            or not isinstance(token_type, str)
            or token_type.casefold() != "bearer"
        ):
            raise SsoTokenError("token-response-invalid")
        try:
            jwks = self._request_json("GET", metadata.jwks_uri, None, {})
        except SsoTokenError as error:
            raise SsoTokenError("jwks-unavailable") from error
        now = self._utc_now()
        character = validate_access_token(
            access_token,
            jwks=jwks,
            client_id=self._client_id,
            expected_scopes=expected_scopes,
            now=now,
        )
        return VerifiedAuthorization(
            character=character,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=now + timedelta(seconds=expires_in),
        )
