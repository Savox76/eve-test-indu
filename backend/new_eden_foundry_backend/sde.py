"""Atomic SDE import and bounded blueprint-activity reads."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


SUPPORTED_BLUEPRINT_ACTIVITIES = ("manufacturing", "reaction")
MAX_BLUEPRINT_ACTIVITY_PAGE_SIZE = 200
MAX_BLUEPRINT_ACTIVITY_FILTER_IDS = 200
MAX_SAFE_INTEGER = 9_007_199_254_740_991


class SdeImportError(RuntimeError):
    """Raised when an SDE bundle is invalid; the previous build remains active."""


class SdeQueryError(RuntimeError):
    """Raised when a blueprint-activity query is invalid."""


@dataclass(frozen=True, slots=True)
class SdeImportResult:
    build_number: str
    groups: int
    types: int
    locations: int
    blueprint_activities: int = 0
    products: int = 0
    materials: int = 0


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SdeImportError(f"invalid_{field}")
    if value <= 0 or value > MAX_SAFE_INTEGER:
        raise SdeImportError(f"invalid_{field}")
    return value


def _text(value: Any, field: str, limit: int = 200) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise SdeImportError(f"invalid_{field}")
    return value.strip()


def _mapping(value: Any, field: str, expected_keys: set[str] | None = None) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SdeImportError(f"invalid_{field}")
    if expected_keys is not None and set(value) != expected_keys:
        raise SdeImportError(f"invalid_{field}")
    return value


def _rows(value: Any, field: str) -> list[Mapping[str, Any]]:
    if isinstance(value, (str, bytes, Mapping)):
        raise SdeImportError(f"invalid_{field}")
    try:
        rows = list(value)
    except TypeError as error:
        raise SdeImportError(f"invalid_{field}") from error
    return [_mapping(row, field) for row in rows]


def _ensure_sde_schema(connection: sqlite3.Connection) -> None:
    """Create rebuildable derived-data tables without changing the app schema version."""
    connection.execute(
        "CREATE TABLE IF NOT EXISTS sde_groups ("
        "group_id INTEGER PRIMARY KEY CHECK(group_id > 0), "
        "name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 200))"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS sde_types ("
        "type_id INTEGER PRIMARY KEY CHECK(type_id > 0), "
        "group_id INTEGER NOT NULL REFERENCES sde_groups(group_id) ON DELETE RESTRICT, "
        "name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 200))"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_sde_types_group_name "
        "ON sde_types(group_id, name COLLATE NOCASE)"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS sde_locations ("
        "location_id INTEGER PRIMARY KEY CHECK(location_id > 0), "
        "parent_location_id TEXT, "
        "name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 200), "
        "kind TEXT NOT NULL CHECK(length(trim(kind)) BETWEEN 1 AND 40))"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_sde_locations_name "
        "ON sde_locations(name COLLATE NOCASE)"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS sde_blueprint_activities ("
        "blueprint_type_id INTEGER NOT NULL "
        "REFERENCES sde_types(type_id) ON DELETE CASCADE, "
        "activity TEXT NOT NULL CHECK(activity IN ('manufacturing','reaction')), "
        "time_seconds INTEGER NOT NULL CHECK(time_seconds > 0), "
        "PRIMARY KEY(blueprint_type_id,activity)) WITHOUT ROWID"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS sde_blueprint_products ("
        "blueprint_type_id INTEGER NOT NULL, "
        "activity TEXT NOT NULL, "
        "product_type_id INTEGER NOT NULL "
        "REFERENCES sde_types(type_id) ON DELETE RESTRICT, "
        "quantity INTEGER NOT NULL CHECK(quantity > 0), "
        "PRIMARY KEY(blueprint_type_id,activity,product_type_id), "
        "FOREIGN KEY(blueprint_type_id,activity) "
        "REFERENCES sde_blueprint_activities(blueprint_type_id,activity) ON DELETE CASCADE"
        ") WITHOUT ROWID"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_sde_blueprint_products_type "
        "ON sde_blueprint_products(product_type_id,activity,blueprint_type_id)"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS sde_blueprint_materials ("
        "blueprint_type_id INTEGER NOT NULL, "
        "activity TEXT NOT NULL, "
        "material_type_id INTEGER NOT NULL "
        "REFERENCES sde_types(type_id) ON DELETE RESTRICT, "
        "quantity INTEGER NOT NULL CHECK(quantity > 0), "
        "PRIMARY KEY(blueprint_type_id,activity,material_type_id), "
        "FOREIGN KEY(blueprint_type_id,activity) "
        "REFERENCES sde_blueprint_activities(blueprint_type_id,activity) ON DELETE CASCADE"
        ") WITHOUT ROWID"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_sde_blueprint_materials_type "
        "ON sde_blueprint_materials(material_type_id,activity,blueprint_type_id)"
    )


def _normalize_reference_data(
    *,
    build_number: Any,
    groups: Any,
    types: Any,
    locations: Any,
) -> tuple[
    str,
    list[tuple[int, str]],
    list[tuple[int, int, str]],
    list[tuple[int, str | None, str, str]],
]:
    build = _text(build_number, "build_number", 80)
    normalized_groups = [
        (_positive_int(row.get("group_id"), "group_id"), _text(row.get("name"), "group_name"))
        for row in _rows(groups, "groups")
    ]
    normalized_types = [
        (
            _positive_int(row.get("type_id"), "type_id"),
            _positive_int(row.get("group_id"), "type_group_id"),
            _text(row.get("name"), "type_name"),
        )
        for row in _rows(types, "types")
    ]
    normalized_locations = [
        (
            _positive_int(row.get("location_id"), "location_id"),
            str(row.get("parent_location_id") or "") or None,
            _text(row.get("name"), "location_name"),
            _text(row.get("kind"), "location_kind", 40),
        )
        for row in _rows(locations, "locations")
    ]
    if not normalized_groups or not normalized_types or not normalized_locations:
        raise SdeImportError("minimal_sde_must_not_be_empty")
    if len({row[0] for row in normalized_groups}) != len(normalized_groups):
        raise SdeImportError("duplicate_group_id")
    if len({row[0] for row in normalized_types}) != len(normalized_types):
        raise SdeImportError("duplicate_type_id")
    if len({row[0] for row in normalized_locations}) != len(normalized_locations):
        raise SdeImportError("duplicate_location_id")
    group_ids = {row[0] for row in normalized_groups}
    if any(row[1] not in group_ids for row in normalized_types):
        raise SdeImportError("unknown_type_group")
    return build, normalized_groups, normalized_types, normalized_locations


def _normalize_blueprint_activities(
    blueprint_activities: Any,
    *,
    type_ids: set[int],
) -> tuple[
    list[tuple[int, str, int]],
    list[tuple[int, str, int, int]],
    list[tuple[int, str, int, int]],
]:
    normalized_activities: list[tuple[int, str, int]] = []
    normalized_products: list[tuple[int, str, int, int]] = []
    normalized_materials: list[tuple[int, str, int, int]] = []
    for raw_activity in _rows(blueprint_activities, "blueprint_activities"):
        row = _mapping(
            raw_activity,
            "blueprint_activity",
            {"blueprint_type_id", "activity", "time_seconds", "products", "materials"},
        )
        blueprint_type_id = _positive_int(row["blueprint_type_id"], "blueprint_type_id")
        activity = _text(row["activity"], "blueprint_activity", 40)
        if activity not in SUPPORTED_BLUEPRINT_ACTIVITIES:
            raise SdeImportError("unsupported_blueprint_activity")
        time_seconds = _positive_int(row["time_seconds"], "blueprint_time_seconds")
        if blueprint_type_id not in type_ids:
            raise SdeImportError("unknown_blueprint_type")

        products: list[tuple[int, str, int, int]] = []
        for raw_product in _rows(row["products"], "blueprint_products"):
            product = _mapping(raw_product, "blueprint_product", {"type_id", "quantity"})
            product_type_id = _positive_int(product["type_id"], "product_type_id")
            if product_type_id not in type_ids:
                raise SdeImportError("unknown_product_type")
            products.append(
                (
                    blueprint_type_id,
                    activity,
                    product_type_id,
                    _positive_int(product["quantity"], "product_quantity"),
                )
            )
        materials: list[tuple[int, str, int, int]] = []
        for raw_material in _rows(row["materials"], "blueprint_materials"):
            material = _mapping(raw_material, "blueprint_material", {"type_id", "quantity"})
            material_type_id = _positive_int(material["type_id"], "material_type_id")
            if material_type_id not in type_ids:
                raise SdeImportError("unknown_material_type")
            materials.append(
                (
                    blueprint_type_id,
                    activity,
                    material_type_id,
                    _positive_int(material["quantity"], "material_quantity"),
                )
            )
        if not products or not materials:
            raise SdeImportError("blueprint_activity_must_have_products_and_materials")
        if len({product[2] for product in products}) != len(products):
            raise SdeImportError("duplicate_blueprint_product")
        if len({material[2] for material in materials}) != len(materials):
            raise SdeImportError("duplicate_blueprint_material")
        normalized_activities.append((blueprint_type_id, activity, time_seconds))
        normalized_products.extend(products)
        normalized_materials.extend(materials)
    if not normalized_activities:
        raise SdeImportError("blueprint_activities_must_not_be_empty")
    if len({row[:2] for row in normalized_activities}) != len(normalized_activities):
        raise SdeImportError("duplicate_blueprint_activity")
    return normalized_activities, normalized_products, normalized_materials


def _replace_sde(
    connection: sqlite3.Connection,
    *,
    build: str,
    groups: Sequence[tuple[int, str]],
    types: Sequence[tuple[int, int, str]],
    locations: Sequence[tuple[int, str | None, str, str]],
    activities: Sequence[tuple[int, str, int]],
    products: Sequence[tuple[int, str, int, int]],
    materials: Sequence[tuple[int, str, int, int]],
    activity_build: bool,
) -> SdeImportResult:
    try:
        connection.execute("BEGIN IMMEDIATE")
        _ensure_sde_schema(connection)
        connection.execute("DELETE FROM sde_blueprint_materials")
        connection.execute("DELETE FROM sde_blueprint_products")
        connection.execute("DELETE FROM sde_blueprint_activities")
        connection.execute("DELETE FROM sde_types")
        connection.execute("DELETE FROM sde_groups")
        connection.execute("DELETE FROM sde_locations")
        connection.executemany("INSERT INTO sde_groups(group_id,name) VALUES (?,?)", groups)
        connection.executemany(
            "INSERT INTO sde_types(type_id,group_id,name) VALUES (?,?,?)", types
        )
        connection.executemany(
            "INSERT INTO sde_locations(location_id,parent_location_id,name,kind) VALUES (?,?,?,?)",
            locations,
        )
        connection.executemany(
            "INSERT INTO sde_blueprint_activities(blueprint_type_id,activity,time_seconds) "
            "VALUES (?,?,?)",
            activities,
        )
        connection.executemany(
            "INSERT INTO sde_blueprint_products("
            "blueprint_type_id,activity,product_type_id,quantity) VALUES (?,?,?,?)",
            products,
        )
        connection.executemany(
            "INSERT INTO sde_blueprint_materials("
            "blueprint_type_id,activity,material_type_id,quantity) VALUES (?,?,?,?)",
            materials,
        )
        connection.execute(
            "INSERT INTO app_metadata(key,value) VALUES('sde_build_number',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
            "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')",
            (build,),
        )
        if activity_build:
            connection.execute(
                "INSERT INTO app_metadata(key,value) "
                "VALUES('sde_blueprint_activity_build_number',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
                "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')",
                (build,),
            )
        else:
            connection.execute(
                "DELETE FROM app_metadata WHERE key='sde_blueprint_activity_build_number'"
            )
        connection.commit()
    except Exception as exc:
        connection.rollback()
        raise SdeImportError("atomic_sde_import_failed") from exc

    return SdeImportResult(
        build_number=build,
        groups=len(groups),
        types=len(types),
        locations=len(locations),
        blueprint_activities=len(activities),
        products=len(products),
        materials=len(materials),
    )


def import_minimal_sde(
    connection: sqlite3.Connection,
    *,
    build_number: str,
    groups: Iterable[Mapping[str, Any]],
    types: Iterable[Mapping[str, Any]],
    locations: Iterable[Mapping[str, Any]],
) -> SdeImportResult:
    """Replace the Paket-17 reference subset and clear any older activity subset."""
    build, normalized_groups, normalized_types, normalized_locations = _normalize_reference_data(
        build_number=build_number,
        groups=groups,
        types=types,
        locations=locations,
    )
    return _replace_sde(
        connection,
        build=build,
        groups=normalized_groups,
        types=normalized_types,
        locations=normalized_locations,
        activities=(),
        products=(),
        materials=(),
        activity_build=False,
    )


def import_industry_sde(
    connection: sqlite3.Connection,
    *,
    build_number: str,
    groups: Iterable[Mapping[str, Any]],
    types: Iterable[Mapping[str, Any]],
    locations: Iterable[Mapping[str, Any]],
    blueprint_activities: Iterable[Mapping[str, Any]],
) -> SdeImportResult:
    """Atomically replace reference data and manufacturing/reaction activities."""
    build, normalized_groups, normalized_types, normalized_locations = _normalize_reference_data(
        build_number=build_number,
        groups=groups,
        types=types,
        locations=locations,
    )
    normalized_activities, normalized_products, normalized_materials = (
        _normalize_blueprint_activities(
            blueprint_activities,
            type_ids={row[0] for row in normalized_types},
        )
    )
    return _replace_sde(
        connection,
        build=build,
        groups=normalized_groups,
        types=normalized_types,
        locations=normalized_locations,
        activities=normalized_activities,
        products=normalized_products,
        materials=normalized_materials,
        activity_build=True,
    )


def current_sde_build(connection: sqlite3.Connection) -> str | None:
    row = connection.execute(
        "SELECT value FROM app_metadata WHERE key='sde_build_number'"
    ).fetchone()
    return None if row is None else str(row[0])


def current_sde_blueprint_activity_build(connection: sqlite3.Connection) -> str | None:
    row = connection.execute(
        "SELECT value FROM app_metadata WHERE key='sde_blueprint_activity_build_number'"
    ).fetchone()
    return None if row is None else str(row[0])


def _query_id_list(value: Any) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) > MAX_BLUEPRINT_ACTIVITY_FILTER_IDS:
        raise SdeQueryError("sde_blueprint_activity_query_invalid")
    result: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int) or not 0 < item <= MAX_SAFE_INTEGER:
            raise SdeQueryError("sde_blueprint_activity_query_invalid")
        result.append(item)
    if len(set(result)) != len(result):
        raise SdeQueryError("sde_blueprint_activity_query_invalid")
    return tuple(result)


def validate_blueprint_activity_query(payload: Any) -> dict[str, Any]:
    expected = {"blueprintTypeIds", "productTypeIds", "activities", "offset", "limit"}
    if not isinstance(payload, Mapping) or set(payload) != expected:
        raise SdeQueryError("sde_blueprint_activity_query_invalid")
    blueprint_type_ids = _query_id_list(payload["blueprintTypeIds"])
    product_type_ids = _query_id_list(payload["productTypeIds"])
    activities = payload["activities"]
    if (
        not isinstance(activities, list)
        or len(activities) > len(SUPPORTED_BLUEPRINT_ACTIVITIES)
        or any(activity not in SUPPORTED_BLUEPRINT_ACTIVITIES for activity in activities)
        or len(set(activities)) != len(activities)
        or isinstance(payload["offset"], bool)
        or not isinstance(payload["offset"], int)
        or not 0 <= payload["offset"] <= MAX_SAFE_INTEGER
        or isinstance(payload["limit"], bool)
        or not isinstance(payload["limit"], int)
        or not 1 <= payload["limit"] <= MAX_BLUEPRINT_ACTIVITY_PAGE_SIZE
    ):
        raise SdeQueryError("sde_blueprint_activity_query_invalid")
    return {
        "blueprintTypeIds": blueprint_type_ids,
        "productTypeIds": product_type_ids,
        "activities": tuple(activities),
        "offset": payload["offset"],
        "limit": payload["limit"],
    }


def _empty_blueprint_activity_page(query: Mapping[str, Any]) -> dict[str, object]:
    return {
        "items": [],
        "total": 0,
        "offset": query["offset"],
        "limit": query["limit"],
        "buildNumber": None,
        "activities": list(SUPPORTED_BLUEPRINT_ACTIVITIES),
    }


def query_blueprint_activities(
    connection: sqlite3.Connection,
    raw_query: Any,
) -> dict[str, object]:
    """Read one bounded page from the currently active activity build."""
    query = validate_blueprint_activity_query(raw_query)
    build_number = current_sde_blueprint_activity_build(connection)
    if build_number is None:
        return _empty_blueprint_activity_page(query)

    available = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'sde_blueprint_%'"
        )
    }
    if not {
        "sde_blueprint_activities",
        "sde_blueprint_products",
        "sde_blueprint_materials",
    } <= available:
        raise SdeQueryError("sde_blueprint_activity_store_invalid")

    where: list[str] = []
    parameters: list[Any] = []
    if query["blueprintTypeIds"]:
        placeholders = ",".join("?" for _ in query["blueprintTypeIds"])
        where.append(f"activity.blueprint_type_id IN ({placeholders})")
        parameters.extend(query["blueprintTypeIds"])
    if query["productTypeIds"]:
        placeholders = ",".join("?" for _ in query["productTypeIds"])
        where.append(
            "EXISTS (SELECT 1 FROM sde_blueprint_products selected_product "
            "WHERE selected_product.blueprint_type_id=activity.blueprint_type_id "
            "AND selected_product.activity=activity.activity "
            f"AND selected_product.product_type_id IN ({placeholders}))"
        )
        parameters.extend(query["productTypeIds"])
    if query["activities"]:
        placeholders = ",".join("?" for _ in query["activities"])
        where.append(f"activity.activity IN ({placeholders})")
        parameters.extend(query["activities"])
    where_sql = "" if not where else " WHERE " + " AND ".join(where)

    total = int(
        connection.execute(
            "SELECT COUNT(*) FROM sde_blueprint_activities activity" + where_sql,
            parameters,
        ).fetchone()[0]
    )
    activity_rows = connection.execute(
        "SELECT activity.blueprint_type_id,blueprint.name AS blueprint_name,"
        "activity.activity,activity.time_seconds "
        "FROM sde_blueprint_activities activity "
        "JOIN sde_types blueprint ON blueprint.type_id=activity.blueprint_type_id"
        + where_sql
        + " ORDER BY blueprint.name COLLATE NOCASE,activity.blueprint_type_id,activity.activity "
        "LIMIT ? OFFSET ?",
        (*parameters, query["limit"], query["offset"]),
    ).fetchall()

    items: list[dict[str, object]] = []
    for row in activity_rows:
        blueprint_type_id = int(row[0])
        activity = str(row[2])
        products = connection.execute(
            "SELECT product.product_type_id,type.name,product.quantity "
            "FROM sde_blueprint_products product "
            "JOIN sde_types type ON type.type_id=product.product_type_id "
            "WHERE product.blueprint_type_id=? AND product.activity=? "
            "ORDER BY type.name COLLATE NOCASE,product.product_type_id",
            (blueprint_type_id, activity),
        ).fetchall()
        materials = connection.execute(
            "SELECT material.material_type_id,type.name,material.quantity "
            "FROM sde_blueprint_materials material "
            "JOIN sde_types type ON type.type_id=material.material_type_id "
            "WHERE material.blueprint_type_id=? AND material.activity=? "
            "ORDER BY type.name COLLATE NOCASE,material.material_type_id",
            (blueprint_type_id, activity),
        ).fetchall()
        items.append(
            {
                "blueprintTypeId": blueprint_type_id,
                "blueprintName": str(row[1]),
                "activity": activity,
                "baseTimeSeconds": int(row[3]),
                "products": [
                    {
                        "typeId": int(product[0]),
                        "typeName": str(product[1]),
                        "quantity": int(product[2]),
                    }
                    for product in products
                ],
                "materials": [
                    {
                        "typeId": int(material[0]),
                        "typeName": str(material[1]),
                        "quantity": int(material[2]),
                    }
                    for material in materials
                ],
            }
        )
    return {
        "items": items,
        "total": total,
        "offset": query["offset"],
        "limit": query["limit"],
        "buildNumber": build_number,
        "activities": list(SUPPORTED_BLUEPRINT_ACTIVITIES),
    }
