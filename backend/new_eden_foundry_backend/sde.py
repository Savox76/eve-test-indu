"""Atomic minimal SDE import for types, groups and locations."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Iterable, Mapping, Any


class SdeImportError(RuntimeError):
    """Raised when an SDE bundle is invalid; the previous build remains active."""


@dataclass(frozen=True, slots=True)
class SdeImportResult:
    build_number: str
    groups: int
    types: int
    locations: int


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise SdeImportError(f"invalid_{field}")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise SdeImportError(f"invalid_{field}") from exc
    if parsed <= 0:
        raise SdeImportError(f"invalid_{field}")
    return parsed


def _text(value: Any, field: str, limit: int = 200) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise SdeImportError(f"invalid_{field}")
    return value.strip()


def import_minimal_sde(
    connection: sqlite3.Connection,
    *,
    build_number: str,
    groups: Iterable[Mapping[str, Any]],
    types: Iterable[Mapping[str, Any]],
    locations: Iterable[Mapping[str, Any]],
) -> SdeImportResult:
    """Replace the minimal SDE dataset in one transaction.

    Input is normalized before the transaction. Any validation, FK or write failure
    leaves the previously active SDE build untouched.
    """
    build = _text(build_number, "build_number", 80)
    normalized_groups = [
        (_positive_int(row.get("group_id"), "group_id"), _text(row.get("name"), "group_name"))
        for row in groups
    ]
    normalized_types = [
        (
            _positive_int(row.get("type_id"), "type_id"),
            _positive_int(row.get("group_id"), "type_group_id"),
            _text(row.get("name"), "type_name"),
        )
        for row in types
    ]
    normalized_locations = [
        (
            _positive_int(row.get("location_id"), "location_id"),
            str(row.get("parent_location_id") or "") or None,
            _text(row.get("name"), "location_name"),
            _text(row.get("kind"), "location_kind", 40),
        )
        for row in locations
    ]
    if not normalized_groups or not normalized_types or not normalized_locations:
        raise SdeImportError("minimal_sde_must_not_be_empty")
    if len({r[0] for r in normalized_groups}) != len(normalized_groups):
        raise SdeImportError("duplicate_group_id")
    if len({r[0] for r in normalized_types}) != len(normalized_types):
        raise SdeImportError("duplicate_type_id")
    if len({r[0] for r in normalized_locations}) != len(normalized_locations):
        raise SdeImportError("duplicate_location_id")
    group_ids = {r[0] for r in normalized_groups}
    if any(r[1] not in group_ids for r in normalized_types):
        raise SdeImportError("unknown_type_group")

    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM sde_types")
        connection.execute("DELETE FROM sde_groups")
        connection.execute("DELETE FROM sde_locations")
        connection.executemany("INSERT INTO sde_groups(group_id,name) VALUES (?,?)", normalized_groups)
        connection.executemany(
            "INSERT INTO sde_types(type_id,group_id,name) VALUES (?,?,?)", normalized_types
        )
        connection.executemany(
            "INSERT INTO sde_locations(location_id,parent_location_id,name,kind) VALUES (?,?,?,?)",
            normalized_locations,
        )
        connection.execute(
            "INSERT INTO app_metadata(key,value) VALUES('sde_build_number',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
            "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')",
            (build,),
        )
        connection.commit()
    except Exception as exc:
        connection.rollback()
        raise SdeImportError("atomic_sde_import_failed") from exc

    return SdeImportResult(build, len(normalized_groups), len(normalized_types), len(normalized_locations))


def current_sde_build(connection: sqlite3.Connection) -> str | None:
    row = connection.execute(
        "SELECT value FROM app_metadata WHERE key='sde_build_number'"
    ).fetchone()
    return None if row is None else str(row[0])
