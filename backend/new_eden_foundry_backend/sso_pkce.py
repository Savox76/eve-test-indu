"""Short-lived EVE SSO authorization flow for the desktop application.

WP12 intentionally stops after a verified authorization callback. The one-time
authorization code and PKCE verifier are discarded until WP13 can exchange the
code and validate the returned JWT before any character identity is trusted.
"""

from __future__ import annotations

import base64
import hashlib
import html
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Final
from urllib.parse import parse_qsl, urlencode, urlsplit

from .sso_registration import (
    SSO_CALLBACK_HOST,
    SSO_CALLBACK_PATH,
    SSO_CALLBACK_PORT,
    SsoRegistrationProfile,
)


SSO_AUTHORIZATION_ENDPOINT: Final = "https://login.eveonline.com/v2/oauth/authorize"
PKCE_LOGIN_TIMEOUT_SECONDS: Final = 180
MAXIMUM_CALLBACK_TARGET_LENGTH: Final = 8_192
MAXIMUM_AUTHORIZATION_CODE_LENGTH: Final = 4_096
TERMINAL_STATES: Final = frozenset(
    {"authorization-received", "cancelled", "timed-out", "failed"}
)


class SsoPkceError(RuntimeError):
    """Raised when a PKCE attempt cannot be started safely."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(slots=True)
class _Attempt:
    attempt_id: str
    state_secret: str | None
    code_verifier: str | None
    scope_packages: tuple[str, ...]
    started_at: datetime
    expires_at: datetime
    state: str = "waiting"
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class CallbackResult:
    status_code: int
    title: str
    detail: str


class _CallbackServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def generate_pkce_pair() -> tuple[str, str]:
    """Return a fresh RFC 7636 verifier and its S256 challenge."""

    verifier = _base64url(secrets.token_bytes(32))
    challenge = _base64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def generate_state() -> str:
    """Return an independent 256-bit CSRF binding value."""

    return _base64url(secrets.token_bytes(32))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso8601(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class SsoPkceManager:
    """Own exactly one transient browser authorization attempt at a time."""

    def __init__(
        self,
        profile: SsoRegistrationProfile,
        *,
        callback_host: str = SSO_CALLBACK_HOST,
        callback_port: int = SSO_CALLBACK_PORT,
        callback_path: str = SSO_CALLBACK_PATH,
        timeout_seconds: float = PKCE_LOGIN_TIMEOUT_SECONDS,
    ) -> None:
        if not profile.is_registered or profile.client_id is None:
            raise SsoPkceError("sso-not-registered")
        if callback_host != SSO_CALLBACK_HOST or not 0 <= callback_port <= 65_535:
            raise ValueError("The callback listener must use the IPv4 loopback interface.")
        if not callback_path.startswith("/") or "?" in callback_path or "#" in callback_path:
            raise ValueError("The callback path is invalid.")
        if timeout_seconds <= 0:
            raise ValueError("The login timeout must be positive.")

        self._profile = profile
        self._callback_host = callback_host
        self._callback_port = callback_port
        self._callback_path = callback_path
        self._timeout_seconds = timeout_seconds
        self._lock = threading.RLock()
        self._attempt: _Attempt | None = None
        self._server: _CallbackServer | None = None
        self._timer: threading.Timer | None = None

    def _callback_uri(self, bound_port: int) -> str:
        if bound_port == SSO_CALLBACK_PORT:
            return self._profile.redirect_uri
        return f"http://{self._callback_host}:{bound_port}{self._callback_path}"

    def _handler_type(self, attempt_id: str) -> type[BaseHTTPRequestHandler]:
        manager = self

        class CallbackHandler(BaseHTTPRequestHandler):
            server_version = "NewEdenFoundryCallback/1"
            sys_version = ""

            def log_message(self, _format: str, *_args: object) -> None:
                return

            def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
                if len(self.path) > MAXIMUM_CALLBACK_TARGET_LENGTH:
                    self._respond(414, "Ungültiger Rückruf", "Die Rückrufadresse ist zu lang.")
                    return
                parsed = urlsplit(self.path)
                expected_host = f"{SSO_CALLBACK_HOST}:{self.server.server_address[1]}"
                if self.headers.get("Host") != expected_host:
                    self._respond(400, "Ungültiger Rückruf", "Der Rückruf-Host stimmt nicht.")
                    return
                if parsed.path != manager._callback_path:
                    self._respond(404, "Nicht gefunden", "Dieser lokale Pfad ist nicht verfügbar.")
                    return
                result = manager.accept_callback(attempt_id, parsed.query)
                self._respond(result.status_code, result.title, result.detail)

            def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
                self._respond(405, "Nicht unterstützt", "Für diesen Rückruf ist GET erforderlich.")

            def _respond(self, status_code: int, title: str, detail: str) -> None:
                document = (
                    "<!doctype html><html lang=\"de\"><head><meta charset=\"utf-8\">"
                    "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
                    f"<title>{html.escape(title)}</title></head><body>"
                    f"<main><h1>{html.escape(title)}</h1><p>{html.escape(detail)}</p>"
                    "<p>Dieses Fenster kann jetzt geschlossen werden.</p></main></body></html>"
                ).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(document)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Pragma", "no-cache")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Security-Policy", "default-src 'none'; base-uri 'none'")
                self.end_headers()
                self.wfile.write(document)

        return CallbackHandler

    def start(self, scope_packages: list[str]) -> tuple[str, dict[str, object]]:
        if (
            not isinstance(scope_packages, list)
            or not scope_packages
            or not all(isinstance(name, str) for name in scope_packages)
        ):
            raise SsoPkceError("invalid-scope-packages")
        selected_packages = tuple(scope_packages)
        if len(set(selected_packages)) != len(selected_packages) or any(
            name not in self._profile.scope_packages for name in selected_packages
        ):
            raise SsoPkceError("invalid-scope-packages")

        with self._lock:
            self._expire_if_needed_locked()
            if self._attempt is not None and self._attempt.state == "waiting":
                raise SsoPkceError("login-already-active")

            attempt_id = secrets.token_urlsafe(18)
            state_secret = generate_state()
            code_verifier, code_challenge = generate_pkce_pair()
            now = _utc_now()
            attempt = _Attempt(
                attempt_id=attempt_id,
                state_secret=state_secret,
                code_verifier=code_verifier,
                scope_packages=selected_packages,
                started_at=now,
                expires_at=now + timedelta(seconds=self._timeout_seconds),
            )
            try:
                server = _CallbackServer(
                    (self._callback_host, self._callback_port),
                    self._handler_type(attempt_id),
                )
            except OSError as error:
                attempt.state_secret = None
                attempt.code_verifier = None
                raise SsoPkceError("callback-unavailable") from error

            bound_port = int(server.server_address[1])
            callback_uri = self._callback_uri(bound_port)
            scopes = tuple(
                scope
                for package_name in selected_packages
                for scope in self._profile.scope_packages[package_name]
            )
            parameters = {
                "response_type": "code",
                "client_id": self._profile.client_id,
                "redirect_uri": callback_uri,
                "scope": " ".join(scopes),
                "state": state_secret,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
            authorization_url = f"{SSO_AUTHORIZATION_ENDPOINT}?{urlencode(parameters)}"

            self._detach_server_locked()
            self._attempt = attempt
            self._server = server
            timer = threading.Timer(self._timeout_seconds, self._expire, args=(attempt_id,))
            timer.daemon = True
            self._timer = timer
            thread = threading.Thread(
                target=server.serve_forever,
                name="foundry-sso-callback",
                daemon=True,
            )
            thread.start()
            timer.start()
            return authorization_url, self._status_locked()

    def status(self) -> dict[str, object]:
        with self._lock:
            self._expire_if_needed_locked()
            return self._status_locked()

    def cancel(self) -> dict[str, object]:
        with self._lock:
            self._expire_if_needed_locked()
            if self._attempt is None:
                return self._status_locked()
            if self._attempt.state == "waiting":
                self._finish_locked("cancelled")
            return self._status_locked()

    def accept_callback(self, attempt_id: str, query: str) -> CallbackResult:
        parameters: dict[str, list[str]] = {}
        try:
            for key, value in parse_qsl(query, keep_blank_values=True, strict_parsing=True):
                parameters.setdefault(key, []).append(value)
        except ValueError:
            return CallbackResult(400, "Ungültiger Rückruf", "Die Antwort war nicht lesbar.")

        with self._lock:
            self._expire_if_needed_locked()
            attempt = self._attempt
            if attempt is None or attempt.attempt_id != attempt_id or attempt.state != "waiting":
                return CallbackResult(410, "Anmeldung beendet", "Dieser Versuch ist nicht mehr aktiv.")

            states = parameters.get("state", [])
            if (
                len(states) != 1
                or not states[0]
                or attempt.state_secret is None
                or not secrets.compare_digest(states[0], attempt.state_secret)
            ):
                return CallbackResult(400, "Sicherheitsprüfung fehlgeschlagen", "Der state-Wert stimmt nicht.")

            errors = parameters.get("error", [])
            codes = parameters.get("code", [])
            if len(errors) == 1 and errors[0] and not codes:
                error_code = "authorization-denied" if errors[0] == "access_denied" else "authorization-failed"
                self._finish_locked("failed", error_code)
                return CallbackResult(400, "Anmeldung nicht abgeschlossen", "EVE SSO hat keine Freigabe erteilt.")
            if (
                errors
                or len(codes) != 1
                or not codes[0]
                or len(codes[0]) > MAXIMUM_AUTHORIZATION_CODE_LENGTH
            ):
                self._finish_locked("failed", "callback-invalid")
                return CallbackResult(400, "Ungültiger Rückruf", "Der Autorisierungscode fehlt oder ist ungültig.")

            # WP12 verifies the browser response but deliberately does not retain the
            # one-time code. WP13 will perform exchange + JWT validation atomically.
            _authorization_code = codes[0]
            self._finish_locked("authorization-received")
            return CallbackResult(
                200,
                "EVE-Autorisierung empfangen",
                "New Eden Foundry hat den sicheren Browser-Rückruf bestätigt.",
            )

    def close(self) -> None:
        server: _CallbackServer | None
        timer: threading.Timer | None
        with self._lock:
            if self._attempt is not None and self._attempt.state == "waiting":
                self._attempt.state = "cancelled"
                self._attempt.state_secret = None
                self._attempt.code_verifier = None
            server, timer = self._detach_server_locked()
        if timer is not None:
            timer.cancel()
        if server is not None:
            server.shutdown()
            server.server_close()

    def _expire(self, attempt_id: str) -> None:
        with self._lock:
            if (
                self._attempt is not None
                and self._attempt.attempt_id == attempt_id
                and self._attempt.state == "waiting"
            ):
                self._finish_locked("timed-out", "login-timeout")

    def _expire_if_needed_locked(self) -> None:
        if (
            self._attempt is not None
            and self._attempt.state == "waiting"
            and _utc_now() >= self._attempt.expires_at
        ):
            self._finish_locked("timed-out", "login-timeout")

    def _finish_locked(self, state: str, error_code: str | None = None) -> None:
        if state not in TERMINAL_STATES or self._attempt is None:
            raise RuntimeError("Invalid terminal SSO state.")
        self._attempt.state = state
        self._attempt.error_code = error_code
        self._attempt.state_secret = None
        self._attempt.code_verifier = None
        server, timer = self._detach_server_locked()
        if timer is not None:
            timer.cancel()
        if server is not None:
            threading.Thread(
                target=self._shutdown_server,
                args=(server,),
                name="foundry-sso-callback-stop",
                daemon=True,
            ).start()

    def _detach_server_locked(
        self,
    ) -> tuple[_CallbackServer | None, threading.Timer | None]:
        server = self._server
        timer = self._timer
        self._server = None
        self._timer = None
        return server, timer

    @staticmethod
    def _shutdown_server(server: _CallbackServer) -> None:
        server.shutdown()
        server.server_close()

    def _status_locked(self) -> dict[str, object]:
        if self._attempt is None:
            return {
                "state": "idle",
                "attemptId": None,
                "scopePackages": [],
                "expiresAt": None,
                "errorCode": None,
            }
        return {
            "state": self._attempt.state,
            "attemptId": self._attempt.attempt_id,
            "scopePackages": list(self._attempt.scope_packages),
            "expiresAt": _iso8601(self._attempt.expires_at),
            "errorCode": self._attempt.error_code,
        }
