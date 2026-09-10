"""Central, bounded EVE ESI HTTP client with cache and resilience policy."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import re
import time
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Final, Protocol

from .version import project_version


ESI_BASE_URL: Final = "https://esi.evetech.net"
ESI_COMPATIBILITY_DATE: Final = "2026-09-09"
ESI_USER_AGENT: Final = (
    f"New-Eden-Foundry/{project_version()} "
    "(+https://github.com/Savox76/eve-test-indu; contact: Savox76)"
)
TRANSIENT_STATUSES: Final = frozenset({408, 420, 425, 429, 500, 502, 503, 504})
DEFAULT_TIMEOUT_SECONDS: Final = 20.0
DEFAULT_MAX_ATTEMPTS: Final = 3
DEFAULT_ERROR_BUDGET_FLOOR: Final = 10
DEFAULT_CIRCUIT_FAILURE_THRESHOLD: Final = 3
DEFAULT_CIRCUIT_COOLDOWN_SECONDS: Final = 60.0
DEFAULT_MAX_RESPONSE_BYTES: Final = 8 * 1024 * 1024
MAX_RETRY_DELAY_SECONDS: Final = 30.0
_MAX_ERROR_BUDGET: Final = 100
_COMPATIBILITY_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CACHE_MAX_AGE = re.compile(r"(?:^|,)\s*max-age=(\d+)\s*(?:,|$)", re.IGNORECASE)


class EsiClientError(RuntimeError):
    """Sanitized failure safe to surface without request credentials or payloads."""

    def __init__(
        self,
        code: str,
        *,
        status: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
        self.retryable = retryable

    def __repr__(self) -> str:
        return (
            "EsiClientError("
            f"code={self.code!r}, status={self.status!r}, retryable={self.retryable!r})"
        )


@dataclass(frozen=True, slots=True)
class RawEsiResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


@dataclass(frozen=True, slots=True)
class EsiResponse:
    status: int
    payload: Any
    headers: Mapping[str, str]
    from_cache: bool


@dataclass(slots=True)
class _CacheEntry:
    payload: Any
    headers: dict[str, str]
    etag: str | None
    last_modified: str | None
    expires_at: float


class EsiTransport(Protocol):
    def __call__(
        self,
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> RawEsiResponse: ...


class EsiPostTransport(Protocol):
    def __call__(
        self,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
        timeout_seconds: float,
    ) -> RawEsiResponse: ...


TokenProvider = Callable[[int, Sequence[str]], str]


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(  # type: ignore[no-untyped-def]
        self,
        request,
        file_pointer,
        code,
        message,
        headers,
        new_url,
    ):
        raise urllib.error.HTTPError(
            request.full_url,
            code,
            "redirect-rejected",
            headers,
            file_pointer,
        )


def _default_transport(
    url: str,
    headers: Mapping[str, str],
    timeout_seconds: float,
) -> RawEsiResponse:
    request = urllib.request.Request(url, headers=dict(headers), method="GET")
    opener = urllib.request.build_opener(_RejectRedirects())
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            return RawEsiResponse(
                status=int(response.status),
                headers=dict(response.headers.items()),
                body=response.read(DEFAULT_MAX_RESPONSE_BYTES + 1),
            )
    except urllib.error.HTTPError as error:
        return RawEsiResponse(
            status=int(error.code),
            headers=dict(error.headers.items()) if error.headers is not None else {},
            body=error.read(DEFAULT_MAX_RESPONSE_BYTES + 1),
        )


def _default_post_transport(
    url: str,
    headers: Mapping[str, str],
    body: bytes,
    timeout_seconds: float,
) -> RawEsiResponse:
    request = urllib.request.Request(
        url, headers=dict(headers), data=body, method="POST"
    )
    opener = urllib.request.build_opener(_RejectRedirects())
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            return RawEsiResponse(
                status=int(response.status),
                headers=dict(response.headers.items()),
                body=response.read(DEFAULT_MAX_RESPONSE_BYTES + 1),
            )
    except urllib.error.HTTPError as error:
        return RawEsiResponse(
            status=int(error.code),
            headers=dict(error.headers.items()) if error.headers is not None else {},
            body=error.read(DEFAULT_MAX_RESPONSE_BYTES + 1),
        )


def _strict_json(payload: bytes) -> Any:
    def without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate-key")
            value[key] = item
        return value

    try:
        return json.loads(payload.decode("utf-8"), object_pairs_hook=without_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise EsiClientError("esi-response-invalid") from error


def _normalized_headers(headers: Mapping[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for name, value in headers.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise EsiClientError("esi-response-invalid")
        normalized[name.lower()] = value.strip()
    return normalized


class EsiClient:
    """Single ESI trust boundary for headers, caching, retries and throttling."""

    def __init__(
        self,
        token_provider: TokenProvider | None = None,
        *,
        transport: EsiTransport = _default_transport,
        post_transport: EsiPostTransport = _default_post_transport,
        compatibility_date: str = ESI_COMPATIBILITY_DATE,
        user_agent: str = ESI_USER_AGENT,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        error_budget_floor: int = DEFAULT_ERROR_BUDGET_FLOOR,
        circuit_failure_threshold: int = DEFAULT_CIRCUIT_FAILURE_THRESHOLD,
        circuit_cooldown_seconds: float = DEFAULT_CIRCUIT_COOLDOWN_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        monotonic: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        try:
            datetime.strptime(compatibility_date, "%Y-%m-%d")
        except (TypeError, ValueError) as error:
            raise ValueError("The ESI compatibility date must be YYYY-MM-DD.") from error
        if not _COMPATIBILITY_DATE.fullmatch(compatibility_date):
            raise ValueError("The ESI compatibility date must be YYYY-MM-DD.")
        if (
            not isinstance(user_agent, str)
            or not user_agent.strip()
            or user_agent.strip() != user_agent
            or len(user_agent) > 256
            or "\r" in user_agent
            or "\n" in user_agent
        ):
            raise ValueError("The ESI User-Agent is invalid.")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(float(timeout_seconds))
            or timeout_seconds <= 0
            or timeout_seconds > 120
        ):
            raise ValueError("The ESI timeout is out of bounds.")
        if (
            isinstance(max_attempts, bool)
            or not isinstance(max_attempts, int)
            or not 1 <= max_attempts <= 5
        ):
            raise ValueError("The ESI attempt count is out of bounds.")
        if (
            isinstance(error_budget_floor, bool)
            or not isinstance(error_budget_floor, int)
            or not 0 <= error_budget_floor <= 100
        ):
            raise ValueError("The ESI error-budget floor is out of bounds.")
        if (
            isinstance(circuit_failure_threshold, bool)
            or not isinstance(circuit_failure_threshold, int)
            or not 1 <= circuit_failure_threshold <= 20
            or isinstance(circuit_cooldown_seconds, bool)
            or not isinstance(circuit_cooldown_seconds, (int, float))
            or not math.isfinite(float(circuit_cooldown_seconds))
            or circuit_cooldown_seconds <= 0
            or circuit_cooldown_seconds > 900
        ):
            raise ValueError("The ESI circuit-breaker policy is out of bounds.")
        if (
            isinstance(max_response_bytes, bool)
            or not isinstance(max_response_bytes, int)
            or max_response_bytes < 1_024
            or max_response_bytes > DEFAULT_MAX_RESPONSE_BYTES
        ):
            raise ValueError("The ESI response limit is out of bounds.")

        self._token_provider = token_provider
        self._transport = transport
        self._post_transport = post_transport
        self._compatibility_date = compatibility_date
        self._user_agent = user_agent
        self._timeout_seconds = float(timeout_seconds)
        self._max_attempts = max_attempts
        self._error_budget_floor = error_budget_floor
        self._circuit_failure_threshold = circuit_failure_threshold
        self._circuit_cooldown_seconds = float(circuit_cooldown_seconds)
        self._max_response_bytes = max_response_bytes
        self._monotonic = monotonic
        self._wall_clock = wall_clock
        self._sleep = sleep
        self._jitter = jitter
        self._cache: dict[tuple[str, int | None], _CacheEntry] = {}
        self._lock = threading.RLock()
        self._budget_remaining = _MAX_ERROR_BUDGET
        self._budget_reset_at = 0.0
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0

    def status(self) -> dict[str, object]:
        with self._lock:
            now = self._monotonic()
            return {
                "state": "open" if now < self._circuit_open_until else "ready",
                "compatibilityDate": self._compatibility_date,
                "errorBudgetRemaining": self._budget_remaining,
                "errorBudgetResetSeconds": max(0, round(self._budget_reset_at - now)),
                "cachedResources": len(self._cache),
            }

    def invalidate(self, *, character_id: int | None = None) -> None:
        if character_id is None:
            with self._lock:
                self._cache.clear()
            return
        if isinstance(character_id, bool) or not isinstance(character_id, int) or character_id <= 0:
            raise ValueError("The character ID must be a positive integer.")
        with self._lock:
            self._cache = {
                key: value for key, value in self._cache.items() if key[1] != character_id
            }

    def get_json(
        self,
        path: str,
        *,
        query: Mapping[str, str | int | Sequence[str | int]] | None = None,
        character_id: int | None = None,
        required_scopes: Sequence[str] = (),
    ) -> EsiResponse:
        url = self._build_url(path, query)
        try:
            scopes = tuple(sorted(set(required_scopes)))
        except TypeError as error:
            raise EsiClientError("esi-auth-request-invalid") from error
        if character_id is None:
            if scopes:
                raise EsiClientError("esi-auth-request-invalid")
        elif (
            isinstance(character_id, bool)
            or not isinstance(character_id, int)
            or character_id <= 0
            or not scopes
            or any(
                not isinstance(scope, str)
                or not scope.startswith("esi-")
                or not scope.endswith(".v1")
                or len(scope) > 200
                for scope in scopes
            )
            or self._token_provider is None
        ):
            raise EsiClientError("esi-auth-request-invalid")

        cache_key = (url, character_id)
        now = self._monotonic()
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached is not None and cached.expires_at > now:
                return EsiResponse(
                    status=200,
                    payload=copy.deepcopy(cached.payload),
                    headers=dict(cached.headers),
                    from_cache=True,
                )

        token = None
        if character_id is not None:
            try:
                token = self._token_provider(character_id, scopes)  # type: ignore[misc]
            except Exception as error:
                raise EsiClientError("esi-access-token-unavailable") from error
            if (
                not isinstance(token, str)
                or not token
                or any(character.isspace() for character in token)
                or len(token) > 8_192
            ):
                raise EsiClientError("esi-access-token-invalid")

        headers = {
            "Accept": "application/json",
            "User-Agent": self._user_agent,
            "X-Compatibility-Date": self._compatibility_date,
        }
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if cached is not None:
            if cached.etag:
                headers["If-None-Match"] = cached.etag
            if cached.last_modified:
                headers["If-Modified-Since"] = cached.last_modified

        last_status: int | None = None
        for attempt in range(self._max_attempts):
            self._before_request()
            try:
                raw = self._transport(url, headers, self._timeout_seconds)
            except Exception:
                self._record_transient_failure()
                if attempt + 1 == self._max_attempts:
                    raise EsiClientError("esi-network-unavailable", retryable=True)
                self._sleep(self._retry_delay(attempt, {}))
                continue

            if (
                not isinstance(raw, RawEsiResponse)
                or isinstance(raw.status, bool)
                or not isinstance(raw.status, int)
                or not 100 <= raw.status <= 599
                or not isinstance(raw.headers, Mapping)
                or not isinstance(raw.body, bytes)
                or len(raw.body) > self._max_response_bytes
            ):
                self._record_terminal_failure()
                raise EsiClientError("esi-response-invalid")
            response_headers = _normalized_headers(raw.headers)
            self._update_error_budget(response_headers)
            last_status = raw.status

            if raw.status == 304:
                if cached is None:
                    self._record_terminal_failure()
                    raise EsiClientError("esi-cache-miss", status=304)
                with self._lock:
                    cached.expires_at = self._cache_expiry(response_headers, now)
                    cached.headers.update(response_headers)
                    payload = copy.deepcopy(cached.payload)
                    cached_headers = dict(cached.headers)
                self._record_success()
                return EsiResponse(
                    status=200,
                    payload=payload,
                    headers=cached_headers,
                    from_cache=True,
                )

            if 200 <= raw.status < 300:
                payload = _strict_json(raw.body)
                entry = _CacheEntry(
                    payload=copy.deepcopy(payload),
                    headers=dict(response_headers),
                    etag=response_headers.get("etag"),
                    last_modified=response_headers.get("last-modified"),
                    expires_at=self._cache_expiry(response_headers, self._monotonic()),
                )
                if "no-store" not in response_headers.get("cache-control", "").lower():
                    with self._lock:
                        self._cache[cache_key] = entry
                self._record_success()
                return EsiResponse(
                    status=raw.status,
                    payload=payload,
                    headers=dict(response_headers),
                    from_cache=False,
                )

            if raw.status not in TRANSIENT_STATUSES:
                self._record_terminal_failure()
                raise EsiClientError(
                    "esi-request-rejected",
                    status=raw.status,
                    retryable=False,
                )

            self._record_transient_failure()
            if attempt + 1 == self._max_attempts:
                break
            self._sleep(self._retry_delay(attempt, response_headers))

        raise EsiClientError(
            "esi-retry-exhausted",
            status=last_status,
            retryable=True,
        )

    def post_json(self, path: str, payload: Any) -> EsiResponse:
        """Send a bounded unauthenticated JSON POST through the same ESI policy."""
        url = self._build_url(path, None)
        try:
            body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise EsiClientError("esi-request-payload-invalid") from error
        if not body or len(body) > 256_000:
            raise EsiClientError("esi-request-payload-invalid")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": self._user_agent,
            "X-Compatibility-Date": self._compatibility_date,
        }
        cache_key = (
            f"POST {url} {hashlib.sha256(body).hexdigest()}",
            None,
        )
        now = self._monotonic()
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached is not None and cached.expires_at > now:
                return EsiResponse(
                    200,
                    copy.deepcopy(cached.payload),
                    dict(cached.headers),
                    True,
                )

        last_status: int | None = None
        for attempt in range(self._max_attempts):
            self._before_request()
            try:
                raw = self._post_transport(url, headers, body, self._timeout_seconds)
            except Exception:
                self._record_transient_failure()
                if attempt + 1 == self._max_attempts:
                    raise EsiClientError("esi-network-unavailable", retryable=True)
                self._sleep(self._retry_delay(attempt, {}))
                continue
            if (
                not isinstance(raw, RawEsiResponse)
                or isinstance(raw.status, bool)
                or not isinstance(raw.status, int)
                or not 100 <= raw.status <= 599
                or not isinstance(raw.headers, Mapping)
                or not isinstance(raw.body, bytes)
                or len(raw.body) > self._max_response_bytes
            ):
                self._record_terminal_failure()
                raise EsiClientError("esi-response-invalid")
            response_headers = _normalized_headers(raw.headers)
            self._update_error_budget(response_headers)
            last_status = raw.status
            if 200 <= raw.status < 300:
                parsed = _strict_json(raw.body)
                if "no-store" not in response_headers.get("cache-control", "").lower():
                    with self._lock:
                        self._cache[cache_key] = _CacheEntry(
                            copy.deepcopy(parsed),
                            dict(response_headers),
                            None,
                            None,
                            self._cache_expiry(response_headers, self._monotonic()),
                        )
                self._record_success()
                return EsiResponse(
                    raw.status, parsed, dict(response_headers), False
                )
            if raw.status not in TRANSIENT_STATUSES:
                self._record_terminal_failure()
                raise EsiClientError(
                    "esi-request-rejected", status=raw.status, retryable=False
                )
            self._record_transient_failure()
            if attempt + 1 == self._max_attempts:
                break
            self._sleep(self._retry_delay(attempt, response_headers))
        raise EsiClientError(
            "esi-retry-exhausted", status=last_status, retryable=True
        )

    def _build_url(
        self,
        path: str,
        query: Mapping[str, str | int | Sequence[str | int]] | None,
    ) -> str:
        if (
            not isinstance(path, str)
            or not path.startswith("/")
            or path.startswith("//")
            or "?" in path
            or "#" in path
            or "\r" in path
            or "\n" in path
        ):
            raise EsiClientError("esi-path-invalid")
        encoded_query = ""
        if query:
            try:
                pairs: list[tuple[str, str | int]] = []
                for key, value in query.items():
                    if not isinstance(key, str) or not key or len(key) > 100:
                        raise ValueError
                    values = value if isinstance(value, (tuple, list)) else (value,)
                    for item in values:
                        if isinstance(item, bool) or not isinstance(item, (str, int)):
                            raise ValueError
                        pairs.append((key, item))
                encoded_query = urllib.parse.urlencode(pairs)
            except (AttributeError, TypeError, ValueError) as error:
                raise EsiClientError("esi-query-invalid") from error
        return f"{ESI_BASE_URL}{path}" + (f"?{encoded_query}" if encoded_query else "")

    def _before_request(self) -> None:
        with self._lock:
            now = self._monotonic()
            if now < self._circuit_open_until:
                raise EsiClientError("esi-circuit-open", retryable=True)
            if self._budget_reset_at and now >= self._budget_reset_at:
                self._budget_remaining = _MAX_ERROR_BUDGET
                self._budget_reset_at = 0.0
            if self._budget_remaining < self._error_budget_floor:
                raise EsiClientError("esi-error-budget-exhausted", retryable=True)

    def _update_error_budget(self, headers: Mapping[str, str]) -> None:
        remaining = headers.get("x-esi-error-limit-remain")
        reset = headers.get("x-esi-error-limit-reset")
        if remaining is None and reset is None:
            return
        with self._lock:
            try:
                parsed_remaining = (
                    int(remaining) if remaining is not None else self._budget_remaining
                )
                parsed_reset = int(reset) if reset is not None else 0
            except ValueError as error:
                raise EsiClientError("esi-response-invalid") from error
            if not 0 <= parsed_remaining <= _MAX_ERROR_BUDGET or not 0 <= parsed_reset <= 3_600:
                raise EsiClientError("esi-response-invalid")
            self._budget_remaining = parsed_remaining
            self._budget_reset_at = self._monotonic() + parsed_reset if parsed_reset else 0.0

    def _record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            self._circuit_open_until = 0.0

    def _record_terminal_failure(self) -> None:
        with self._lock:
            self._consecutive_failures = 0

    def _record_transient_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._circuit_failure_threshold:
                self._circuit_open_until = (
                    self._monotonic() + self._circuit_cooldown_seconds
                )

    def _retry_delay(self, attempt: int, headers: Mapping[str, str]) -> float:
        retry_after = headers.get("retry-after")
        if retry_after is not None:
            try:
                parsed_seconds = float(retry_after)
                if not math.isfinite(parsed_seconds):
                    raise ValueError
                return min(MAX_RETRY_DELAY_SECONDS, max(0.0, parsed_seconds))
            except ValueError:
                try:
                    parsed = parsedate_to_datetime(retry_after)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    seconds = parsed.timestamp() - self._wall_clock()
                    return min(MAX_RETRY_DELAY_SECONDS, max(0.0, seconds))
                except (TypeError, ValueError, OverflowError):
                    pass
        return min(
            MAX_RETRY_DELAY_SECONDS,
            (0.25 * (2**attempt)) + max(0.0, min(1.0, self._jitter())) * 0.25,
        )

    def _cache_expiry(self, headers: Mapping[str, str], now: float) -> float:
        cache_control = headers.get("cache-control", "")
        match = _CACHE_MAX_AGE.search(cache_control)
        if match is not None:
            return now + int(match.group(1))
        expires = headers.get("expires")
        if expires is not None:
            try:
                parsed = parsedate_to_datetime(expires)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return now + max(0.0, parsed.timestamp() - self._wall_clock())
            except (TypeError, ValueError, OverflowError):
                return now
        return now
