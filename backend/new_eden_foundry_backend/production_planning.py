"""Persistent production goals and deterministic gross-material expansion."""

from __future__ import annotations

import heapq
import json
import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from .character_skill_sync import CharacterSkillSyncError, validate_character_skills
from .industry_facility_view import (
    IndustryFacilityViewError,
    industry_facility_index,
)
from .industry_job_evidence import (
    IndustryJobEvidenceError,
    load_latest_job_snapshots,
    parse_timestamp,
)
from .sde import (
    MAX_SAFE_INTEGER,
    SUPPORTED_BLUEPRINT_ACTIVITIES,
    current_sde_blueprint_activity_build,
)


MAX_PAGE_SIZE = 100
MAX_CATALOG_PAGE_SIZE = 100
MAX_PLAN_STEPS = 500
MAX_INVENTORY_LOCATION_GROUPS = 50
MAX_RESERVATION_CLAIMS = 50
MAX_BLUEPRINT_CANDIDATES = 50
MAX_STEP_BLUEPRINT_ASSIGNMENTS = MAX_PLAN_STEPS - 1
MAX_STEP_SUPPLY_MODES = MAX_PLAN_STEPS - 1
MAX_PRODUCTION_FACILITIES = 200
MAX_PRODUCTION_MATERIAL_LOCATIONS = 200
RESERVATION_RULE = "priority-desc-created-asc-plan-id-asc"
MATERIAL_EFFICIENCY_RULE = "max-runs-ceil-base-runs-percent"
TIME_EFFICIENCY_RULE = "max-one-ceil-base-runs-percent"
CHAIN_BLUEPRINT_ASSIGNMENT_RULE = "explicit-per-recipe-unique-item"
CHARACTER_SKILL_TIME_RULE = (
    "job-wide-ceil-industry-4-advanced-industry-3-reactions-4-active-levels"
)
FACILITY_EVIDENCE_RULE = "assigned-blueprint-before-active-before-latest-owner-job"
SUPPLY_MODE_RULE = "stock-first-before-recursive-build"
INDUSTRY_SKILL_ID = 3380
ADVANCED_INDUSTRY_SKILL_ID = 3388
REACTIONS_SKILL_ID = 45746
_SKILL_SOURCE_UNSET = object()
_JOB_SOURCE_UNSET = object()
PLAN_STATES = (
    "ready",
    "sde-unavailable",
    "recipe-missing",
    "cycle",
    "complexity-limit",
)
PLAN_SORT_FIELDS = ("priority", "product", "owner", "activity", "state", "updated")
SORT_DIRECTIONS = ("asc", "desc")
INVENTORY_STATES = ("covered", "shortage", "snapshot-missing", "not-applicable")
BLUEPRINT_ASSIGNMENT_STATES = (
    "ready",
    "unassigned",
    "snapshot-missing",
    "missing",
    "type-mismatch",
    "runs-insufficient",
)
ASSET_LOCATION_STATUSES = ("resolved", "restricted", "unresolved", "cycle", "pending")
FACILITY_STATES = (
    "ready",
    "job-snapshot-missing",
    "job-missing",
    "facility-snapshot-missing",
    "facility-missing",
    "facility-unavailable",
)
PLAN_FACILITY_STATES = ("ready", "partial", "missing", "not-applicable")
SUPPLY_MODES = ("stock-first", "stock-only", "build")
LOCATION_SELECTION_STATES = (
    "unselected",
    "ready",
    "facility-missing",
    "material-location-missing",
)
ACTIVE_JOB_STATUSES = ("active", "paused", "ready")
PRODUCTION_JOB_ACTIVITY_IDS = {
    "manufacturing": (1,),
    "reaction": (9, 11),
}


class ProductionPlanningError(RuntimeError):
    """Raised for an invalid request or inconsistent production source."""


@dataclass(frozen=True, slots=True)
class Recipe:
    blueprint_type_id: int
    blueprint_name: str
    activity: str
    base_time_seconds: int
    product_type_id: int
    product_name: str
    output_quantity: int
    products: tuple[tuple[int, str, int], ...]
    materials: tuple[tuple[int, str, int], ...]


@dataclass(frozen=True, slots=True)
class InventorySource:
    character_id: int
    owner_name: str
    snapshot_id: int
    sync_run_id: int
    observed_at: str
    stock: dict[int, tuple[dict[str, Any], ...]]
    facilities: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class BlueprintItem:
    item_id: int
    type_id: int
    kind: str
    material_efficiency: int
    time_efficiency: int
    runs: int
    location_id: int
    location_flag: str


@dataclass(frozen=True, slots=True)
class BlueprintSource:
    character_id: int
    snapshot_id: int
    sync_run_id: int
    observed_at: str
    items: dict[int, BlueprintItem]


@dataclass(frozen=True, slots=True)
class SkillSource:
    character_id: int
    snapshot_id: int
    sync_run_id: int
    observed_at: str
    active_levels: dict[int, int]


def _positive_int(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, int)
        and 0 < value <= MAX_SAFE_INTEGER
    )


def _non_negative_int(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, int)
        and 0 <= value <= MAX_SAFE_INTEGER
    )


def _normalized_text(value: Any, limit: int) -> str:
    if not isinstance(value, str):
        raise ProductionPlanningError("production_plan_request_invalid")
    normalized = " ".join(value.split())
    if len(normalized) > limit:
        raise ProductionPlanningError("production_plan_request_invalid")
    return normalized


def validate_production_plan_query(payload: Any) -> dict[str, Any]:
    expected = {
        "search",
        "ownerCharacterId",
        "activity",
        "state",
        "offset",
        "limit",
        "sortBy",
        "sortDirection",
    }
    if not isinstance(payload, Mapping) or set(payload) != expected:
        raise ProductionPlanningError("production_plan_query_invalid")
    try:
        search = _normalized_text(payload["search"], 120)
    except ProductionPlanningError as error:
        raise ProductionPlanningError("production_plan_query_invalid") from error
    owner = payload["ownerCharacterId"]
    activity = payload["activity"]
    state = payload["state"]
    if (
        owner is not None
        and not _positive_int(owner)
        or activity is not None
        and activity not in SUPPORTED_BLUEPRINT_ACTIVITIES
        or state is not None
        and state not in PLAN_STATES
        or not _non_negative_int(payload["offset"])
        or not _positive_int(payload["limit"])
        or payload["limit"] > MAX_PAGE_SIZE
        or payload["sortBy"] not in PLAN_SORT_FIELDS
        or payload["sortDirection"] not in SORT_DIRECTIONS
    ):
        raise ProductionPlanningError("production_plan_query_invalid")
    return {
        **payload,
        "search": search,
    }


def validate_production_catalog_query(payload: Any) -> dict[str, Any]:
    expected = {"search", "activity", "offset", "limit"}
    if not isinstance(payload, Mapping) or set(payload) != expected:
        raise ProductionPlanningError("production_catalog_query_invalid")
    try:
        search = _normalized_text(payload["search"], 120)
    except ProductionPlanningError as error:
        raise ProductionPlanningError("production_catalog_query_invalid") from error
    activity = payload["activity"]
    if (
        activity is not None
        and activity not in SUPPORTED_BLUEPRINT_ACTIVITIES
        or not _non_negative_int(payload["offset"])
        or not _positive_int(payload["limit"])
        or payload["limit"] > MAX_CATALOG_PAGE_SIZE
    ):
        raise ProductionPlanningError("production_catalog_query_invalid")
    return {**payload, "search": search}


def validate_production_plan_input(payload: Any) -> dict[str, Any]:
    expected = {
        "planId",
        "ownerCharacterId",
        "blueprintTypeId",
        "blueprintItemId",
        "stepBlueprintAssignments",
        "facilityId",
        "materialLocationId",
        "stepSupplyModes",
        "activity",
        "productTypeId",
        "targetQuantity",
        "priority",
        "note",
    }
    if not isinstance(payload, Mapping) or set(payload) != expected:
        raise ProductionPlanningError("production_plan_input_invalid")
    plan_id = payload["planId"]
    blueprint_item_id = payload["blueprintItemId"]
    raw_step_assignments = payload["stepBlueprintAssignments"]
    facility_id = payload["facilityId"]
    material_location_id = payload["materialLocationId"]
    raw_supply_modes = payload["stepSupplyModes"]
    note = payload["note"]
    if note is not None:
        try:
            note = _normalized_text(note, 240) or None
        except ProductionPlanningError as error:
            raise ProductionPlanningError("production_plan_input_invalid") from error
    if (
        plan_id is not None
        and not _positive_int(plan_id)
        or blueprint_item_id is not None
        and not _positive_int(blueprint_item_id)
        or not isinstance(raw_step_assignments, list)
        or len(raw_step_assignments) > MAX_STEP_BLUEPRINT_ASSIGNMENTS
        or facility_id is not None
        and not _positive_int(facility_id)
        or material_location_id is not None
        and not _positive_int(material_location_id)
        or material_location_id is not None
        and facility_id is None
        or not isinstance(raw_supply_modes, list)
        or len(raw_supply_modes) > MAX_STEP_SUPPLY_MODES
        or not _positive_int(payload["ownerCharacterId"])
        or not _positive_int(payload["blueprintTypeId"])
        or payload["activity"] not in SUPPORTED_BLUEPRINT_ACTIVITIES
        or not _positive_int(payload["productTypeId"])
        or not _positive_int(payload["targetQuantity"])
        or not _non_negative_int(payload["priority"])
        or payload["priority"] > 999
    ):
        raise ProductionPlanningError("production_plan_input_invalid")
    step_assignments: list[dict[str, Any]] = []
    assignment_keys: set[tuple[int, str, int]] = set()
    assigned_item_ids: set[int] = set()
    root_key = (
        int(payload["blueprintTypeId"]),
        str(payload["activity"]),
        int(payload["productTypeId"]),
    )
    for assignment in raw_step_assignments:
        if not isinstance(assignment, Mapping) or set(assignment) != {
            "blueprintTypeId",
            "activity",
            "productTypeId",
            "blueprintItemId",
        }:
            raise ProductionPlanningError("production_plan_input_invalid")
        key = (
            assignment["blueprintTypeId"],
            assignment["activity"],
            assignment["productTypeId"],
        )
        item_id = assignment["blueprintItemId"]
        if (
            not _positive_int(key[0])
            or key[1] != "manufacturing"
            or not _positive_int(key[2])
            or not _positive_int(item_id)
            or key == root_key
            or key in assignment_keys
            or item_id in assigned_item_ids
            or item_id == blueprint_item_id
        ):
            raise ProductionPlanningError("production_plan_input_invalid")
        assignment_keys.add(key)
        assigned_item_ids.add(int(item_id))
        step_assignments.append(
            {
                "blueprintTypeId": int(key[0]),
                "activity": str(key[1]),
                "productTypeId": int(key[2]),
                "blueprintItemId": int(item_id),
            }
        )
    step_assignments.sort(
        key=lambda value: (
            value["productTypeId"],
            value["activity"],
            value["blueprintTypeId"],
        )
    )
    step_supply_modes: list[dict[str, Any]] = []
    supply_keys: set[tuple[int, str, int]] = set()
    for supply in raw_supply_modes:
        if not isinstance(supply, Mapping) or set(supply) != {
            "blueprintTypeId",
            "activity",
            "productTypeId",
            "supplyMode",
        }:
            raise ProductionPlanningError("production_plan_input_invalid")
        key = (
            supply["blueprintTypeId"],
            supply["activity"],
            supply["productTypeId"],
        )
        if (
            not _positive_int(key[0])
            or key[1] not in SUPPORTED_BLUEPRINT_ACTIVITIES
            or not _positive_int(key[2])
            or supply["supplyMode"] not in SUPPLY_MODES
            or key == root_key
            or key in supply_keys
        ):
            raise ProductionPlanningError("production_plan_input_invalid")
        supply_keys.add(key)
        step_supply_modes.append(
            {
                "blueprintTypeId": int(key[0]),
                "activity": str(key[1]),
                "productTypeId": int(key[2]),
                "supplyMode": str(supply["supplyMode"]),
            }
        )
    step_supply_modes.sort(
        key=lambda value: (
            value["productTypeId"],
            value["activity"],
            value["blueprintTypeId"],
        )
    )
    return {
        **payload,
        "note": note,
        "stepBlueprintAssignments": step_assignments,
        "stepSupplyModes": step_supply_modes,
    }


def validate_production_plan_delete(payload: Any) -> int:
    if not isinstance(payload, Mapping) or set(payload) != {"planId"}:
        raise ProductionPlanningError("production_plan_delete_invalid")
    if not _positive_int(payload["planId"]):
        raise ProductionPlanningError("production_plan_delete_invalid")
    return int(payload["planId"])


def _sde_tables_available(connection: sqlite3.Connection) -> bool:
    names = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'sde_%'"
        )
    }
    return {
        "sde_types",
        "sde_blueprint_activities",
        "sde_blueprint_products",
        "sde_blueprint_materials",
    } <= names


def _checked_add(left: int, right: int) -> int:
    result = left + right
    if result > MAX_SAFE_INTEGER:
        raise ProductionPlanningError("production_plan_calculation_overflow")
    return result


def _checked_multiply(left: int, right: int) -> int:
    result = left * right
    if result > MAX_SAFE_INTEGER:
        raise ProductionPlanningError("production_plan_calculation_overflow")
    return result


def _material_quantity(base_quantity: int, runs: int, material_efficiency: int) -> int:
    """Apply EVE blueprint ME once to a complete job and round up to units.

    The percentage product has at most two decimal places, so integer ceiling is
    exact and avoids binary floating-point drift. Every run still consumes at
    least one unit of each material.
    """

    if (
        not _positive_int(base_quantity)
        or not _positive_int(runs)
        or not _non_negative_int(material_efficiency)
        or material_efficiency > 10
    ):
        raise ProductionPlanningError("production_material_efficiency_invalid")
    unmodified = _checked_multiply(base_quantity, runs)
    numerator = _checked_multiply(unmodified, 100 - material_efficiency)
    adjusted = (numerator + 99) // 100
    return max(runs, adjusted)


def _blueprint_time_seconds(
    base_time_seconds: int, runs: int, time_efficiency: int
) -> int:
    """Apply blueprint TE once to a complete job with exact integer ceiling."""

    if (
        not _positive_int(base_time_seconds)
        or not _positive_int(runs)
        or not _non_negative_int(time_efficiency)
        or time_efficiency > 20
    ):
        raise ProductionPlanningError("production_time_efficiency_invalid")
    base_total = _checked_multiply(base_time_seconds, runs)
    factor = 100 - time_efficiency
    whole_seconds = _checked_multiply(base_total // 100, factor)
    partial_seconds = ((base_total % 100) * factor + 99) // 100
    return max(1, _checked_add(whole_seconds, partial_seconds))


def _character_time_seconds(
    base_time_seconds: int,
    runs: int,
    time_efficiency: int,
    activity: str,
    active_levels: Mapping[int, int],
) -> int:
    """Apply blueprint TE and active character skills once to a complete job."""

    if (
        not _positive_int(base_time_seconds)
        or not _positive_int(runs)
        or not _non_negative_int(time_efficiency)
        or time_efficiency > 20
        or activity not in SUPPORTED_BLUEPRINT_ACTIVITIES
    ):
        raise ProductionPlanningError("production_character_time_invalid")
    levels = {
        skill_id: active_levels.get(skill_id, 0)
        for skill_id in (
            INDUSTRY_SKILL_ID,
            ADVANCED_INDUSTRY_SKILL_ID,
            REACTIONS_SKILL_ID,
        )
    }
    if any(
        not _non_negative_int(level) or level > 5 for level in levels.values()
    ):
        raise ProductionPlanningError("production_character_time_invalid")
    factors = [100 - time_efficiency]
    if activity == "manufacturing":
        factors.extend(
            (
                100 - 4 * levels[INDUSTRY_SKILL_ID],
                100 - 3 * levels[ADVANCED_INDUSTRY_SKILL_ID],
            )
        )
    else:
        factors.append(100 - 4 * levels[REACTIONS_SKILL_ID])
    numerator = _checked_multiply(base_time_seconds, runs)
    denominator = 1
    for factor in factors:
        numerator *= factor
        denominator *= 100
    return max(1, (numerator + denominator - 1) // denominator)


def _time_skills(
    activity: str, source: SkillSource | None
) -> list[dict[str, Any]]:
    definitions = (
        (
            (INDUSTRY_SKILL_ID, "Industry", 4),
            (ADVANCED_INDUSTRY_SKILL_ID, "Advanced Industry", 3),
        )
        if activity == "manufacturing"
        else ((REACTIONS_SKILL_ID, "Reactions", 4),)
    )
    return [
        {
            "skillId": skill_id,
            "skillName": name,
            "activeLevel": (
                None if source is None else source.active_levels.get(skill_id, 0)
            ),
            "percentPerLevel": percent,
        }
        for skill_id, name, percent in definitions
    ]


def _skill_source(
    connection: sqlite3.Connection, character_id: int
) -> SkillSource | None:
    row = connection.execute(
        "SELECT cached_snapshots.id,cached_snapshots.sync_run_id,"
        "cached_snapshots.payload_json,cached_snapshots.observed_at "
        "FROM cached_snapshots JOIN sync_runs "
        "ON sync_runs.id=cached_snapshots.sync_run_id "
        "WHERE cached_snapshots.resource=? AND sync_runs.source='character_skills' "
        "AND sync_runs.status='completed' "
        "ORDER BY cached_snapshots.observed_at DESC,cached_snapshots.id DESC LIMIT 1",
        (f"character_skills:{character_id}",),
    ).fetchone()
    if row is None:
        return None
    try:
        payload = json.loads(str(row[2]))
        if (
            not isinstance(payload, Mapping)
            or payload.get("characterId") != character_id
            or not isinstance(row[3], str)
            or not str(row[3]).strip()
            or len(str(row[3])) > 64
        ):
            raise ProductionPlanningError("production_skill_snapshot_invalid")
        validated = validate_character_skills(
            {key: value for key, value in payload.items() if key != "characterId"}
        )
    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
        CharacterSkillSyncError,
    ) as error:
        raise ProductionPlanningError("production_skill_snapshot_invalid") from error
    return SkillSource(
        character_id=character_id,
        snapshot_id=int(row[0]),
        sync_run_id=int(row[1]),
        observed_at=str(row[3]),
        active_levels={
            int(skill["skill_id"]): int(skill["active_skill_level"])
            for skill in validated["skills"]
        },
    )


def _load_skill_sources(
    connection: sqlite3.Connection, plan_rows: list[sqlite3.Row]
) -> dict[int, SkillSource | None]:
    return {
        character_id: _skill_source(connection, character_id)
        for character_id in sorted(
            {int(row["owner_character_id"]) for row in plan_rows}
        )
    }


def _skill_evidence(source: SkillSource | None) -> dict[str, Any]:
    return {
        "characterSkillState": "snapshot-missing" if source is None else "ready",
        "skillSnapshotId": None if source is None else source.snapshot_id,
        "skillSyncRunId": None if source is None else source.sync_run_id,
        "skillObservedAt": None if source is None else source.observed_at,
    }


def _load_production_job_sources(
    connection: sqlite3.Connection,
) -> dict[int, dict[str, Any]]:
    try:
        return load_latest_job_snapshots(connection)
    except IndustryJobEvidenceError as error:
        raise ProductionPlanningError("production_job_snapshot_invalid") from error


def _load_production_facilities(
    connection: sqlite3.Connection,
) -> tuple[bool, dict[int, dict[str, Any]]]:
    snapshot_available = connection.execute(
        "SELECT 1 FROM cached_snapshots JOIN sync_runs "
        "ON sync_runs.id=cached_snapshots.sync_run_id "
        "WHERE cached_snapshots.resource='industry_facilities' "
        "AND sync_runs.source='industry_facilities' "
        "AND sync_runs.status='completed' LIMIT 1"
    ).fetchone() is not None
    try:
        return snapshot_available, industry_facility_index(connection)
    except IndustryFacilityViewError as error:
        raise ProductionPlanningError("production_facility_snapshot_invalid") from error


def _empty_facility_evidence(
    state: str,
    job_source: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if state not in FACILITY_STATES:
        raise ProductionPlanningError("production_facility_evidence_invalid")
    return {
        "state": state,
        "evidence": "none",
        "jobId": None,
        "jobStatus": None,
        "facilityId": None,
        "facilityName": None,
        "facilityKind": None,
        "facilityAccess": None,
        "solarSystemId": None,
        "solarSystemName": None,
        "securityStatus": None,
        "securityClass": None,
        "systemCostIndex": None,
        "jobSnapshotId": None if job_source is None else int(job_source["snapshotId"]),
        "jobSyncRunId": None if job_source is None else int(job_source["syncRunId"]),
        "jobObservedAt": None if job_source is None else str(job_source["observedAt"]),
        "facilitySnapshotId": None,
        "facilitySyncRunId": None,
        "facilityObservedAt": None,
    }


def _facility_evidence(
    recipe: Recipe,
    blueprint_item_id: int | None,
    job_source: Mapping[str, Any] | None,
    facility_snapshot_available: bool,
    facilities: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    """Resolve the strongest personal-job facility evidence for one recipe step."""

    if job_source is None:
        return _empty_facility_evidence("job-snapshot-missing", None)
    matching_jobs = [
        job
        for job in job_source["jobs"]
        if int(job["blueprint_type_id"]) == recipe.blueprint_type_id
        and int(job["activity_id"]) in PRODUCTION_JOB_ACTIVITY_IDS[recipe.activity]
    ]
    if not matching_jobs:
        return _empty_facility_evidence("job-missing", job_source)

    def rank(job: Mapping[str, Any]) -> tuple[bool, bool, datetime, int]:
        return (
            blueprint_item_id is not None
            and int(job["blueprint_id"]) == blueprint_item_id,
            str(job["status"]) in ACTIVE_JOB_STATUSES,
            parse_timestamp(job["start_date"]),
            int(job["job_id"]),
        )

    job = max(matching_jobs, key=rank)
    exact_blueprint = (
        blueprint_item_id is not None
        and int(job["blueprint_id"]) == blueprint_item_id
    )
    active = str(job["status"]) in ACTIVE_JOB_STATUSES
    evidence = (
        "assigned-blueprint-job"
        if exact_blueprint
        else "active-blueprint-type-job"
        if active
        else "latest-blueprint-type-job"
    )
    base = {
        **_empty_facility_evidence(
            "facility-snapshot-missing"
            if not facility_snapshot_available
            else "facility-missing",
            job_source,
        ),
        "evidence": evidence,
        "jobId": int(job["job_id"]),
        "jobStatus": str(job["status"]),
        "facilityId": int(job["facility_id"]),
    }
    facility = facilities.get(int(job["facility_id"]))
    if facility is None:
        return base
    state = (
        "ready"
        if facility["access"] in {"public", "available"}
        else "facility-unavailable"
    )
    return {
        **base,
        "state": state,
        "facilityName": facility["facilityName"],
        "facilityKind": facility["kind"],
        "facilityAccess": facility["access"],
        "solarSystemId": facility["solarSystemId"],
        "solarSystemName": facility["solarSystemName"],
        "securityStatus": facility["securityStatus"],
        "securityClass": facility["securityClass"],
        "systemCostIndex": facility["costIndices"].get(recipe.activity),
        "facilitySnapshotId": int(facility["snapshotId"]),
        "facilitySyncRunId": int(facility["syncRunId"]),
        "facilityObservedAt": str(facility["observedAt"]),
    }


def _blueprint_source(
    connection: sqlite3.Connection, character_id: int
) -> BlueprintSource | None:
    row = connection.execute(
        "SELECT cached_snapshots.id,cached_snapshots.sync_run_id,"
        "cached_snapshots.payload_json,cached_snapshots.observed_at "
        "FROM cached_snapshots JOIN sync_runs "
        "ON sync_runs.id=cached_snapshots.sync_run_id "
        "WHERE cached_snapshots.resource=? AND sync_runs.status='completed' "
        "ORDER BY cached_snapshots.observed_at DESC,cached_snapshots.id DESC LIMIT 1",
        (f"character_blueprints:{character_id}",),
    ).fetchone()
    if row is None:
        return None
    try:
        payload = json.loads(str(row[2]))
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ProductionPlanningError("production_blueprint_snapshot_invalid") from error
    if (
        not isinstance(payload, Mapping)
        or payload.get("characterId") != character_id
        or not isinstance(payload.get("blueprints"), list)
    ):
        raise ProductionPlanningError("production_blueprint_snapshot_invalid")
    items: dict[int, BlueprintItem] = {}
    for raw_item in payload["blueprints"]:
        if not isinstance(raw_item, Mapping):
            raise ProductionPlanningError("production_blueprint_snapshot_invalid")
        try:
            item_id = int(raw_item["item_id"])
            type_id = int(raw_item["type_id"])
            quantity = int(raw_item["quantity"])
            material_efficiency = int(raw_item["material_efficiency"])
            time_efficiency = int(raw_item["time_efficiency"])
            runs = int(raw_item["runs"])
            location_id = int(raw_item["location_id"])
            location_flag = str(raw_item["location_flag"])
        except (KeyError, TypeError, ValueError) as error:
            raise ProductionPlanningError("production_blueprint_snapshot_invalid") from error
        if (
            not _positive_int(item_id)
            or not _positive_int(type_id)
            or item_id in items
            or quantity == 0
            or quantity < -2
            or quantity > MAX_SAFE_INTEGER
            or not 0 <= material_efficiency <= 10
            or not 0 <= time_efficiency <= 20
            or not -1 <= runs <= MAX_SAFE_INTEGER
            or not _positive_int(location_id)
            or not location_flag
            or len(location_flag) > 100
        ):
            raise ProductionPlanningError("production_blueprint_snapshot_invalid")
        items[item_id] = BlueprintItem(
            item_id=item_id,
            type_id=type_id,
            kind="copy" if quantity == -2 else "original",
            material_efficiency=material_efficiency,
            time_efficiency=time_efficiency,
            runs=runs,
            location_id=location_id,
            location_flag=location_flag,
        )
    return BlueprintSource(
        character_id=character_id,
        snapshot_id=int(row[0]),
        sync_run_id=int(row[1]),
        observed_at=str(row[3]),
        items=items,
    )


def _load_blueprint_sources(
    connection: sqlite3.Connection, plan_rows: list[sqlite3.Row]
) -> dict[int, BlueprintSource | None]:
    return {
        character_id: _blueprint_source(connection, character_id)
        for character_id in sorted(
            {int(row["owner_character_id"]) for row in plan_rows}
        )
    }


def _blueprint_candidate(item: BlueprintItem, required_runs: int) -> dict[str, Any]:
    suitable = item.kind == "original" or item.runs >= required_runs
    return {
        "itemId": item.item_id,
        "kind": item.kind,
        "materialEfficiency": item.material_efficiency,
        "timeEfficiency": item.time_efficiency,
        "runs": item.runs,
        "locationId": item.location_id,
        "locationFlag": item.location_flag,
        "suitable": suitable,
        "reason": "ready" if suitable else "runs-insufficient",
    }


def _blueprint_assignment_for_recipe(
    blueprint_type_id: int,
    assigned_id: int | None,
    source: BlueprintSource | None,
    required_runs: int,
) -> dict[str, Any]:
    matching = [] if source is None else [
        item for item in source.items.values() if item.type_id == blueprint_type_id
    ]
    matching.sort(
        key=lambda item: (
            not (item.kind == "original" or item.runs >= required_runs),
            -item.material_efficiency,
            item.kind != "original",
            -(MAX_SAFE_INTEGER if item.kind == "original" else item.runs),
            item.item_id,
        )
    )
    candidate_count = len(matching)
    candidates = matching[:MAX_BLUEPRINT_CANDIDATES]
    assigned = None if source is None or assigned_id is None else source.items.get(int(assigned_id))
    if assigned is not None and assigned.type_id == blueprint_type_id and assigned not in candidates:
        candidates = [*candidates[: MAX_BLUEPRINT_CANDIDATES - 1], assigned]
    if source is None:
        state = "snapshot-missing"
    elif assigned_id is None:
        state = "unassigned"
    elif assigned is None:
        state = "missing"
    elif assigned.type_id != blueprint_type_id:
        state = "type-mismatch"
    elif assigned.kind == "copy" and assigned.runs < required_runs:
        state = "runs-insufficient"
    else:
        state = "ready"
    return {
        "blueprintAssignmentState": state,
        "blueprintItemId": None if assigned_id is None else int(assigned_id),
        "blueprintKind": None if assigned is None else assigned.kind,
        "blueprintMaterialEfficiency": None if assigned is None else assigned.material_efficiency,
        "blueprintTimeEfficiency": None if assigned is None else assigned.time_efficiency,
        "blueprintRuns": None if assigned is None else assigned.runs,
        "blueprintLocationId": None if assigned is None else assigned.location_id,
        "blueprintLocationFlag": None if assigned is None else assigned.location_flag,
        "blueprintSnapshotId": None if source is None else source.snapshot_id,
        "blueprintSyncRunId": None if source is None else source.sync_run_id,
        "blueprintObservedAt": None if source is None else source.observed_at,
        "blueprintCandidateCount": candidate_count,
        "blueprintCandidates": [
            _blueprint_candidate(item, required_runs) for item in candidates
        ],
    }


def _blueprint_assignment(
    plan: Mapping[str, Any],
    source: BlueprintSource | None,
    required_runs: int,
) -> dict[str, Any]:
    assigned_id = (
        plan["blueprint_item_id"] if "blueprint_item_id" in plan.keys() else None
    )
    return _blueprint_assignment_for_recipe(
        int(plan["blueprint_type_id"]),
        None if assigned_id is None else int(assigned_id),
        source,
        required_runs,
    )


def _step_blueprint_assignments(
    connection: sqlite3.Connection, plan_id: int
) -> dict[tuple[int, str, int], int]:
    if not _positive_int(plan_id):
        raise ProductionPlanningError("production_plan_input_invalid")
    return {
        (int(row[0]), str(row[1]), int(row[2])): int(row[3])
        for row in connection.execute(
            "SELECT blueprint_type_id,activity,product_type_id,blueprint_item_id "
            "FROM production_plan_step_blueprints WHERE plan_id=? "
            "ORDER BY product_type_id,activity,blueprint_type_id",
            (plan_id,),
        )
    }


def _load_step_blueprint_assignments(
    connection: sqlite3.Connection,
) -> dict[int, dict[tuple[int, str, int], int]]:
    result: dict[int, dict[tuple[int, str, int], int]] = defaultdict(dict)
    for row in connection.execute(
        "SELECT plan_id,blueprint_type_id,activity,product_type_id,blueprint_item_id "
        "FROM production_plan_step_blueprints "
        "ORDER BY plan_id,product_type_id,activity,blueprint_type_id"
    ):
        plan_id = int(row[0])
        key = (int(row[1]), str(row[2]), int(row[3]))
        if key in result[plan_id]:
            raise ProductionPlanningError("production_blueprint_assignment_invalid")
        result[plan_id][key] = int(row[4])
    return dict(result)


def _step_supply_modes(
    connection: sqlite3.Connection, plan_id: int
) -> dict[tuple[int, str, int], str]:
    if not _positive_int(plan_id):
        raise ProductionPlanningError("production_plan_input_invalid")
    return {
        (int(row[0]), str(row[1]), int(row[2])): str(row[3])
        for row in connection.execute(
            "SELECT blueprint_type_id,activity,product_type_id,supply_mode "
            "FROM production_plan_step_supply_modes WHERE plan_id=? "
            "ORDER BY product_type_id,activity,blueprint_type_id",
            (plan_id,),
        )
    }


def _load_step_supply_modes(
    connection: sqlite3.Connection,
) -> dict[int, dict[tuple[int, str, int], str]]:
    result: dict[int, dict[tuple[int, str, int], str]] = defaultdict(dict)
    for row in connection.execute(
        "SELECT plan_id,blueprint_type_id,activity,product_type_id,supply_mode "
        "FROM production_plan_step_supply_modes "
        "ORDER BY plan_id,product_type_id,activity,blueprint_type_id"
    ):
        plan_id = int(row[0])
        key = (int(row[1]), str(row[2]), int(row[3]))
        mode = str(row[4])
        if key in result[plan_id] or mode not in SUPPLY_MODES:
            raise ProductionPlanningError("production_supply_mode_invalid")
        result[plan_id][key] = mode
    return dict(result)


def _load_recipes(connection: sqlite3.Connection) -> tuple[
    dict[int, list[Recipe]], dict[tuple[int, str, int], Recipe]
]:
    activity_rows = list(
        connection.execute(
            "SELECT activity.blueprint_type_id,blueprint.name AS blueprint_name,"
            "activity.activity,activity.time_seconds,product.product_type_id,"
            "product_type.name AS product_name,product.quantity "
            "FROM sde_blueprint_activities activity "
            "JOIN sde_types blueprint ON blueprint.type_id=activity.blueprint_type_id "
            "JOIN sde_blueprint_products product "
            "ON product.blueprint_type_id=activity.blueprint_type_id "
            "AND product.activity=activity.activity "
            "JOIN sde_types product_type ON product_type.type_id=product.product_type_id "
            "ORDER BY product.product_type_id,activity.activity,activity.blueprint_type_id"
        )
    )
    products: dict[tuple[int, str], list[tuple[int, str, int]]] = defaultdict(list)
    for row in connection.execute(
        "SELECT product.blueprint_type_id,product.activity,product.product_type_id,"
        "type.name,product.quantity FROM sde_blueprint_products product "
        "JOIN sde_types type ON type.type_id=product.product_type_id "
        "ORDER BY product.blueprint_type_id,product.activity,type.name COLLATE NOCASE,"
        "product.product_type_id"
    ):
        products[(int(row[0]), str(row[1]))].append(
            (int(row[2]), str(row[3]), int(row[4]))
        )
    materials: dict[tuple[int, str], list[tuple[int, str, int]]] = defaultdict(list)
    for row in connection.execute(
        "SELECT material.blueprint_type_id,material.activity,material.material_type_id,"
        "type.name,material.quantity FROM sde_blueprint_materials material "
        "JOIN sde_types type ON type.type_id=material.material_type_id "
        "ORDER BY material.blueprint_type_id,material.activity,type.name COLLATE NOCASE,"
        "material.material_type_id"
    ):
        materials[(int(row[0]), str(row[1]))].append(
            (int(row[2]), str(row[3]), int(row[4]))
        )
    by_product: dict[int, list[Recipe]] = defaultdict(list)
    by_exact: dict[tuple[int, str, int], Recipe] = {}
    for row in activity_rows:
        key = (int(row[0]), str(row[2]))
        recipe = Recipe(
            blueprint_type_id=key[0],
            blueprint_name=str(row[1]),
            activity=key[1],
            base_time_seconds=int(row[3]),
            product_type_id=int(row[4]),
            product_name=str(row[5]),
            output_quantity=int(row[6]),
            products=tuple(products[key]),
            materials=tuple(materials[key]),
        )
        by_product[recipe.product_type_id].append(recipe)
        by_exact[(recipe.blueprint_type_id, recipe.activity, recipe.product_type_id)] = recipe
    for recipes in by_product.values():
        recipes.sort(key=lambda item: (item.activity != "manufacturing", item.blueprint_type_id))
    return dict(by_product), by_exact


def _fallback_name(connection: sqlite3.Connection, type_id: int) -> str:
    if _sde_tables_available(connection):
        row = connection.execute(
            "SELECT name FROM sde_types WHERE type_id=?", (type_id,)
        ).fetchone()
        if row is not None:
            return str(row[0])
    row = connection.execute(
        "SELECT name FROM resolved_type_names WHERE type_id=?", (type_id,)
    ).fetchone()
    return str(row[0]) if row is not None else f"Type #{type_id}"


def _inventory_payload(raw: Any, error_code: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ProductionPlanningError(error_code) from error
    if not isinstance(payload, Mapping):
        raise ProductionPlanningError(error_code)
    return payload


def _inventory_timestamp(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip() or raw.strip() != raw or len(raw) > 64:
        raise ProductionPlanningError("production_inventory_snapshot_invalid")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise ProductionPlanningError("production_inventory_snapshot_invalid") from error
    if parsed.tzinfo is None:
        raise ProductionPlanningError("production_inventory_snapshot_invalid")
    return raw


def _inventory_location_paths(
    connection: sqlite3.Connection,
    character_id: int,
    asset_snapshot_id: int,
) -> tuple[bool, dict[int, dict[str, Any]]]:
    rows = connection.execute(
        "SELECT cached_snapshots.payload_json FROM cached_snapshots "
        "JOIN sync_runs ON sync_runs.id=cached_snapshots.sync_run_id "
        "WHERE cached_snapshots.resource=? AND sync_runs.status='completed' "
        "ORDER BY cached_snapshots.observed_at DESC,cached_snapshots.id DESC",
        (f"asset_locations:{character_id}",),
    )
    for row in rows:
        payload = _inventory_payload(
            row[0], "production_inventory_location_snapshot_invalid"
        )
        if payload.get("assetSnapshotId") != asset_snapshot_id:
            continue
        if payload.get("characterId") != character_id or not isinstance(
            payload.get("locations"), list
        ):
            raise ProductionPlanningError(
                "production_inventory_location_snapshot_invalid"
            )
        locations: dict[int, dict[str, Any]] = {}
        for raw_location in payload["locations"]:
            if not isinstance(raw_location, Mapping):
                raise ProductionPlanningError(
                    "production_inventory_location_snapshot_invalid"
                )
            item_id = raw_location.get("itemId")
            status = raw_location.get("status")
            path = raw_location.get("path")
            if (
                not _positive_int(item_id)
                or status not in ASSET_LOCATION_STATUSES[:-1]
                or not isinstance(path, list)
                or not 1 <= len(path) <= 64
                or item_id in locations
            ):
                raise ProductionPlanningError(
                    "production_inventory_location_snapshot_invalid"
                )
            labels: list[str] = []
            nodes: list[dict[str, Any]] = []
            for node in path:
                if not isinstance(node, Mapping):
                    raise ProductionPlanningError(
                        "production_inventory_location_snapshot_invalid"
                    )
                location_id = node.get("locationId")
                kind = node.get("kind")
                name = node.get("name")
                access = node.get("access")
                if (
                    not _positive_int(location_id)
                    or not isinstance(kind, str)
                    or not kind.strip()
                    or kind.strip() != kind
                    or len(kind) > 40
                    or not isinstance(access, str)
                    or not access.strip()
                    or access.strip() != access
                    or len(access) > 40
                    or not (
                        name is None
                        or isinstance(name, str)
                        and bool(name.strip())
                        and name.strip() == name
                        and len(name) <= 200
                    )
                ):
                    raise ProductionPlanningError(
                        "production_inventory_location_snapshot_invalid"
                    )
                label = str(name) if name is not None else f"{kind} #{location_id}"
                labels.append(label)
                nodes.append(
                    {
                        "locationId": int(location_id),
                        "kind": str(kind),
                        "name": label,
                        "access": str(access),
                    }
                )
            locations[int(item_id)] = {
                "status": str(status),
                "path": " / ".join(labels),
                "nodes": tuple(nodes),
            }
        return True, locations
    return False, {}


def _facility_from_nodes(nodes: tuple[dict[str, Any], ...]) -> dict[str, Any] | None:
    for node in reversed(nodes):
        if node["kind"] in {"station", "structure"}:
            return node
    return None


def _production_inventory_path_is_eligible(
    nodes: tuple[dict[str, Any], ...],
) -> bool:
    facility_seen = False
    for node in nodes:
        if node["kind"] in {"station", "structure"}:
            facility_seen = True
            continue
        if facility_seen and node["kind"] != "container":
            return False
    return facility_seen


def _inventory_facilities(
    character_id: int,
    locations: Mapping[int, Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    facilities: dict[int, dict[str, Any]] = {}
    for location in locations.values():
        nodes = tuple(location["nodes"])
        facility_node = _facility_from_nodes(nodes)
        if facility_node is None:
            continue
        facility_id = int(facility_node["locationId"])
        facility = facilities.setdefault(
            facility_id,
            {
                "ownerCharacterId": character_id,
                "facilityId": facility_id,
                "facilityName": str(facility_node["name"]),
                "facilityKind": str(facility_node["kind"]),
                "facilityAccess": str(facility_node["access"]),
                "locationStatus": str(location["status"]),
                "materialLocations": {},
            },
        )
        facility["materialLocations"].setdefault(
            facility_id,
            {
                "locationId": facility_id,
                "locationName": str(facility_node["name"]),
                "locationPath": str(facility_node["name"]),
                "locationKind": "facility",
            },
        )
        labels: list[str] = []
        facility_seen = False
        selectable = True
        for node in nodes:
            labels.append(str(node["name"]))
            if node["kind"] in {"station", "structure"}:
                facility_seen = True
                selectable = True
                continue
            if not facility_seen:
                continue
            if node["kind"] != "container":
                selectable = False
                continue
            if not selectable:
                continue
            location_id = int(node["locationId"])
            facility["materialLocations"].setdefault(
                location_id,
                {
                    "locationId": location_id,
                    "locationName": str(node["name"]),
                    "locationPath": " / ".join(labels),
                    "locationKind": "container",
                },
            )
    result: list[dict[str, Any]] = []
    for facility in sorted(
        facilities.values(),
        key=lambda value: (str(value["facilityName"]).casefold(), value["facilityId"]),
    )[:MAX_PRODUCTION_FACILITIES]:
        material_locations = sorted(
            facility.pop("materialLocations").values(),
            key=lambda value: (
                value["locationKind"] != "facility",
                str(value["locationPath"]).casefold(),
                value["locationId"],
            ),
        )[:MAX_PRODUCTION_MATERIAL_LOCATIONS]
        result.append({**facility, "materialLocations": material_locations})
    return tuple(result)


def _inventory_source(
    connection: sqlite3.Connection,
    character_id: int,
    owner_name: str,
) -> InventorySource | None:
    row = connection.execute(
        "SELECT cached_snapshots.id,cached_snapshots.sync_run_id,"
        "cached_snapshots.payload_json,cached_snapshots.observed_at "
        "FROM cached_snapshots JOIN sync_runs "
        "ON sync_runs.id=cached_snapshots.sync_run_id "
        "WHERE cached_snapshots.resource=? AND sync_runs.status='completed' "
        "ORDER BY cached_snapshots.observed_at DESC,cached_snapshots.id DESC LIMIT 1",
        (f"character_assets:{character_id}",),
    ).fetchone()
    if row is None:
        return None
    snapshot_id = int(row[0])
    payload = _inventory_payload(row[2], "production_inventory_snapshot_invalid")
    if payload.get("characterId") != character_id or not isinstance(
        payload.get("assets"), list
    ):
        raise ProductionPlanningError("production_inventory_snapshot_invalid")
    observed_at = _inventory_timestamp(row[3])
    has_location_snapshot, locations = _inventory_location_paths(
        connection, character_id, snapshot_id
    )
    seen_items: set[int] = set()
    grouped: dict[int, dict[tuple[int, str, str, str], dict[str, Any]]] = defaultdict(dict)
    for raw_asset in payload["assets"]:
        if not isinstance(raw_asset, Mapping):
            raise ProductionPlanningError("production_inventory_snapshot_invalid")
        item_id = raw_asset.get("item_id")
        type_id = raw_asset.get("type_id")
        location_id = raw_asset.get("location_id")
        quantity = raw_asset.get("quantity")
        location_type = raw_asset.get("location_type")
        location_flag = raw_asset.get("location_flag")
        if (
            not _positive_int(item_id)
            or not _positive_int(type_id)
            or not _positive_int(location_id)
            or not _non_negative_int(quantity)
            or not isinstance(location_type, str)
            or not location_type.strip()
            or location_type.strip() != location_type
            or len(location_type) > 40
            or not isinstance(location_flag, str)
            or not location_flag.strip()
            or location_flag.strip() != location_flag
            or len(location_flag) > 100
            or item_id in seen_items
        ):
            raise ProductionPlanningError("production_inventory_snapshot_invalid")
        seen_items.add(int(item_id))
        if int(quantity) == 0:
            continue
        location = locations.get(int(item_id))
        status = "pending" if location is None else str(location["status"])
        path = "" if location is None else str(location["path"])
        nodes = () if location is None else tuple(location["nodes"])
        facility = _facility_from_nodes(nodes)
        facility_id = None if facility is None else int(facility["locationId"])
        path_location_ids = tuple(int(node["locationId"]) for node in nodes)
        key = (int(location_id), status, path, location_flag)
        current = grouped[int(type_id)].get(key)
        if current is None:
            grouped[int(type_id)][key] = {
                "ownerCharacterId": character_id,
                "ownerName": owner_name,
                "locationId": int(location_id),
                "locationStatus": status,
                "locationPath": path,
                "locationFlag": location_flag,
                "quantity": int(quantity),
                "positionCount": 1,
                "assetSnapshotId": snapshot_id,
                "assetSyncRunId": int(row[1]),
                "assetObservedAt": observed_at,
                "_facilityId": facility_id,
                "_pathLocationIds": path_location_ids,
                "_productionInventoryEligible": _production_inventory_path_is_eligible(
                    nodes
                ),
            }
        else:
            current["quantity"] = _checked_add(int(current["quantity"]), int(quantity))
            current["positionCount"] = _checked_add(int(current["positionCount"]), 1)
    if has_location_snapshot and set(locations) != seen_items:
        raise ProductionPlanningError("production_inventory_location_snapshot_invalid")
    stock = {
        type_id: tuple(
            sorted(
                values.values(),
                key=lambda item: (
                    str(item["locationPath"]).casefold(),
                    str(item["locationFlag"]).casefold(),
                    int(item["locationId"]),
                ),
            )
        )
        for type_id, values in grouped.items()
    }
    return InventorySource(
        character_id=character_id,
        owner_name=owner_name,
        snapshot_id=snapshot_id,
        sync_run_id=int(row[1]),
        observed_at=observed_at,
        stock=stock,
        facilities=_inventory_facilities(character_id, locations),
    )


def _load_inventory_sources(
    connection: sqlite3.Connection,
    plan_rows: list[sqlite3.Row],
) -> dict[int, InventorySource]:
    plan_owner_ids = {int(row["owner_character_id"]) for row in plan_rows}
    rows = connection.execute(
        "SELECT character_id,COALESCE(alias,name),enabled FROM characters ORDER BY character_id"
    )
    sources: dict[int, InventorySource] = {}
    for row in rows:
        character_id = int(row[0])
        if not bool(row[2]) and character_id not in plan_owner_ids:
            continue
        source = _inventory_source(connection, character_id, str(row[1]))
        if source is not None:
            sources[character_id] = source
    return sources


def _production_location_options(
    sources: Mapping[int, InventorySource],
) -> list[dict[str, Any]]:
    return [
        facility
        for character_id in sorted(sources)
        for facility in sources[character_id].facilities
    ][:MAX_PRODUCTION_FACILITIES]


def _location_selection(
    plan: Mapping[str, Any], source: InventorySource | None
) -> dict[str, Any]:
    facility_id = plan["facility_id"] if "facility_id" in plan.keys() else None
    material_location_id = (
        plan["material_location_id"]
        if "material_location_id" in plan.keys()
        else None
    )
    empty = {
        "facilityId": None if facility_id is None else int(facility_id),
        "facilityName": None,
        "materialLocationId": (
            None if material_location_id is None else int(material_location_id)
        ),
        "materialLocationName": None,
        "materialLocationPath": None,
    }
    if facility_id is None:
        return {**empty, "locationSelectionState": "unselected"}
    facility = next(
        (
            candidate
            for candidate in (() if source is None else source.facilities)
            if candidate["facilityId"] == int(facility_id)
        ),
        None,
    )
    if facility is None:
        return {**empty, "locationSelectionState": "facility-missing"}
    selected = {
        **empty,
        "facilityName": str(facility["facilityName"]),
    }
    if material_location_id is None:
        return {**selected, "locationSelectionState": "ready"}
    material_location = next(
        (
            candidate
            for candidate in facility["materialLocations"]
            if candidate["locationId"] == int(material_location_id)
        ),
        None,
    )
    if material_location is None:
        return {
            **selected,
            "locationSelectionState": "material-location-missing",
        }
    return {
        **selected,
        "materialLocationName": str(material_location["locationName"]),
        "materialLocationPath": str(material_location["locationPath"]),
        "locationSelectionState": "ready",
    }


def _inventory_locations(
    groups: tuple[dict[str, Any], ...],
) -> tuple[int, int, list[dict[str, Any]]]:
    quantity = 0
    positions = 0
    for group in groups:
        quantity = _checked_add(quantity, int(group["quantity"]))
        positions = _checked_add(positions, int(group["positionCount"]))
    return quantity, positions, [
        {key: value for key, value in group.items() if not key.startswith("_")}
        for group in groups[:MAX_INVENTORY_LOCATION_GROUPS]
    ]


def _selected_inventory_groups(
    source: InventorySource | None,
    plan: Mapping[str, Any],
    material_type_id: int,
) -> tuple[dict[str, Any], ...]:
    if source is None:
        return ()
    groups = source.stock.get(material_type_id, ())
    facility_id = plan["facility_id"] if "facility_id" in plan.keys() else None
    material_location_id = (
        plan["material_location_id"]
        if "material_location_id" in plan.keys()
        else None
    )
    if facility_id is None:
        return groups
    facility_groups = tuple(
        group
        for group in groups
        if group["_facilityId"] == int(facility_id)
        and bool(group["_productionInventoryEligible"])
    )
    if material_location_id is None:
        return facility_groups
    if int(material_location_id) == int(facility_id):
        return tuple(
            group
            for group in facility_groups
            if int(group["locationId"]) == int(facility_id)
        )
    return tuple(
        group
        for group in facility_groups
        if int(material_location_id) in group["_pathLocationIds"]
    )


def _reservation_group_key(
    character_id: int, material_type_id: int, group: Mapping[str, Any]
) -> tuple[int, int, int, str, str, str]:
    return (
        character_id,
        material_type_id,
        int(group["locationId"]),
        str(group["locationStatus"]),
        str(group["locationPath"]),
        str(group["locationFlag"]),
    )


def _reserved_in_group(
    reservations: Mapping[tuple[int, int, int, str, str, str], list[dict[str, Any]]],
    key: tuple[int, int, int, str, str, str],
) -> int:
    return sum(int(claim["quantity"]) for claim in reservations.get(key, ()))


def _free_inventory_quantity(
    source: InventorySource | None,
    plan: Mapping[str, Any],
    material_type_id: int,
    reservations: Mapping[
        tuple[int, int, int, str, str, str], list[dict[str, Any]]
    ],
) -> int:
    if source is None:
        return 0
    return sum(
        max(
            0,
            int(group["quantity"])
            - _reserved_in_group(
                reservations,
                _reservation_group_key(
                    source.character_id, material_type_id, group
                ),
            ),
        )
        for group in _selected_inventory_groups(source, plan, material_type_id)
    )


def _prior_reservation_claims(
    source: InventorySource,
    material_type_id: int,
    groups: tuple[dict[str, Any], ...],
    reservations: Mapping[
        tuple[int, int, int, str, str, str], list[dict[str, Any]]
    ],
) -> tuple[dict[str, Any], ...]:
    by_plan: dict[int, dict[str, Any]] = {}
    for group in groups:
        key = _reservation_group_key(source.character_id, material_type_id, group)
        for claim in reservations.get(key, ()):
            plan_id = int(claim["planId"])
            current = by_plan.get(plan_id)
            if current is None:
                by_plan[plan_id] = dict(claim)
            else:
                current["quantity"] = _checked_add(
                    int(current["quantity"]), int(claim["quantity"])
                )
    return tuple(by_plan.values())


def _apply_inventory(
    resolution: dict[str, Any],
    plan: sqlite3.Row,
    sources: Mapping[int, InventorySource],
    reservations: dict[
        tuple[int, int, int, str, str, str], list[dict[str, Any]]
    ],
) -> dict[str, Any]:
    owner_character_id = int(plan["owner_character_id"])
    if resolution["state"] != "ready":
        return {
            **resolution,
            "inventoryState": "not-applicable",
            "assetSnapshotId": None,
            "assetSyncRunId": None,
            "assetObservedAt": None,
        }
    source = sources.get(owner_character_id)
    materials: list[dict[str, Any]] = []
    for material in resolution["grossMaterials"]:
        material_type_id = int(material["typeId"])
        required_quantity = int(material["quantity"])
        available_groups = _selected_inventory_groups(
            source, plan, material_type_id
        )
        prior_reservations = (
            ()
            if source is None
            else _prior_reservation_claims(
                source,
                material_type_id,
                available_groups,
                reservations,
            )
        )
        available_quantity, available_positions, available_locations = _inventory_locations(
            available_groups
        )
        excluded_groups = tuple(
            group
            for character_id, candidate in sorted(
                sources.items(), key=lambda item: (item[1].owner_name.casefold(), item[0])
            )
            for group in candidate.stock.get(material_type_id, ())
            if character_id != owner_character_id or group not in available_groups
        )
        excluded_quantity, excluded_positions, excluded_locations = _inventory_locations(
            excluded_groups
        )
        if source is None:
            availability_state = "snapshot-missing"
            available: int | None = None
            reserved: int | None = None
            reserved_by_prior: int | None = None
            remaining: int | None = None
            inventory_shortage: int | None = None
            reservation_conflict: int | None = None
            missing: int | None = None
        else:
            available = available_quantity
            reserved_by_prior = sum(
                int(claim["quantity"]) for claim in prior_reservations
            )
            available_before_plan = _free_inventory_quantity(
                source, plan, material_type_id, reservations
            )
            reserved = min(required_quantity, available_before_plan)
            remaining = available_before_plan - reserved
            missing = required_quantity - reserved
            inventory_shortage = max(0, required_quantity - available)
            reservation_conflict = missing - inventory_shortage
            availability_state = "covered" if missing == 0 else "shortage"
            if reserved > 0:
                still_needed = reserved
                for group in available_groups:
                    key = _reservation_group_key(
                        owner_character_id, material_type_id, group
                    )
                    free = max(
                        0,
                        int(group["quantity"])
                        - _reserved_in_group(reservations, key),
                    )
                    allocation = min(still_needed, free)
                    if allocation == 0:
                        continue
                    reservations.setdefault(key, []).append(
                        {
                            "planId": int(plan["id"]),
                            "productTypeId": int(plan["product_type_id"]),
                            "productName": str(resolution["productName"]),
                            "priority": int(plan["priority"]),
                            "quantity": allocation,
                            "createdAt": str(plan["created_at"]),
                        }
                    )
                    still_needed -= allocation
                    if still_needed == 0:
                        break
                if still_needed != 0:
                    raise ProductionPlanningError("production_inventory_reservation_invalid")
        materials.append(
            {
                **material,
                "availabilityState": availability_state,
                "availableQuantity": available,
                "reservedQuantity": reserved,
                "reservedByPriorPlansQuantity": reserved_by_prior,
                "remainingQuantity": remaining,
                "inventoryShortageQuantity": inventory_shortage,
                "reservationConflictQuantity": reservation_conflict,
                "missingQuantity": missing,
                "priorReservationCount": len(prior_reservations),
                "priorReservations": list(
                    prior_reservations[:MAX_RESERVATION_CLAIMS]
                ),
                "availablePositionCount": available_positions,
                "availableLocationCount": len(available_groups),
                "availableLocations": available_locations,
                "excludedQuantity": excluded_quantity,
                "excludedPositionCount": excluded_positions,
                "excludedLocationCount": len(excluded_groups),
                "excludedLocations": excluded_locations,
            }
        )
    if not materials:
        inventory_state = "covered"
    elif source is None:
        inventory_state = "snapshot-missing"
    elif any(material["missingQuantity"] > 0 for material in materials):
        inventory_state = "shortage"
    else:
        inventory_state = "covered"
    return {
        **resolution,
        "grossMaterials": materials,
        "inventoryState": inventory_state,
        "assetSnapshotId": None if source is None else source.snapshot_id,
        "assetSyncRunId": None if source is None else source.sync_run_id,
        "assetObservedAt": None if source is None else source.observed_at,
    }


def _empty_resolution(
    connection: sqlite3.Connection,
    plan: Mapping[str, Any],
    state: str,
    build_number: str | None,
) -> dict[str, Any]:
    return {
        "state": state,
        "buildNumber": build_number,
        "blueprintName": _fallback_name(connection, int(plan["blueprint_type_id"])),
        "productName": _fallback_name(connection, int(plan["product_type_id"])),
        "steps": [],
        "supplyDecisions": [],
        "_supplyRecipeKeys": [],
        "grossMaterials": [],
        "warnings": [],
        "cycleTypeIds": [],
        "totalBaseTimeSeconds": None,
        "totalBlueprintTimeSeconds": None,
        "timeEfficiencySavingsSeconds": None,
        "totalCharacterTimeSeconds": None,
        "characterSkillTimeSavingsSeconds": None,
        "facilityState": "not-applicable",
    }


def resolve_production_plan(
    connection: sqlite3.Connection,
    plan: Mapping[str, Any],
    *,
    loaded_recipes: tuple[dict[int, list[Recipe]], dict[tuple[int, str, int], Recipe]]
    | None = None,
    blueprint_source: BlueprintSource | None = None,
    skill_source: SkillSource | None | object = _SKILL_SOURCE_UNSET,
    job_source: Mapping[str, Any] | None | object = _JOB_SOURCE_UNSET,
    facility_context: tuple[bool, Mapping[int, Mapping[str, Any]]] | None = None,
    step_blueprint_assignments: Mapping[tuple[int, str, int], int] | None = None,
    step_supply_modes: Mapping[tuple[int, str, int], str] | None = None,
    inventory_source: InventorySource | None = None,
    reservations: Mapping[
        tuple[int, int, int, str, str, str], list[dict[str, Any]]
    ]
    | None = None,
) -> dict[str, Any]:
    """Resolve one goal with a stable recipe tie-break and exact integer rounding."""

    build_number = current_sde_blueprint_activity_build(connection)
    owner_character_id = (
        int(plan["owner_character_id"])
        if "owner_character_id" in plan.keys()
        else None
    )
    if blueprint_source is None and owner_character_id is not None:
        blueprint_source = _blueprint_source(connection, owner_character_id)
    if skill_source is _SKILL_SOURCE_UNSET:
        skill_source = (
            _skill_source(connection, owner_character_id)
            if owner_character_id is not None
            else None
        )
    if skill_source is not None and not isinstance(skill_source, SkillSource):
        raise ProductionPlanningError("production_skill_snapshot_invalid")
    if job_source is _JOB_SOURCE_UNSET:
        job_source = (
            _load_production_job_sources(connection).get(owner_character_id)
            if owner_character_id is not None
            else None
        )
    if job_source is not None and not isinstance(job_source, Mapping):
        raise ProductionPlanningError("production_job_snapshot_invalid")
    if facility_context is None:
        facility_context = _load_production_facilities(connection)
    facility_snapshot_available, facilities = facility_context
    if step_blueprint_assignments is None:
        step_blueprint_assignments = (
            _step_blueprint_assignments(connection, int(plan["id"]))
            if "id" in plan.keys() and plan["id"] is not None
            else {}
        )
    if any(
        not isinstance(key, tuple)
        or len(key) != 3
        or not _positive_int(key[0])
        or key[1] not in SUPPORTED_BLUEPRINT_ACTIVITIES
        or not _positive_int(key[2])
        or not _positive_int(item_id)
        for key, item_id in step_blueprint_assignments.items()
    ):
        raise ProductionPlanningError("production_blueprint_assignment_invalid")
    if step_supply_modes is None:
        step_supply_modes = (
            _step_supply_modes(connection, int(plan["id"]))
            if "id" in plan.keys() and plan["id"] is not None
            else {}
        )
    if any(
        not isinstance(key, tuple)
        or len(key) != 3
        or not _positive_int(key[0])
        or key[1] not in SUPPORTED_BLUEPRINT_ACTIVITIES
        or not _positive_int(key[2])
        or mode not in SUPPLY_MODES
        for key, mode in step_supply_modes.items()
    ):
        raise ProductionPlanningError("production_supply_mode_invalid")
    initial_assignment = _blueprint_assignment(plan, blueprint_source, 1)
    skill_evidence = _skill_evidence(skill_source)
    if build_number is None or not _sde_tables_available(connection):
        return {
            **_empty_resolution(connection, plan, "sde-unavailable", build_number),
            **initial_assignment,
            **skill_evidence,
            "appliedMaterialEfficiency": 0,
            "appliedTimeEfficiency": 0,
        }
    by_product, by_exact = loaded_recipes or _load_recipes(connection)
    root_key = (
        int(plan["blueprint_type_id"]),
        str(plan["activity"]),
        int(plan["product_type_id"]),
    )
    root = by_exact.get(root_key)
    if root is None:
        return {
            **_empty_resolution(connection, plan, "recipe-missing", build_number),
            **initial_assignment,
            **skill_evidence,
            "appliedMaterialEfficiency": 0,
            "appliedTimeEfficiency": 0,
        }

    root_runs = (
        int(plan["target_quantity"]) + root.output_quantity - 1
    ) // root.output_quantity
    assignment = _blueprint_assignment(plan, blueprint_source, root_runs)
    applied_material_efficiency = (
        int(assignment["blueprintMaterialEfficiency"])
        if assignment["blueprintAssignmentState"] == "ready"
        and root.activity == "manufacturing"
        else 0
    )
    applied_time_efficiency = (
        int(assignment["blueprintTimeEfficiency"])
        if assignment["blueprintAssignmentState"] == "ready"
        and root.activity == "manufacturing"
        else 0
    )

    selected: dict[int, Recipe] = {root.product_type_id: root}
    warnings: list[dict[str, Any]] = []
    pending: deque[int] = deque([root.product_type_id])
    while pending:
        product_type_id = pending.popleft()
        recipe = selected[product_type_id]
        for material_type_id, material_name, _quantity in recipe.materials:
            if material_type_id in selected:
                continue
            candidates = by_product.get(material_type_id, [])
            if not candidates:
                continue
            selected[material_type_id] = candidates[0]
            if len(candidates) > 1:
                warnings.append(
                    {
                        "code": "alternative-recipe",
                        "typeId": material_type_id,
                        "typeName": material_name,
                        "selectedBlueprintTypeId": candidates[0].blueprint_type_id,
                        "candidateCount": len(candidates),
                    }
                )
            pending.append(material_type_id)
            if len(selected) > MAX_PLAN_STEPS:
                result = _empty_resolution(
                    connection, plan, "complexity-limit", build_number
                )
                result["blueprintName"] = root.blueprint_name
                result["productName"] = root.product_name
                result["warnings"] = warnings
                return {
                    **result,
                    **assignment,
                    **skill_evidence,
                    "appliedMaterialEfficiency": 0,
                    "appliedTimeEfficiency": 0,
                }

    edges: dict[int, set[int]] = {type_id: set() for type_id in selected}
    indegree = {type_id: 0 for type_id in selected}
    for type_id, recipe in selected.items():
        for material_type_id, _name, _quantity in recipe.materials:
            if material_type_id in selected and material_type_id not in edges[type_id]:
                edges[type_id].add(material_type_id)
                indegree[material_type_id] += 1

    ready: list[tuple[int, int]] = []
    for type_id, count in indegree.items():
        if count == 0:
            heapq.heappush(ready, (type_id != root.product_type_id, type_id))
    ordered: list[int] = []
    while ready:
        _root_rank, type_id = heapq.heappop(ready)
        ordered.append(type_id)
        for child in sorted(edges[type_id]):
            indegree[child] -= 1
            if indegree[child] == 0:
                heapq.heappush(ready, (child != root.product_type_id, child))
    if len(ordered) != len(selected):
        result = _empty_resolution(connection, plan, "cycle", build_number)
        result["blueprintName"] = root.blueprint_name
        result["productName"] = root.product_name
        result["warnings"] = warnings
        result["cycleTypeIds"] = sorted(
            type_id for type_id, count in indegree.items() if count > 0
        )
        return {
            **result,
            **assignment,
            **skill_evidence,
            "appliedMaterialEfficiency": 0,
            "appliedTimeEfficiency": 0,
        }

    required: dict[int, int] = defaultdict(int)
    required[root.product_type_id] = int(plan["target_quantity"])
    unmodified_required: dict[int, int] = defaultdict(int)
    unmodified_required[root.product_type_id] = int(plan["target_quantity"])
    gross: dict[int, tuple[str, int]] = {}
    unmodified_gross: dict[int, int] = {}
    steps: list[dict[str, Any]] = []
    supply_decisions: list[dict[str, Any]] = []
    reservation_view = {} if reservations is None else reservations
    total_base_time = 0
    total_blueprint_time = 0
    total_character_time: int | None = 0 if skill_source is not None else None
    for sequence, product_type_id in enumerate(ordered, start=1):
        recipe = selected[product_type_id]
        quantity_needed = required[product_type_id]
        recipe_key = (
            recipe.blueprint_type_id,
            recipe.activity,
            recipe.product_type_id,
        )
        is_root = recipe_key == root_key
        if quantity_needed == 0:
            continue
        supply_mode = "build" if is_root else step_supply_modes.get(
            recipe_key, "stock-first"
        )
        stock_available = (
            0
            if is_root
            else _free_inventory_quantity(
                inventory_source,
                plan,
                product_type_id,
                reservation_view,
            )
        )
        stock_quantity = (
            0 if is_root or supply_mode == "build" else min(quantity_needed, stock_available)
        )
        external_quantity = (
            quantity_needed
            if supply_mode == "stock-only"
            else stock_quantity
        )
        build_quantity = (
            quantity_needed
            if is_root or supply_mode == "build"
            else 0
            if supply_mode == "stock-only"
            else quantity_needed - stock_quantity
        )
        if not is_root:
            supply_decisions.append(
                {
                    "blueprintTypeId": recipe.blueprint_type_id,
                    "activity": recipe.activity,
                    "productTypeId": product_type_id,
                    "productName": recipe.product_name,
                    "supplyMode": supply_mode,
                    "requiredQuantity": quantity_needed,
                    "stockAvailableQuantity": stock_available,
                    "stockUsedQuantity": stock_quantity,
                    "buildQuantity": build_quantity,
                    "shortageQuantity": (
                        max(0, quantity_needed - stock_available)
                        if supply_mode == "stock-only"
                        else 0
                    ),
                    "blueprintRequired": build_quantity > 0,
                }
            )
        if external_quantity > 0:
            previous = gross.get(product_type_id, (recipe.product_name, 0))
            gross[product_type_id] = (
                recipe.product_name,
                _checked_add(previous[1], external_quantity),
            )
            unmodified_gross[product_type_id] = _checked_add(
                unmodified_gross.get(product_type_id, 0), external_quantity
            )
        if build_quantity == 0:
            continue
        quantity_needed = build_quantity
        runs = (quantity_needed + recipe.output_quantity - 1) // recipe.output_quantity
        unmodified_quantity_needed = max(
            quantity_needed,
            unmodified_required[product_type_id] - stock_quantity,
        )
        unmodified_runs = (
            unmodified_quantity_needed + recipe.output_quantity - 1
        ) // recipe.output_quantity
        produced_quantity = _checked_multiply(runs, recipe.output_quantity)
        step_assignment = (
            assignment
            if is_root
            else _blueprint_assignment_for_recipe(
                recipe.blueprint_type_id,
                step_blueprint_assignments.get(recipe_key),
                blueprint_source,
                runs,
            )
        )
        material_efficiency = (
            int(step_assignment["blueprintMaterialEfficiency"])
            if step_assignment["blueprintAssignmentState"] == "ready"
            and recipe.activity == "manufacturing"
            else 0
        )
        time_efficiency = (
            int(step_assignment["blueprintTimeEfficiency"])
            if step_assignment["blueprintAssignmentState"] == "ready"
            and recipe.activity == "manufacturing"
            else 0
        )
        direct_materials: list[dict[str, Any]] = []
        for material_type_id, material_name, base_quantity in recipe.materials:
            unmodified_quantity = _checked_multiply(runs, base_quantity)
            unmodified_plan_quantity = _checked_multiply(
                unmodified_runs, base_quantity
            )
            gross_quantity = _material_quantity(
                base_quantity, runs, material_efficiency
            )
            direct_materials.append(
                {
                    "typeId": material_type_id,
                    "typeName": material_name,
                    "quantityPerRun": base_quantity,
                    "unmodifiedGrossQuantity": unmodified_quantity,
                    "grossQuantity": gross_quantity,
                    "materialEfficiency": material_efficiency,
                    "materialEfficiencySavings": unmodified_quantity
                    - gross_quantity,
                    "producedByPlan": material_type_id in selected,
                }
            )
            if material_type_id in selected:
                required[material_type_id] = _checked_add(
                    required[material_type_id], gross_quantity
                )
                unmodified_required[material_type_id] = _checked_add(
                    unmodified_required[material_type_id],
                    unmodified_plan_quantity,
                )
            else:
                previous = gross.get(material_type_id, (material_name, 0))
                gross[material_type_id] = (
                    material_name,
                    _checked_add(previous[1], gross_quantity),
                )
                unmodified_gross[material_type_id] = _checked_add(
                    unmodified_gross.get(material_type_id, 0),
                    unmodified_plan_quantity,
                )
        step_time = _checked_multiply(runs, recipe.base_time_seconds)
        step_blueprint_time = _blueprint_time_seconds(
            recipe.base_time_seconds, runs, time_efficiency
        )
        step_character_time = (
            None
            if skill_source is None
            else _character_time_seconds(
                recipe.base_time_seconds,
                runs,
                time_efficiency,
                recipe.activity,
                skill_source.active_levels,
            )
        )
        step_facility_evidence = _facility_evidence(
            recipe,
            step_assignment["blueprintItemId"],
            job_source,
            facility_snapshot_available,
            facilities,
        )
        total_base_time = _checked_add(total_base_time, step_time)
        total_blueprint_time = _checked_add(
            total_blueprint_time, step_blueprint_time
        )
        if total_character_time is not None and step_character_time is not None:
            total_character_time = _checked_add(
                total_character_time, step_character_time
            )
        steps.append(
            {
                "sequence": sequence,
                "blueprintTypeId": recipe.blueprint_type_id,
                "blueprintName": recipe.blueprint_name,
                "activity": recipe.activity,
                "productTypeId": product_type_id,
                "productName": recipe.product_name,
                "requiredQuantity": build_quantity,
                "supplyMode": supply_mode,
                "stockUsedQuantity": stock_quantity,
                "outputQuantityPerRun": recipe.output_quantity,
                "runs": runs,
                "unmodifiedRuns": unmodified_runs,
                "runsSavedByMaterialEfficiency": unmodified_runs - runs,
                "producedQuantity": produced_quantity,
                "surplusQuantity": produced_quantity - quantity_needed,
                "baseTimeSecondsPerRun": recipe.base_time_seconds,
                "totalBaseTimeSeconds": step_time,
                "timeEfficiency": time_efficiency,
                "timeEfficiencyApplied": time_efficiency > 0,
                "totalBlueprintTimeSeconds": step_blueprint_time,
                "timeEfficiencySavingsSeconds": step_time - step_blueprint_time,
                "timeSkills": _time_skills(recipe.activity, skill_source),
                "characterSkillTimeApplied": (
                    step_character_time is not None
                    and step_character_time < step_blueprint_time
                ),
                "totalCharacterTimeSeconds": step_character_time,
                "characterSkillTimeSavingsSeconds": (
                    None
                    if step_character_time is None
                    else step_blueprint_time - step_character_time
                ),
                "recipeAlternatives": len(by_product.get(product_type_id, [])),
                "materialEfficiency": material_efficiency,
                "materialEfficiencyApplied": material_efficiency > 0,
                "blueprintAssignment": step_assignment,
                "facilityEvidence": step_facility_evidence,
                "materials": direct_materials,
            }
        )
    produced_type_ids = {int(step["productTypeId"]) for step in steps}
    execution_steps = [
        {
            **step,
            "sequence": sequence,
            "materials": [
                {
                    **material,
                    "producedByPlan": int(material["typeId"]) in produced_type_ids,
                }
                for material in step["materials"]
            ],
        }
        for sequence, step in enumerate(reversed(steps), start=1)
    ]
    ready_facilities = sum(
        step["facilityEvidence"]["state"] == "ready" for step in execution_steps
    )
    facility_state = (
        "ready"
        if ready_facilities == len(execution_steps)
        else "partial"
        if ready_facilities > 0
        else "missing"
    )
    return {
        "state": "ready",
        "buildNumber": build_number,
        "blueprintName": root.blueprint_name,
        "productName": root.product_name,
        "steps": execution_steps,
        "supplyDecisions": sorted(
            supply_decisions,
            key=lambda item: (item["productName"].casefold(), item["productTypeId"]),
        ),
        "_supplyRecipeKeys": sorted(
            (
                recipe.blueprint_type_id,
                recipe.activity,
                recipe.product_type_id,
            )
            for recipe in selected.values()
            if (
                recipe.blueprint_type_id,
                recipe.activity,
                recipe.product_type_id,
            )
            != root_key
        ),
        "grossMaterials": [
            {
                "typeId": type_id,
                "typeName": value[0],
                "quantity": value[1],
                "unmodifiedQuantity": unmodified_gross[type_id],
                "materialEfficiencySavings": unmodified_gross[type_id]
                - value[1],
            }
            for type_id, value in sorted(
                gross.items(), key=lambda item: (item[1][0].casefold(), item[0])
            )
        ],
        "warnings": sorted(warnings, key=lambda item: (item["typeName"].casefold(), item["typeId"])),
        "cycleTypeIds": [],
        "totalBaseTimeSeconds": total_base_time,
        "totalBlueprintTimeSeconds": total_blueprint_time,
        "timeEfficiencySavingsSeconds": total_base_time - total_blueprint_time,
        "totalCharacterTimeSeconds": total_character_time,
        "characterSkillTimeSavingsSeconds": (
            None
            if total_character_time is None
            else total_blueprint_time - total_character_time
        ),
        "facilityState": facility_state,
        **assignment,
        **skill_evidence,
        "appliedMaterialEfficiency": applied_material_efficiency,
        "appliedTimeEfficiency": applied_time_efficiency,
    }


def query_production_catalog(
    connection: sqlite3.Connection, raw_query: Any
) -> dict[str, Any]:
    query = validate_production_catalog_query(raw_query)
    build_number = current_sde_blueprint_activity_build(connection)
    empty = {
        "items": [],
        "total": 0,
        "offset": query["offset"],
        "limit": query["limit"],
        "activities": list(SUPPORTED_BLUEPRINT_ACTIVITIES),
        "buildNumber": build_number,
    }
    if build_number is None or not _sde_tables_available(connection):
        return empty
    where: list[str] = []
    parameters: list[Any] = []
    if query["search"]:
        escaped = (
            query["search"].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        where.append("(product_type.name LIKE ? ESCAPE '\\' COLLATE NOCASE OR blueprint.name LIKE ? ESCAPE '\\' COLLATE NOCASE)")
        parameters.extend([f"%{escaped}%", f"%{escaped}%"])
    if query["activity"] is not None:
        where.append("activity.activity=?")
        parameters.append(query["activity"])
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    joins = (
        "FROM sde_blueprint_activities activity "
        "JOIN sde_types blueprint ON blueprint.type_id=activity.blueprint_type_id "
        "JOIN sde_blueprint_products product ON product.blueprint_type_id=activity.blueprint_type_id "
        "AND product.activity=activity.activity "
        "JOIN sde_types product_type ON product_type.type_id=product.product_type_id "
    )
    total = int(
        connection.execute(f"SELECT COUNT(*) {joins}{where_sql}", parameters).fetchone()[0]
    )
    rows = connection.execute(
        "SELECT activity.blueprint_type_id,blueprint.name,activity.activity,"
        "activity.time_seconds,product.product_type_id,product_type.name,product.quantity,"
        "(SELECT COUNT(*) FROM sde_blueprint_materials material "
        "WHERE material.blueprint_type_id=activity.blueprint_type_id "
        "AND material.activity=activity.activity) "
        f"{joins}{where_sql} ORDER BY product_type.name COLLATE NOCASE,"
        "activity.activity,activity.blueprint_type_id,product.product_type_id LIMIT ? OFFSET ?",
        [*parameters, query["limit"], query["offset"]],
    )
    return {
        **empty,
        "items": [
            {
                "blueprintTypeId": int(row[0]),
                "blueprintName": str(row[1]),
                "activity": str(row[2]),
                "baseTimeSeconds": int(row[3]),
                "productTypeId": int(row[4]),
                "productName": str(row[5]),
                "outputQuantity": int(row[6]),
                "materialCount": int(row[7]),
            }
            for row in rows
        ],
        "total": total,
    }


def _plan_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            "SELECT plan.id,plan.owner_character_id,COALESCE(character.alias,character.name) "
            "AS owner_name,plan.blueprint_type_id,plan.blueprint_item_id,plan.facility_id,"
            "plan.material_location_id,plan.activity,plan.product_type_id,"
            "plan.target_quantity,plan.priority,plan.note,plan.created_at,plan.updated_at "
            "FROM production_plans plan JOIN characters character "
            "ON character.character_id=plan.owner_character_id ORDER BY plan.id"
        )
    )


def _serialize_plan(row: sqlite3.Row, resolution: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "planId": int(row["id"]),
        "ownerCharacterId": int(row["owner_character_id"]),
        "ownerName": str(row["owner_name"]),
        "blueprintTypeId": int(row["blueprint_type_id"]),
        "blueprintName": resolution["blueprintName"],
        "facilityId": resolution["facilityId"],
        "facilityName": resolution["facilityName"],
        "materialLocationId": resolution["materialLocationId"],
        "materialLocationName": resolution["materialLocationName"],
        "materialLocationPath": resolution["materialLocationPath"],
        "locationSelectionState": resolution["locationSelectionState"],
        "blueprintItemId": resolution["blueprintItemId"],
        "blueprintAssignmentState": resolution["blueprintAssignmentState"],
        "blueprintKind": resolution["blueprintKind"],
        "blueprintMaterialEfficiency": resolution["blueprintMaterialEfficiency"],
        "blueprintTimeEfficiency": resolution["blueprintTimeEfficiency"],
        "blueprintRuns": resolution["blueprintRuns"],
        "blueprintLocationId": resolution["blueprintLocationId"],
        "blueprintLocationFlag": resolution["blueprintLocationFlag"],
        "blueprintSnapshotId": resolution["blueprintSnapshotId"],
        "blueprintSyncRunId": resolution["blueprintSyncRunId"],
        "blueprintObservedAt": resolution["blueprintObservedAt"],
        "blueprintCandidateCount": resolution["blueprintCandidateCount"],
        "blueprintCandidates": resolution["blueprintCandidates"],
        "appliedMaterialEfficiency": resolution["appliedMaterialEfficiency"],
        "appliedTimeEfficiency": resolution["appliedTimeEfficiency"],
        "activity": str(row["activity"]),
        "productTypeId": int(row["product_type_id"]),
        "productName": resolution["productName"],
        "targetQuantity": int(row["target_quantity"]),
        "priority": int(row["priority"]),
        "note": None if row["note"] is None else str(row["note"]),
        "state": resolution["state"],
        "buildNumber": resolution["buildNumber"],
        "steps": resolution["steps"],
        "supplyDecisions": resolution["supplyDecisions"],
        "grossMaterials": resolution["grossMaterials"],
        "warnings": resolution["warnings"],
        "cycleTypeIds": resolution["cycleTypeIds"],
        "totalBaseTimeSeconds": resolution["totalBaseTimeSeconds"],
        "totalBlueprintTimeSeconds": resolution["totalBlueprintTimeSeconds"],
        "timeEfficiencySavingsSeconds": resolution["timeEfficiencySavingsSeconds"],
        "totalCharacterTimeSeconds": resolution["totalCharacterTimeSeconds"],
        "characterSkillTimeSavingsSeconds": resolution[
            "characterSkillTimeSavingsSeconds"
        ],
        "characterSkillState": resolution["characterSkillState"],
        "skillSnapshotId": resolution["skillSnapshotId"],
        "skillSyncRunId": resolution["skillSyncRunId"],
        "skillObservedAt": resolution["skillObservedAt"],
        "facilityState": resolution["facilityState"],
        "inventoryState": resolution["inventoryState"],
        "assetSnapshotId": resolution["assetSnapshotId"],
        "assetSyncRunId": resolution["assetSyncRunId"],
        "assetObservedAt": resolution["assetObservedAt"],
        "createdAt": str(row["created_at"]),
        "updatedAt": str(row["updated_at"]),
    }


def query_production_plans(connection: sqlite3.Connection, raw_query: Any) -> dict[str, Any]:
    query = validate_production_plan_query(raw_query)
    build_number = current_sde_blueprint_activity_build(connection)
    loaded_recipes = (
        _load_recipes(connection)
        if build_number is not None and _sde_tables_available(connection)
        else None
    )
    plan_rows = _plan_rows(connection)
    blueprint_sources = _load_blueprint_sources(connection, plan_rows)
    step_blueprint_assignments = _load_step_blueprint_assignments(connection)
    step_supply_modes = _load_step_supply_modes(connection)
    skill_sources = _load_skill_sources(connection, plan_rows)
    job_sources = _load_production_job_sources(connection)
    facility_context = _load_production_facilities(connection)
    inventory_sources = _load_inventory_sources(connection, plan_rows)
    reservations: dict[
        tuple[int, int, int, str, str, str], list[dict[str, Any]]
    ] = {}
    inventory_resolutions: dict[int, dict[str, Any]] = {}
    for row in sorted(
        plan_rows,
        key=lambda item: (
            int(item["owner_character_id"]),
            -int(item["priority"]),
            str(item["created_at"]),
            int(item["id"]),
        ),
    ):
        plan_id = int(row["id"])
        owner_character_id = int(row["owner_character_id"])
        inventory_source = inventory_sources.get(owner_character_id)
        resolution = resolve_production_plan(
            connection,
            row,
            loaded_recipes=loaded_recipes,
            blueprint_source=blueprint_sources.get(owner_character_id),
            skill_source=skill_sources.get(owner_character_id),
            job_source=job_sources.get(owner_character_id),
            facility_context=facility_context,
            step_blueprint_assignments=step_blueprint_assignments.get(plan_id, {}),
            step_supply_modes=step_supply_modes.get(plan_id, {}),
            inventory_source=inventory_source,
            reservations=reservations,
        )
        inventory_resolutions[plan_id] = _apply_inventory(
            {
                **resolution,
                **_location_selection(row, inventory_source),
            },
            row,
            inventory_sources,
            reservations,
        )
    records = [
        _serialize_plan(
            row,
            inventory_resolutions[int(row["id"])],
        )
        for row in plan_rows
    ]
    search = query["search"].casefold()
    records = [
        record
        for record in records
        if (query["ownerCharacterId"] is None or record["ownerCharacterId"] == query["ownerCharacterId"])
        and (query["activity"] is None or record["activity"] == query["activity"])
        and (
            not search
            or search in str(record["productName"]).casefold()
            or search in str(record["blueprintName"]).casefold()
            or search in str(record["ownerName"]).casefold()
            or search in str(record["note"] or "").casefold()
        )
    ]
    summary = {state: sum(record["state"] == state for record in records) for state in PLAN_STATES}
    if query["state"] is not None:
        records = [record for record in records if record["state"] == query["state"]]
    sort_keys = {
        "product": lambda item: (str(item["productName"]).casefold(), item["productTypeId"], item["planId"]),
        "owner": lambda item: (str(item["ownerName"]).casefold(), item["ownerCharacterId"], item["planId"]),
        "activity": lambda item: (item["activity"], str(item["productName"]).casefold(), item["planId"]),
        "state": lambda item: (PLAN_STATES.index(item["state"]), str(item["productName"]).casefold(), item["planId"]),
        "updated": lambda item: (item["updatedAt"], item["planId"]),
    }
    if query["sortBy"] == "priority":
        direction = -1 if query["sortDirection"] == "desc" else 1
        records.sort(
            key=lambda item: (
                direction * int(item["priority"]),
                item["createdAt"],
                item["planId"],
            )
        )
    else:
        records.sort(
            key=sort_keys[query["sortBy"]],
            reverse=query["sortDirection"] == "desc",
        )
    total = len(records)
    page = records[query["offset"] : query["offset"] + query["limit"]]
    owners = [
        {"characterId": int(row[0]), "name": str(row[1])}
        for row in connection.execute(
            "SELECT character_id,COALESCE(alias,name) FROM characters "
            "WHERE enabled=1 ORDER BY COALESCE(alias,name) COLLATE NOCASE,character_id"
        )
    ]
    return {
        "items": page,
        "total": total,
        "offset": query["offset"],
        "limit": query["limit"],
        "owners": owners,
        "locationOptions": _production_location_options(inventory_sources),
        "activities": list(SUPPORTED_BLUEPRINT_ACTIVITIES),
        "states": list(PLAN_STATES),
        "summary": summary,
        "buildNumber": build_number,
        "inventoryApplied": True,
        "reservationsApplied": True,
        "reservationRule": RESERVATION_RULE,
        "blueprintMaterialEfficiencyApplied": True,
        "materialEfficiencyRule": MATERIAL_EFFICIENCY_RULE,
        "blueprintTimeEfficiencyApplied": True,
        "timeEfficiencyRule": TIME_EFFICIENCY_RULE,
        "blueprintChainAssignmentsApplied": True,
        "blueprintChainAssignmentRule": CHAIN_BLUEPRINT_ASSIGNMENT_RULE,
        "characterSkillTimeApplied": True,
        "characterSkillTimeRule": CHARACTER_SKILL_TIME_RULE,
        "facilityEvidenceApplied": True,
        "facilityEvidenceRule": FACILITY_EVIDENCE_RULE,
        "supplyModesApplied": True,
        "supplyModeRule": SUPPLY_MODE_RULE,
        "remainingModifiersApplied": False,
    }


def production_work_queues(
    connection: sqlite3.Connection,
    job_snapshots: Mapping[int, Mapping[str, Any]],
) -> dict[int, dict[str, dict[str, int]]]:
    """Count assigned goals for the character slot overview without inventing completion."""

    build_number = current_sde_blueprint_activity_build(connection)
    loaded_recipes = (
        _load_recipes(connection)
        if build_number is not None and _sde_tables_available(connection)
        else None
    )
    result: dict[int, dict[str, dict[str, int]]] = {}
    activity_ids = {"manufacturing": {1}, "reaction": {9, 11}}
    for row in _plan_rows(connection):
        owner = int(row["owner_character_id"])
        activity = str(row["activity"])
        slot_activity = "manufacturing" if activity == "manufacturing" else "reactions"
        counters = result.setdefault(owner, {}).setdefault(
            slot_activity,
            {"queued": 0, "blocked": 0, "running": 0, "complete": 0},
        )
        resolution = resolve_production_plan(
            connection, row, loaded_recipes=loaded_recipes
        )
        if resolution["state"] != "ready":
            counters["blocked"] += 1
            continue
        jobs = job_snapshots.get(owner, {}).get("jobs", [])
        running = any(
            job.get("status") in {"active", "paused", "ready"}
            and job.get("activity_id") in activity_ids[activity]
            and job.get("blueprint_type_id") == int(row["blueprint_type_id"])
            for job in jobs
        )
        counters["running" if running else "queued"] += 1
    return result


def save_production_plan(connection: sqlite3.Connection, raw_input: Any) -> dict[str, Any]:
    value = validate_production_plan_input(raw_input)
    if current_sde_blueprint_activity_build(connection) is None or not _sde_tables_available(connection):
        raise ProductionPlanningError("production_sde_unavailable")
    recipe = connection.execute(
        "SELECT 1 FROM sde_blueprint_products WHERE blueprint_type_id=? AND activity=? "
        "AND product_type_id=?",
        (value["blueprintTypeId"], value["activity"], value["productTypeId"]),
    ).fetchone()
    if recipe is None:
        raise ProductionPlanningError("production_recipe_missing")
    if connection.execute(
        "SELECT 1 FROM characters WHERE character_id=? AND enabled=1",
        (value["ownerCharacterId"],),
    ).fetchone() is None:
        raise ProductionPlanningError("production_owner_missing")
    candidate = {
        "owner_character_id": value["ownerCharacterId"],
        "blueprint_type_id": value["blueprintTypeId"],
        "blueprint_item_id": value["blueprintItemId"],
        "facility_id": value["facilityId"],
        "material_location_id": value["materialLocationId"],
        "activity": value["activity"],
        "product_type_id": value["productTypeId"],
        "target_quantity": value["targetQuantity"],
    }
    step_assignments = {
        (
            int(assignment["blueprintTypeId"]),
            str(assignment["activity"]),
            int(assignment["productTypeId"]),
        ): int(assignment["blueprintItemId"])
        for assignment in value["stepBlueprintAssignments"]
    }
    supply_modes = {
        (
            int(supply["blueprintTypeId"]),
            str(supply["activity"]),
            int(supply["productTypeId"]),
        ): str(supply["supplyMode"])
        for supply in value["stepSupplyModes"]
    }
    resolved = resolve_production_plan(
        connection,
        candidate,
        step_blueprint_assignments=step_assignments,
        step_supply_modes=supply_modes,
    )
    if resolved["state"] in {"cycle", "complexity-limit"}:
        raise ProductionPlanningError(f"production_plan_{resolved['state']}")
    if (
        value["blueprintItemId"] is not None
        and resolved["blueprintAssignmentState"] != "ready"
    ):
        raise ProductionPlanningError(
            f"production_blueprint_{resolved['blueprintAssignmentState']}"
        )
    resolved_steps = {
        (
            int(step["blueprintTypeId"]),
            str(step["activity"]),
            int(step["productTypeId"]),
        ): step
        for step in resolved["steps"]
    }
    resolved_supply_keys = set(resolved["_supplyRecipeKeys"])
    if any(key not in resolved_supply_keys for key in supply_modes):
        raise ProductionPlanningError("production_supply_step_missing")
    for key in step_assignments:
        step = resolved_steps.get(key)
        if step is None:
            if key not in resolved_supply_keys:
                raise ProductionPlanningError("production_blueprint_step_missing")
            inactive_assignment = _blueprint_assignment_for_recipe(
                key[0],
                step_assignments[key],
                _blueprint_source(connection, value["ownerCharacterId"]),
                1,
            )
            if inactive_assignment["blueprintAssignmentState"] != "ready":
                raise ProductionPlanningError(
                    f"production_blueprint_{inactive_assignment['blueprintAssignmentState']}"
                )
            continue
        assignment = step["blueprintAssignment"]
        if assignment["blueprintAssignmentState"] != "ready":
            raise ProductionPlanningError(
                f"production_blueprint_{assignment['blueprintAssignmentState']}"
            )
    if value["facilityId"] is not None:
        owner_row = connection.execute(
            "SELECT COALESCE(alias,name) FROM characters WHERE character_id=?",
            (value["ownerCharacterId"],),
        ).fetchone()
        inventory_source = _inventory_source(
            connection, value["ownerCharacterId"], str(owner_row[0])
        )
        if _location_selection(candidate, inventory_source)[
            "locationSelectionState"
        ] != "ready":
            raise ProductionPlanningError("production_location_selection_invalid")
    try:
        connection.execute("BEGIN IMMEDIATE")
        assigned_item_ids = [
            *(
                []
                if value["blueprintItemId"] is None
                else [int(value["blueprintItemId"])]
            ),
            *step_assignments.values(),
        ]
        excluded_plan_id = -1 if value["planId"] is None else int(value["planId"])
        for item_id in assigned_item_ids:
            conflict = connection.execute(
                "SELECT 1 FROM production_plans WHERE blueprint_item_id=? AND id<>? "
                "UNION ALL SELECT 1 FROM production_plan_step_blueprints "
                "WHERE blueprint_item_id=? AND plan_id<>? LIMIT 1",
                (item_id, excluded_plan_id, item_id, excluded_plan_id),
            ).fetchone()
            if conflict is not None:
                raise ProductionPlanningError("production_blueprint_already_assigned")
        if value["planId"] is None:
            cursor = connection.execute(
                "INSERT INTO production_plans(owner_character_id,blueprint_type_id,blueprint_item_id,"
                "facility_id,material_location_id,activity,product_type_id,target_quantity,priority,note) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    value["ownerCharacterId"], value["blueprintTypeId"], value["blueprintItemId"],
                    value["facilityId"], value["materialLocationId"], value["activity"],
                    value["productTypeId"], value["targetQuantity"], value["priority"], value["note"],
                ),
            )
            plan_id = int(cursor.lastrowid)
        else:
            cursor = connection.execute(
                "UPDATE production_plans SET owner_character_id=?,blueprint_type_id=?,blueprint_item_id=?,"
                "facility_id=?,material_location_id=?,activity=?,product_type_id=?,target_quantity=?,priority=?,note=?,"
                "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
                (
                    value["ownerCharacterId"], value["blueprintTypeId"], value["blueprintItemId"],
                    value["facilityId"], value["materialLocationId"], value["activity"],
                    value["productTypeId"], value["targetQuantity"], value["priority"], value["note"],
                    value["planId"],
                ),
            )
            if cursor.rowcount != 1:
                raise ProductionPlanningError("production_plan_missing")
            plan_id = int(value["planId"])
        connection.execute(
            "DELETE FROM production_plan_step_blueprints WHERE plan_id=?",
            (plan_id,),
        )
        connection.executemany(
            "INSERT INTO production_plan_step_blueprints("
            "plan_id,blueprint_type_id,activity,product_type_id,blueprint_item_id"
            ") VALUES (?,?,?,?,?)",
            [
                (
                    plan_id,
                    assignment["blueprintTypeId"],
                    assignment["activity"],
                    assignment["productTypeId"],
                    assignment["blueprintItemId"],
                )
                for assignment in value["stepBlueprintAssignments"]
            ],
        )
        connection.execute(
            "DELETE FROM production_plan_step_supply_modes WHERE plan_id=?",
            (plan_id,),
        )
        connection.executemany(
            "INSERT INTO production_plan_step_supply_modes("
            "plan_id,blueprint_type_id,activity,product_type_id,supply_mode"
            ") VALUES (?,?,?,?,?)",
            [
                (
                    plan_id,
                    supply["blueprintTypeId"],
                    supply["activity"],
                    supply["productTypeId"],
                    supply["supplyMode"],
                )
                for supply in value["stepSupplyModes"]
            ],
        )
        connection.commit()
    except sqlite3.IntegrityError as error:
        connection.rollback()
        if "blueprint_item_id" in str(error):
            raise ProductionPlanningError("production_blueprint_already_assigned") from error
        raise
    except Exception:
        connection.rollback()
        raise
    return {
        "saved": True,
        "planId": plan_id,
        "ownerCharacterId": value["ownerCharacterId"],
        "blueprintTypeId": value["blueprintTypeId"],
        "blueprintItemId": value["blueprintItemId"],
        "stepBlueprintAssignments": value["stepBlueprintAssignments"],
        "facilityId": value["facilityId"],
        "materialLocationId": value["materialLocationId"],
        "stepSupplyModes": value["stepSupplyModes"],
        "activity": value["activity"],
        "productTypeId": value["productTypeId"],
        "targetQuantity": value["targetQuantity"],
        "priority": value["priority"],
        "note": value["note"],
    }


def delete_production_plan(connection: sqlite3.Connection, raw_input: Any) -> dict[str, Any]:
    plan_id = validate_production_plan_delete(raw_input)
    connection.execute("BEGIN IMMEDIATE")
    try:
        cursor = connection.execute("DELETE FROM production_plans WHERE id=?", (plan_id,))
        if cursor.rowcount != 1:
            raise ProductionPlanningError("production_plan_missing")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {"deleted": True, "planId": plan_id}
