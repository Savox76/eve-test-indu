"""Bounded read model for complete industry-facility reference snapshots."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping

from .industry_facility_sync import (
    IndustryFacilitySyncError,
    MAX_SAFE_INTEGER,
    validate_industry_reference,
)
from .industry_job_evidence import (
    IndustryJobEvidenceError,
    load_latest_job_snapshots,
    parse_timestamp,
)


MAX_PAGE_SIZE = 200
DISPLAY_COST_ACTIVITIES = (
    "manufacturing",
    "reaction",
    "copying",
    "invention",
    "researching_material_efficiency",
    "researching_time_efficiency",
)
FACILITY_KINDS = ("station", "structure", "unknown")
FACILITY_ACCESS_STATES = ("public", "available", "restricted", "scope-missing", "unknown")
SORT_FIELDS = ("facility", "system", "type", "cost", "jobs", "access", "age")
JOB_COST_ACTIVITIES = {
    1: "manufacturing",
    3: "researching_time_efficiency",
    4: "researching_material_efficiency",
    5: "copying",
    7: "reverse_engineering",
    8: "invention",
    9: "reaction",
    11: "reaction",
}


class IndustryFacilityViewError(RuntimeError):
    """Raised when a query or persisted facility reference is invalid."""


def validate_industry_facility_query(payload: Any) -> dict[str, Any]:
    expected = {
        "search",
        "kind",
        "access",
        "activity",
        "usedOnly",
        "offset",
        "limit",
        "sortBy",
        "sortDirection",
    }
    if not isinstance(payload, Mapping) or set(payload) != expected:
        raise IndustryFacilityViewError("industry_facility_query_invalid")
    search = payload["search"]
    if (
        not isinstance(search, str)
        or len(search) > 120
        or payload["kind"] not in (None, *FACILITY_KINDS)
        or payload["access"] not in (None, *FACILITY_ACCESS_STATES)
        or payload["activity"] not in DISPLAY_COST_ACTIVITIES
        or not isinstance(payload["usedOnly"], bool)
        or isinstance(payload["offset"], bool)
        or not isinstance(payload["offset"], int)
        or not 0 <= payload["offset"] <= MAX_SAFE_INTEGER
        or isinstance(payload["limit"], bool)
        or not isinstance(payload["limit"], int)
        or not 1 <= payload["limit"] <= MAX_PAGE_SIZE
        or payload["sortBy"] not in SORT_FIELDS
        or payload["sortDirection"] not in ("asc", "desc")
    ):
        raise IndustryFacilityViewError("industry_facility_query_invalid")
    return {**payload, "search": " ".join(search.strip().split())}


def _latest_reference(
    connection: sqlite3.Connection,
) -> tuple[sqlite3.Row, dict[str, Any]] | None:
    row = connection.execute(
        """
        SELECT cached_snapshots.id,cached_snapshots.sync_run_id,
               cached_snapshots.payload_json,cached_snapshots.observed_at
        FROM cached_snapshots
        JOIN sync_runs ON sync_runs.id=cached_snapshots.sync_run_id
        WHERE cached_snapshots.resource='industry_facilities'
          AND sync_runs.source='industry_facilities'
          AND sync_runs.status='completed'
        ORDER BY cached_snapshots.observed_at DESC,cached_snapshots.id DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        return None
    try:
        payload = validate_industry_reference(json.loads(str(row["payload_json"])))
        observed = parse_timestamp(str(row["observed_at"]))
    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
        IndustryFacilitySyncError,
        IndustryJobEvidenceError,
    ) as error:
        raise IndustryFacilityViewError("industry_facility_snapshot_invalid") from error
    if observed.tzinfo is None:
        raise IndustryFacilityViewError("industry_facility_snapshot_invalid")
    return row, payload


def _usage(connection: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    try:
        snapshots = load_latest_job_snapshots(connection)
    except IndustryJobEvidenceError as error:
        raise IndustryFacilityViewError("industry_job_snapshot_invalid") from error
    usage: dict[int, dict[str, Any]] = {}
    for character_id, snapshot in snapshots.items():
        for job in snapshot["jobs"]:
            facility_id = int(job["facility_id"])
            entry = usage.setdefault(
                facility_id,
                {"characters": set(), "activities": set(), "jobs": 0, "active": 0},
            )
            entry["characters"].add(character_id)
            entry["activities"].add(int(job["activity_id"]))
            entry["jobs"] += 1
            entry["active"] += job["status"] in ("active", "paused", "ready")
    return usage


def _facility_index(
    row: sqlite3.Row,
    payload: Mapping[str, Any],
) -> dict[int, dict[str, Any]]:
    names = {int(name["id"]): str(name["name"]) for name in payload["names"]}
    systems = {
        int(system["solar_system_id"]): {
            str(index["activity"]): float(index["cost_index"])
            for index in system["cost_indices"]
        }
        for system in payload["systems"]
    }
    result: dict[int, dict[str, Any]] = {}
    for facility in payload["facilities"]:
        facility_id = int(facility["facility_id"])
        system_id = int(facility["solar_system_id"])
        result[facility_id] = {
            "facilityId": facility_id,
            "facilityName": names[facility_id],
            "kind": "station",
            "access": "public",
            "typeId": int(facility["type_id"]),
            "typeName": names[int(facility["type_id"])],
            "ownerId": int(facility["owner_id"]),
            "ownerName": names[int(facility["owner_id"])],
            "regionId": int(facility["region_id"]),
            "regionName": names[int(facility["region_id"])],
            "solarSystemId": system_id,
            "solarSystemName": names[system_id],
            "tax": facility["tax"],
            "costIndices": systems.get(system_id, {}),
            "errorCode": None,
            "snapshotId": int(row["id"]),
            "syncRunId": int(row["sync_run_id"]),
            "observedAt": str(row["observed_at"]),
        }
    for structure in payload["structures"]:
        facility_id = int(structure["facility_id"])
        system_id = structure["solar_system_id"]
        type_id = structure["type_id"]
        owner_id = structure["owner_id"]
        result[facility_id] = {
            "facilityId": facility_id,
            "facilityName": structure["name"],
            "kind": "structure" if facility_id >= 1_000_000_000_000 else "unknown",
            "access": structure["access"],
            "typeId": type_id,
            "typeName": None if type_id is None else names[int(type_id)],
            "ownerId": owner_id,
            "ownerName": None if owner_id is None else names[int(owner_id)],
            "regionId": None,
            "regionName": None,
            "solarSystemId": system_id,
            "solarSystemName": None if system_id is None else names[int(system_id)],
            "tax": None,
            "costIndices": {} if system_id is None else systems.get(int(system_id), {}),
            "errorCode": structure["error_code"],
            "snapshotId": int(row["id"]),
            "syncRunId": int(row["sync_run_id"]),
            "observedAt": str(row["observed_at"]),
        }
    return result


def industry_facility_index(connection: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    """Return the latest validated facilities indexed for jobs and other read models."""

    latest = _latest_reference(connection)
    if latest is None:
        return {}
    return _facility_index(*latest)


def query_industry_facilities(
    connection: sqlite3.Connection,
    raw_query: Any,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    query = validate_industry_facility_query(raw_query)
    latest = _latest_reference(connection)
    if latest is None:
        return {
            "items": [],
            "total": 0,
            "npcFacilities": 0,
            "observedFacilities": 0,
            "restrictedStructures": 0,
            "systems": 0,
            "offset": query["offset"],
            "limit": query["limit"],
            "activity": query["activity"],
            "activities": list(DISPLAY_COST_ACTIVITIES),
            "kinds": list(FACILITY_KINDS),
            "accessStates": list(FACILITY_ACCESS_STATES),
            "observedAt": None,
            "ageSeconds": None,
        }
    row, payload = latest
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age = max(0, int((current - parse_timestamp(str(row["observed_at"]))).total_seconds()))
    usage = _usage(connection)
    facilities = _facility_index(row, payload)
    rows: list[dict[str, Any]] = []
    tokens = query["search"].casefold().split()
    for facility in facilities.values():
        facility_usage = usage.get(
            int(facility["facilityId"]),
            {"characters": set(), "activities": set(), "jobs": 0, "active": 0},
        )
        if query["kind"] is not None and query["kind"] != facility["kind"]:
            continue
        if query["access"] is not None and query["access"] != facility["access"]:
            continue
        if query["usedOnly"] and facility_usage["jobs"] == 0:
            continue
        row_value = {
            **facility,
            "activityCostIndex": facility["costIndices"].get(query["activity"]),
            "usedByCharacterIds": sorted(facility_usage["characters"]),
            "observedActivityIds": sorted(facility_usage["activities"]),
            "jobCount": int(facility_usage["jobs"]),
            "activeJobs": int(facility_usage["active"]),
            "ageSeconds": age,
        }
        del row_value["costIndices"]
        if tokens:
            haystack = " ".join(
                str(row_value.get(field) or "")
                for field in (
                    "facilityId",
                    "facilityName",
                    "typeId",
                    "typeName",
                    "ownerId",
                    "ownerName",
                    "regionId",
                    "regionName",
                    "solarSystemId",
                    "solarSystemName",
                    "kind",
                    "access",
                    "errorCode",
                )
            ).casefold()
            if not all(token in haystack for token in tokens):
                continue
        rows.append(row_value)

    getters = {
        "facility": lambda item: str(item["facilityName"] or f"#{item['facilityId']}").casefold(),
        "system": lambda item: str(item["solarSystemName"] or "").casefold(),
        "type": lambda item: str(item["typeName"] or "").casefold(),
        "cost": lambda item: item["activityCostIndex"],
        "jobs": lambda item: int(item["jobCount"]),
        "access": lambda item: FACILITY_ACCESS_STATES.index(str(item["access"])),
        "age": lambda item: int(item["ageSeconds"]),
    }
    rows.sort(key=lambda item: int(item["facilityId"]))
    rows.sort(
        key=lambda item: (
            getters[query["sortBy"]](item) is None,
            getters[query["sortBy"]](item),
        ),
        reverse=query["sortDirection"] == "desc",
    )
    if query["sortBy"] == "cost":
        rows.sort(key=lambda item: item["activityCostIndex"] is None)
    total = len(rows)
    page = rows[query["offset"] : query["offset"] + query["limit"]]
    return {
        "items": page,
        "total": total,
        "npcFacilities": len(payload["facilities"]),
        "observedFacilities": len(payload["structures"]),
        "restrictedStructures": sum(
            structure["access"] in {"restricted", "scope-missing"}
            for structure in payload["structures"]
        ),
        "systems": len(payload["systems"]),
        "offset": query["offset"],
        "limit": query["limit"],
        "activity": query["activity"],
        "activities": list(DISPLAY_COST_ACTIVITIES),
        "kinds": list(FACILITY_KINDS),
        "accessStates": list(FACILITY_ACCESS_STATES),
        "observedAt": str(row["observed_at"]),
        "ageSeconds": age,
    }
