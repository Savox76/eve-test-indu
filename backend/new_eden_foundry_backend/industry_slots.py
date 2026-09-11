"""Character-separated industry slot capacity, occupancy and work queue."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping

from .industry_job_evidence import (
    IndustryJobEvidenceError,
    load_latest_job_snapshots,
    parse_timestamp,
)
from .research_planning import (
    ResearchPlanningError,
    _latest_blueprints,
    _latest_skills,
)
from .production_planning import production_work_queues


MAX_SAFE_INTEGER = 9_007_199_254_740_991
MAX_PAGE_SIZE = 200
SLOT_ACTIVITIES = ("manufacturing", "reactions", "science")
ACTIVE_JOB_STATUSES = ("active", "paused", "ready")
JOB_ACTIVITY_GROUPS = {
    "manufacturing": (1,),
    "reactions": (9, 11),
    "science": (3, 4, 5, 7, 8),
}
SLOT_SKILLS = {
    "manufacturing": (3387, 24625),
    "reactions": (45748, 45749),
    "science": (3406, 24624),
}
UTILIZATION_STATES = ("unknown", "available", "full", "overbooked")


class IndustrySlotError(RuntimeError):
    """Raised when a slot query or one of its persisted sources is invalid."""


def validate_industry_slot_query(payload: Any) -> dict[str, Any]:
    expected = {"ownerCharacterId", "offset", "limit"}
    if not isinstance(payload, Mapping) or set(payload) != expected:
        raise IndustrySlotError("industry_slot_query_invalid")
    owner = payload["ownerCharacterId"]
    offset = payload["offset"]
    limit = payload["limit"]
    if (
        owner is not None
        and (isinstance(owner, bool) or not isinstance(owner, int) or not 0 < owner <= MAX_SAFE_INTEGER)
        or isinstance(offset, bool)
        or not isinstance(offset, int)
        or not 0 <= offset <= MAX_SAFE_INTEGER
        or isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_PAGE_SIZE
    ):
        raise IndustrySlotError("industry_slot_query_invalid")
    return dict(payload)


def _source_age(
    observed_values: list[datetime],
    current_time: datetime,
) -> tuple[str | None, int | None]:
    oldest = min(observed_values) if observed_values else None
    if oldest is None:
        return None, None
    return (
        oldest.isoformat().replace("+00:00", "Z"),
        max(0, int((current_time - oldest).total_seconds())),
    )


def _research_work_queue(
    connection: sqlite3.Connection,
    blueprints: Mapping[tuple[int, int], Mapping[str, Any]],
    skills: Mapping[int, Mapping[str, Any]],
    jobs: Mapping[int, Mapping[str, Any]],
) -> dict[int, dict[str, int]]:
    active_research = {
        (character_id, int(job["blueprint_id"]))
        for character_id, snapshot in jobs.items()
        for job in snapshot["jobs"]
        if job["activity_id"] in (3, 4) and job["status"] in ACTIVE_JOB_STATUSES
    }
    queues: dict[int, dict[str, int]] = {}
    for row in connection.execute(
        "SELECT owner_character_id,blueprint_item_id,target_material_efficiency,"
        "target_time_efficiency FROM research_plans ORDER BY owner_character_id,blueprint_item_id"
    ):
        character_id = int(row["owner_character_id"])
        item_id = int(row["blueprint_item_id"])
        counters = queues.setdefault(
            character_id,
            {"queued": 0, "blocked": 0, "running": 0, "complete": 0},
        )
        blueprint = blueprints.get((character_id, item_id))
        if (character_id, item_id) in active_research:
            counters["running"] += 1
        elif blueprint is None or character_id not in skills:
            counters["blocked"] += 1
        elif (
            int(blueprint["materialEfficiency"]) >= int(row["target_material_efficiency"])
            and int(blueprint["timeEfficiency"]) >= int(row["target_time_efficiency"])
        ):
            counters["complete"] += 1
        else:
            counters["queued"] += 1
    return queues


def _activity_record(
    activity: str,
    skill: Mapping[str, Any] | None,
    job_snapshot: Mapping[str, Any] | None,
    plan_queue: Mapping[str, int],
) -> dict[str, object]:
    primary_skill_id, advanced_skill_id = SLOT_SKILLS[activity]
    if skill is None:
        primary_level = advanced_level = capacity = None
    else:
        levels = skill["levels"]
        primary_level = int(levels.get(primary_skill_id, 0))
        advanced_level = int(levels.get(advanced_skill_id, 0))
        capacity = 1 + primary_level + advanced_level

    if job_snapshot is None:
        active = paused = ready = occupied = None
        next_end = None
    else:
        activity_ids = JOB_ACTIVITY_GROUPS[activity]
        relevant = [
            job
            for job in job_snapshot["jobs"]
            if job["activity_id"] in activity_ids and job["status"] in ACTIVE_JOB_STATUSES
        ]
        active = sum(job["status"] == "active" for job in relevant)
        paused = sum(job["status"] == "paused" for job in relevant)
        ready = sum(job["status"] == "ready" for job in relevant)
        occupied = len(relevant)
        active_end_dates = [
            (parse_timestamp(job["end_date"]), str(job["end_date"]))
            for job in relevant
            if job["status"] == "active"
        ]
        next_end = min(active_end_dates)[1] if active_end_dates else None

    if capacity is None or occupied is None:
        available = None
        state = "unknown"
    else:
        available = max(0, capacity - occupied)
        state = "overbooked" if occupied > capacity else "full" if occupied == capacity else "available"

    planning_available = activity in {"manufacturing", "reactions", "science"}
    return {
        "activity": activity,
        "capacity": capacity,
        "occupied": occupied,
        "available": available,
        "utilizationState": state,
        "activeJobs": active,
        "pausedJobs": paused,
        "readyJobs": ready,
        "nextJobEndDate": next_end,
        "primarySkillId": primary_skill_id,
        "primarySkillLevel": primary_level,
        "advancedSkillId": advanced_skill_id,
        "advancedSkillLevel": advanced_level,
        "queuedPlans": plan_queue.get("queued", 0) if planning_available else None,
        "blockedPlans": plan_queue.get("blocked", 0) if planning_available else None,
        "runningPlans": plan_queue.get("running", 0) if planning_available else None,
        "completePlans": plan_queue.get("complete", 0) if planning_available else None,
        "planningAvailable": planning_available,
    }


def query_industry_slots(
    connection: sqlite3.Connection,
    raw_query: Any,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    """Build a bounded overview without treating missing source data as zero."""

    query = validate_industry_slot_query(raw_query)
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    try:
        skills = _latest_skills(connection)
    except ResearchPlanningError as error:
        raise IndustrySlotError("industry_slot_skill_snapshot_invalid") from error
    try:
        jobs = load_latest_job_snapshots(connection)
    except IndustryJobEvidenceError as error:
        raise IndustrySlotError("industry_slot_job_snapshot_invalid") from error
    try:
        blueprints = _latest_blueprints(connection)
    except ResearchPlanningError as error:
        raise IndustrySlotError("industry_slot_blueprint_snapshot_invalid") from error
    research_queues = _research_work_queue(connection, blueprints, skills, jobs)
    production_queues = production_work_queues(connection, jobs)

    owners = [
        {
            "characterId": int(row["character_id"]),
            "name": str(row["alias"] or row["name"]),
        }
        for row in connection.execute(
            "SELECT character_id,name,alias FROM characters "
            "ORDER BY COALESCE(alias,name) COLLATE NOCASE,character_id"
        )
    ]
    rows: list[dict[str, object]] = []
    for owner in owners:
        character_id = int(owner["characterId"])
        skill = skills.get(character_id)
        job_snapshot = jobs.get(character_id)
        source_dates: list[datetime] = []
        if skill is not None:
            observed = parse_timestamp(skill["observedAt"])
            source_dates.append(observed)
        if job_snapshot is not None:
            observed = parse_timestamp(job_snapshot["observedAt"])
            source_dates.append(observed)
        observed_at, age_seconds = _source_age(source_dates, current_time)
        rows.append(
            {
                "characterId": character_id,
                "name": owner["name"],
                "activities": [
                    _activity_record(
                        activity,
                        skill,
                        job_snapshot,
                        (
                            research_queues.get(character_id, {})
                            if activity == "science"
                            else production_queues.get(character_id, {}).get(activity, {})
                        ),
                    )
                    for activity in SLOT_ACTIVITIES
                ],
                "skillSnapshotId": None if skill is None else skill["snapshotId"],
                "skillSyncRunId": None if skill is None else skill["syncRunId"],
                "skillObservedAt": None if skill is None else skill["observedAt"],
                "jobSnapshotId": None if job_snapshot is None else job_snapshot["snapshotId"],
                "jobSyncRunId": None if job_snapshot is None else job_snapshot["syncRunId"],
                "jobObservedAt": None if job_snapshot is None else job_snapshot["observedAt"],
                "observedAt": observed_at,
                "ageSeconds": age_seconds,
            }
        )

    filtered = [
        row
        for row in rows
        if query["ownerCharacterId"] is None
        or row["characterId"] == query["ownerCharacterId"]
    ]
    total = len(filtered)
    page = filtered[query["offset"] : query["offset"] + query["limit"]]
    filtered_observed_values = [
        parse_timestamp(row["observedAt"])
        for row in filtered
        if row["observedAt"] is not None
    ]
    overall_observed_at, overall_age_seconds = _source_age(
        filtered_observed_values,
        current_time,
    )
    return {
        "items": page,
        "total": total,
        "offset": query["offset"],
        "limit": query["limit"],
        "owners": owners,
        "activities": list(SLOT_ACTIVITIES),
        "observedAt": overall_observed_at,
        "ageSeconds": overall_age_seconds,
    }
