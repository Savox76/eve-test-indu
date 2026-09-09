"""Authenticated loopback sidecar for the local desktop application."""

from __future__ import annotations

import json
import secrets
import socket
import sys
import threading
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TextIO

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .appearance import appearance_payload, read_font_scale, set_font_scale
from .database import DatabaseStatus, connect_database, initialize_database
from .identity import list_characters, upsert_character
from .storage import ProgramStorage, ProgramStorageError, prepare_program_storage
from .startup_state import StartupDataState, inspect_startup_data_state
from .sso_registration import (
    SsoRegistrationProfile,
    load_bundled_sso_registration_profile,
)
from .sso_pkce import SsoPkceError, SsoPkceManager
from .sso_tokens import VerifiedCharacter
from .updater import (
    UpdateChannel,
    UpdateManifestError,
    read_update_channel,
    set_update_channel,
    verify_bundled_test_manifest,
)
from .version import project_version


PROTOCOL_VERSION: Final = 1
LOOPBACK_HOST: Final = "127.0.0.1"
MINIMUM_SESSION_TOKEN_LENGTH: Final = 64
MAXIMUM_SESSION_TOKEN_LENGTH: Final = 512
MAXIMUM_STARTUP_MESSAGE_LENGTH: Final = 16_384


class StartupProtocolError(ValueError):
    """Raised when the trusted parent sends an invalid startup message."""


@dataclass(frozen=True, slots=True)
class StartupConfiguration:
    protocol: int
    session_token: str
    program_directory: Path


def parse_startup_configuration(raw_message: str) -> StartupConfiguration:
    if not raw_message or len(raw_message) > MAXIMUM_STARTUP_MESSAGE_LENGTH:
        raise StartupProtocolError("The startup message has an invalid length.")

    try:
        payload = json.loads(raw_message)
    except json.JSONDecodeError as error:
        raise StartupProtocolError("The startup message is not valid JSON.") from error

    if not isinstance(payload, dict) or set(payload) != {
        "protocol",
        "sessionToken",
        "programDirectory",
    }:
        raise StartupProtocolError("The startup message has unexpected fields.")

    protocol = payload["protocol"]
    session_token = payload["sessionToken"]
    program_directory_value = payload["programDirectory"]
    if isinstance(protocol, bool) or protocol != PROTOCOL_VERSION:
        raise StartupProtocolError("The startup protocol version is unsupported.")
    if (
        not isinstance(session_token, str)
        or not MINIMUM_SESSION_TOKEN_LENGTH <= len(session_token) <= MAXIMUM_SESSION_TOKEN_LENGTH
        or session_token.strip() != session_token
        or any(character.isspace() for character in session_token)
    ):
        raise StartupProtocolError("The session token is invalid.")
    if not isinstance(program_directory_value, str) or not program_directory_value.strip():
        raise StartupProtocolError("The program directory is invalid.")

    program_directory = Path(program_directory_value)
    if not program_directory.is_absolute():
        raise StartupProtocolError("The program directory must be absolute.")

    return StartupConfiguration(
        protocol=protocol,
        session_token=session_token,
        program_directory=program_directory,
    )


def read_startup_configuration(stream: TextIO) -> StartupConfiguration:
    raw_message = stream.readline(MAXIMUM_STARTUP_MESSAGE_LENGTH + 1)
    if len(raw_message) > MAXIMUM_STARTUP_MESSAGE_LENGTH:
        raise StartupProtocolError("The startup message is too long.")
    return parse_startup_configuration(raw_message)


def is_authorized(authorization_header: str | None, session_token: str) -> bool:
    if not isinstance(authorization_header, str):
        return False
    expected = f"Bearer {session_token}"
    return secrets.compare_digest(authorization_header, expected)


def store_verified_character(database_path: Path, identity: VerifiedCharacter) -> None:
    """Persist only an identity that already passed EVE JWT validation."""

    with closing(connect_database(database_path)) as connection:
        existing = next(
            (
                character
                for character in list_characters(connection)
                if character.character_id == identity.character_id
            ),
            None,
        )
        upsert_character(
            connection,
            character_id=identity.character_id,
            name=identity.name,
            account_group_id=(existing.account_group_id if existing is not None else None),
            scopes=identity.scopes,
            enabled=True,
        )


def create_application(
    startup: StartupConfiguration,
    storage: ProgramStorage,
    database: DatabaseStatus,
    data_state: StartupDataState,
    manifest_state: str,
    sso_registration: SsoRegistrationProfile,
    sso_login: SsoPkceManager,
) -> FastAPI:
    app = FastAPI(
        title="New Eden Foundry local core",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.middleware("http")
    async def require_session_token(request: Request, call_next):  # type: ignore[no-untyped-def]
        if not is_authorized(request.headers.get("authorization"), startup.session_token):
            return JSONResponse(
                status_code=401,
                content={"detail": "A valid local session token is required."},
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await call_next(request)

    @app.get("/health")
    async def health() -> dict[str, object]:
        with closing(connect_database(storage.database_path)) as connection:
            selected_channel = read_update_channel(connection)
            font_scale = read_font_scale(connection)
            character_count = len(list_characters(connection))
        return {
            "service": "new-eden-foundry-core",
            "state": "ready",
            "version": project_version(),
            "protocol": PROTOCOL_VERSION,
            "database": {
                "state": "ready",
                "schemaVersion": database.schema_version,
                "integrity": database.integrity,
                "location": storage.relative_database_path.as_posix(),
                "lastMigrationBackup": database.last_migration_backup,
            },
            "data": data_state.as_api_payload(),
            "updater": {
                "channel": selected_channel.value,
                "manifestState": manifest_state,
                "publicDistribution": False,
            },
            "appearance": appearance_payload(font_scale),
            "characters": {"connected": character_count},
            "ssoRegistration": sso_registration.as_status_payload(),
        }

    @app.get("/settings/update")
    async def get_update_settings() -> dict[str, object]:
        with closing(connect_database(storage.database_path)) as connection:
            selected_channel = read_update_channel(connection)
        return {
            "channel": selected_channel.value,
            "manifestState": manifest_state,
            "publicDistribution": False,
        }

    @app.put("/settings/update")
    async def put_update_settings(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                status_code=422,
                content={"detail": "The update-channel request is invalid."},
            )
        if not isinstance(payload, dict) or set(payload) != {"channel"}:
            return JSONResponse(
                status_code=422,
                content={"detail": "The update-channel request is invalid."},
            )
        try:
            with closing(connect_database(storage.database_path)) as connection:
                selected_channel = set_update_channel(connection, payload["channel"])
        except (TypeError, ValueError):
            return JSONResponse(
                status_code=422,
                content={"detail": "The selected update channel is unsupported."},
            )
        return JSONResponse(
            content={
                "channel": selected_channel.value,
                "manifestState": manifest_state,
                "publicDistribution": False,
            }
        )

    @app.get("/settings/appearance")
    async def get_appearance_settings() -> dict[str, str]:
        with closing(connect_database(storage.database_path)) as connection:
            return appearance_payload(read_font_scale(connection))

    @app.put("/settings/appearance")
    async def put_appearance_settings(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                status_code=422,
                content={"detail": "The appearance request is invalid."},
            )
        if not isinstance(payload, dict) or set(payload) != {"fontScale"}:
            return JSONResponse(
                status_code=422,
                content={"detail": "The appearance request is invalid."},
            )
        try:
            with closing(connect_database(storage.database_path)) as connection:
                font_scale = set_font_scale(connection, payload["fontScale"])
        except (TypeError, ValueError):
            return JSONResponse(
                status_code=422,
                content={"detail": "The selected font scale is unsupported."},
            )
        return JSONResponse(content=appearance_payload(font_scale))

    @app.get("/characters")
    async def get_characters() -> dict[str, object]:
        with closing(connect_database(storage.database_path)) as connection:
            characters = list_characters(connection)
        return {"characters": [character.as_api_payload() for character in characters]}

    @app.get("/sso/login")
    async def get_sso_login() -> dict[str, object]:
        return sso_login.status()

    @app.post("/sso/login")
    async def start_sso_login(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                status_code=422,
                content={"detail": "The SSO login request is invalid."},
            )
        if not isinstance(payload, dict) or set(payload) != {"scopePackages"}:
            return JSONResponse(
                status_code=422,
                content={"detail": "The SSO login request is invalid."},
            )
        try:
            authorization_url, status = sso_login.start(payload["scopePackages"])
        except SsoPkceError as error:
            status_code = 409 if error.code in {
                "login-already-active",
                "callback-unavailable",
            } else 422
            return JSONResponse(status_code=status_code, content={"detail": error.code})
        return JSONResponse(content={"authorizationUrl": authorization_url, "status": status})

    @app.delete("/sso/login")
    async def cancel_sso_login() -> dict[str, object]:
        return sso_login.cancel()

    return app


def _emit_event(stream: TextIO, payload: dict[str, object]) -> None:
    stream.write(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n")
    stream.flush()


def _monitor_parent(stream: TextIO, server: uvicorn.Server) -> None:
    for raw_message in stream:
        try:
            message = json.loads(raw_message)
        except json.JSONDecodeError:
            continue
        if isinstance(message, dict) and message.get("command") == "shutdown":
            server.should_exit = True
            return
    server.should_exit = True


def run_sidecar(input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout) -> int:
    try:
        startup = read_startup_configuration(input_stream)
    except StartupProtocolError:
        _emit_event(output_stream, {"event": "error", "code": "invalid-startup"})
        return 2

    try:
        storage = prepare_program_storage(startup.program_directory)
    except ProgramStorageError:
        _emit_event(output_stream, {"event": "error", "code": "program-storage-unavailable"})
        return 3

    try:
        database = initialize_database(
            storage.database_path,
            backup_directory=storage.backup_directory,
        )
        with closing(connect_database(storage.database_path)) as connection:
            data_state = inspect_startup_data_state(connection)
            update_channel = read_update_channel(connection)
            font_scale = read_font_scale(connection)
    except Exception:
        _emit_event(output_stream, {"event": "error", "code": "database-startup-failed"})
        return 4

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((LOOPBACK_HOST, 0))
        listener.listen(128)
        port = int(listener.getsockname()[1])
    except OSError:
        listener.close()
        _emit_event(output_stream, {"event": "error", "code": "loopback-bind-failed"})
        return 5

    try:
        verify_bundled_test_manifest()
        manifest_state = "verified"
    except UpdateManifestError:
        manifest_state = "invalid"

    sso_registration = load_bundled_sso_registration_profile()
    try:
        sso_login = SsoPkceManager(
            sso_registration,
            identity_handler=lambda identity: store_verified_character(
                storage.database_path,
                identity,
            ),
        )
    except SsoPkceError:
        listener.close()
        _emit_event(output_stream, {"event": "error", "code": "sso-not-registered"})
        return 6

    application = create_application(
        startup,
        storage,
        database,
        data_state,
        manifest_state,
        sso_registration,
        sso_login,
    )
    server = uvicorn.Server(
        uvicorn.Config(
            application,
            host=LOOPBACK_HOST,
            port=port,
            access_log=False,
            log_config=None,
            log_level="critical",
            loop="asyncio",
            http="h11",
            lifespan="off",
        )
    )
    monitor = threading.Thread(
        target=_monitor_parent,
        args=(input_stream, server),
        name="foundry-parent-monitor",
        daemon=True,
    )
    monitor.start()

    _emit_event(
        output_stream,
        {
            "event": "ready",
            "protocol": PROTOCOL_VERSION,
            "host": LOOPBACK_HOST,
            "port": port,
            "database": {
                "state": "ready",
                "schemaVersion": database.schema_version,
                "location": storage.relative_database_path.as_posix(),
                "lastMigrationBackup": database.last_migration_backup,
            },
            "data": data_state.as_api_payload(),
            "updater": {
                "channel": update_channel.value,
                "manifestState": manifest_state,
                "publicDistribution": False,
            },
            "appearance": appearance_payload(font_scale),
            "ssoRegistration": sso_registration.as_status_payload(),
        },
    )

    try:
        server.run(sockets=[listener])
    finally:
        sso_login.close()
        listener.close()
    return 0


def main() -> int:
    return run_sidecar()


if __name__ == "__main__":
    raise SystemExit(main())
