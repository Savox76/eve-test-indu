"""Deterministic asset deltas and a bounded local change-history read model."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Final, Iterable, Mapping

from .industry_job_evidence import (
    IndustryJobEvidenceError,
    correlate_asset_event,
    load_latest_job_snapshots,
)


DEFAULT_DELTA_PAGE_SIZE: Final = 50
MAX_DELTA_PAGE_SIZE: Final = 200
MAX_SEARCH_LENGTH: Final = 120
MAX_SAFE_INTEGER: Final = 9_007_199_254_740_991
DELTA_CHANGE_TYPES: Final = ("added", "removed", "quantity", "location")
DELTA_DIRECTIONS: Final = ("inbound", "outbound", "neutral")


class AssetDeltaError(RuntimeError):
    """Raised when complete snapshots cannot produce or expose trustworthy deltas."""


@dataclass(frozen=True, slots=True)
class AssetDeltaQuery:
    search: str = ""
    owner_character_id: int | None = None
    change_type: str | None = None
    offset: int = 0
    limit: int = DEFAULT_DELTA_PAGE_SIZE
    type_id: int | None = None
    previous_asset_snapshot_id: int | None = None
    current_asset_snapshot_id: int | None = None


def validate_asset_delta_query(
    *,
    search: Any = "",
    owner_character_id: Any = None,
    change_type: Any = None,
    offset: Any = 0,
    limit: Any = DEFAULT_DELTA_PAGE_SIZE,
    type_id: Any = None,
    previous_asset_snapshot_id: Any = None,
    current_asset_snapshot_id: Any = None,
) -> AssetDeltaQuery:
    if not isinstance(search, str) or len(search) > MAX_SEARCH_LENGTH:
        raise AssetDeltaError("asset_delta_query_invalid")
    normalized_search = " ".join(search.strip().split())
    if owner_character_id is not None and (
        isinstance(owner_character_id, bool)
        or not isinstance(owner_character_id, int)
        or not 0 < owner_character_id <= MAX_SAFE_INTEGER
    ):
        raise AssetDeltaError("asset_delta_query_invalid")
    if change_type is not None and change_type not in DELTA_CHANGE_TYPES:
        raise AssetDeltaError("asset_delta_query_invalid")
    group_values = (type_id, previous_asset_snapshot_id, current_asset_snapshot_id)
    if any(value is not None for value in group_values) and not all(
        value is not None for value in group_values
    ):
        raise AssetDeltaError("asset_delta_query_invalid")
    if any(
        value is not None
        and (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 < value <= MAX_SAFE_INTEGER
        )
        for value in group_values
    ):
        raise AssetDeltaError("asset_delta_query_invalid")
    if (
        isinstance(offset, bool)
        or not isinstance(offset, int)
        or not 0 <= offset <= MAX_SAFE_INTEGER
        or isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_DELTA_PAGE_SIZE
    ):
        raise AssetDeltaError("asset_delta_query_invalid")
    return AssetDeltaQuery(
        normalized_search,
        owner_character_id,
        change_type,
        offset,
        limit,
        type_id,
        previous_asset_snapshot_id,
        current_asset_snapshot_id,
    )


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip() or len(value) > 64:
        raise AssetDeltaError("asset_delta_snapshot_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise AssetDeltaError("asset_delta_snapshot_invalid") from error
    if parsed.tzinfo is None:
        raise AssetDeltaError("asset_delta_snapshot_invalid")
    return parsed.astimezone(timezone.utc)


def _positive_integer(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= MAX_SAFE_INTEGER:
        raise AssetDeltaError("asset_snapshot_invalid")
    return value


def _quantity(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SAFE_INTEGER:
        raise AssetDeltaError("asset_snapshot_invalid")
    return value


def _bounded_text(value: Any, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or len(value) > maximum
    ):
        raise AssetDeltaError("asset_snapshot_invalid")
    return value


def _asset_index(payload: Any, character_id: int) -> dict[int, dict[str, object]]:
    if not isinstance(payload, Mapping) or payload.get("characterId") != character_id:
        raise AssetDeltaError("asset_snapshot_invalid")
    raw_assets = payload.get("assets")
    if not isinstance(raw_assets, list):
        raise AssetDeltaError("asset_snapshot_invalid")
    result: dict[int, dict[str, object]] = {}
    for raw in raw_assets:
        if not isinstance(raw, Mapping):
            raise AssetDeltaError("asset_snapshot_invalid")
        item_id = _positive_integer(raw.get("item_id"))
        if item_id in result:
            raise AssetDeltaError("asset_snapshot_invalid")
        result[item_id] = {
            "itemId": item_id,
            "typeId": _positive_integer(raw.get("type_id")),
            "quantity": _quantity(raw.get("quantity")),
            "locationId": _positive_integer(raw.get("location_id")),
            "locationType": _bounded_text(raw.get("location_type"), 40),
            "locationFlag": _bounded_text(raw.get("location_flag"), 100),
        }
    return result


def _event_id(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_asset_delta_payload(
    *,
    character_id: int,
    current_snapshot_id: int,
    current_sync_run_id: int,
    current_observed_at: str,
    current_payload: Any,
    previous_snapshot_id: int | None = None,
    previous_sync_run_id: int | None = None,
    previous_observed_at: str | None = None,
    previous_payload: Any = None,
) -> dict[str, object]:
    """Compare two complete snapshots and return one deterministic audit payload."""
    character_id = _positive_integer(character_id)
    current_snapshot_id = _positive_integer(current_snapshot_id)
    current_sync_run_id = _positive_integer(current_sync_run_id)
    _parse_timestamp(current_observed_at)
    current = _asset_index(current_payload, character_id)
    baseline = previous_snapshot_id is None
    if baseline:
        if any(
            value is not None
            for value in (previous_sync_run_id, previous_observed_at, previous_payload)
        ):
            raise AssetDeltaError("asset_delta_source_invalid")
        previous: dict[int, dict[str, object]] = {}
    else:
        previous_snapshot_id = _positive_integer(previous_snapshot_id)
        previous_sync_run_id = _positive_integer(previous_sync_run_id)
        if previous_observed_at is None or previous_payload is None:
            raise AssetDeltaError("asset_delta_source_invalid")
        if _parse_timestamp(previous_observed_at) > _parse_timestamp(current_observed_at):
            raise AssetDeltaError("asset_delta_source_invalid")
        previous = _asset_index(previous_payload, character_id)

    events: list[dict[str, object]] = []
    if not baseline:
        for item_id in sorted(set(previous) | set(current)):
            before = previous.get(item_id)
            after = current.get(item_id)
            if before is None:
                change_types = ["added"]
            elif after is None:
                change_types = ["removed"]
            else:
                if before["typeId"] != after["typeId"]:
                    raise AssetDeltaError("asset_item_identity_changed")
                change_types = []
                if before["quantity"] != after["quantity"]:
                    change_types.append("quantity")
                if any(
                    before[field] != after[field]
                    for field in ("locationId", "locationType", "locationFlag")
                ):
                    change_types.append("location")
                if not change_types:
                    continue

            type_id = int((after or before or {})["typeId"])
            before_quantity = None if before is None else int(before["quantity"])
            after_quantity = None if after is None else int(after["quantity"])
            quantity_delta = (after_quantity or 0) - (before_quantity or 0)
            direction = (
                "inbound" if quantity_delta > 0 else "outbound" if quantity_delta < 0 else "neutral"
            )
            event: dict[str, object] = {
                "itemId": item_id,
                "typeId": type_id,
                "changeTypes": change_types,
                "quantityBefore": before_quantity,
                "quantityAfter": after_quantity,
                "quantityDelta": quantity_delta,
                "locationIdBefore": None if before is None else before["locationId"],
                "locationIdAfter": None if after is None else after["locationId"],
                "locationTypeBefore": None if before is None else before["locationType"],
                "locationTypeAfter": None if after is None else after["locationType"],
                "locationFlagBefore": None if before is None else before["locationFlag"],
                "locationFlagAfter": None if after is None else after["locationFlag"],
                "jobCorrelation": {
                    "state": "unmatched",
                    "key": f"{character_id}:{type_id}",
                    "direction": direction,
                    "windowStart": previous_observed_at,
                    "windowEnd": current_observed_at,
                },
            }
            event["eventId"] = _event_id(
                {
                    "characterId": character_id,
                    "previousAssetSnapshotId": previous_snapshot_id,
                    "currentAssetSnapshotId": current_snapshot_id,
                    **event,
                }
            )
            events.append(event)

    return {
        "characterId": character_id,
        "baseline": baseline,
        "previousAssetSnapshotId": previous_snapshot_id,
        "currentAssetSnapshotId": current_snapshot_id,
        "previousAssetSyncRunId": previous_sync_run_id,
        "currentAssetSyncRunId": current_sync_run_id,
        "previousObservedAt": previous_observed_at,
        "currentObservedAt": current_observed_at,
        "events": events,
        "summary": {
            "events": len(events),
            **{
                change_type: sum(change_type in event["changeTypes"] for event in events)
                for change_type in DELTA_CHANGE_TYPES
            },
        },
    }


def _json_object(raw: Any) -> Mapping[str, Any]:
    try:
        payload = json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise AssetDeltaError("asset_delta_snapshot_invalid") from error
    if not isinstance(payload, Mapping):
        raise AssetDeltaError("asset_delta_snapshot_invalid")
    return payload


def _nullable_positive(value: Any) -> int | None:
    return None if value is None else _positive_integer(value)


def _nullable_quantity(value: Any) -> int | None:
    return None if value is None else _quantity(value)


def _nullable_text(value: Any, maximum: int) -> str | None:
    return None if value is None else _bounded_text(value, maximum)


def _validated_event(raw: Any, payload: Mapping[str, Any]) -> dict[str, object]:
    if not isinstance(raw, Mapping):
        raise AssetDeltaError("asset_delta_snapshot_invalid")
    event_id = raw.get("eventId")
    change_types = raw.get("changeTypes")
    correlation = raw.get("jobCorrelation")
    if (
        not isinstance(event_id, str)
        or len(event_id) != 64
        or any(character not in "0123456789abcdef" for character in event_id)
        or not isinstance(change_types, list)
        or not change_types
        or len(change_types) > 2
        or any(value not in DELTA_CHANGE_TYPES for value in change_types)
        or len(set(change_types)) != len(change_types)
        or not isinstance(correlation, Mapping)
        or correlation.get("state") != "unmatched"
        or correlation.get("direction") not in DELTA_DIRECTIONS
        or correlation.get("windowStart") != payload.get("previousObservedAt")
        or correlation.get("windowEnd") != payload.get("currentObservedAt")
    ):
        raise AssetDeltaError("asset_delta_snapshot_invalid")
    item_id = _positive_integer(raw.get("itemId"))
    type_id = _positive_integer(raw.get("typeId"))
    expected_key = f"{payload['characterId']}:{type_id}"
    if correlation.get("key") != expected_key:
        raise AssetDeltaError("asset_delta_snapshot_invalid")
    before_quantity = _nullable_quantity(raw.get("quantityBefore"))
    after_quantity = _nullable_quantity(raw.get("quantityAfter"))
    quantity_delta = raw.get("quantityDelta")
    if (
        isinstance(quantity_delta, bool)
        or not isinstance(quantity_delta, int)
        or abs(quantity_delta) > MAX_SAFE_INTEGER
        or quantity_delta != (after_quantity or 0) - (before_quantity or 0)
    ):
        raise AssetDeltaError("asset_delta_snapshot_invalid")
    location_id_before = _nullable_positive(raw.get("locationIdBefore"))
    location_id_after = _nullable_positive(raw.get("locationIdAfter"))
    location_type_before = _nullable_text(raw.get("locationTypeBefore"), 40)
    location_type_after = _nullable_text(raw.get("locationTypeAfter"), 40)
    location_flag_before = _nullable_text(raw.get("locationFlagBefore"), 100)
    location_flag_after = _nullable_text(raw.get("locationFlagAfter"), 100)
    if (
        ("added" in change_types) != (before_quantity is None and after_quantity is not None)
        or ("removed" in change_types) != (before_quantity is not None and after_quantity is None)
        or ("quantity" in change_types)
        != (before_quantity is not None and after_quantity is not None and quantity_delta != 0)
        or ("location" in change_types)
        != (
            before_quantity is not None
            and after_quantity is not None
            and (location_id_before, location_type_before, location_flag_before)
            != (location_id_after, location_type_after, location_flag_after)
        )
        or correlation.get("direction")
        != ("inbound" if quantity_delta > 0 else "outbound" if quantity_delta < 0 else "neutral")
    ):
        raise AssetDeltaError("asset_delta_snapshot_invalid")
    normalized = {
        "eventId": event_id,
        "itemId": item_id,
        "typeId": type_id,
        "changeTypes": list(change_types),
        "quantityBefore": before_quantity,
        "quantityAfter": after_quantity,
        "quantityDelta": quantity_delta,
        "locationIdBefore": location_id_before,
        "locationIdAfter": location_id_after,
        "locationTypeBefore": location_type_before,
        "locationTypeAfter": location_type_after,
        "locationFlagBefore": location_flag_before,
        "locationFlagAfter": location_flag_after,
        "jobCorrelation": {
            "state": "unmatched",
            "key": expected_key,
            "direction": correlation["direction"],
            "windowStart": correlation["windowStart"],
            "windowEnd": correlation["windowEnd"],
        },
    }
    fingerprint_payload = {
        "characterId": payload["characterId"],
        "previousAssetSnapshotId": payload["previousAssetSnapshotId"],
        "currentAssetSnapshotId": payload["currentAssetSnapshotId"],
        **{key: value for key, value in normalized.items() if key != "eventId"},
    }
    if event_id != _event_id(fingerprint_payload):
        raise AssetDeltaError("asset_delta_snapshot_invalid")
    return normalized


def _delta_snapshots(connection: sqlite3.Connection) -> Iterable[sqlite3.Row]:
    return connection.execute(
        """
        SELECT cached_snapshots.payload_json, cached_snapshots.observed_at,
               sync_runs.id AS sync_run_id,
               characters.character_id, characters.name, characters.alias
        FROM cached_snapshots
        JOIN sync_runs ON sync_runs.id = cached_snapshots.sync_run_id
        JOIN characters ON characters.character_id = sync_runs.character_id
        WHERE cached_snapshots.resource = 'asset_deltas:' || characters.character_id
          AND characters.enabled = 1
          AND sync_runs.source = 'character_assets'
          AND sync_runs.status = 'completed'
        ORDER BY cached_snapshots.observed_at DESC, cached_snapshots.id DESC
        """
    )


def _asset_location_paths(
    connection: sqlite3.Connection,
    character_id: int,
) -> dict[int, dict[int, tuple[str, str | None]]]:
    """Return the newest complete path map for every historical asset snapshot."""
    rows = connection.execute(
        """
        SELECT cached_snapshots.payload_json
        FROM cached_snapshots
        JOIN sync_runs ON sync_runs.id = cached_snapshots.sync_run_id
        WHERE cached_snapshots.resource=? AND sync_runs.status='completed'
          AND sync_runs.source='asset_locations'
        ORDER BY cached_snapshots.observed_at DESC, cached_snapshots.id DESC
        """,
        (f"asset_locations:{character_id}",),
    ).fetchall()
    snapshots: dict[int, dict[int, tuple[str, str | None]]] = {}
    for row in rows:
        payload = _json_object(row["payload_json"])
        asset_snapshot_id = _positive_integer(payload.get("assetSnapshotId"))
        if asset_snapshot_id in snapshots:
            continue
        raw_locations = payload.get("locations")
        if payload.get("characterId") != character_id or not isinstance(raw_locations, list):
            raise AssetDeltaError("asset_delta_location_snapshot_invalid")
        locations: dict[int, tuple[str, str | None]] = {}
        for raw_location in raw_locations:
            if not isinstance(raw_location, Mapping):
                raise AssetDeltaError("asset_delta_location_snapshot_invalid")
            item_id = _positive_integer(raw_location.get("itemId"))
            status = raw_location.get("status")
            path = raw_location.get("path")
            if (
                status not in {"resolved", "restricted", "unresolved", "cycle"}
                or not isinstance(path, list)
                or len(path) > 64
                or item_id in locations
            ):
                raise AssetDeltaError("asset_delta_location_snapshot_invalid")
            labels: list[str] = []
            for node in path:
                if not isinstance(node, Mapping):
                    raise AssetDeltaError("asset_delta_location_snapshot_invalid")
                node_id = _positive_integer(node.get("locationId"))
                kind = _bounded_text(node.get("kind"), 40)
                access = _bounded_text(node.get("access"), 40)
                name = node.get("name")
                type_id = node.get("typeId")
                if (
                    name is not None
                    and (
                        not isinstance(name, str)
                        or not name.strip()
                        or name.strip() != name
                        or len(name) > 200
                    )
                    or type_id is not None
                    and (
                        isinstance(type_id, bool)
                        or not isinstance(type_id, int)
                        or not 0 < type_id <= MAX_SAFE_INTEGER
                    )
                ):
                    raise AssetDeltaError("asset_delta_location_snapshot_invalid")
                # Reading these values is intentional: all stored nodes remain fail-closed.
                if not access:
                    raise AssetDeltaError("asset_delta_location_snapshot_invalid")
                labels.append(str(name) if name is not None else f"{kind} #{node_id}")
            path_label = " / ".join(labels)
            if len(path_label) > 16_000:
                raise AssetDeltaError("asset_delta_location_snapshot_invalid")
            locations[item_id] = (str(status), path_label or None)
        snapshots[asset_snapshot_id] = locations
    return snapshots


def _type_names(connection: sqlite3.Connection) -> dict[int, str]:
    has_sde = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sde_types'"
    ).fetchone() is not None
    names = {
        int(row[0]): str(row[1])
        for row in connection.execute("SELECT type_id,name FROM resolved_type_names")
    }
    if has_sde:
        names.update(
            {
                int(row[0]): str(row[1])
                for row in connection.execute("SELECT type_id,name FROM sde_types")
            }
        )
    return names


def _read_asset_delta_events(
    connection: sqlite3.Connection,
    query: AssetDeltaQuery,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    query = validate_asset_delta_query(
        search=query.search,
        owner_character_id=query.owner_character_id,
        change_type=query.change_type,
        offset=query.offset,
        limit=query.limit,
        type_id=query.type_id,
        previous_asset_snapshot_id=query.previous_asset_snapshot_id,
        current_asset_snapshot_id=query.current_asset_snapshot_id,
    )
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    type_names = _type_names(connection)
    try:
        industry_jobs = load_latest_job_snapshots(connection)
    except IndustryJobEvidenceError as error:
        raise AssetDeltaError("asset_delta_job_evidence_invalid") from error
    search_tokens = query.search.casefold().split()
    events: list[dict[str, object]] = []
    owners: dict[int, str] = {}
    latest_observed_at: str | None = None
    has_baseline = False
    seen_event_ids: set[str] = set()
    location_paths: dict[int, dict[int, dict[int, tuple[str, str | None]]]] = {}

    for row in _delta_snapshots(connection):
        character_id = int(row["character_id"])
        owner_name = str(row["alias"] or row["name"])
        owners[character_id] = owner_name
        payload = _json_object(row["payload_json"])
        if payload.get("characterId") != character_id:
            raise AssetDeltaError("asset_delta_snapshot_invalid")
        baseline = payload.get("baseline")
        raw_events = payload.get("events")
        if not isinstance(baseline, bool) or not isinstance(raw_events, list):
            raise AssetDeltaError("asset_delta_snapshot_invalid")
        current_observed_at = payload.get("currentObservedAt")
        _parse_timestamp(current_observed_at)
        previous_observed_at = payload.get("previousObservedAt")
        previous_snapshot_id = payload.get("previousAssetSnapshotId")
        previous_sync_run_id = payload.get("previousAssetSyncRunId")
        if (
            str(row["observed_at"]) != current_observed_at
            or _positive_integer(payload.get("currentAssetSnapshotId")) <= 0
            or _positive_integer(payload.get("currentAssetSyncRunId")) != int(row["sync_run_id"])
            or baseline
            and (
                raw_events
                or previous_observed_at is not None
                or previous_snapshot_id is not None
                or previous_sync_run_id is not None
            )
            or not baseline
            and (
                _nullable_positive(previous_snapshot_id) is None
                or _nullable_positive(previous_sync_run_id) is None
                or previous_observed_at is None
                or _parse_timestamp(previous_observed_at) > _parse_timestamp(current_observed_at)
            )
        ):
            raise AssetDeltaError("asset_delta_snapshot_invalid")
        if query.owner_character_id is not None and character_id != query.owner_character_id:
            continue
        if character_id not in location_paths:
            location_paths[character_id] = _asset_location_paths(connection, character_id)
        character_locations = location_paths[character_id]
        if latest_observed_at is None:
            latest_observed_at = current_observed_at
        has_baseline = True
        for raw_event in raw_events:
            event = _validated_event(raw_event, payload)
            if event["eventId"] in seen_event_ids:
                raise AssetDeltaError("asset_delta_snapshot_invalid")
            seen_event_ids.add(str(event["eventId"]))
            if query.change_type is not None and query.change_type not in event["changeTypes"]:
                continue
            if query.type_id is not None and (
                int(event["typeId"]) != query.type_id
                or payload.get("previousAssetSnapshotId") != query.previous_asset_snapshot_id
                or payload.get("currentAssetSnapshotId") != query.current_asset_snapshot_id
            ):
                continue
            persisted_correlation = event["jobCorrelation"]
            if not isinstance(persisted_correlation, Mapping):
                raise AssetDeltaError("asset_delta_snapshot_invalid")
            event["jobCorrelation"] = correlate_asset_event(
                industry_jobs,
                character_id=character_id,
                type_id=int(event["typeId"]),
                direction=str(persisted_correlation["direction"]),
                window_start=str(persisted_correlation["windowStart"]),
                window_end=str(persisted_correlation["windowEnd"]),
                location_id_after=(
                    None
                    if event["locationIdAfter"] is None
                    else int(event["locationIdAfter"])
                ),
            )
            type_name = type_names.get(int(event["typeId"]), f"Type #{event['typeId']}")
            item_id = int(event["itemId"])
            previous_id = _nullable_positive(payload.get("previousAssetSnapshotId"))
            current_id = _positive_integer(payload.get("currentAssetSnapshotId"))
            before_location = (
                None
                if previous_id is None
                else character_locations.get(previous_id, {}).get(item_id)
            )
            after_location = character_locations.get(current_id, {}).get(item_id)
            if (
                event["quantityBefore"] is not None
                and previous_id in character_locations
                and before_location is None
                or event["quantityAfter"] is not None
                and current_id in character_locations
                and after_location is None
            ):
                raise AssetDeltaError("asset_delta_location_snapshot_invalid")
            location_status_before = None if before_location is None else before_location[0]
            location_path_before = None if before_location is None else before_location[1]
            location_status_after = None if after_location is None else after_location[0]
            location_path_after = None if after_location is None else after_location[1]
            if search_tokens:
                haystack = " ".join(
                    (
                        type_name,
                        owner_name,
                        str(event["itemId"]),
                        str(event["typeId"]),
                        str(event["eventId"]),
                        " ".join(str(value) for value in event["changeTypes"]),
                        str(event["locationFlagBefore"] or ""),
                        str(event["locationFlagAfter"] or ""),
                        str(event["locationIdBefore"] or ""),
                        str(event["locationIdAfter"] or ""),
                        str(location_path_before or ""),
                        str(location_path_after or ""),
                        " ".join(str(value) for value in event["jobCorrelation"]["jobIds"]),
                    )
                ).casefold()
                if not all(token in haystack for token in search_tokens):
                    continue
            observed_at = str(current_observed_at)
            age_seconds = max(0, int((current_time - _parse_timestamp(observed_at)).total_seconds()))
            events.append(
                {
                    **event,
                    "typeName": type_name,
                    "ownerCharacterId": character_id,
                    "ownerName": owner_name,
                    "locationStatusBefore": location_status_before,
                    "locationPathBefore": location_path_before,
                    "locationStatusAfter": location_status_after,
                    "locationPathAfter": location_path_after,
                    "previousAssetSnapshotId": previous_id,
                    "currentAssetSnapshotId": current_id,
                    "currentAssetSyncRunId": _positive_integer(payload.get("currentAssetSyncRunId")),
                    "observedAt": observed_at,
                    "ageSeconds": age_seconds,
                }
            )
        expected_summary = {
            "events": len(raw_events),
            **{
                change_type: sum(
                    change_type in event.get("changeTypes", [])
                    for event in raw_events
                    if isinstance(event, Mapping)
                )
                for change_type in DELTA_CHANGE_TYPES
            },
        }
        if payload.get("summary") != expected_summary:
            raise AssetDeltaError("asset_delta_snapshot_invalid")

    events.sort(
        key=lambda event: (
            _parse_timestamp(event["observedAt"]),
            int(event["currentAssetSnapshotId"]),
            int(event["itemId"]),
        ),
        reverse=True,
    )
    summary = {
        change_type: sum(change_type in event["changeTypes"] for event in events)
        for change_type in DELTA_CHANGE_TYPES
    }
    owner_options = [
        {"characterId": character_id, "name": owner_name}
        for character_id, owner_name in sorted(
            owners.items(), key=lambda item: (item[1].casefold(), item[0])
        )
    ]
    age_seconds = (
        None
        if latest_observed_at is None
        else max(0, int((current_time - _parse_timestamp(latest_observed_at)).total_seconds()))
    )
    return {
        "events": events,
        "owners": owner_options,
        "changeTypes": list(DELTA_CHANGE_TYPES),
        "summary": summary,
        "hasBaseline": has_baseline,
        "observedAt": latest_observed_at,
        "ageSeconds": age_seconds,
    }


def query_asset_deltas(
    connection: sqlite3.Connection,
    query: AssetDeltaQuery,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    result = _read_asset_delta_events(connection, query, now=now)
    events = result.pop("events")
    if not isinstance(events, list):
        raise AssetDeltaError("asset_delta_snapshot_invalid")
    return {
        "items": events[query.offset : query.offset + query.limit],
        "total": len(events),
        "offset": query.offset,
        "limit": query.limit,
        **result,
    }


def _checked_group_quantity(value: int) -> int:
    if abs(value) > MAX_SAFE_INTEGER:
        raise AssetDeltaError("asset_delta_group_overflow")
    return value


def query_asset_delta_groups(
    connection: sqlite3.Connection,
    query: AssetDeltaQuery,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    """Group filtered events before pagination without weakening their audit evidence."""
    if any(
        value is not None
        for value in (
            query.type_id,
            query.previous_asset_snapshot_id,
            query.current_asset_snapshot_id,
        )
    ):
        raise AssetDeltaError("asset_delta_query_invalid")
    result = _read_asset_delta_events(connection, query, now=now)
    events = result.pop("events")
    if not isinstance(events, list):
        raise AssetDeltaError("asset_delta_snapshot_invalid")
    grouped: dict[tuple[int, int, int, int], dict[str, Any]] = {}
    for event in events:
        previous_id = int(event["previousAssetSnapshotId"])
        current_id = int(event["currentAssetSnapshotId"])
        key = (
            int(event["ownerCharacterId"]),
            int(event["typeId"]),
            previous_id,
            current_id,
        )
        group = grouped.get(key)
        if group is None:
            group_id = _event_id(
                {
                    "ownerCharacterId": key[0],
                    "typeId": key[1],
                    "previousAssetSnapshotId": key[2],
                    "currentAssetSnapshotId": key[3],
                }
            )
            group = {
                "groupId": group_id,
                "typeId": key[1],
                "typeName": event["typeName"],
                "ownerCharacterId": key[0],
                "ownerName": event["ownerName"],
                "changeTypes": set(),
                "eventCount": 0,
                "itemIds": set(),
                "quantityBefore": 0,
                "quantityAfter": 0,
                "quantityDelta": 0,
                "locationsBefore": set(),
                "locationsAfter": set(),
                "previousAssetSnapshotId": previous_id,
                "currentAssetSnapshotId": current_id,
                "currentAssetSyncRunId": event["currentAssetSyncRunId"],
                "observedAt": event["observedAt"],
                "ageSeconds": event["ageSeconds"],
                "correlations": {
                    "linked": 0,
                    "ambiguous": 0,
                    "unmatched": 0,
                    "unavailable": 0,
                    "not-applicable": 0,
                },
            }
            grouped[key] = group
        group["eventCount"] += 1
        group["itemIds"].add(int(event["itemId"]))
        group["changeTypes"].update(event["changeTypes"])
        group["quantityBefore"] = _checked_group_quantity(
            int(group["quantityBefore"]) + int(event["quantityBefore"] or 0)
        )
        group["quantityAfter"] = _checked_group_quantity(
            int(group["quantityAfter"]) + int(event["quantityAfter"] or 0)
        )
        group["quantityDelta"] = _checked_group_quantity(
            int(group["quantityDelta"]) + int(event["quantityDelta"])
        )
        for side in ("Before", "After"):
            location_id = event[f"locationId{side}"]
            if location_id is not None:
                group[f"locations{side}"].add(
                    (
                        int(location_id),
                        event[f"locationType{side}"],
                        event[f"locationFlag{side}"],
                        event[f"locationPath{side}"],
                    )
                )
        state = str(event["jobCorrelation"]["state"])
        group["correlations"][state] += 1

    groups: list[dict[str, object]] = []
    for group in grouped.values():
        before_locations = group.pop("locationsBefore")
        after_locations = group.pop("locationsAfter")
        item_ids = group.pop("itemIds")
        change_types = group.pop("changeTypes")

        def single_location(
            values: set[tuple[int, str | None, str | None, str | None]],
        ) -> tuple[int | None, str | None, str | None]:
            if len(values) != 1:
                return None, None, None
            location_id, _location_type, flag, path = next(iter(values))
            return location_id, flag, path

        before_id, before_flag, before_path = single_location(before_locations)
        after_id, after_flag, after_path = single_location(after_locations)
        correlation_summary = group.pop("correlations")
        groups.append(
            {
                **group,
                "changeTypes": [
                    change_type
                    for change_type in DELTA_CHANGE_TYPES
                    if change_type in change_types
                ],
                "itemCount": len(item_ids),
                "locationCountBefore": len(before_locations),
                "locationCountAfter": len(after_locations),
                "locationIdBefore": before_id,
                "locationIdAfter": after_id,
                "locationFlagBefore": before_flag,
                "locationFlagAfter": after_flag,
                "locationPathBefore": before_path,
                "locationPathAfter": after_path,
                "jobCorrelationSummary": correlation_summary,
            }
        )
    groups.sort(
        key=lambda group: (
            _parse_timestamp(group["observedAt"]),
            str(group["typeName"]).casefold(),
            str(group["groupId"]),
        ),
        reverse=True,
    )
    return {
        "items": groups[query.offset : query.offset + query.limit],
        "total": len(groups),
        "eventTotal": len(events),
        "offset": query.offset,
        "limit": query.limit,
        **result,
    }
