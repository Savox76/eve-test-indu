"""Persistent ME/TE research plans derived from verified local snapshots."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping

from .blueprint_sync import BlueprintSyncError, _validate_blueprint
from .character_skill_sync import CharacterSkillSyncError, validate_character_skills
from .industry_facility_view import IndustryFacilityViewError, industry_facility_index
from .industry_job_evidence import (
    IndustryJobEvidenceError,
    load_latest_job_snapshots,
    parse_timestamp,
)


MAX_SAFE_INTEGER = 9_007_199_254_740_991
MAX_PAGE_SIZE = 200
MAX_NOTE_LENGTH = 240
RESEARCH_STATES = (
    "unplanned",
    "ready",
    "queued",
    "running",
    "complete",
    "unverified",
    "missing",
)
RESEARCH_ACTIVITIES = ("material", "time")
SORT_FIELDS = ("priority", "blueprint", "owner", "state", "me", "te", "age")
ACTIVE_JOB_STATUSES = ("active", "paused", "ready")
SCIENCE_ACTIVITY_IDS = (3, 4, 5, 7, 8)
RESEARCH_ACTIVITY_IDS = {"time": 3, "material": 4}
SKILL_IDS = {
    "research": 3403,
    "laboratory_operation": 3406,
    "metallurgy": 3409,
    "advanced_laboratory_operation": 24624,
}


class ResearchPlanningError(RuntimeError):
    """Raised when a research-plan command or source snapshot is invalid."""


def _positive_integer(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= MAX_SAFE_INTEGER:
        raise ResearchPlanningError("research_plan_invalid")
    return value


def _bounded_integer(value: Any, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ResearchPlanningError("research_plan_invalid")
    return value


def _normalized_note(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ResearchPlanningError("research_plan_invalid")
    normalized = " ".join(value.strip().split())
    if not normalized:
        return None
    if len(normalized) > MAX_NOTE_LENGTH:
        raise ResearchPlanningError("research_plan_invalid")
    return normalized


def validate_research_plan(payload: Any) -> dict[str, Any]:
    expected = {
        "ownerCharacterId",
        "blueprintItemId",
        "nextActivity",
        "targetMaterialEfficiency",
        "targetTimeEfficiency",
        "priority",
        "note",
    }
    if not isinstance(payload, Mapping) or set(payload) != expected:
        raise ResearchPlanningError("research_plan_invalid")
    next_activity = payload["nextActivity"]
    if next_activity not in RESEARCH_ACTIVITIES:
        raise ResearchPlanningError("research_plan_invalid")
    return {
        "ownerCharacterId": _positive_integer(payload["ownerCharacterId"]),
        "blueprintItemId": _positive_integer(payload["blueprintItemId"]),
        "nextActivity": next_activity,
        "targetMaterialEfficiency": _bounded_integer(
            payload["targetMaterialEfficiency"], 0, 10
        ),
        "targetTimeEfficiency": _bounded_integer(payload["targetTimeEfficiency"], 0, 20),
        "priority": _bounded_integer(payload["priority"], 0, 999),
        "note": _normalized_note(payload["note"]),
    }


def validate_research_plan_identity(payload: Any) -> dict[str, int]:
    expected = {"ownerCharacterId", "blueprintItemId"}
    if not isinstance(payload, Mapping) or set(payload) != expected:
        raise ResearchPlanningError("research_plan_invalid")
    return {
        "ownerCharacterId": _positive_integer(payload["ownerCharacterId"]),
        "blueprintItemId": _positive_integer(payload["blueprintItemId"]),
    }


def validate_research_query(payload: Any) -> dict[str, Any]:
    expected = {
        "search",
        "ownerCharacterId",
        "state",
        "plannedOnly",
        "offset",
        "limit",
        "sortBy",
        "sortDirection",
    }
    if not isinstance(payload, Mapping) or set(payload) != expected:
        raise ResearchPlanningError("research_query_invalid")
    search = payload["search"]
    owner = payload["ownerCharacterId"]
    if (
        not isinstance(search, str)
        or len(search) > 120
        or owner is not None
        and (isinstance(owner, bool) or not isinstance(owner, int) or not 0 < owner <= MAX_SAFE_INTEGER)
        or payload["state"] not in (None, *RESEARCH_STATES)
        or not isinstance(payload["plannedOnly"], bool)
        or isinstance(payload["offset"], bool)
        or not isinstance(payload["offset"], int)
        or not 0 <= payload["offset"] <= MAX_SAFE_INTEGER
        or isinstance(payload["limit"], bool)
        or not isinstance(payload["limit"], int)
        or not 1 <= payload["limit"] <= MAX_PAGE_SIZE
        or payload["sortBy"] not in SORT_FIELDS
        or payload["sortDirection"] not in ("asc", "desc")
    ):
        raise ResearchPlanningError("research_query_invalid")
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


def _latest_blueprints(connection: sqlite3.Connection) -> dict[tuple[int, int], dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT cached_snapshots.id AS snapshot_id,cached_snapshots.sync_run_id,
               cached_snapshots.payload_json,cached_snapshots.observed_at,
               characters.character_id,characters.name,characters.alias
        FROM characters JOIN cached_snapshots
          ON cached_snapshots.resource='character_blueprints:' || characters.character_id
        JOIN sync_runs ON sync_runs.id=cached_snapshots.sync_run_id
        WHERE sync_runs.source='character_blueprints'
          AND sync_runs.status='completed'
          AND cached_snapshots.id=(
            SELECT candidate.id FROM cached_snapshots AS candidate
            JOIN sync_runs AS candidate_run ON candidate_run.id=candidate.sync_run_id
            WHERE candidate.resource='character_blueprints:' || characters.character_id
              AND candidate_run.source='character_blueprints'
              AND candidate_run.status='completed'
            ORDER BY candidate.observed_at DESC,candidate.id DESC LIMIT 1)
        ORDER BY characters.character_id
        """
    ).fetchall()
    result: dict[tuple[int, int], dict[str, Any]] = {}
    for row in rows:
        character_id = int(row["character_id"])
        try:
            payload = json.loads(str(row["payload_json"]))
            observed = parse_timestamp(str(row["observed_at"]))
        except (TypeError, ValueError, json.JSONDecodeError, IndustryJobEvidenceError) as error:
            raise ResearchPlanningError("research_blueprint_snapshot_invalid") from error
        if (
            not isinstance(payload, Mapping)
            or set(payload) != {"characterId", "pages", "blueprints"}
            or payload.get("characterId") != character_id
            or isinstance(payload.get("pages"), bool)
            or not isinstance(payload.get("pages"), int)
            or not 1 <= int(payload["pages"]) <= 1_000
            or not isinstance(payload.get("blueprints"), list)
        ):
            raise ResearchPlanningError("research_blueprint_snapshot_invalid")
        seen: set[int] = set()
        for raw_blueprint in payload["blueprints"]:
            try:
                blueprint = _validate_blueprint(raw_blueprint)
            except BlueprintSyncError as error:
                raise ResearchPlanningError("research_blueprint_snapshot_invalid") from error
            item_id = int(blueprint["item_id"])
            if item_id in seen:
                raise ResearchPlanningError("research_blueprint_snapshot_invalid")
            seen.add(item_id)
            if int(blueprint["quantity"]) != -1:
                continue
            result[(character_id, item_id)] = {
                "ownerName": str(row["alias"] or row["name"]),
                "typeId": int(blueprint["type_id"]),
                "materialEfficiency": int(blueprint["material_efficiency"]),
                "timeEfficiency": int(blueprint["time_efficiency"]),
                "locationId": int(blueprint["location_id"]),
                "locationFlag": str(blueprint["location_flag"]),
                "snapshotId": int(row["snapshot_id"]),
                "syncRunId": int(row["sync_run_id"]),
                "observedAt": str(row["observed_at"]),
                "observed": observed,
            }
    return result


def _latest_skills(connection: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT cached_snapshots.id AS snapshot_id,cached_snapshots.sync_run_id,
               cached_snapshots.payload_json,cached_snapshots.observed_at,
               characters.character_id
        FROM characters JOIN cached_snapshots
          ON cached_snapshots.resource='character_skills:' || characters.character_id
        JOIN sync_runs ON sync_runs.id=cached_snapshots.sync_run_id
        WHERE sync_runs.source='character_skills'
          AND sync_runs.status='completed'
          AND cached_snapshots.id=(
            SELECT candidate.id FROM cached_snapshots AS candidate
            JOIN sync_runs AS candidate_run ON candidate_run.id=candidate.sync_run_id
            WHERE candidate.resource='character_skills:' || characters.character_id
              AND candidate_run.source='character_skills'
              AND candidate_run.status='completed'
            ORDER BY candidate.observed_at DESC,candidate.id DESC LIMIT 1)
        ORDER BY characters.character_id
        """
    ).fetchall()
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        character_id = int(row["character_id"])
        try:
            payload = json.loads(str(row["payload_json"]))
            if not isinstance(payload, Mapping) or payload.get("characterId") != character_id:
                raise ResearchPlanningError("research_skill_snapshot_invalid")
            validated = validate_character_skills(
                {key: value for key, value in payload.items() if key != "characterId"}
            )
            parse_timestamp(str(row["observed_at"]))
        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
            CharacterSkillSyncError,
            IndustryJobEvidenceError,
        ) as error:
            raise ResearchPlanningError("research_skill_snapshot_invalid") from error
        levels = {
            int(skill["skill_id"]): int(skill["active_skill_level"])
            for skill in validated["skills"]
        }
        result[character_id] = {
            "levels": levels,
            "snapshotId": int(row["snapshot_id"]),
            "syncRunId": int(row["sync_run_id"]),
            "observedAt": str(row["observed_at"]),
        }
    return result


def _jobs(connection: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    try:
        return load_latest_job_snapshots(connection)
    except IndustryJobEvidenceError as error:
        raise ResearchPlanningError("research_job_snapshot_invalid") from error


def _facility_for_job(
    facility_index: Mapping[int, Mapping[str, Any]],
    job: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if job is None:
        return {
            "facilityId": None,
            "facilityName": None,
            "facilityAccess": "unknown",
            "solarSystemName": None,
            "systemCostIndex": None,
            "facilityEvidence": "none",
        }
    facility = facility_index.get(int(job["facility_id"]))
    activity = "researching_material_efficiency" if job["activity_id"] == 4 else "researching_time_efficiency"
    return {
        "facilityId": int(job["facility_id"]),
        "facilityName": None if facility is None else facility["facilityName"],
        "facilityAccess": "unknown" if facility is None else facility["access"],
        "solarSystemName": None if facility is None else facility["solarSystemName"],
        "systemCostIndex": None
        if facility is None
        else facility["costIndices"].get(activity),
        "facilityEvidence": "active-job" if job["status"] in ACTIVE_JOB_STATUSES else "last-owner-job",
    }


def save_research_plan(connection: sqlite3.Connection, raw_plan: Any) -> dict[str, Any]:
    plan = validate_research_plan(raw_plan)
    key = (plan["ownerCharacterId"], plan["blueprintItemId"])
    blueprints = _latest_blueprints(connection)
    current = blueprints.get(key)
    existing = connection.execute(
        "SELECT blueprint_type_id FROM research_plans "
        "WHERE owner_character_id=? AND blueprint_item_id=?",
        key,
    ).fetchone()
    if current is None and existing is None:
        raise ResearchPlanningError("research_blueprint_not_found")
    if current is not None and (
        plan["targetMaterialEfficiency"] < current["materialEfficiency"]
        or plan["targetTimeEfficiency"] < current["timeEfficiency"]
    ):
        raise ResearchPlanningError("research_target_below_current")
    blueprint_type_id = int(
        current["typeId"] if current is not None else existing["blueprint_type_id"]
    )
    connection.execute(
        """
        INSERT INTO research_plans(
          owner_character_id,blueprint_item_id,blueprint_type_id,next_activity,
          target_material_efficiency,target_time_efficiency,priority,note)
        VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(owner_character_id,blueprint_item_id) DO UPDATE SET
          blueprint_type_id=excluded.blueprint_type_id,
          next_activity=excluded.next_activity,
          target_material_efficiency=excluded.target_material_efficiency,
          target_time_efficiency=excluded.target_time_efficiency,
          priority=excluded.priority,note=excluded.note,
          updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
        """,
        (
            plan["ownerCharacterId"],
            plan["blueprintItemId"],
            blueprint_type_id,
            plan["nextActivity"],
            plan["targetMaterialEfficiency"],
            plan["targetTimeEfficiency"],
            plan["priority"],
            plan["note"],
        ),
    )
    connection.commit()
    return {**plan, "blueprintTypeId": blueprint_type_id, "saved": True}


def delete_research_plan(connection: sqlite3.Connection, raw_identity: Any) -> dict[str, Any]:
    identity = validate_research_plan_identity(raw_identity)
    deleted = connection.execute(
        "DELETE FROM research_plans WHERE owner_character_id=? AND blueprint_item_id=?",
        (identity["ownerCharacterId"], identity["blueprintItemId"]),
    ).rowcount
    connection.commit()
    return {**identity, "deleted": deleted == 1}


def query_research_plans(
    connection: sqlite3.Connection,
    raw_query: Any,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    query = validate_research_query(raw_query)
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    names = _type_names(connection)
    blueprints = _latest_blueprints(connection)
    skills = _latest_skills(connection)
    jobs = _jobs(connection)
    try:
        facilities = industry_facility_index(connection)
    except IndustryFacilityViewError as error:
        raise ResearchPlanningError("research_facility_snapshot_invalid") from error
    plans = {
        (int(row["owner_character_id"]), int(row["blueprint_item_id"])): row
        for row in connection.execute(
            "SELECT * FROM research_plans ORDER BY owner_character_id,blueprint_item_id"
        )
    }
    character_names = {
        int(row["character_id"]): str(row["alias"] or row["name"])
        for row in connection.execute(
            "SELECT character_id,name,alias FROM characters ORDER BY character_id"
        )
    }
    active_jobs: dict[int, list[dict[str, Any]]] = {}
    research_jobs: dict[tuple[int, int], list[dict[str, Any]]] = {}
    recent_jobs: dict[tuple[int, int], dict[str, Any]] = {}
    for character_id, snapshot in jobs.items():
        for job in snapshot["jobs"]:
            if job["activity_id"] in SCIENCE_ACTIVITY_IDS and job["status"] in ACTIVE_JOB_STATUSES:
                active_jobs.setdefault(character_id, []).append(job)
            if job["activity_id"] in (3, 4):
                key = (character_id, int(job["blueprint_id"]))
                if job["status"] in ACTIVE_JOB_STATUSES:
                    research_jobs.setdefault(key, []).append(job)
                recent_key = (character_id, int(job["activity_id"]))
                previous = recent_jobs.get(recent_key)
                if previous is None or parse_timestamp(job["start_date"]) > parse_timestamp(
                    previous["start_date"]
                ):
                    recent_jobs[recent_key] = job

    owners: list[dict[str, Any]] = []
    owner_stats: dict[int, dict[str, Any]] = {}
    owner_ids = sorted({key[0] for key in blueprints} | {key[0] for key in plans})
    for character_id in owner_ids:
        skill = skills.get(character_id)
        used = len(active_jobs.get(character_id, []))
        if skill is None:
            capacity = available = None
            levels: Mapping[int, int] = {}
        else:
            levels = skill["levels"]
            capacity = 1 + levels.get(SKILL_IDS["laboratory_operation"], 0) + levels.get(
                SKILL_IDS["advanced_laboratory_operation"], 0
            )
            available = max(0, capacity - used)
        stats = {
            "characterId": character_id,
            "name": character_names.get(character_id, f"Character #{character_id}"),
            "slotCapacity": capacity,
            "slotsUsed": used,
            "slotsAvailable": available,
            "laboratoryOperationLevel": levels.get(SKILL_IDS["laboratory_operation"], 0),
            "advancedLaboratoryOperationLevel": levels.get(
                SKILL_IDS["advanced_laboratory_operation"], 0
            ),
            "researchLevel": levels.get(SKILL_IDS["research"], 0),
            "metallurgyLevel": levels.get(SKILL_IDS["metallurgy"], 0),
            "skillSnapshotId": None if skill is None else skill["snapshotId"],
            "skillSyncRunId": None if skill is None else skill["syncRunId"],
        }
        owners.append(stats)
        owner_stats[character_id] = stats

    all_rows: list[dict[str, Any]] = []
    observed_values: list[datetime] = []
    keys = sorted(set(blueprints) | set(plans))
    for key in keys:
        character_id, item_id = key
        blueprint = blueprints.get(key)
        saved = plans.get(key)
        if saved is None:
            type_id = int(blueprint["typeId"])
            next_activity = "material"
            target_me = int(blueprint["materialEfficiency"])
            target_te = int(blueprint["timeEfficiency"])
            priority = 0
            note = None
            created_at = updated_at = None
            planned = False
        else:
            type_id = int(saved["blueprint_type_id"])
            next_activity = str(saved["next_activity"])
            target_me = int(saved["target_material_efficiency"])
            target_te = int(saved["target_time_efficiency"])
            priority = int(saved["priority"])
            note = saved["note"]
            created_at = str(saved["created_at"])
            updated_at = str(saved["updated_at"])
            planned = True
        current_me = None if blueprint is None else int(blueprint["materialEfficiency"])
        current_te = None if blueprint is None else int(blueprint["timeEfficiency"])
        matching_jobs = research_jobs.get(key, [])
        matching_jobs.sort(key=lambda job: (parse_timestamp(job["start_date"]), int(job["job_id"])), reverse=True)
        active_job = matching_jobs[0] if matching_jobs else None
        stats = owner_stats[character_id]
        if not planned:
            state = "unplanned"
        elif blueprint is None and active_job is None:
            state = "missing"
        elif active_job is not None:
            state = "running"
        elif current_me is not None and current_te is not None and current_me >= target_me and current_te >= target_te:
            state = "complete"
        elif stats["slotCapacity"] is None:
            state = "unverified"
        elif stats["slotsAvailable"] == 0:
            state = "queued"
        else:
            state = "ready"
        activity_id = RESEARCH_ACTIVITY_IDS[next_activity]
        facility_job = active_job or recent_jobs.get((character_id, activity_id))
        facility = _facility_for_job(facilities, facility_job)
        if active_job is None and facility_job is not None:
            facility["facilityEvidence"] = "last-owner-job"
        observed_at = None if blueprint is None else str(blueprint["observedAt"])
        age = None
        if blueprint is not None:
            observed_values.append(blueprint["observed"])
            age = max(0, int((current_time - blueprint["observed"]).total_seconds()))
        row = {
            "ownerCharacterId": character_id,
            "ownerName": stats["name"],
            "blueprintItemId": item_id,
            "blueprintTypeId": type_id,
            "blueprintName": names.get(type_id, f"Type #{type_id}"),
            "blueprintPresent": blueprint is not None,
            "currentMaterialEfficiency": current_me,
            "currentTimeEfficiency": current_te,
            "locationId": None if blueprint is None else blueprint["locationId"],
            "locationFlag": None if blueprint is None else blueprint["locationFlag"],
            "planned": planned,
            "nextActivity": next_activity,
            "targetMaterialEfficiency": target_me,
            "targetTimeEfficiency": target_te,
            "priority": priority,
            "note": note,
            "state": state,
            "slotCapacity": stats["slotCapacity"],
            "slotsUsed": stats["slotsUsed"],
            "slotsAvailable": stats["slotsAvailable"],
            "researchLevel": stats["researchLevel"],
            "metallurgyLevel": stats["metallurgyLevel"],
            "activeJobId": None if active_job is None else int(active_job["job_id"]),
            "activeJobActivity": None
            if active_job is None
            else ("material" if active_job["activity_id"] == 4 else "time"),
            "activeJobStatus": None if active_job is None else active_job["status"],
            "activeJobStartDate": None if active_job is None else active_job["start_date"],
            "activeJobEndDate": None if active_job is None else active_job["end_date"],
            "activeJobCost": None if active_job is None else active_job["cost"],
            **facility,
            "blueprintSnapshotId": None if blueprint is None else blueprint["snapshotId"],
            "blueprintSyncRunId": None if blueprint is None else blueprint["syncRunId"],
            "skillSnapshotId": stats["skillSnapshotId"],
            "skillSyncRunId": stats["skillSyncRunId"],
            "jobSnapshotId": None if character_id not in jobs else jobs[character_id]["snapshotId"],
            "jobSyncRunId": None if character_id not in jobs else jobs[character_id]["syncRunId"],
            "observedAt": observed_at,
            "ageSeconds": age,
            "createdAt": created_at,
            "updatedAt": updated_at,
        }
        all_rows.append(row)

    summary = {state: 0 for state in RESEARCH_STATES}
    for row in all_rows:
        summary[str(row["state"])] += 1
    tokens = query["search"].casefold().split()
    rows = [
        row
        for row in all_rows
        if (query["ownerCharacterId"] is None or row["ownerCharacterId"] == query["ownerCharacterId"])
        and (query["state"] is None or row["state"] == query["state"])
        and (not query["plannedOnly"] or row["planned"])
        and (
            not tokens
            or all(
                token
                in (
                    f"{row['blueprintName']} {row['ownerName']} {row['blueprintItemId']} "
                    f"{row['blueprintTypeId']} {row['note'] or ''} {row['facilityName'] or ''}"
                ).casefold()
                for token in tokens
            )
        )
    ]
    state_order = {state: index for index, state in enumerate(RESEARCH_STATES)}
    getters = {
        "priority": lambda row: int(row["priority"]),
        "blueprint": lambda row: str(row["blueprintName"]).casefold(),
        "owner": lambda row: str(row["ownerName"]).casefold(),
        "state": lambda row: state_order[str(row["state"])],
        "me": lambda row: -1 if row["currentMaterialEfficiency"] is None else int(row["currentMaterialEfficiency"]),
        "te": lambda row: -1 if row["currentTimeEfficiency"] is None else int(row["currentTimeEfficiency"]),
        "age": lambda row: MAX_SAFE_INTEGER if row["ageSeconds"] is None else int(row["ageSeconds"]),
    }
    reverse = query["sortDirection"] == "desc"
    rows.sort(
        key=lambda row: (
            getters[query["sortBy"]](row),
            str(row["blueprintName"]).casefold(),
            int(row["blueprintItemId"]),
        ),
        reverse=reverse,
    )
    total = len(rows)
    page = rows[query["offset"] : query["offset"] + query["limit"]]
    oldest = min(observed_values) if observed_values else None
    return {
        "items": page,
        "total": total,
        "offset": query["offset"],
        "limit": query["limit"],
        "owners": owners,
        "states": list(RESEARCH_STATES),
        "activities": list(RESEARCH_ACTIVITIES),
        "summary": summary,
        "observedAt": None if oldest is None else oldest.isoformat().replace("+00:00", "Z"),
        "ageSeconds": None
        if oldest is None
        else max(0, int((current_time - oldest).total_seconds())),
        "estimatesAvailable": False,
    }
