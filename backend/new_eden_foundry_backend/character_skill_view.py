"""Bounded read model for complete character-skill snapshots."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping


MAX_SAFE_INTEGER = 9_007_199_254_740_991
MAX_PAGE_SIZE = 200
LEVELS = (0, 1, 2, 3, 4, 5)
ACTIVE_STATES = ("normal", "limited", "boosted")
SORT_FIELDS = ("skill", "owner", "trained", "active", "skillpoints", "age")


class CharacterSkillViewError(RuntimeError):
    """Raised when a query or stored skill snapshot is invalid."""


def validate_character_skill_query(payload: Any) -> dict[str, Any]:
    expected = {
        "search",
        "ownerCharacterId",
        "trainedLevel",
        "activeState",
        "offset",
        "limit",
        "sortBy",
        "sortDirection",
    }
    if not isinstance(payload, Mapping) or set(payload) != expected:
        raise CharacterSkillViewError("character_skill_query_invalid")
    search = payload["search"]
    owner = payload["ownerCharacterId"]
    trained_level = payload["trainedLevel"]
    if (
        not isinstance(search, str)
        or len(search) > 120
        or owner is not None
        and (isinstance(owner, bool) or not isinstance(owner, int) or not 0 < owner <= MAX_SAFE_INTEGER)
        or trained_level is not None
        and (isinstance(trained_level, bool) or trained_level not in LEVELS)
        or payload["activeState"] not in (None, *ACTIVE_STATES)
        or isinstance(payload["offset"], bool)
        or not isinstance(payload["offset"], int)
        or not 0 <= payload["offset"] <= MAX_SAFE_INTEGER
        or isinstance(payload["limit"], bool)
        or not isinstance(payload["limit"], int)
        or not 1 <= payload["limit"] <= MAX_PAGE_SIZE
        or payload["sortBy"] not in SORT_FIELDS
        or payload["sortDirection"] not in ("asc", "desc")
    ):
        raise CharacterSkillViewError("character_skill_query_invalid")
    return {**payload, "search": " ".join(search.strip().split())}


def _type_names(connection: sqlite3.Connection) -> dict[int, str]:
    names = {
        int(row[0]): str(row[1])
        for row in connection.execute("SELECT type_id,name FROM resolved_type_names")
    }
    if connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sde_types'"
    ).fetchone() is not None:
        names.update(
            {
                int(row[0]): str(row[1])
                for row in connection.execute("SELECT type_id,name FROM sde_types")
            }
        )
    return names


def _active_state(active_level: int, trained_level: int) -> str:
    if active_level < trained_level:
        return "limited"
    if active_level > trained_level:
        return "boosted"
    return "normal"


def query_character_skills(
    connection: sqlite3.Connection,
    raw_query: Any,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    query = validate_character_skill_query(raw_query)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    names = _type_names(connection)
    rows: list[dict[str, object]] = []
    owners: list[dict[str, object]] = []
    observed_values: list[str] = []
    total_sp = 0
    unallocated_sp = 0
    snapshots = connection.execute(
        """
        SELECT characters.character_id,characters.name,characters.alias,
               cached_snapshots.id,cached_snapshots.sync_run_id,
               cached_snapshots.payload_json,cached_snapshots.observed_at
        FROM characters JOIN cached_snapshots
          ON cached_snapshots.resource='character_skills:' || characters.character_id
        JOIN sync_runs ON sync_runs.id=cached_snapshots.sync_run_id
        WHERE sync_runs.status='completed' AND cached_snapshots.id=(
          SELECT candidate.id FROM cached_snapshots AS candidate
          JOIN sync_runs AS candidate_run ON candidate_run.id=candidate.sync_run_id
          WHERE candidate.resource='character_skills:' || characters.character_id
            AND candidate_run.status='completed'
          ORDER BY candidate.observed_at DESC,candidate.id DESC LIMIT 1)
        ORDER BY characters.name COLLATE NOCASE,characters.character_id
        """
    ).fetchall()
    tokens = query["search"].casefold().split()
    for snapshot in snapshots:
        character_id = int(snapshot["character_id"])
        owner_name = str(snapshot["alias"] or snapshot["name"])
        owners.append({"characterId": character_id, "name": owner_name})
        try:
            payload = json.loads(str(snapshot["payload_json"]))
            observed = datetime.fromisoformat(str(snapshot["observed_at"]).replace("Z", "+00:00"))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise CharacterSkillViewError("character_skill_snapshot_invalid") from error
        if (
            not isinstance(payload, Mapping)
            or payload.get("characterId") != character_id
            or not isinstance(payload.get("skills"), list)
            or not isinstance(payload.get("total_sp"), int)
            or isinstance(payload.get("total_sp"), bool)
            or not isinstance(payload.get("unallocated_sp"), int)
            or isinstance(payload.get("unallocated_sp"), bool)
            or observed.tzinfo is None
        ):
            raise CharacterSkillViewError("character_skill_snapshot_invalid")
        if query["ownerCharacterId"] is not None and query["ownerCharacterId"] != character_id:
            continue
        observed_text = str(snapshot["observed_at"])
        observed_values.append(observed_text)
        age = max(0, int((current - observed.astimezone(timezone.utc)).total_seconds()))
        snapshot_total = int(payload["total_sp"])
        snapshot_unallocated = int(payload["unallocated_sp"])
        if not 0 <= snapshot_total <= MAX_SAFE_INTEGER or not 0 <= snapshot_unallocated <= MAX_SAFE_INTEGER:
            raise CharacterSkillViewError("character_skill_snapshot_invalid")
        total_sp += snapshot_total
        unallocated_sp += snapshot_unallocated
        seen: set[int] = set()
        summed_sp = 0
        for item in payload["skills"]:
            if not isinstance(item, Mapping) or set(item) != {
                "active_skill_level", "skill_id", "skillpoints_in_skill", "trained_skill_level"
            }:
                raise CharacterSkillViewError("character_skill_snapshot_invalid")
            if any(
                isinstance(item[field], bool) or not isinstance(item[field], int)
                for field in (
                    "active_skill_level",
                    "skill_id",
                    "skillpoints_in_skill",
                    "trained_skill_level",
                )
            ):
                raise CharacterSkillViewError("character_skill_snapshot_invalid")
            try:
                skill_id = int(item["skill_id"])
                active_level = int(item["active_skill_level"])
                trained_level = int(item["trained_skill_level"])
                skillpoints = int(item["skillpoints_in_skill"])
            except (TypeError, ValueError) as error:
                raise CharacterSkillViewError("character_skill_snapshot_invalid") from error
            if (
                skill_id in seen
                or not 0 < skill_id <= MAX_SAFE_INTEGER
                or not 0 <= active_level <= 5
                or not 0 <= trained_level <= 5
                or not 0 <= skillpoints <= MAX_SAFE_INTEGER
            ):
                raise CharacterSkillViewError("character_skill_snapshot_invalid")
            seen.add(skill_id)
            summed_sp += skillpoints
            state = _active_state(active_level, trained_level)
            if query["trainedLevel"] is not None and query["trainedLevel"] != trained_level:
                continue
            if query["activeState"] is not None and query["activeState"] != state:
                continue
            skill_name = names.get(skill_id, f"Type #{skill_id}")
            if tokens and not all(
                token in f"{skill_name} {owner_name} {skill_id}".casefold() for token in tokens
            ):
                continue
            rows.append(
                {
                    "skillId": skill_id,
                    "skillName": skill_name,
                    "ownerCharacterId": character_id,
                    "ownerName": owner_name,
                    "trainedLevel": trained_level,
                    "activeLevel": active_level,
                    "skillpoints": skillpoints,
                    "activeState": state,
                    "snapshotId": int(snapshot["id"]),
                    "syncRunId": int(snapshot["sync_run_id"]),
                    "observedAt": observed_text,
                    "ageSeconds": age,
                }
            )
        if summed_sp != snapshot_total:
            raise CharacterSkillViewError("character_skill_snapshot_invalid")

    getters = {
        "skill": lambda row: str(row["skillName"]).casefold(),
        "owner": lambda row: str(row["ownerName"]).casefold(),
        "trained": lambda row: int(row["trainedLevel"]),
        "active": lambda row: int(row["activeLevel"]),
        "skillpoints": lambda row: int(row["skillpoints"]),
        "age": lambda row: int(row["ageSeconds"]),
    }
    rows.sort(
        key=lambda row: (
            getters[query["sortBy"]](row),
            str(row["ownerName"]).casefold(),
            int(row["skillId"]),
        ),
        reverse=query["sortDirection"] == "desc",
    )
    owners.sort(key=lambda owner: (str(owner["name"]).casefold(), int(owner["characterId"])))
    total = len(rows)
    page = rows[query["offset"] : query["offset"] + query["limit"]]
    oldest = min(observed_values) if observed_values else None
    age = None
    if oldest is not None:
        parsed = datetime.fromisoformat(oldest.replace("Z", "+00:00")).astimezone(timezone.utc)
        age = max(0, int((current - parsed).total_seconds()))
    return {
        "items": page,
        "total": total,
        "totalSp": total_sp,
        "unallocatedSp": unallocated_sp,
        "offset": query["offset"],
        "limit": query["limit"],
        "owners": owners,
        "levels": list(LEVELS),
        "activeStates": list(ACTIVE_STATES),
        "observedAt": oldest,
        "ageSeconds": age,
    }
