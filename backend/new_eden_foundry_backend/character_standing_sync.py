"""Character-standing synchronization with complete snapshot semantics."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping

from .esi_client import EsiClient, EsiClientError
from .sde import MAX_SAFE_INTEGER


CHARACTER_STANDING_SCOPE = "esi-characters.read_standings.v1"
STANDING_SCALE = 1_000_000
MAX_CHARACTER_STANDINGS = 100_000
STANDING_TYPES = ("agent", "npc_corp", "faction")


class CharacterStandingSyncError(RuntimeError):
    """Raised when ESI cannot publish a trustworthy standing snapshot."""


@dataclass(frozen=True, slots=True)
class CharacterStandingSyncResult:
    character_id: int
    sync_run_id: int
    standings: int


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_standing(row: Any) -> dict[str, Any]:
    if not isinstance(row, Mapping) or set(row) != {"from_id", "from_type", "standing"}:
        raise CharacterStandingSyncError("character_standing_payload_invalid")
    from_id = row["from_id"]
    from_type = row["from_type"]
    value = row["standing"]
    if (
        isinstance(from_id, bool)
        or not isinstance(from_id, int)
        or not 0 < from_id <= MAX_SAFE_INTEGER
        or from_type not in STANDING_TYPES
        or isinstance(value, bool)
        or not isinstance(value, (int, float, Decimal))
    ):
        raise CharacterStandingSyncError("character_standing_payload_invalid")
    try:
        decimal_value = Decimal(str(value))
        scaled = (decimal_value * STANDING_SCALE).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    except (InvalidOperation, ValueError) as error:
        raise CharacterStandingSyncError("character_standing_payload_invalid") from error
    if not decimal_value.is_finite() or decimal_value < -10 or decimal_value > 10:
        raise CharacterStandingSyncError("character_standing_payload_invalid")
    return {
        "fromId": from_id,
        "fromType": from_type,
        "standingMillionths": int(scaled),
    }


def validate_character_standings(payload: Any) -> list[dict[str, Any]]:
    """Validate and normalize the official character-standings response."""

    if not isinstance(payload, list) or len(payload) > MAX_CHARACTER_STANDINGS:
        raise CharacterStandingSyncError("character_standing_payload_invalid")
    standings = [_validate_standing(row) for row in payload]
    identities = [(row["fromType"], row["fromId"]) for row in standings]
    if len(identities) != len(set(identities)):
        raise CharacterStandingSyncError("character_standing_payload_invalid")
    standings.sort(key=lambda row: (STANDING_TYPES.index(row["fromType"]), row["fromId"]))
    return standings


def sync_character_standings(
    connection: sqlite3.Connection,
    client: EsiClient,
    character_id: int,
) -> CharacterStandingSyncResult:
    """Fetch and atomically publish one enabled character's unmodified standings."""

    if isinstance(character_id, bool) or not isinstance(character_id, int) or character_id <= 0:
        raise ValueError("character_id must be positive")
    character = connection.execute(
        "SELECT enabled FROM characters WHERE character_id=?", (character_id,)
    ).fetchone()
    if character is None or not bool(character[0]):
        raise CharacterStandingSyncError("character_not_syncable")

    started = _utc_now()
    run = connection.execute(
        "INSERT INTO sync_runs(source,status,started_at,character_id) "
        "VALUES('character_standings','running',?,?)",
        (started, character_id),
    )
    run_id = int(run.lastrowid)
    try:
        response = client.get_json(
            f"/characters/{character_id}/standings/",
            character_id=character_id,
            required_scopes=(CHARACTER_STANDING_SCOPE,),
        )
        standings = validate_character_standings(response.payload)
        completed_at = _utc_now()
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (
                run_id,
                f"character_standings:{character_id}",
                json.dumps(
                    {"characterId": character_id, "standings": standings},
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                completed_at,
            ),
        )
        connection.execute(
            "UPDATE sync_runs SET status='completed',completed_at=?,data_timestamp=? "
            "WHERE id=? AND status='running'",
            (completed_at, completed_at, run_id),
        )
        connection.commit()
        return CharacterStandingSyncResult(
            character_id=character_id,
            sync_run_id=run_id,
            standings=len(standings),
        )
    except Exception as error:
        if connection.in_transaction:
            connection.rollback()
        completed_at = _utc_now()
        code = (
            error.code
            if isinstance(error, EsiClientError)
            else str(error)
            if isinstance(error, CharacterStandingSyncError)
            else "character_standing_sync_failed"
        )
        connection.execute(
            "UPDATE sync_runs SET status='failed',completed_at=?,error_code=? "
            "WHERE id=? AND status='running'",
            (completed_at, code[:120], run_id),
        )
        connection.commit()
        if isinstance(error, (CharacterStandingSyncError, EsiClientError)):
            raise
        raise CharacterStandingSyncError("character_standing_sync_failed") from error
