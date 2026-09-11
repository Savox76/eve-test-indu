"""Character-skill synchronization with complete snapshot semantics."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .esi_client import EsiClient, EsiClientError


CHARACTER_SKILL_SCOPE = "esi-skills.read_skills.v1"
MAX_SAFE_INTEGER = 9_007_199_254_740_991


class CharacterSkillSyncError(RuntimeError):
    """Raised when an ESI response cannot publish a trustworthy skill snapshot."""


@dataclass(frozen=True, slots=True)
class CharacterSkillSyncResult:
    character_id: int
    sync_run_id: int
    skills: int
    total_sp: int
    unallocated_sp: int
    type_ids: tuple[int, ...]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _non_negative_integer(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SAFE_INTEGER:
        raise CharacterSkillSyncError("character_skill_payload_invalid")
    return value


def _validate_skill(row: Any) -> dict[str, int]:
    required = {
        "active_skill_level",
        "skill_id",
        "skillpoints_in_skill",
        "trained_skill_level",
    }
    if not isinstance(row, Mapping) or set(row) != required:
        raise CharacterSkillSyncError("character_skill_payload_invalid")
    skill_id = _non_negative_integer(row["skill_id"])
    skillpoints = _non_negative_integer(row["skillpoints_in_skill"])
    active_level = _non_negative_integer(row["active_skill_level"])
    trained_level = _non_negative_integer(row["trained_skill_level"])
    if skill_id == 0 or active_level > 5 or trained_level > 5:
        raise CharacterSkillSyncError("character_skill_payload_invalid")
    return {
        "active_skill_level": active_level,
        "skill_id": skill_id,
        "skillpoints_in_skill": skillpoints,
        "trained_skill_level": trained_level,
    }


def validate_character_skills(payload: Any) -> dict[str, Any]:
    """Validate and normalize the official character-skills response."""

    if not isinstance(payload, Mapping) or set(payload) not in (
        {"skills", "total_sp"},
        {"skills", "total_sp", "unallocated_sp"},
    ):
        raise CharacterSkillSyncError("character_skill_payload_invalid")
    if not isinstance(payload["skills"], list):
        raise CharacterSkillSyncError("character_skill_payload_invalid")
    skills = [_validate_skill(row) for row in payload["skills"]]
    skill_ids = [skill["skill_id"] for skill in skills]
    total_sp = _non_negative_integer(payload["total_sp"])
    unallocated_sp = _non_negative_integer(payload.get("unallocated_sp", 0))
    if len(skill_ids) != len(set(skill_ids)) or sum(
        skill["skillpoints_in_skill"] for skill in skills
    ) != total_sp:
        raise CharacterSkillSyncError("character_skill_payload_invalid")
    skills.sort(key=lambda skill: skill["skill_id"])
    return {"skills": skills, "total_sp": total_sp, "unallocated_sp": unallocated_sp}


def sync_character_skills(
    connection: sqlite3.Connection,
    client: EsiClient,
    character_id: int,
) -> CharacterSkillSyncResult:
    """Fetch and atomically publish one enabled character's trained skills."""

    if isinstance(character_id, bool) or not isinstance(character_id, int) or character_id <= 0:
        raise ValueError("character_id must be positive")
    character = connection.execute(
        "SELECT enabled FROM characters WHERE character_id=?", (character_id,)
    ).fetchone()
    if character is None or not bool(character[0]):
        raise CharacterSkillSyncError("character_not_syncable")

    started = _utc_now()
    run = connection.execute(
        "INSERT INTO sync_runs(source,status,started_at,character_id) "
        "VALUES('character_skills','running',?,?)",
        (started, character_id),
    )
    run_id = int(run.lastrowid)
    try:
        response = client.get_json(
            f"/characters/{character_id}/skills/",
            character_id=character_id,
            required_scopes=(CHARACTER_SKILL_SCOPE,),
        )
        validated = validate_character_skills(response.payload)
        completed_at = _utc_now()
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (
                run_id,
                f"character_skills:{character_id}",
                json.dumps(
                    {"characterId": character_id, **validated},
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
        return CharacterSkillSyncResult(
            character_id=character_id,
            sync_run_id=run_id,
            skills=len(validated["skills"]),
            total_sp=int(validated["total_sp"]),
            unallocated_sp=int(validated["unallocated_sp"]),
            type_ids=tuple(skill["skill_id"] for skill in validated["skills"]),
        )
    except Exception as error:
        if connection.in_transaction:
            connection.rollback()
        completed_at = _utc_now()
        code = (
            error.code
            if isinstance(error, EsiClientError)
            else str(error)
            if isinstance(error, CharacterSkillSyncError)
            else "character_skill_sync_failed"
        )
        connection.execute(
            "UPDATE sync_runs SET status='failed',completed_at=?,error_code=? "
            "WHERE id=? AND status='running'",
            (completed_at, code[:120], run_id),
        )
        connection.commit()
        if isinstance(error, (CharacterSkillSyncError, EsiClientError)):
            raise
        raise CharacterSkillSyncError("character_skill_sync_failed") from error
