"""Bounded, searchable asset read model and safe CSV export."""

from __future__ import annotations

import csv
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Mapping


DEFAULT_PAGE_SIZE: Final = 100
MAX_PAGE_SIZE: Final = 200
MAX_SEARCH_LENGTH: Final = 120
MAX_SAFE_INTEGER: Final = 9_007_199_254_740_991
LOCATION_STATUSES: Final = (
    "resolved",
    "restricted",
    "unresolved",
    "cycle",
    "pending",
)
SORT_FIELDS: Final = ("type", "owner", "location", "flag", "quantity", "age")
SORT_DIRECTIONS: Final = ("asc", "desc")


class AssetViewError(RuntimeError):
    """Raised when filters or a supposedly complete local snapshot are invalid."""


@dataclass(frozen=True, slots=True)
class AssetQuery:
    search: str = ""
    owner_character_id: int | None = None
    location_status: str | None = None
    offset: int = 0
    limit: int = DEFAULT_PAGE_SIZE
    sort_by: str = "type"
    sort_direction: str = "asc"


@dataclass(frozen=True, slots=True)
class AssetCsvExport:
    filename: str
    relative_path: str
    rows: int

    def as_payload(self) -> dict[str, object]:
        return {
            "filename": self.filename,
            "relativePath": self.relative_path,
            "rows": self.rows,
        }


def validate_asset_query(
    *,
    search: Any = "",
    owner_character_id: Any = None,
    location_status: Any = None,
    offset: Any = 0,
    limit: Any = DEFAULT_PAGE_SIZE,
    sort_by: Any = "type",
    sort_direction: Any = "asc",
) -> AssetQuery:
    if not isinstance(search, str) or len(search) > MAX_SEARCH_LENGTH:
        raise AssetViewError("asset_query_invalid")
    normalized_search = " ".join(search.strip().split())
    if owner_character_id is not None and (
        isinstance(owner_character_id, bool)
        or not isinstance(owner_character_id, int)
        or owner_character_id <= 0
        or owner_character_id > MAX_SAFE_INTEGER
    ):
        raise AssetViewError("asset_query_invalid")
    if location_status is not None and location_status not in LOCATION_STATUSES:
        raise AssetViewError("asset_query_invalid")
    if (
        isinstance(offset, bool)
        or not isinstance(offset, int)
        or offset < 0
        or offset > MAX_SAFE_INTEGER
        or isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_PAGE_SIZE
    ):
        raise AssetViewError("asset_query_invalid")
    if sort_by not in SORT_FIELDS or sort_direction not in SORT_DIRECTIONS:
        raise AssetViewError("asset_query_invalid")
    return AssetQuery(
        normalized_search,
        owner_character_id,
        location_status,
        offset,
        limit,
        sort_by,
        sort_direction,
    )


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AssetViewError("asset_snapshot_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise AssetViewError("asset_snapshot_invalid") from error
    if parsed.tzinfo is None:
        raise AssetViewError("asset_snapshot_invalid")
    return parsed.astimezone(timezone.utc)


def _snapshot_age(observed_at: str, now: datetime) -> int:
    return max(0, int((now - _parse_timestamp(observed_at)).total_seconds()))


def _load_json_object(raw: Any, error_code: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise AssetViewError(error_code) from error
    if not isinstance(payload, Mapping):
        raise AssetViewError(error_code)
    return payload


def _latest_asset_snapshots(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT characters.character_id, characters.name, characters.alias,
               cached_snapshots.id AS snapshot_id,
               cached_snapshots.payload_json, cached_snapshots.observed_at
        FROM characters
        JOIN cached_snapshots
          ON cached_snapshots.resource = 'character_assets:' || characters.character_id
        JOIN sync_runs ON sync_runs.id = cached_snapshots.sync_run_id
        WHERE characters.enabled = 1
          AND sync_runs.status = 'completed'
          AND cached_snapshots.id = (
              SELECT candidate.id
              FROM cached_snapshots AS candidate
              JOIN sync_runs AS candidate_run
                ON candidate_run.id = candidate.sync_run_id
              WHERE candidate.resource = 'character_assets:' || characters.character_id
                AND candidate_run.status = 'completed'
              ORDER BY candidate.observed_at DESC, candidate.id DESC
              LIMIT 1
          )
        ORDER BY characters.name COLLATE NOCASE, characters.character_id
        """
    ).fetchall()


def _enabled_owners(connection: sqlite3.Connection) -> list[dict[str, object]]:
    return [
        {
            "characterId": int(row["character_id"]),
            "name": str(row["alias"] or row["name"]),
        }
        for row in connection.execute(
            """
            SELECT character_id, name, alias
            FROM characters
            WHERE enabled = 1
            ORDER BY COALESCE(alias, name) COLLATE NOCASE, character_id
            """
        )
    ]


def _matching_locations(
    connection: sqlite3.Connection,
    character_id: int,
    asset_snapshot_id: int,
) -> tuple[bool, dict[int, Mapping[str, Any]]]:
    candidates = connection.execute(
        """
        SELECT cached_snapshots.payload_json
        FROM cached_snapshots
        JOIN sync_runs ON sync_runs.id = cached_snapshots.sync_run_id
        WHERE cached_snapshots.resource = ? AND sync_runs.status = 'completed'
        ORDER BY cached_snapshots.observed_at DESC, cached_snapshots.id DESC
        """,
        (f"asset_locations:{character_id}",),
    ).fetchall()
    for candidate in candidates:
        payload = _load_json_object(candidate[0], "asset_location_snapshot_invalid")
        if payload.get("assetSnapshotId") != asset_snapshot_id:
            continue
        if payload.get("characterId") != character_id or not isinstance(
            payload.get("locations"), list
        ):
            raise AssetViewError("asset_location_snapshot_invalid")
        locations: dict[int, Mapping[str, Any]] = {}
        for location in payload["locations"]:
            if not isinstance(location, Mapping):
                raise AssetViewError("asset_location_snapshot_invalid")
            item_id = location.get("itemId")
            status = location.get("status")
            path = location.get("path")
            if (
                isinstance(item_id, bool)
                or not isinstance(item_id, int)
                or item_id <= 0
                or status not in LOCATION_STATUSES[:-1]
                or not isinstance(path, list)
                or len(path) > 64
                or len(path) == 0
                or item_id in locations
            ):
                raise AssetViewError("asset_location_snapshot_invalid")
            for node in path:
                if (
                    not isinstance(node, Mapping)
                    or isinstance(node.get("locationId"), bool)
                    or not isinstance(node.get("locationId"), int)
                    or node["locationId"] <= 0
                    or node["locationId"] > MAX_SAFE_INTEGER
                    or not isinstance(node.get("kind"), str)
                    or not node["kind"].strip()
                    or len(node["kind"].strip()) > 40
                    or not isinstance(node.get("access"), str)
                    or not node["access"].strip()
                    or len(node["access"].strip()) > 40
                    or not (
                        node.get("name") is None
                        or isinstance(node.get("name"), str)
                        and bool(node["name"].strip())
                        and len(node["name"].strip()) <= 200
                    )
                    or not (
                        node.get("typeId") is None
                        or not isinstance(node.get("typeId"), bool)
                        and isinstance(node.get("typeId"), int)
                        and 0 < node["typeId"] <= MAX_SAFE_INTEGER
                    )
                ):
                    raise AssetViewError("asset_location_snapshot_invalid")
            locations[item_id] = location
        return True, locations
    return False, {}


def _type_names(connection: sqlite3.Connection) -> dict[int, str]:
    table_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sde_types'"
    ).fetchone()
    names = {
        int(row[0]): str(row[1])
        for row in connection.execute("SELECT type_id,name FROM resolved_type_names")
    }
    if table_exists is not None:
        names.update(
            {
                int(row[0]): str(row[1])
                for row in connection.execute("SELECT type_id,name FROM sde_types")
            }
        )
    return names


def _validated_asset(row: Any) -> Mapping[str, Any]:
    if not isinstance(row, Mapping):
        raise AssetViewError("asset_snapshot_invalid")
    integers = ("item_id", "type_id", "location_id", "quantity")
    if any(
        isinstance(row.get(field), bool) or not isinstance(row.get(field), int)
        for field in integers
    ):
        raise AssetViewError("asset_snapshot_invalid")
    if (
        row["item_id"] <= 0
        or row["item_id"] > MAX_SAFE_INTEGER
        or row["type_id"] <= 0
        or row["type_id"] > MAX_SAFE_INTEGER
        or row["location_id"] <= 0
        or row["location_id"] > MAX_SAFE_INTEGER
        or not 0 <= row["quantity"] <= MAX_SAFE_INTEGER
        or not isinstance(row.get("location_type"), str)
        or not row["location_type"].strip()
        or row["location_type"].strip() != row["location_type"]
        or len(row["location_type"]) > 40
        or not isinstance(row.get("location_flag"), str)
        or not row["location_flag"].strip()
        or row["location_flag"].strip() != row["location_flag"]
        or len(row["location_flag"]) > 100
    ):
        raise AssetViewError("asset_snapshot_invalid")
    return row


def _path_payload(location: Mapping[str, Any] | None) -> tuple[str, list[dict[str, object]]]:
    if location is None:
        return "", []
    nodes: list[dict[str, object]] = []
    labels: list[str] = []
    for raw_node in location["path"]:
        node = {
            "locationId": int(raw_node["locationId"]),
            "kind": str(raw_node["kind"]),
            "name": raw_node.get("name"),
            "access": str(raw_node["access"]),
            "typeId": raw_node.get("typeId"),
        }
        nodes.append(node)
        labels.append(
            str(raw_node["name"])
            if raw_node.get("name") is not None
            else f"{raw_node['kind']} #{raw_node['locationId']}"
        )
    return " / ".join(labels), nodes


def _build_rows(
    connection: sqlite3.Connection,
    query: AssetQuery,
    now: datetime,
) -> tuple[list[dict[str, object]], list[dict[str, object]], str | None, int | None]:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)
    names = _type_names(connection)
    result: list[dict[str, object]] = []
    owners = _enabled_owners(connection)
    relevant_observed: list[str] = []
    search_tokens = query.search.casefold().split()

    for snapshot in _latest_asset_snapshots(connection):
        character_id = int(snapshot["character_id"])
        owner_name = str(snapshot["alias"] or snapshot["name"])
        if query.owner_character_id is not None and character_id != query.owner_character_id:
            continue
        observed_at = str(snapshot["observed_at"])
        age_seconds = _snapshot_age(observed_at, now)
        relevant_observed.append(observed_at)
        payload = _load_json_object(snapshot["payload_json"], "asset_snapshot_invalid")
        if payload.get("characterId") != character_id or not isinstance(
            payload.get("assets"), list
        ):
            raise AssetViewError("asset_snapshot_invalid")
        has_location_snapshot, locations = _matching_locations(
            connection,
            character_id,
            int(snapshot["snapshot_id"]),
        )
        seen_items: set[int] = set()
        for raw_asset in payload["assets"]:
            asset = _validated_asset(raw_asset)
            item_id = int(asset["item_id"])
            if item_id in seen_items:
                raise AssetViewError("asset_snapshot_invalid")
            seen_items.add(item_id)
            location = locations.get(item_id)
            location_status = str(location["status"]) if location is not None else "pending"
            if query.location_status is not None and location_status != query.location_status:
                continue
            path_label, path_nodes = _path_payload(location)
            type_id = int(asset["type_id"])
            type_name = names.get(type_id, f"Type #{type_id}")
            if search_tokens:
                haystack = " ".join(
                    (
                        type_name,
                        owner_name,
                        path_label,
                        str(asset["location_flag"]),
                        str(item_id),
                        str(type_id),
                    )
                ).casefold()
                if not all(token in haystack for token in search_tokens):
                    continue
            result.append(
                {
                    "itemId": item_id,
                    "typeId": type_id,
                    "typeName": type_name,
                    "quantity": int(asset["quantity"]),
                    "ownerCharacterId": character_id,
                    "ownerName": owner_name,
                    "locationFlag": str(asset["location_flag"]),
                    "locationStatus": location_status,
                    "locationPath": path_label,
                    "locationNodes": path_nodes,
                    "observedAt": observed_at,
                    "ageSeconds": age_seconds,
                }
            )
        if has_location_snapshot and set(locations) != seen_items:
            raise AssetViewError("asset_location_snapshot_invalid")

    sort_values = {
        "type": lambda row: str(row["typeName"]).casefold(),
        "owner": lambda row: str(row["ownerName"]).casefold(),
        "location": lambda row: str(row["locationPath"]).casefold(),
        "flag": lambda row: str(row["locationFlag"]).casefold(),
        "quantity": lambda row: int(row["quantity"]),
        "age": lambda row: int(row["ageSeconds"]),
    }
    selected_sort = sort_values[query.sort_by]
    result.sort(
        key=lambda row: (selected_sort(row), int(row["itemId"])),
        reverse=query.sort_direction == "desc",
    )
    owners.sort(key=lambda owner: (str(owner["name"]).casefold(), int(owner["characterId"])))
    observed_at = min(relevant_observed, key=_parse_timestamp) if relevant_observed else None
    age_seconds = _snapshot_age(observed_at, now) if observed_at is not None else None
    return result, owners, observed_at, age_seconds


def query_assets(
    connection: sqlite3.Connection,
    query: AssetQuery,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    query = validate_asset_query(
        search=query.search,
        owner_character_id=query.owner_character_id,
        location_status=query.location_status,
        offset=query.offset,
        limit=query.limit,
        sort_by=query.sort_by,
        sort_direction=query.sort_direction,
    )
    current_time = now or datetime.now(timezone.utc)
    rows, owners, observed_at, age_seconds = _build_rows(connection, query, current_time)
    total = len(rows)
    page = rows[query.offset : query.offset + query.limit]
    quantity_total = sum(int(row["quantity"]) for row in rows)
    if quantity_total > MAX_SAFE_INTEGER:
        raise AssetViewError("asset_quantity_overflow")
    return {
        "items": page,
        "total": total,
        "quantityTotal": quantity_total,
        "offset": query.offset,
        "limit": query.limit,
        "owners": owners,
        "locationStatuses": list(LOCATION_STATUSES),
        "observedAt": observed_at,
        "ageSeconds": age_seconds,
    }


def _csv_safe_text(value: object) -> str:
    text = str(value)
    return f"'{text}" if text.lstrip().startswith(("=", "+", "-", "@")) else text


def export_assets_csv(
    connection: sqlite3.Connection,
    query: AssetQuery,
    export_directory: Path,
    *,
    now: datetime | None = None,
) -> AssetCsvExport:
    query = validate_asset_query(
        search=query.search,
        owner_character_id=query.owner_character_id,
        location_status=query.location_status,
        offset=query.offset,
        limit=query.limit,
        sort_by=query.sort_by,
        sort_direction=query.sort_direction,
    )
    if query.offset != 0:
        raise AssetViewError("asset_query_invalid")
    current_time = now or datetime.now(timezone.utc)
    rows, _owners, _observed_at, _age_seconds = _build_rows(
        connection,
        AssetQuery(
            query.search,
            query.owner_character_id,
            query.location_status,
            0,
            MAX_PAGE_SIZE,
            query.sort_by,
            query.sort_direction,
        ),
        current_time,
    )
    export_directory.mkdir(parents=True, exist_ok=True)
    if export_directory.is_symlink() or not export_directory.is_dir():
        raise AssetViewError("asset_export_unavailable")
    stamp = current_time.astimezone(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"assets-{stamp}.csv"
    destination = export_directory / filename
    suffix = 1
    while destination.exists() or (export_directory / f".{filename}.tmp").exists():
        filename = f"assets-{stamp}-{suffix}.csv"
        destination = export_directory / filename
        suffix += 1
    temporary = export_directory / f".{filename}.tmp"
    try:
        with temporary.open("x", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(
                (
                    "item_id",
                    "type_id",
                    "type_name",
                    "quantity",
                    "owner_character_id",
                    "owner_name",
                    "location_flag",
                    "location_status",
                    "location_path",
                    "observed_at",
                    "age_seconds",
                )
            )
            for row in rows:
                writer.writerow(
                    (
                        row["itemId"],
                        row["typeId"],
                        _csv_safe_text(row["typeName"]),
                        row["quantity"],
                        row["ownerCharacterId"],
                        _csv_safe_text(row["ownerName"]),
                        _csv_safe_text(row["locationFlag"]),
                        row["locationStatus"],
                        _csv_safe_text(row["locationPath"]),
                        row["observedAt"],
                        row["ageSeconds"],
                    )
                )
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise AssetViewError("asset_export_unavailable") from error
    return AssetCsvExport(
        filename,
        f"data/exports/{filename}",
        len(rows),
    )
