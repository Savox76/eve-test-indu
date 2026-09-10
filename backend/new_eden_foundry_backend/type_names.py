"""Bounded ESI inventory-type name resolution persisted in SQLite."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping
from typing import Any, Final

from .esi_client import EsiClient


MAX_SAFE_INTEGER: Final = 9_007_199_254_740_991
TYPE_NAME_BATCH_SIZE: Final = 1_000


class TypeNameResolutionError(RuntimeError):
    pass


def _validated_ids(type_ids: Iterable[int]) -> list[int]:
    values = sorted(set(type_ids))
    if any(
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 < value <= MAX_SAFE_INTEGER
        for value in values
    ):
        raise TypeNameResolutionError("type_name_ids_invalid")
    return values


def _validated_names(payload: Any, expected: set[int]) -> list[tuple[int, str]]:
    if not isinstance(payload, list) or len(payload) != len(expected):
        raise TypeNameResolutionError("type_name_payload_invalid")
    result: list[tuple[int, str]] = []
    for row in payload:
        if not isinstance(row, Mapping) or set(row) != {"id", "name", "category"}:
            raise TypeNameResolutionError("type_name_payload_invalid")
        type_id = row["id"]
        name = row["name"]
        if (
            isinstance(type_id, bool)
            or not isinstance(type_id, int)
            or type_id not in expected
            or row["category"] != "inventory_type"
            or not isinstance(name, str)
            or not name.strip()
            or name != name.strip()
            or len(name) > 200
        ):
            raise TypeNameResolutionError("type_name_payload_invalid")
        result.append((type_id, name))
    if {type_id for type_id, _name in result} != expected:
        raise TypeNameResolutionError("type_name_payload_invalid")
    return result


def resolve_type_names(
    connection: sqlite3.Connection,
    client: EsiClient,
    type_ids: Iterable[int],
) -> int:
    """Resolve only unknown type IDs in bounded ESI batches."""
    requested = _validated_ids(type_ids)
    if not requested:
        return 0
    requested_set = set(requested)
    known = {
        int(row[0])
        for row in connection.execute("SELECT type_id FROM resolved_type_names")
        if int(row[0]) in requested_set
    }
    table_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sde_types'"
    ).fetchone()
    if table_exists is not None:
        known.update(
            int(row[0])
            for row in connection.execute("SELECT type_id FROM sde_types")
            if int(row[0]) in requested_set
        )
    missing = [type_id for type_id in requested if type_id not in known]
    resolved: list[tuple[int, str]] = []
    for start in range(0, len(missing), TYPE_NAME_BATCH_SIZE):
        batch = missing[start : start + TYPE_NAME_BATCH_SIZE]
        response = client.post_json("/universe/names/", batch)
        resolved.extend(_validated_names(response.payload, set(batch)))
    if resolved:
        connection.executemany(
            "INSERT INTO resolved_type_names(type_id,name) VALUES(?,?) "
            "ON CONFLICT(type_id) DO UPDATE SET name=excluded.name, "
            "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')",
            resolved,
        )
        connection.commit()
    return len(resolved)
