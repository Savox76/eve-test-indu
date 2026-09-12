"""Character blueprint synchronization with complete-run snapshot semantics."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .esi_client import EsiClient, EsiClientError


BLUEPRINT_SCOPE = "esi-characters.read_blueprints.v1"
MAX_SAFE_INTEGER = 9_007_199_254_740_991


class BlueprintSyncError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BlueprintSyncResult:
    character_id: int
    sync_run_id: int
    pages: int
    blueprints: int
    type_ids: tuple[int, ...]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_blueprint(row: Any) -> dict[str, Any]:
    required = {
        "item_id", "type_id", "location_id", "location_flag", "quantity",
        "time_efficiency", "material_efficiency", "runs",
    }
    if not isinstance(row, Mapping) or not required.issubset(row):
        raise BlueprintSyncError("blueprint_payload_invalid")
    integers = tuple(row[key] for key in required - {"location_flag"})
    if any(isinstance(value, bool) or not isinstance(value, int) for value in integers):
        raise BlueprintSyncError("blueprint_payload_invalid")
    if (
        not 0 < row["item_id"] <= MAX_SAFE_INTEGER
        or not 0 < row["type_id"] <= MAX_SAFE_INTEGER
        or not 0 < row["location_id"] <= MAX_SAFE_INTEGER
        or row["quantity"] == 0
        or not -2 <= row["quantity"] <= MAX_SAFE_INTEGER
        or not 0 <= row["material_efficiency"] <= 10
        or not 0 <= row["time_efficiency"] <= 20
        or not -1 <= row["runs"] <= MAX_SAFE_INTEGER
        or not isinstance(row["location_flag"], str)
        or not row["location_flag"].strip()
        or row["location_flag"] != row["location_flag"].strip()
        or len(row["location_flag"]) > 100
    ):
        raise BlueprintSyncError("blueprint_payload_invalid")
    return {key: row[key] for key in sorted(required)}


def _page_count(headers: Mapping[str, str]) -> int:
    try:
        pages = int(headers.get("x-pages", "1"))
    except (TypeError, ValueError) as error:
        raise BlueprintSyncError("blueprint_pages_invalid") from error
    if not 1 <= pages <= 1_000:
        raise BlueprintSyncError("blueprint_pages_invalid")
    return pages


def sync_character_blueprints(
    connection: sqlite3.Connection,
    client: EsiClient,
    character_id: int,
) -> BlueprintSyncResult:
    if isinstance(character_id, bool) or not isinstance(character_id, int) or character_id <= 0:
        raise ValueError("character_id must be positive")
    character = connection.execute(
        "SELECT enabled FROM characters WHERE character_id=?", (character_id,)
    ).fetchone()
    if character is None or not bool(character[0]):
        raise BlueprintSyncError("character_not_syncable")
    started = _utc_now()
    run = connection.execute(
        "INSERT INTO sync_runs(source,status,started_at,character_id) "
        "VALUES('character_blueprints','running',?,?)",
        (started, character_id),
    )
    run_id = int(run.lastrowid)
    try:
        first = client.get_json(
            f"/characters/{character_id}/blueprints/",
            query={"page": 1},
            character_id=character_id,
            required_scopes=(BLUEPRINT_SCOPE,),
        )
        pages = _page_count(first.headers)
        if not isinstance(first.payload, list):
            raise BlueprintSyncError("blueprint_payload_invalid")
        blueprints = [_validate_blueprint(row) for row in first.payload]
        for page in range(2, pages + 1):
            response = client.get_json(
                f"/characters/{character_id}/blueprints/",
                query={"page": page},
                character_id=character_id,
                required_scopes=(BLUEPRINT_SCOPE,),
            )
            if not isinstance(response.payload, list):
                raise BlueprintSyncError("blueprint_payload_invalid")
            blueprints.extend(_validate_blueprint(row) for row in response.payload)
        item_ids = [row["item_id"] for row in blueprints]
        if len(item_ids) != len(set(item_ids)):
            raise BlueprintSyncError("duplicate_blueprint_item")
        completed = _utc_now()
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (
                run_id,
                f"character_blueprints:{character_id}",
                json.dumps(
                    {"characterId": character_id, "pages": pages, "blueprints": blueprints},
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                completed,
            ),
        )
        connection.execute(
            "UPDATE sync_runs SET status='completed',completed_at=?,data_timestamp=? "
            "WHERE id=? AND status='running'",
            (completed, completed, run_id),
        )
        connection.commit()
        return BlueprintSyncResult(
            character_id, run_id, pages, len(blueprints),
            tuple(sorted({int(row["type_id"]) for row in blueprints})),
        )
    except Exception as error:
        if connection.in_transaction:
            connection.rollback()
        completed = _utc_now()
        code = error.code if isinstance(error, EsiClientError) else (
            str(error) if isinstance(error, BlueprintSyncError) else "blueprint_sync_failed"
        )
        connection.execute(
            "UPDATE sync_runs SET status='failed',completed_at=?,error_code=? "
            "WHERE id=? AND status='running'",
            (completed, code[:120], run_id),
        )
        connection.commit()
        if isinstance(error, (BlueprintSyncError, EsiClientError)):
            raise
        raise BlueprintSyncError("blueprint_sync_failed") from error
