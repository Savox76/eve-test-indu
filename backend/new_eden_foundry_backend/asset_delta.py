"""Deterministic asset deltas and a bounded local change-history read model."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Final, Iterable, Mapping


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


def validate_asset_delta_query(
    *,
    search: Any = "",
    owner_character_id: Any = None,
    change_type: Any = None,
    offset: Any = 0,
    limit: Any = DEFAULT_DELTA_PAGE_SIZE,
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
          AND sync_runs.source = 'character_assets'
          AND sync_runs.status = 'completed'
        ORDER BY cached_snapshots.observed_at DESC, cached_snapshots.id DESC
        """
    )


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


def query_asset_deltas(
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
    )
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    type_names = _type_names(connection)
    search_tokens = query.search.casefold().split()
    events: list[dict[str, object]] = []
    owners: dict[int, str] = {}
    latest_observed_at: str | None = None
    has_baseline = False
    seen_event_ids: set[str] = set()

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
            type_name = type_names.get(int(event["typeId"]), f"Type #{event['typeId']}")
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
                    "previousAssetSnapshotId": payload.get("previousAssetSnapshotId"),
                    "currentAssetSnapshotId": _positive_integer(payload.get("currentAssetSnapshotId")),
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
    total = len(events)
    page = events[query.offset : query.offset + query.limit]
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
        "items": page,
        "total": total,
        "offset": query.offset,
        "limit": query.limit,
        "owners": owner_options,
        "changeTypes": list(DELTA_CHANGE_TYPES),
        "summary": summary,
        "hasBaseline": has_baseline,
        "observedAt": latest_observed_at,
        "ageSeconds": age_seconds,
    }
