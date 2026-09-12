"""Authenticated loopback sidecar for the local desktop application."""

from __future__ import annotations

import json
import secrets
import socket
import sqlite3
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
from .asset_delta import (
    AssetDeltaError,
    query_asset_deltas,
    validate_asset_delta_query,
)
from .asset_view import (
    AssetViewError,
    export_assets_csv,
    query_asset_summary,
    query_assets,
    validate_asset_query,
    validate_asset_summary_query,
)
from .asset_sync import AssetSyncError, sync_character_assets
from .blueprint_sync import BlueprintSyncError, sync_character_blueprints
from .blueprint_view import BlueprintViewError, query_blueprints, validate_blueprint_query
from .character_skill_sync import CharacterSkillSyncError, sync_character_skills
from .character_skill_view import (
    CharacterSkillViewError,
    query_character_skills,
    validate_character_skill_query,
)
from .database import DatabaseStatus, connect_database, initialize_database
from .esi_client import EsiClient, EsiClientError
from .identity import (
    CharacterRecord,
    create_account_group,
    delete_account_group,
    list_account_groups,
    list_characters,
    update_account_group,
    update_character,
    upsert_character,
)
from .industry_facility_sync import IndustryFacilitySyncError, sync_industry_facilities
from .industry_facility_view import (
    IndustryFacilityViewError,
    query_industry_facilities,
    validate_industry_facility_query,
)
from .industry_job_sync import IndustryJobSyncError, sync_character_industry_jobs
from .industry_job_view import (
    IndustryJobViewError,
    query_industry_jobs,
    validate_industry_job_query,
)
from .industry_slots import (
    IndustrySlotError,
    query_industry_slots,
    validate_industry_slot_query,
)
from .location_resolution import (
    LocationResolutionError,
    resolve_latest_character_asset_locations,
)
from .official_sde import install_bundled_industry_sde
from .production_planning import (
    ProductionPlanningError,
    delete_production_plan,
    query_production_catalog,
    query_production_plans,
    save_production_plan,
    validate_production_catalog_query,
    validate_production_plan_delete,
    validate_production_plan_input,
    validate_production_plan_query,
)
from .research_planning import (
    ResearchPlanningError,
    delete_research_plan,
    query_research_plans,
    save_research_plan,
    validate_research_plan,
    validate_research_plan_identity,
    validate_research_query,
)
from .sde import (
    SdeQueryError,
    query_blueprint_activities,
    validate_blueprint_activity_query,
)
from .storage import ProgramStorage, ProgramStorageError, prepare_program_storage
from .startup_state import (
    StartupDataState,
    inspect_startup_data_state,
    recover_interrupted_sync_runs,
)
from .sso_registration import (
    SsoRegistrationProfile,
    load_bundled_sso_registration_profile,
)
from .sso_pkce import SsoPkceError, SsoPkceManager
from .sso_tokens import EveSsoClient, VerifiedAuthorization, VerifiedCharacter
from .token_service import CharacterTokenService
from .token_vault import (
    RefreshTokenVault,
    TokenVaultError,
    create_system_refresh_token_vault,
)
from .type_names import TypeNameResolutionError, resolve_type_names
from .updater import (
    PublicReleaseCheckError,
    UpdateChannel,
    UpdateManifestError,
    check_public_releases,
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


def public_sync_error_code(error: BaseException) -> str:
    code = str(getattr(error, "code", str(error)))
    status = getattr(error, "status", None)
    if code == "esi-request-rejected" and isinstance(status, int):
        code = f"{code}-{status}"
    return code[:120]


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


def store_verified_authorization(
    database_path: Path,
    token_vault: RefreshTokenVault,
    authorization: VerifiedAuthorization,
    token_service: CharacterTokenService | None = None,
) -> None:
    """Commit identity and its refresh token without exposing token material."""

    candidate = token_vault.stage(
        authorization.character.character_id,
        authorization.refresh_token,
    )
    try:
        store_verified_character(database_path, authorization.character)
    except BaseException:
        token_vault.discard(candidate)
        raise
    token_vault.commit(candidate)
    if token_service is not None:
        token_service.remember(authorization)



def managed_character_payload(
    character: CharacterRecord,
    sso_registration: SsoRegistrationProfile,
    token_vault: RefreshTokenVault,
) -> dict[str, object]:
    """Add derived scope-package and credential state without exposing secrets."""

    granted_scopes = set(character.scopes)
    package_statuses: list[dict[str, object]] = []
    for package_name, required_scopes in sso_registration.scope_packages.items():
        granted_count = len(granted_scopes.intersection(required_scopes))
        if granted_count == len(required_scopes):
            status = "granted"
        elif granted_count:
            status = "partial"
        else:
            status = "missing"
        package_statuses.append(
            {
                "id": package_name,
                "status": status,
                "grantedCount": granted_count,
                "requiredCount": len(required_scopes),
            }
        )

    try:
        credential_state = "stored" if token_vault.contains(character.character_id) else "missing"
    except TokenVaultError:
        credential_state = "unavailable"

    return {
        **character.as_api_payload(),
        "credentialState": credential_state,
        "scopePackages": package_statuses,
    }


def delete_character_completely(
    database_path: Path,
    token_vault: RefreshTokenVault,
    character_id: int,
    token_service: CharacterTokenService | None = None,
) -> bool:
    """Remove credential, cached lease, identity, scopes, sync history and snapshots."""

    with closing(connect_database(database_path)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            exists = connection.execute(
                "SELECT 1 FROM characters WHERE character_id = ?",
                (character_id,),
            ).fetchone()
            if exists is None:
                connection.execute("ROLLBACK")
                return False
            # Global facility snapshots may contain structures observed through a
            # character's personal jobs. Rebuild them after deletion instead of
            # retaining location evidence without its owner context.
            connection.execute(
                "DELETE FROM sync_runs WHERE source = 'industry_facilities'"
            )
            connection.execute(
                "DELETE FROM characters WHERE character_id = ?",
                (character_id,),
            )
            token_vault.delete(character_id)
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise
    if token_service is not None:
        token_service.forget(character_id)
    return True

def create_application(
    startup: StartupConfiguration,
    storage: ProgramStorage,
    database: DatabaseStatus,
    data_state: StartupDataState,
    manifest_state: str,
    sso_registration: SsoRegistrationProfile,
    sso_login: SsoPkceManager,
    token_vault: RefreshTokenVault,
    token_service: CharacterTokenService | None = None,
    esi_client: EsiClient | None = None,
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
            "esiClient": (
                esi_client.status()
                if esi_client is not None
                else {"state": "unavailable", "compatibilityDate": None}
            ),
            "credentials": {
                "backend": token_vault.backend_name,
                "state": (
                    "available"
                    if token_vault.backend_name == "windows-credential-manager"
                    else "unavailable"
                ),
            },
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

    @app.get("/updates/check")
    def get_public_release_notice() -> dict[str, object]:
        with closing(connect_database(storage.database_path)) as connection:
            selected_channel = read_update_channel(connection)
        try:
            return check_public_releases(selected_channel, project_version())
        except PublicReleaseCheckError as error:
            return {
                "state": "error",
                "channel": selected_channel.value,
                "currentVersion": project_version(),
                "latestVersion": None,
                "releaseUrl": None,
                "publishedAt": None,
                "automaticInstall": False,
                "errorCode": str(error),
            }

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

    @app.post("/assets/query")
    async def post_asset_query(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "asset_query_invalid"})
        if not isinstance(payload, dict) or set(payload) != {
            "search",
            "ownerCharacterId",
            "locationStatus",
            "offset",
            "limit",
            "sortBy",
            "sortDirection",
        }:
            return JSONResponse(status_code=422, content={"detail": "asset_query_invalid"})
        try:
            asset_query = validate_asset_query(
                search=payload["search"],
                owner_character_id=payload["ownerCharacterId"],
                location_status=payload["locationStatus"],
                offset=payload["offset"],
                limit=payload["limit"],
                sort_by=payload["sortBy"],
                sort_direction=payload["sortDirection"],
            )
            with closing(connect_database(storage.database_path)) as connection:
                result = query_assets(connection, asset_query)
        except AssetViewError as error:
            code = str(error)
            return JSONResponse(
                status_code=422 if code == "asset_query_invalid" else 500,
                content={"detail": code},
            )
        return JSONResponse(content=result)

    @app.post("/assets/summary/query")
    async def post_asset_summary_query(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                status_code=422, content={"detail": "asset_summary_query_invalid"}
            )
        if not isinstance(payload, dict) or set(payload) != {
            "search",
            "ownerCharacterId",
            "locationStatus",
            "offset",
            "limit",
            "sortBy",
            "sortDirection",
        }:
            return JSONResponse(
                status_code=422, content={"detail": "asset_summary_query_invalid"}
            )
        try:
            summary_query = validate_asset_summary_query(
                search=payload["search"],
                owner_character_id=payload["ownerCharacterId"],
                location_status=payload["locationStatus"],
                offset=payload["offset"],
                limit=payload["limit"],
                sort_by=payload["sortBy"],
                sort_direction=payload["sortDirection"],
            )
            with closing(connect_database(storage.database_path)) as connection:
                result = query_asset_summary(connection, summary_query)
        except AssetViewError as error:
            code = str(error)
            return JSONResponse(
                status_code=422
                if code in {"asset_query_invalid", "asset_summary_query_invalid"}
                else 500,
                content={"detail": code},
            )
        return JSONResponse(content=result)

    @app.post("/assets/sync")
    async def post_asset_sync() -> JSONResponse:
        if esi_client is None:
            return JSONResponse(status_code=503, content={"detail": "esi_client_unavailable"})
        with closing(connect_database(storage.database_path)) as connection:
            character_ids = [
                int(row[0])
                for row in connection.execute(
                    "SELECT character_id FROM characters WHERE enabled=1 ORDER BY character_id"
                ).fetchall()
            ]
            results: list[dict[str, object]] = []
            for character_id in character_ids:
                try:
                    synced = sync_character_assets(connection, esi_client, character_id)
                except (AssetSyncError, AssetDeltaError, EsiClientError) as error:
                    results.append(
                        {
                            "characterId": character_id,
                            "status": "failed",
                            "pages": 0,
                            "assets": 0,
                            "resolved": 0,
                            "restricted": 0,
                            "unresolved": 0,
                            "cycles": 0,
                            "errorCode": public_sync_error_code(error),
                        }
                    )
                    continue

                enrichment_errors: list[str] = []
                try:
                    resolve_type_names(connection, esi_client, synced.type_ids)
                except (TypeNameResolutionError, EsiClientError) as error:
                    code = public_sync_error_code(error)
                    enrichment_errors.append(f"type-names/{code}")

                resolved_counts = {
                    "resolved": 0,
                    "restricted": 0,
                    "unresolved": 0,
                    "cycles": 0,
                }
                try:
                    resolved = resolve_latest_character_asset_locations(
                        connection, esi_client, character_id
                    )
                    resolved_counts = {
                        "resolved": resolved.resolved,
                        "restricted": resolved.restricted,
                        "unresolved": resolved.unresolved,
                        "cycles": resolved.cycles,
                    }
                except (LocationResolutionError, EsiClientError) as error:
                    code = public_sync_error_code(error)
                    enrichment_errors.append(f"locations/{code}")

                results.append(
                    {
                        "characterId": character_id,
                        "status": "partial" if enrichment_errors else "completed",
                        "pages": synced.pages,
                        "assets": synced.assets,
                        **resolved_counts,
                        "errorCode": (
                            ";".join(enrichment_errors)[:120]
                            if enrichment_errors
                            else None
                        ),
                    }
                )
        completed = sum(result["status"] == "completed" for result in results)
        partial = sum(result["status"] == "partial" for result in results)
        return JSONResponse(
            content={
                "characters": results,
                "completed": completed,
                "partial": partial,
                "failed": len(results) - completed - partial,
                "assets": sum(int(result["assets"]) for result in results),
            }
        )

    @app.post("/blueprints/query")
    async def post_blueprint_query(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "blueprint_query_invalid"})
        try:
            validate_blueprint_query(payload)
            with closing(connect_database(storage.database_path)) as connection:
                result = query_blueprints(connection, payload)
        except BlueprintViewError as error:
            code = str(error)
            return JSONResponse(
                status_code=422 if code == "blueprint_query_invalid" else 500,
                content={"detail": code},
            )
        except Exception:
            return JSONResponse(status_code=500, content={"detail": "blueprint_query_failed"})
        return JSONResponse(content=result)

    @app.post("/blueprints/sync")
    async def post_blueprint_sync() -> JSONResponse:
        if esi_client is None:
            return JSONResponse(status_code=503, content={"detail": "esi_client_unavailable"})
        with closing(connect_database(storage.database_path)) as connection:
            character_ids = [
                int(row[0])
                for row in connection.execute(
                    "SELECT character_id FROM characters WHERE enabled=1 ORDER BY character_id"
                ).fetchall()
            ]
            results: list[dict[str, object]] = []
            for character_id in character_ids:
                try:
                    synced = sync_character_blueprints(connection, esi_client, character_id)
                    resolve_type_names(connection, esi_client, synced.type_ids)
                    results.append(
                        {
                            "characterId": character_id,
                            "status": "completed",
                            "pages": synced.pages,
                            "blueprints": synced.blueprints,
                            "errorCode": None,
                        }
                    )
                except (BlueprintSyncError, TypeNameResolutionError, EsiClientError) as error:
                    results.append(
                        {
                            "characterId": character_id,
                            "status": "failed",
                            "pages": 0,
                            "blueprints": 0,
                            "errorCode": public_sync_error_code(error),
                        }
                    )
        return JSONResponse(
            content={
                "characters": results,
                "completed": sum(result["status"] == "completed" for result in results),
                "failed": sum(result["status"] == "failed" for result in results),
                "blueprints": sum(int(result["blueprints"]) for result in results),
            }
        )

    @app.post("/industry-jobs/query")
    async def post_industry_job_query(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "industry_job_query_invalid"})
        try:
            validate_industry_job_query(payload)
            with closing(connect_database(storage.database_path)) as connection:
                result = query_industry_jobs(connection, payload)
        except IndustryJobViewError as error:
            code = str(error)
            return JSONResponse(
                status_code=422 if code == "industry_job_query_invalid" else 500,
                content={"detail": code},
            )
        except Exception:
            return JSONResponse(status_code=500, content={"detail": "industry_job_query_failed"})
        return JSONResponse(content=result)

    @app.post("/industry-jobs/sync")
    async def post_industry_job_sync() -> JSONResponse:
        if esi_client is None:
            return JSONResponse(status_code=503, content={"detail": "esi_client_unavailable"})
        with closing(connect_database(storage.database_path)) as connection:
            character_ids = [
                int(row[0])
                for row in connection.execute(
                    "SELECT character_id FROM characters WHERE enabled=1 ORDER BY character_id"
                ).fetchall()
            ]
            results: list[dict[str, object]] = []
            for character_id in character_ids:
                try:
                    synced = sync_character_industry_jobs(connection, esi_client, character_id)
                    resolve_type_names(connection, esi_client, synced.type_ids)
                    results.append(
                        {
                            "characterId": character_id,
                            "status": "completed",
                            "jobs": synced.jobs,
                            "active": synced.active,
                            "completedJobs": synced.completed,
                            "errorCode": None,
                        }
                    )
                except (IndustryJobSyncError, TypeNameResolutionError, EsiClientError) as error:
                    results.append(
                        {
                            "characterId": character_id,
                            "status": "failed",
                            "jobs": 0,
                            "active": 0,
                            "completedJobs": 0,
                            "errorCode": public_sync_error_code(error),
                        }
                    )
        completed = sum(result["status"] == "completed" for result in results)
        return JSONResponse(
            content={
                "characters": results,
                "completed": completed,
                "failed": len(results) - completed,
                "jobs": sum(int(result["jobs"]) for result in results),
                "active": sum(int(result["active"]) for result in results),
                "completedJobs": sum(int(result["completedJobs"]) for result in results),
            }
        )

    @app.post("/skills/query")
    async def post_character_skill_query(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "character_skill_query_invalid"})
        try:
            validate_character_skill_query(payload)
            with closing(connect_database(storage.database_path)) as connection:
                result = query_character_skills(connection, payload)
        except CharacterSkillViewError as error:
            code = str(error)
            return JSONResponse(
                status_code=422 if code == "character_skill_query_invalid" else 500,
                content={"detail": code},
            )
        except Exception:
            return JSONResponse(status_code=500, content={"detail": "character_skill_query_failed"})
        return JSONResponse(content=result)

    @app.post("/skills/sync")
    async def post_character_skill_sync() -> JSONResponse:
        if esi_client is None:
            return JSONResponse(status_code=503, content={"detail": "esi_client_unavailable"})
        with closing(connect_database(storage.database_path)) as connection:
            character_ids = [
                int(row[0])
                for row in connection.execute(
                    "SELECT character_id FROM characters WHERE enabled=1 ORDER BY character_id"
                ).fetchall()
            ]
            results: list[dict[str, object]] = []
            for character_id in character_ids:
                try:
                    synced = sync_character_skills(connection, esi_client, character_id)
                    resolve_type_names(connection, esi_client, synced.type_ids)
                    results.append(
                        {
                            "characterId": character_id,
                            "status": "completed",
                            "skills": synced.skills,
                            "totalSp": synced.total_sp,
                            "unallocatedSp": synced.unallocated_sp,
                            "errorCode": None,
                        }
                    )
                except (CharacterSkillSyncError, TypeNameResolutionError, EsiClientError) as error:
                    results.append(
                        {
                            "characterId": character_id,
                            "status": "failed",
                            "skills": 0,
                            "totalSp": 0,
                            "unallocatedSp": 0,
                            "errorCode": public_sync_error_code(error),
                        }
                    )
        completed = sum(result["status"] == "completed" for result in results)
        return JSONResponse(
            content={
                "characters": results,
                "completed": completed,
                "failed": len(results) - completed,
                "skills": sum(int(result["skills"]) for result in results),
                "totalSp": sum(int(result["totalSp"]) for result in results),
                "unallocatedSp": sum(int(result["unallocatedSp"]) for result in results),
            }
        )

    @app.post("/industry-facilities/query")
    async def post_industry_facility_query(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                status_code=422,
                content={"detail": "industry_facility_query_invalid"},
            )
        try:
            validate_industry_facility_query(payload)
            with closing(connect_database(storage.database_path)) as connection:
                result = query_industry_facilities(connection, payload)
        except IndustryFacilityViewError as error:
            code = str(error)
            return JSONResponse(
                status_code=422 if code == "industry_facility_query_invalid" else 500,
                content={"detail": code},
            )
        except Exception:
            return JSONResponse(
                status_code=500,
                content={"detail": "industry_facility_query_failed"},
            )
        return JSONResponse(content=result)

    @app.post("/industry-facilities/sync")
    async def post_industry_facility_sync() -> JSONResponse:
        if esi_client is None:
            return JSONResponse(status_code=503, content={"detail": "esi_client_unavailable"})
        try:
            with closing(connect_database(storage.database_path)) as connection:
                synced = sync_industry_facilities(connection, esi_client)
        except (IndustryFacilitySyncError, EsiClientError) as error:
            return JSONResponse(
                status_code=503,
                content={"detail": public_sync_error_code(error)},
            )
        return JSONResponse(
            content={
                "syncRunId": synced.sync_run_id,
                "facilities": synced.facilities,
                "npcFacilities": synced.npc_facilities,
                "observedFacilities": synced.observed_facilities,
                "restrictedStructures": synced.restricted_structures,
                "systems": synced.systems,
                "resolvedNames": synced.resolved_names,
            }
        )

    @app.post("/industry-slots/query")
    async def post_industry_slot_query(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "industry_slot_query_invalid"})
        try:
            validate_industry_slot_query(payload)
            with closing(connect_database(storage.database_path)) as connection:
                result = query_industry_slots(connection, payload)
        except IndustrySlotError as error:
            code = str(error)
            return JSONResponse(
                status_code=422 if code == "industry_slot_query_invalid" else 500,
                content={"detail": code},
            )
        except Exception:
            return JSONResponse(status_code=500, content={"detail": "industry_slot_query_failed"})
        return JSONResponse(content=result)

    @app.post("/sde/blueprint-activities/query")
    async def post_sde_blueprint_activity_query(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                status_code=422,
                content={"detail": "sde_blueprint_activity_query_invalid"},
            )
        try:
            validate_blueprint_activity_query(payload)
            with closing(connect_database(storage.database_path)) as connection:
                result = query_blueprint_activities(connection, payload)
        except SdeQueryError as error:
            code = str(error)
            return JSONResponse(
                status_code=(
                    422 if code == "sde_blueprint_activity_query_invalid" else 500
                ),
                content={"detail": code},
            )
        except Exception:
            return JSONResponse(
                status_code=500,
                content={"detail": "sde_blueprint_activity_query_failed"},
            )
        return JSONResponse(content=result)

    @app.post("/production-plans/catalog")
    async def post_production_catalog_query(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "production_catalog_query_invalid"})
        try:
            validate_production_catalog_query(payload)
            with closing(connect_database(storage.database_path)) as connection:
                result = query_production_catalog(connection, payload)
        except ProductionPlanningError as error:
            return JSONResponse(status_code=422, content={"detail": str(error)})
        except Exception:
            return JSONResponse(status_code=500, content={"detail": "production_catalog_query_failed"})
        return JSONResponse(content=result)

    @app.post("/production-plans/query")
    async def post_production_plan_query(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "production_plan_query_invalid"})
        try:
            validate_production_plan_query(payload)
            with closing(connect_database(storage.database_path)) as connection:
                result = query_production_plans(connection, payload)
        except ProductionPlanningError as error:
            code = str(error)
            return JSONResponse(
                status_code=422 if code == "production_plan_query_invalid" else 500,
                content={"detail": code},
            )
        except Exception:
            return JSONResponse(status_code=500, content={"detail": "production_plan_query_failed"})
        return JSONResponse(content=result)

    @app.post("/production-plans/save")
    async def post_production_plan_save(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "production_plan_input_invalid"})
        try:
            validate_production_plan_input(payload)
            with closing(connect_database(storage.database_path)) as connection:
                result = save_production_plan(connection, payload)
        except ProductionPlanningError as error:
            code = str(error)
            status = 404 if code in {"production_owner_missing", "production_plan_missing"} else 409 if code in {
                "production_sde_unavailable", "production_recipe_missing",
                "production_plan_cycle", "production_plan_complexity-limit",
            } else 422
            return JSONResponse(status_code=status, content={"detail": code})
        except Exception:
            return JSONResponse(status_code=500, content={"detail": "production_plan_save_failed"})
        return JSONResponse(content=result)

    @app.post("/production-plans/delete")
    async def post_production_plan_delete(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "production_plan_delete_invalid"})
        try:
            validate_production_plan_delete(payload)
            with closing(connect_database(storage.database_path)) as connection:
                result = delete_production_plan(connection, payload)
        except ProductionPlanningError as error:
            code = str(error)
            return JSONResponse(
                status_code=404 if code == "production_plan_missing" else 422,
                content={"detail": code},
            )
        except Exception:
            return JSONResponse(status_code=500, content={"detail": "production_plan_delete_failed"})
        return JSONResponse(content=result)

    @app.post("/research-plans/query")
    async def post_research_plan_query(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "research_query_invalid"})
        try:
            validate_research_query(payload)
            with closing(connect_database(storage.database_path)) as connection:
                result = query_research_plans(connection, payload)
        except ResearchPlanningError as error:
            code = str(error)
            return JSONResponse(
                status_code=422 if code == "research_query_invalid" else 500,
                content={"detail": code},
            )
        except Exception:
            return JSONResponse(status_code=500, content={"detail": "research_query_failed"})
        return JSONResponse(content=result)

    @app.post("/research-plans/save")
    async def post_research_plan_save(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "research_plan_invalid"})
        try:
            validate_research_plan(payload)
            with closing(connect_database(storage.database_path)) as connection:
                result = save_research_plan(connection, payload)
        except ResearchPlanningError as error:
            code = str(error)
            if code == "research_blueprint_not_found":
                status = 404
            elif code == "research_target_below_current":
                status = 409
            else:
                status = 422
            return JSONResponse(status_code=status, content={"detail": code})
        except Exception:
            return JSONResponse(status_code=500, content={"detail": "research_plan_save_failed"})
        return JSONResponse(content=result)

    @app.post("/research-plans/delete")
    async def post_research_plan_delete(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "research_plan_invalid"})
        try:
            validate_research_plan_identity(payload)
            with closing(connect_database(storage.database_path)) as connection:
                result = delete_research_plan(connection, payload)
        except ResearchPlanningError as error:
            return JSONResponse(status_code=422, content={"detail": str(error)})
        except Exception:
            return JSONResponse(status_code=500, content={"detail": "research_plan_delete_failed"})
        return JSONResponse(content=result)

    @app.post("/assets/export")
    async def post_asset_export(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "asset_query_invalid"})
        if not isinstance(payload, dict) or set(payload) != {
            "search",
            "ownerCharacterId",
            "locationStatus",
            "sortBy",
            "sortDirection",
        }:
            return JSONResponse(status_code=422, content={"detail": "asset_query_invalid"})
        try:
            asset_query = validate_asset_query(
                search=payload["search"],
                owner_character_id=payload["ownerCharacterId"],
                location_status=payload["locationStatus"],
                sort_by=payload["sortBy"],
                sort_direction=payload["sortDirection"],
            )
            with closing(connect_database(storage.database_path)) as connection:
                exported = export_assets_csv(
                    connection,
                    asset_query,
                    storage.export_directory,
                )
        except AssetViewError as error:
            code = str(error)
            return JSONResponse(
                status_code=422 if code == "asset_query_invalid" else 500,
                content={"detail": code},
            )
        return JSONResponse(content=exported.as_payload())

    @app.post("/assets/deltas/query")
    async def post_asset_delta_query(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                status_code=422,
                content={"detail": "asset_delta_query_invalid"},
            )
        if not isinstance(payload, dict) or set(payload) != {
            "search",
            "ownerCharacterId",
            "changeType",
            "offset",
            "limit",
        }:
            return JSONResponse(
                status_code=422,
                content={"detail": "asset_delta_query_invalid"},
            )
        try:
            delta_query = validate_asset_delta_query(
                search=payload["search"],
                owner_character_id=payload["ownerCharacterId"],
                change_type=payload["changeType"],
                offset=payload["offset"],
                limit=payload["limit"],
            )
            with closing(connect_database(storage.database_path)) as connection:
                result = query_asset_deltas(connection, delta_query)
        except AssetDeltaError as error:
            code = str(error)
            return JSONResponse(
                status_code=422 if code == "asset_delta_query_invalid" else 500,
                content={"detail": code},
            )
        return JSONResponse(content=result)

    @app.get("/characters")
    async def get_characters() -> dict[str, object]:
        with closing(connect_database(storage.database_path)) as connection:
            characters = list_characters(connection)
        return {
            "characters": [
                managed_character_payload(character, sso_registration, token_vault)
                for character in characters
            ]
        }

    @app.patch("/characters/{character_id}")
    async def patch_character(character_id: int, request: Request) -> JSONResponse:
        if character_id <= 0:
            return JSONResponse(
                status_code=422,
                content={"detail": "character-update-invalid"},
            )
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                status_code=422,
                content={"detail": "character-update-invalid"},
            )
        if not isinstance(payload, dict) or set(payload) != {
            "alias",
            "accountGroupId",
            "enabled",
        }:
            return JSONResponse(
                status_code=422,
                content={"detail": "character-update-invalid"},
            )
        try:
            with closing(connect_database(storage.database_path)) as connection:
                character = update_character(
                    connection,
                    character_id,
                    alias=payload["alias"],
                    account_group_id=payload["accountGroupId"],
                    enabled=payload["enabled"],
                )
        except LookupError:
            return JSONResponse(
                status_code=404,
                content={"detail": "character-not-found"},
            )
        except (TypeError, ValueError, sqlite3.IntegrityError):
            return JSONResponse(
                status_code=422,
                content={"detail": "character-update-invalid"},
            )
        return JSONResponse(
            content={
                "character": managed_character_payload(
                    character,
                    sso_registration,
                    token_vault,
                )
            }
        )

    @app.delete("/characters/{character_id}")
    async def remove_character(character_id: int) -> JSONResponse:
        if character_id <= 0:
            return JSONResponse(
                status_code=422,
                content={"detail": "character-delete-invalid"},
            )
        try:
            deleted = delete_character_completely(
                storage.database_path,
                token_vault,
                character_id,
                token_service,
            )
        except TokenVaultError as error:
            return JSONResponse(status_code=503, content={"detail": error.code})
        if not deleted:
            return JSONResponse(
                status_code=404,
                content={"detail": "character-not-found"},
            )
        return JSONResponse(
            content={"deleted": True, "characterId": character_id}
        )

    @app.get("/account-groups")
    async def get_account_groups() -> dict[str, object]:
        with closing(connect_database(storage.database_path)) as connection:
            groups = list_account_groups(connection)
        return {"groups": [group.as_api_payload() for group in groups]}

    @app.post("/account-groups")
    async def post_account_group(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                status_code=422,
                content={"detail": "account-group-invalid"},
            )
        if not isinstance(payload, dict) or set(payload) != {"label"}:
            return JSONResponse(
                status_code=422,
                content={"detail": "account-group-invalid"},
            )
        try:
            with closing(connect_database(storage.database_path)) as connection:
                group_id = create_account_group(connection, payload["label"])
                group = next(
                    group
                    for group in list_account_groups(connection)
                    if group.id == group_id
                )
        except sqlite3.IntegrityError:
            return JSONResponse(
                status_code=409,
                content={"detail": "account-group-conflict"},
            )
        except (TypeError, ValueError):
            return JSONResponse(
                status_code=422,
                content={"detail": "account-group-invalid"},
            )
        return JSONResponse(content={"group": group.as_api_payload()})

    @app.patch("/account-groups/{group_id}")
    async def patch_account_group(group_id: int, request: Request) -> JSONResponse:
        if group_id <= 0:
            return JSONResponse(
                status_code=422,
                content={"detail": "account-group-invalid"},
            )
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                status_code=422,
                content={"detail": "account-group-invalid"},
            )
        if not isinstance(payload, dict) or set(payload) != {"label"}:
            return JSONResponse(
                status_code=422,
                content={"detail": "account-group-invalid"},
            )
        try:
            with closing(connect_database(storage.database_path)) as connection:
                group = update_account_group(
                    connection,
                    group_id,
                    label=payload["label"],
                )
        except LookupError:
            return JSONResponse(
                status_code=404,
                content={"detail": "account-group-not-found"},
            )
        except sqlite3.IntegrityError:
            return JSONResponse(
                status_code=409,
                content={"detail": "account-group-conflict"},
            )
        except (TypeError, ValueError):
            return JSONResponse(
                status_code=422,
                content={"detail": "account-group-invalid"},
            )
        return JSONResponse(content={"group": group.as_api_payload()})

    @app.delete("/account-groups/{group_id}")
    async def remove_account_group(group_id: int) -> JSONResponse:
        if group_id <= 0:
            return JSONResponse(
                status_code=422,
                content={"detail": "account-group-invalid"},
            )
        try:
            with closing(connect_database(storage.database_path)) as connection:
                deleted = delete_account_group(connection, group_id)
        except (TypeError, ValueError):
            return JSONResponse(
                status_code=422,
                content={"detail": "account-group-invalid"},
            )
        if not deleted:
            return JSONResponse(
                status_code=404,
                content={"detail": "account-group-not-found"},
            )
        return JSONResponse(content={"deleted": True, "groupId": group_id})

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
        required_packages = list(sso_registration.scope_packages)
        if payload["scopePackages"] != required_packages:
            return JSONResponse(
                status_code=422,
                content={"detail": "required-scope-packages-missing"},
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
            recover_interrupted_sync_runs(connection)
            install_bundled_industry_sde(connection)
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
    token_vault = create_system_refresh_token_vault()
    assert sso_registration.client_id is not None
    sso_client = EveSsoClient(sso_registration.client_id)
    token_service = CharacterTokenService(token_vault, sso_client)
    esi_client = EsiClient(
        lambda character_id, scopes: token_service.access_token(
            character_id,
            scopes,
        ).token
    )
    try:
        sso_login = SsoPkceManager(
            sso_registration,
            sso_client=sso_client,
            authorization_handler=lambda authorization: store_verified_authorization(
                storage.database_path,
                token_vault,
                authorization,
                token_service,
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
        token_vault,
        token_service,
        esi_client,
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
            "esiClient": esi_client.status(),
            "credentials": {
                "backend": token_vault.backend_name,
                "state": (
                    "available"
                    if token_vault.backend_name == "windows-credential-manager"
                    else "unavailable"
                ),
            },
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
    query_asset_summary,
