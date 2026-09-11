"""Bounded read model for character industry jobs and correlation evidence."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping

from .asset_delta import (
    AssetDeltaError,
    _delta_snapshots,
    _json_object,
    _positive_integer,
    _validated_event,
)
from .blueprint_sync import BlueprintSyncError, _validate_blueprint
from .industry_job_evidence import (
    IndustryJobEvidenceError,
    load_latest_job_snapshots,
    parse_timestamp,
)
from .industry_facility_view import (
    IndustryFacilityViewError,
    JOB_COST_ACTIVITIES,
    industry_facility_index,
)
from .industry_job_sync import ACTIVITY_IDS, JOB_STATUSES


MAX_SAFE_INTEGER = 9_007_199_254_740_991
MAX_PAGE_SIZE = 200
MAX_SEARCH_LENGTH = 120
SORT_FIELDS = ("start", "end", "type", "owner", "activity", "status", "runs", "cost", "correlation", "age")
CORRELATION_STATES = ("linked", "partial", "ambiguous", "unmatched", "pending")
ACTIVITY_KEYS = {
    1: "manufacturing",
    3: "research-time",
    4: "research-material",
    5: "copying",
    7: "reverse-engineering",
    8: "invention",
    9: "reactions",
    11: "reactions",
}


class IndustryJobViewError(RuntimeError):
    """Raised when a job query or persisted source evidence is invalid."""


def validate_industry_job_query(payload: Any) -> dict[str, Any]:
    expected = {
        "search",
        "ownerCharacterId",
        "status",
        "activityId",
        "correlation",
        "offset",
        "limit",
        "sortBy",
        "sortDirection",
    }
    if not isinstance(payload, Mapping) or set(payload) != expected:
        raise IndustryJobViewError("industry_job_query_invalid")
    search = payload["search"]
    owner = payload["ownerCharacterId"]
    activity_id = payload["activityId"]
    offset = payload["offset"]
    limit = payload["limit"]
    if (
        not isinstance(search, str)
        or len(search) > MAX_SEARCH_LENGTH
        or owner is not None
        and (isinstance(owner, bool) or not isinstance(owner, int) or not 0 < owner <= MAX_SAFE_INTEGER)
        or payload["status"] not in (None, *JOB_STATUSES)
        or activity_id is not None
        and (isinstance(activity_id, bool) or activity_id not in ACTIVITY_IDS)
        or payload["correlation"] not in (None, *CORRELATION_STATES)
        or isinstance(offset, bool)
        or not isinstance(offset, int)
        or not 0 <= offset <= MAX_SAFE_INTEGER
        or isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_PAGE_SIZE
        or payload["sortBy"] not in SORT_FIELDS
        or payload["sortDirection"] not in ("asc", "desc")
    ):
        raise IndustryJobViewError("industry_job_query_invalid")
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


def _blueprint_evidence(connection: sqlite3.Connection) -> tuple[set[int], dict[tuple[int, int], list[dict[str, object]]]]:
    snapshots = connection.execute(
        """
        SELECT cached_snapshots.id AS snapshot_id,cached_snapshots.sync_run_id,
               cached_snapshots.payload_json,cached_snapshots.observed_at,
               sync_runs.character_id
        FROM cached_snapshots
        JOIN sync_runs ON sync_runs.id=cached_snapshots.sync_run_id
        WHERE sync_runs.source='character_blueprints'
          AND sync_runs.status='completed'
          AND cached_snapshots.resource='character_blueprints:' || sync_runs.character_id
        ORDER BY sync_runs.character_id,cached_snapshots.observed_at DESC,cached_snapshots.id DESC
        """
    ).fetchall()
    available: set[int] = set()
    evidence: dict[tuple[int, int], list[dict[str, object]]] = {}
    latest_seen: set[int] = set()
    for row in snapshots:
        character_id = int(row["character_id"])
        available.add(character_id)
        current = character_id not in latest_seen
        latest_seen.add(character_id)
        try:
            payload = json.loads(str(row["payload_json"]))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise IndustryJobViewError("blueprint_evidence_invalid") from error
        if (
            not isinstance(payload, Mapping)
            or payload.get("characterId") != character_id
            or not isinstance(payload.get("blueprints"), list)
        ):
            raise IndustryJobViewError("blueprint_evidence_invalid")
        observed_at = str(row["observed_at"])
        parse_timestamp(observed_at)
        seen: set[int] = set()
        try:
            blueprints = [_validate_blueprint(item) for item in payload["blueprints"]]
        except BlueprintSyncError as error:
            raise IndustryJobViewError("blueprint_evidence_invalid") from error
        for blueprint in blueprints:
            item_id = int(blueprint["item_id"])
            if item_id in seen:
                raise IndustryJobViewError("blueprint_evidence_invalid")
            seen.add(item_id)
            evidence.setdefault((character_id, item_id), []).append(
                {
                    "state": "current" if current else "historical",
                    "typeId": int(blueprint["type_id"]),
                    "snapshotId": int(row["snapshot_id"]),
                    "syncRunId": int(row["sync_run_id"]),
                    "observedAt": observed_at,
                }
            )
    return available, evidence


def _asset_evidence(connection: sqlite3.Connection) -> tuple[set[int], dict[tuple[int, int], list[dict[str, object]]]]:
    available: set[int] = set()
    evidence: dict[tuple[int, int], list[dict[str, object]]] = {}
    try:
        for row in _delta_snapshots(connection):
            character_id = int(row["character_id"])
            available.add(character_id)
            payload = _json_object(row["payload_json"])
            if payload.get("characterId") != character_id or not isinstance(payload.get("events"), list):
                raise IndustryJobViewError("asset_evidence_invalid")
            for raw_event in payload["events"]:
                event = _validated_event(raw_event, payload)
                correlation = event["jobCorrelation"]
                if not isinstance(correlation, Mapping) or correlation["direction"] != "inbound":
                    continue
                type_id = int(event["typeId"])
                evidence.setdefault((character_id, type_id), []).append(
                    {
                        "eventId": str(event["eventId"]),
                        "locationIdAfter": event["locationIdAfter"],
                        "windowStart": str(correlation["windowStart"]),
                        "windowEnd": str(correlation["windowEnd"]),
                        "previousAssetSnapshotId": _positive_integer(payload.get("previousAssetSnapshotId")),
                        "currentAssetSnapshotId": _positive_integer(payload.get("currentAssetSnapshotId")),
                        "currentAssetSyncRunId": _positive_integer(payload.get("currentAssetSyncRunId")),
                    }
                )
    except AssetDeltaError as error:
        raise IndustryJobViewError("asset_evidence_invalid") from error
    return available, evidence


def _blueprint_correlation(
    available: set[int],
    evidence: Mapping[tuple[int, int], list[dict[str, object]]],
    character_id: int,
    blueprint_id: int,
    blueprint_type_id: int,
) -> dict[str, object]:
    candidates = evidence.get((character_id, blueprint_id), [])
    if candidates and any(candidate["typeId"] != blueprint_type_id for candidate in candidates):
        raise IndustryJobViewError("blueprint_evidence_invalid")
    if not candidates:
        return {
            "state": "unmatched" if character_id in available else "unavailable",
            "snapshotId": None,
            "syncRunId": None,
            "observedAt": None,
        }
    candidate = candidates[0]
    return {
        "state": candidate["state"],
        "snapshotId": candidate["snapshotId"],
        "syncRunId": candidate["syncRunId"],
        "observedAt": candidate["observedAt"],
    }


def _asset_correlation(
    available: set[int],
    evidence: Mapping[tuple[int, int], list[dict[str, object]]],
    character_id: int,
    job: Mapping[str, Any],
) -> dict[str, object]:
    base: dict[str, object] = {
        "eventIds": [],
        "candidateCount": 0,
        "locationMatched": False,
    }
    if job["status"] in ("active", "paused", "ready"):
        return {**base, "state": "pending"}
    if (
        job["status"] != "delivered"
        or job["product_type_id"] is None
        or job["completed_date"] is None
    ):
        return {**base, "state": "not-applicable"}
    if character_id not in available:
        return {**base, "state": "unavailable"}
    completed = parse_timestamp(job["completed_date"])
    candidates = [
        event
        for event in evidence.get((character_id, int(job["product_type_id"])), [])
        if parse_timestamp(event["windowStart"]) <= completed <= parse_timestamp(event["windowEnd"])
    ]
    location_candidates = [
        event for event in candidates if event["locationIdAfter"] == job["output_location_id"]
    ]
    selected = location_candidates or candidates
    selected.sort(key=lambda event: str(event["eventId"]))
    if not selected:
        state = "unmatched"
    elif len(selected) == 1:
        state = "linked"
    else:
        state = "ambiguous"
    return {
        **base,
        "state": state,
        "eventIds": [str(event["eventId"]) for event in selected[:20]],
        "candidateCount": len(selected),
        "locationMatched": bool(location_candidates),
    }


def _overall_correlation(status: str, blueprint: Mapping[str, object], asset: Mapping[str, object]) -> str:
    if status in ("active", "paused", "ready"):
        return "pending"
    if asset["state"] == "ambiguous":
        return "ambiguous"
    blueprint_linked = blueprint["state"] in ("current", "historical")
    asset_linked = asset["state"] == "linked"
    if blueprint_linked and (asset_linked or asset["state"] == "not-applicable"):
        return "linked"
    if blueprint_linked or asset_linked:
        return "partial"
    return "unmatched"


def query_industry_jobs(
    connection: sqlite3.Connection,
    raw_query: Any,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    query = validate_industry_job_query(raw_query)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    type_names = _type_names(connection)
    try:
        job_snapshots = load_latest_job_snapshots(connection)
    except IndustryJobEvidenceError as error:
        raise IndustryJobViewError("industry_job_snapshot_invalid") from error
    try:
        facilities = industry_facility_index(connection)
    except IndustryFacilityViewError as error:
        raise IndustryJobViewError("industry_facility_snapshot_invalid") from error
    blueprint_available, blueprints = _blueprint_evidence(connection)
    asset_available, assets = _asset_evidence(connection)
    tokens = query["search"].casefold().split()
    rows: list[dict[str, object]] = []
    owners: list[dict[str, object]] = []
    observed_values: list[str] = []
    activities: set[int] = set()

    for character_id, snapshot in job_snapshots.items():
        owner_name = str(snapshot["ownerName"])
        owners.append({"characterId": character_id, "name": owner_name})
        observed_at = str(snapshot["observedAt"])
        observed_values.append(observed_at)
        if query["ownerCharacterId"] is not None and query["ownerCharacterId"] != character_id:
            continue
        age_seconds = max(0, int((current - parse_timestamp(observed_at)).total_seconds()))
        for job in snapshot["jobs"]:
            activity_id = int(job["activity_id"])
            activities.add(activity_id)
            if query["status"] is not None and query["status"] != job["status"]:
                continue
            if query["activityId"] is not None and query["activityId"] != activity_id:
                continue
            blueprint_type_id = int(job["blueprint_type_id"])
            product_type_id = None if job["product_type_id"] is None else int(job["product_type_id"])
            blueprint_name = type_names.get(blueprint_type_id, f"Type #{blueprint_type_id}")
            product_name = (
                None
                if product_type_id is None
                else type_names.get(product_type_id, f"Type #{product_type_id}")
            )
            blueprint_correlation = _blueprint_correlation(
                blueprint_available,
                blueprints,
                character_id,
                int(job["blueprint_id"]),
                blueprint_type_id,
            )
            asset_correlation = _asset_correlation(asset_available, assets, character_id, job)
            correlation_state = _overall_correlation(
                str(job["status"]), blueprint_correlation, asset_correlation
            )
            facility = facilities.get(int(job["facility_id"]), {})
            cost_indices = facility.get("costIndices", {})
            if not isinstance(cost_indices, Mapping):
                raise IndustryJobViewError("industry_facility_snapshot_invalid")
            facility_activity = JOB_COST_ACTIVITIES[activity_id]
            if query["correlation"] is not None and query["correlation"] != correlation_state:
                continue
            row: dict[str, object] = {
                "jobId": int(job["job_id"]),
                "ownerCharacterId": character_id,
                "ownerName": owner_name,
                "activityId": activity_id,
                "activityKey": ACTIVITY_KEYS[activity_id],
                "status": str(job["status"]),
                "blueprintItemId": int(job["blueprint_id"]),
                "blueprintTypeId": blueprint_type_id,
                "blueprintName": blueprint_name,
                "productTypeId": product_type_id,
                "productName": product_name,
                "runs": int(job["runs"]),
                "successfulRuns": job["successful_runs"],
                "licensedRuns": job["licensed_runs"],
                "probability": job["probability"],
                "cost": job["cost"],
                "durationSeconds": int(job["duration"]),
                "facilityId": int(job["facility_id"]),
                "facilityName": facility.get("facilityName"),
                "facilityKind": facility.get("kind", "unknown"),
                "facilityAccess": facility.get("access", "unknown"),
                "solarSystemId": facility.get("solarSystemId"),
                "solarSystemName": facility.get("solarSystemName"),
                "systemCostIndex": cost_indices.get(facility_activity),
                "stationId": int(job["station_id"]),
                "blueprintLocationId": int(job["blueprint_location_id"]),
                "outputLocationId": int(job["output_location_id"]),
                "startDate": str(job["start_date"]),
                "endDate": str(job["end_date"]),
                "completedDate": job["completed_date"],
                "pauseDate": job["pause_date"],
                "blueprintCorrelation": blueprint_correlation,
                "assetCorrelation": asset_correlation,
                "correlationState": correlation_state,
                "jobSnapshotId": int(snapshot["snapshotId"]),
                "jobSyncRunId": int(snapshot["syncRunId"]),
                "observedAt": observed_at,
                "ageSeconds": age_seconds,
            }
            if tokens:
                haystack = " ".join(
                    (
                        str(row["jobId"]),
                        owner_name,
                        blueprint_name,
                        product_name or "",
                        str(blueprint_type_id),
                        str(product_type_id or ""),
                        str(row["blueprintItemId"]),
                        str(row["activityKey"]),
                        str(row["status"]),
                        str(row["facilityName"] or ""),
                        str(row["solarSystemName"] or ""),
                        correlation_state,
                        " ".join(str(value) for value in asset_correlation["eventIds"]),
                    )
                ).casefold()
                if not all(token in haystack for token in tokens):
                    continue
            rows.append(row)

    getters = {
        "start": lambda row: parse_timestamp(row["startDate"]),
        "end": lambda row: parse_timestamp(row["endDate"]),
        "type": lambda row: str(row["productName"] or row["blueprintName"]).casefold(),
        "owner": lambda row: str(row["ownerName"]).casefold(),
        "activity": lambda row: int(row["activityId"]),
        "status": lambda row: str(row["status"]),
        "runs": lambda row: int(row["runs"]),
        "cost": lambda row: float(row["cost"] or 0),
        "correlation": lambda row: str(row["correlationState"]),
        "age": lambda row: int(row["ageSeconds"]),
    }
    rows.sort(
        key=lambda row: (getters[query["sortBy"]](row), int(row["jobId"])),
        reverse=query["sortDirection"] == "desc",
    )
    owners.sort(key=lambda owner: (str(owner["name"]).casefold(), int(owner["characterId"])))
    total = len(rows)
    active_total = sum(
        row["status"] in ("active", "paused", "ready") for row in rows
    )
    page = rows[query["offset"] : query["offset"] + query["limit"]]
    observed_at = min(observed_values, key=parse_timestamp) if observed_values else None
    age_seconds = (
        None
        if observed_at is None
        else max(0, int((current - parse_timestamp(observed_at)).total_seconds()))
    )
    return {
        "items": page,
        "total": total,
        "activeTotal": active_total,
        "offset": query["offset"],
        "limit": query["limit"],
        "owners": owners,
        "statuses": list(JOB_STATUSES),
        "activities": sorted(activities),
        "correlations": list(CORRELATION_STATES),
        "observedAt": observed_at,
        "ageSeconds": age_seconds,
    }
