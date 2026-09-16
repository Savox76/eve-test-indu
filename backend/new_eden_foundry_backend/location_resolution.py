"""Resolve asset roots and container paths without weakening snapshot semantics."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Protocol

from .esi_client import EsiClient, EsiClientError


STRUCTURE_SCOPE = "esi-universe.read_structures.v1"
ASSET_SCOPE = "esi-assets.read_assets.v1"
STRUCTURE_ID_MINIMUM = 1_000_000_000_000
MAX_CONTAINER_DEPTH = 64
ASSET_NAME_BATCH_SIZE = 1_000
# Cargo, secure cargo, audit/station and freight containers from the official SDE.
STORAGE_CONTAINER_GROUP_IDS = frozenset({12, 340, 448, 649})


class LocationResolutionError(RuntimeError):
    """Raised when no complete resolved-location snapshot can be published."""


@dataclass(frozen=True, slots=True)
class RootLocation:
    location_id: int
    kind: str
    name: str | None
    solar_system_id: int | None = None
    type_id: int | None = None
    access: str = "available"
    error_code: str | None = None


class LocationProvider(Protocol):
    def station(self, location_id: int) -> RootLocation: ...

    def structure(self, location_id: int, character_id: int) -> RootLocation: ...


class EsiLocationProvider:
    """Resolve dynamic roots through the central ESI trust boundary."""

    def __init__(self, client: EsiClient) -> None:
        self._client = client

    def station(self, location_id: int) -> RootLocation:
        _require_positive_id(location_id, "station_id")
        try:
            response = self._client.get_json(f"/universe/stations/{location_id}/")
        except EsiClientError as error:
            if error.status == 404:
                return RootLocation(
                    location_id,
                    "station",
                    None,
                    access="unknown",
                    error_code="station_not_found",
                )
            raise
        payload = _location_payload(response.payload, "station")
        return RootLocation(
            location_id,
            "station",
            payload["name"],
            solar_system_id=payload["system_id"],
        )

    def structure(self, location_id: int, character_id: int) -> RootLocation:
        _require_positive_id(location_id, "structure_id")
        _require_positive_id(character_id, "character_id")
        try:
            response = self._client.get_json(
                f"/universe/structures/{location_id}/",
                character_id=character_id,
                required_scopes=(STRUCTURE_SCOPE,),
            )
        except EsiClientError as error:
            if error.status == 403:
                return RootLocation(
                    location_id,
                    "structure",
                    None,
                    access="restricted",
                    error_code="structure_forbidden",
                )
            if error.status == 404:
                return RootLocation(
                    location_id,
                    "structure",
                    None,
                    access="unknown",
                    error_code="structure_not_found",
                )
            raise
        payload = _location_payload(response.payload, "structure")
        return RootLocation(
            location_id,
            "structure",
            payload["name"],
            solar_system_id=payload["solar_system_id"],
            type_id=payload.get("type_id"),
        )


@dataclass(frozen=True, slots=True)
class LocationNode:
    location_id: int
    kind: str
    name: str | None
    access: str
    type_id: int | None = None

    def as_payload(self) -> dict[str, object]:
        return {
            "locationId": self.location_id,
            "kind": self.kind,
            "name": self.name,
            "access": self.access,
            "typeId": self.type_id,
        }


@dataclass(frozen=True, slots=True)
class ResolvedAssetLocation:
    item_id: int
    status: str
    path: tuple[LocationNode, ...]
    error_code: str | None = None

    def as_payload(self) -> dict[str, object]:
        return {
            "itemId": self.item_id,
            "status": self.status,
            "path": [node.as_payload() for node in self.path],
            "errorCode": self.error_code,
        }


@dataclass(frozen=True, slots=True)
class LocationResolutionResult:
    character_id: int
    sync_run_id: int
    asset_snapshot_id: int
    asset_sync_run_id: int
    assets: int
    resolved: int
    restricted: int
    unresolved: int
    cycles: int


@dataclass(frozen=True, slots=True)
class _Asset:
    item_id: int
    type_id: int
    location_id: int
    location_type: str


@dataclass(frozen=True, slots=True)
class _SdeLocation:
    location_id: int
    parent_location_id: int | None
    name: str
    kind: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_positive_id(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise LocationResolutionError(f"invalid_{field}")
    return value


def _bounded_text(value: Any, field: str, limit: int = 200) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise LocationResolutionError(f"invalid_{field}_payload")
    return value.strip()


def _location_payload(payload: Any, kind: str) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise LocationResolutionError(f"invalid_{kind}_payload")
    system_field = "system_id" if kind == "station" else "solar_system_id"
    name = _bounded_text(payload.get("name"), kind)
    system_id = _require_positive_id(payload.get(system_field), system_field)
    result: dict[str, Any] = {"name": name, system_field: system_id}
    if kind == "structure" and payload.get("type_id") is not None:
        result["type_id"] = _require_positive_id(payload.get("type_id"), "type_id")
    return result


def _validated_assets(rows: Iterable[Mapping[str, Any]]) -> list[_Asset]:
    assets: list[_Asset] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise LocationResolutionError("asset_snapshot_invalid")
        item_id = _require_positive_id(row.get("item_id"), "asset_item_id")
        type_id = _require_positive_id(row.get("type_id"), "asset_type_id")
        location_id = _require_positive_id(row.get("location_id"), "asset_location_id")
        location_type = row.get("location_type")
        if location_type not in {"item", "other", "solar_system", "station"}:
            raise LocationResolutionError("asset_location_type_invalid")
        assets.append(_Asset(item_id, type_id, location_id, str(location_type)))
    if len({asset.item_id for asset in assets}) != len(assets):
        raise LocationResolutionError("duplicate_asset_item")
    return assets


def _load_sde_locations(connection: sqlite3.Connection) -> dict[int, _SdeLocation]:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sde_locations'"
    ).fetchone()
    if exists is None:
        return {}
    locations: dict[int, _SdeLocation] = {}
    for row in connection.execute(
        "SELECT location_id,parent_location_id,name,kind FROM sde_locations"
    ):
        raw_parent = row[1]
        try:
            parent = None if raw_parent in (None, "") else int(raw_parent)
        except (TypeError, ValueError) as error:
            raise LocationResolutionError("sde_location_parent_invalid") from error
        locations[int(row[0])] = _SdeLocation(
            int(row[0]), parent, str(row[2]), str(row[3])
        )
    return locations


def _load_sde_type_names(connection: sqlite3.Connection) -> dict[int, str]:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sde_types'"
    ).fetchone()
    names = {
        int(row[0]): str(row[1])
        for row in connection.execute("SELECT type_id,name FROM resolved_type_names")
    }
    if exists is not None:
        names.update(
            {
                int(row[0]): str(row[1])
                for row in connection.execute("SELECT type_id,name FROM sde_types")
            }
        )
    return names


def _storage_container_type_ids(connection: sqlite3.Connection) -> frozenset[int]:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sde_types'"
    ).fetchone()
    if exists is None:
        return frozenset()
    placeholders = ",".join("?" for _ in STORAGE_CONTAINER_GROUP_IDS)
    rows = connection.execute(
        f"SELECT type_id FROM sde_types WHERE group_id IN ({placeholders})",
        tuple(sorted(STORAGE_CONTAINER_GROUP_IDS)),
    )
    return frozenset(int(row[0]) for row in rows)


def _custom_container_names(
    client: EsiClient,
    character_id: int,
    assets: list[_Asset],
    storage_container_type_ids: frozenset[int],
) -> dict[int, str]:
    asset_by_id = {asset.item_id: asset for asset in assets}
    parent_ids = {asset.location_id for asset in assets if asset.location_id in asset_by_id}
    container_ids = sorted(
        item_id
        for item_id in parent_ids
        if asset_by_id[item_id].type_id in storage_container_type_ids
    )
    names: dict[int, str] = {}
    for offset in range(0, len(container_ids), ASSET_NAME_BATCH_SIZE):
        batch = container_ids[offset : offset + ASSET_NAME_BATCH_SIZE]
        response = client.post_json(
            f"/characters/{character_id}/assets/names/",
            batch,
            character_id=character_id,
            required_scopes=(ASSET_SCOPE,),
        )
        if not isinstance(response.payload, list) or len(response.payload) > len(batch):
            raise LocationResolutionError("asset_name_payload_invalid")
        batch_ids = set(batch)
        for raw in response.payload:
            if not isinstance(raw, Mapping) or set(raw) != {"item_id", "name"}:
                raise LocationResolutionError("asset_name_payload_invalid")
            item_id = _require_positive_id(raw.get("item_id"), "asset_name_item_id")
            raw_name = raw.get("name")
            name = _bounded_text(raw_name, "asset_name")
            if (
                item_id not in batch_ids
                or item_id in names
                or not isinstance(raw_name, str)
                or name != raw_name
            ):
                raise LocationResolutionError("asset_name_payload_invalid")
            names[item_id] = name
    return names


def resolve_asset_locations(
    connection: sqlite3.Connection,
    provider: LocationProvider,
    character_id: int,
    asset_rows: Iterable[Mapping[str, Any]],
    *,
    custom_item_names: Mapping[int, str] | None = None,
    storage_container_type_ids: frozenset[int] | None = None,
) -> tuple[ResolvedAssetLocation, ...]:
    """Resolve root-first paths for one complete character asset snapshot."""
    _require_positive_id(character_id, "character_id")
    assets = _validated_assets(asset_rows)
    if custom_item_names is None:
        custom_item_names = {}
    if not isinstance(custom_item_names, Mapping) or any(
        isinstance(item_id, bool)
        or not isinstance(item_id, int)
        or item_id <= 0
        or not isinstance(name, str)
        or not name.strip()
        or name.strip() != name
        or len(name) > 200
        for item_id, name in custom_item_names.items()
    ):
        raise LocationResolutionError("asset_name_payload_invalid")
    if storage_container_type_ids is None:
        storage_container_type_ids = _storage_container_type_ids(connection)
    by_item_id = {asset.item_id: asset for asset in assets}
    sde_locations = _load_sde_locations(connection)
    type_names = _load_sde_type_names(connection)
    granted_scopes = {
        str(row[0])
        for row in connection.execute(
            "SELECT scope FROM character_scopes WHERE character_id=?", (character_id,)
        )
    }
    memo: dict[int, ResolvedAssetLocation] = {}
    root_cache: dict[tuple[str, int], ResolvedAssetLocation] = {}

    def sde_path(location_id: int) -> ResolvedAssetLocation | None:
        if location_id not in sde_locations:
            return None
        current = location_id
        visited: list[int] = []
        nodes: list[LocationNode] = []
        while current in sde_locations:
            if current in visited:
                cycle = visited[visited.index(current) :] + [current]
                return ResolvedAssetLocation(
                    0,
                    "cycle",
                    tuple(LocationNode(value, "sde_cycle", None, "unknown") for value in cycle),
                    "sde_location_cycle",
                )
            if len(visited) >= MAX_CONTAINER_DEPTH:
                return ResolvedAssetLocation(0, "unresolved", (), "location_depth_exceeded")
            visited.append(current)
            location = sde_locations[current]
            nodes.append(
                LocationNode(
                    location.location_id,
                    location.kind,
                    location.name,
                    "available",
                )
            )
            if location.parent_location_id is None:
                break
            current = location.parent_location_id
        nodes.reverse()
        return ResolvedAssetLocation(0, "resolved", tuple(nodes))

    def with_system(root: RootLocation) -> ResolvedAssetLocation:
        nodes: list[LocationNode] = []
        if root.solar_system_id is not None:
            system = sde_path(root.solar_system_id)
            if system is not None and system.status == "resolved":
                nodes.extend(system.path)
        nodes.append(
            LocationNode(
                root.location_id,
                root.kind,
                root.name,
                root.access,
                root.type_id,
            )
        )
        status = (
            "restricted"
            if root.access == "restricted"
            else "unresolved"
            if root.access == "unknown"
            else "resolved"
        )
        return ResolvedAssetLocation(0, status, tuple(nodes), root.error_code)

    def root(asset: _Asset) -> ResolvedAssetLocation:
        local = sde_path(asset.location_id)
        if local is not None:
            return local
        key = (asset.location_type, asset.location_id)
        if key in root_cache:
            return root_cache[key]
        if asset.location_type == "station":
            resolved = with_system(provider.station(asset.location_id))
        elif asset.location_type == "solar_system":
            resolved = ResolvedAssetLocation(
                0,
                "unresolved",
                (LocationNode(asset.location_id, "solar_system", None, "unknown"),),
                "solar_system_not_in_sde",
            )
        elif asset.location_id >= STRUCTURE_ID_MINIMUM:
            if STRUCTURE_SCOPE not in granted_scopes:
                resolved = with_system(
                    RootLocation(
                        asset.location_id,
                        "structure",
                        None,
                        access="restricted",
                        error_code="structure_scope_missing",
                    )
                )
            else:
                resolved = with_system(
                    provider.structure(asset.location_id, character_id)
                )
        elif asset.location_type == "item":
            resolved = ResolvedAssetLocation(
                0,
                "unresolved",
                (LocationNode(asset.location_id, "inventory_item", None, "unknown"),),
                "container_missing",
            )
        else:
            resolved = ResolvedAssetLocation(
                0,
                "unresolved",
                (LocationNode(asset.location_id, "other", None, "unknown"),),
                "location_unknown",
            )
        root_cache[key] = resolved
        return resolved

    def walk(item_id: int, stack: tuple[int, ...]) -> ResolvedAssetLocation:
        if item_id in memo:
            return memo[item_id]
        if item_id in stack:
            cycle = stack[stack.index(item_id) :] + (item_id,)
            result = ResolvedAssetLocation(
                item_id,
                "cycle",
                tuple(LocationNode(value, "container_cycle", None, "unknown") for value in cycle),
                "container_cycle",
            )
            for cycle_item in set(cycle):
                memo[cycle_item] = ResolvedAssetLocation(
                    cycle_item, result.status, result.path, result.error_code
                )
            return result
        if len(stack) >= MAX_CONTAINER_DEPTH:
            return ResolvedAssetLocation(
                item_id, "unresolved", (), "container_depth_exceeded"
            )
        asset = by_item_id[item_id]
        if asset.location_id in by_item_id:
            parent = walk(asset.location_id, stack + (item_id,))
            if parent.status == "cycle":
                result = ResolvedAssetLocation(
                    item_id, parent.status, parent.path, parent.error_code
                )
            else:
                parent_asset = by_item_id[asset.location_id]
                is_storage_container = (
                    parent_asset.type_id in storage_container_type_ids
                )
                result = ResolvedAssetLocation(
                    item_id,
                    parent.status,
                    parent.path
                    + (
                        LocationNode(
                            parent_asset.item_id,
                            "container" if is_storage_container else "inventory_item",
                            (
                                custom_item_names.get(parent_asset.item_id)
                                if is_storage_container
                                else None
                            )
                            or type_names.get(parent_asset.type_id),
                            "available",
                            parent_asset.type_id,
                        ),
                    ),
                    parent.error_code,
                )
        else:
            resolved_root = root(asset)
            result = ResolvedAssetLocation(
                item_id,
                resolved_root.status,
                resolved_root.path,
                resolved_root.error_code,
            )
        memo[item_id] = result
        return result

    return tuple(walk(asset.item_id, ()) for asset in assets)


def resolve_latest_character_asset_locations(
    connection: sqlite3.Connection,
    client: EsiClient,
    character_id: int,
) -> LocationResolutionResult:
    """Publish resolved paths only after the complete source snapshot is resolved."""
    _require_positive_id(character_id, "character_id")
    character = connection.execute(
        "SELECT enabled FROM characters WHERE character_id=?", (character_id,)
    ).fetchone()
    if character is None or not bool(character[0]):
        raise LocationResolutionError("character_not_resolvable")
    source = connection.execute(
        """
        SELECT cached_snapshots.id, cached_snapshots.sync_run_id,
               cached_snapshots.payload_json, cached_snapshots.observed_at
        FROM cached_snapshots
        JOIN sync_runs ON sync_runs.id = cached_snapshots.sync_run_id
        WHERE cached_snapshots.resource=? AND sync_runs.status='completed'
        ORDER BY cached_snapshots.observed_at DESC, cached_snapshots.id DESC
        LIMIT 1
        """,
        (f"character_assets:{character_id}",),
    ).fetchone()
    if source is None:
        raise LocationResolutionError("asset_snapshot_missing")

    started = _utc_now()
    cursor = connection.execute(
        "INSERT INTO sync_runs(source,status,started_at,character_id) "
        "VALUES('asset_locations','running',?,?)",
        (started, character_id),
    )
    run_id = int(cursor.lastrowid)
    try:
        try:
            source_payload = json.loads(str(source[2]))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise LocationResolutionError("asset_snapshot_invalid") from error
        if (
            not isinstance(source_payload, Mapping)
            or source_payload.get("characterId") != character_id
            or not isinstance(source_payload.get("assets"), list)
        ):
            raise LocationResolutionError("asset_snapshot_invalid")
        validated_assets = _validated_assets(source_payload["assets"])
        storage_container_type_ids = _storage_container_type_ids(connection)
        try:
            custom_item_names = _custom_container_names(
                client,
                character_id,
                validated_assets,
                storage_container_type_ids,
            )
        except EsiClientError:
            custom_item_names = {}
        locations = resolve_asset_locations(
            connection,
            EsiLocationProvider(client),
            character_id,
            source_payload["assets"],
            custom_item_names=custom_item_names,
            storage_container_type_ids=storage_container_type_ids,
        )
        counts = {
            status: sum(location.status == status for location in locations)
            for status in ("resolved", "restricted", "unresolved", "cycle")
        }
        completed = _utc_now()
        payload = json.dumps(
            {
                "characterId": character_id,
                "assetSnapshotId": int(source[0]),
                "assetSyncRunId": int(source[1]),
                "assetObservedAt": str(source[3]),
                "locations": [location.as_payload() for location in locations],
                "summary": counts,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (run_id, f"asset_locations:{character_id}", payload, completed),
        )
        connection.execute(
            "UPDATE sync_runs SET status='completed',completed_at=?,data_timestamp=? "
            "WHERE id=? AND status='running'",
            (completed, str(source[3]), run_id),
        )
        connection.commit()
        return LocationResolutionResult(
            character_id,
            run_id,
            int(source[0]),
            int(source[1]),
            len(locations),
            counts["resolved"],
            counts["restricted"],
            counts["unresolved"],
            counts["cycle"],
        )
    except Exception as error:
        if connection.in_transaction:
            connection.rollback()
        completed = _utc_now()
        code = (
            error.code
            if isinstance(error, EsiClientError)
            else str(error)
            if isinstance(error, LocationResolutionError)
            else "location_resolution_failed"
        )
        connection.execute(
            "UPDATE sync_runs SET status='failed',completed_at=?,error_code=? "
            "WHERE id=? AND status='running'",
            (completed, code[:120], run_id),
        )
        connection.commit()
        if isinstance(error, (LocationResolutionError, EsiClientError)):
            raise
        raise LocationResolutionError("location_resolution_failed") from error
