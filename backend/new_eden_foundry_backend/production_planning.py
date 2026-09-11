"""Persistent production goals and deterministic gross-material expansion."""

from __future__ import annotations

import heapq
import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Mapping

from .sde import (
    MAX_SAFE_INTEGER,
    SUPPORTED_BLUEPRINT_ACTIVITIES,
    current_sde_blueprint_activity_build,
)


MAX_PAGE_SIZE = 100
MAX_CATALOG_PAGE_SIZE = 100
MAX_PLAN_STEPS = 500
PLAN_STATES = (
    "ready",
    "sde-unavailable",
    "recipe-missing",
    "cycle",
    "complexity-limit",
)
PLAN_SORT_FIELDS = ("priority", "product", "owner", "activity", "state", "updated")
SORT_DIRECTIONS = ("asc", "desc")


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
        "activity",
        "productTypeId",
        "targetQuantity",
        "priority",
        "note",
    }
    if not isinstance(payload, Mapping) or set(payload) != expected:
        raise ProductionPlanningError("production_plan_input_invalid")
    plan_id = payload["planId"]
    note = payload["note"]
    if note is not None:
        try:
            note = _normalized_text(note, 240) or None
        except ProductionPlanningError as error:
            raise ProductionPlanningError("production_plan_input_invalid") from error
    if (
        plan_id is not None
        and not _positive_int(plan_id)
        or not _positive_int(payload["ownerCharacterId"])
        or not _positive_int(payload["blueprintTypeId"])
        or payload["activity"] not in SUPPORTED_BLUEPRINT_ACTIVITIES
        or not _positive_int(payload["productTypeId"])
        or not _positive_int(payload["targetQuantity"])
        or not _non_negative_int(payload["priority"])
        or payload["priority"] > 999
    ):
        raise ProductionPlanningError("production_plan_input_invalid")
    return {**payload, "note": note}


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
        "grossMaterials": [],
        "warnings": [],
        "cycleTypeIds": [],
        "totalBaseTimeSeconds": None,
    }


def resolve_production_plan(
    connection: sqlite3.Connection,
    plan: Mapping[str, Any],
    *,
    loaded_recipes: tuple[dict[int, list[Recipe]], dict[tuple[int, str, int], Recipe]]
    | None = None,
) -> dict[str, Any]:
    """Resolve one goal with a stable recipe tie-break and exact integer rounding."""

    build_number = current_sde_blueprint_activity_build(connection)
    if build_number is None or not _sde_tables_available(connection):
        return _empty_resolution(connection, plan, "sde-unavailable", build_number)
    by_product, by_exact = loaded_recipes or _load_recipes(connection)
    root_key = (
        int(plan["blueprint_type_id"]),
        str(plan["activity"]),
        int(plan["product_type_id"]),
    )
    root = by_exact.get(root_key)
    if root is None:
        return _empty_resolution(connection, plan, "recipe-missing", build_number)

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
                return result

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
        return result

    required: dict[int, int] = defaultdict(int)
    required[root.product_type_id] = int(plan["target_quantity"])
    gross: dict[int, tuple[str, int]] = {}
    steps: list[dict[str, Any]] = []
    total_base_time = 0
    for sequence, product_type_id in enumerate(ordered, start=1):
        recipe = selected[product_type_id]
        quantity_needed = required[product_type_id]
        runs = (quantity_needed + recipe.output_quantity - 1) // recipe.output_quantity
        produced_quantity = _checked_multiply(runs, recipe.output_quantity)
        direct_materials: list[dict[str, Any]] = []
        for material_type_id, material_name, base_quantity in recipe.materials:
            gross_quantity = _checked_multiply(runs, base_quantity)
            direct_materials.append(
                {
                    "typeId": material_type_id,
                    "typeName": material_name,
                    "quantityPerRun": base_quantity,
                    "grossQuantity": gross_quantity,
                    "producedByPlan": material_type_id in selected,
                }
            )
            if material_type_id in selected:
                required[material_type_id] = _checked_add(
                    required[material_type_id], gross_quantity
                )
            else:
                previous = gross.get(material_type_id, (material_name, 0))[1]
                gross[material_type_id] = (
                    material_name,
                    _checked_add(previous, gross_quantity),
                )
        step_time = _checked_multiply(runs, recipe.base_time_seconds)
        total_base_time = _checked_add(total_base_time, step_time)
        steps.append(
            {
                "sequence": sequence,
                "blueprintTypeId": recipe.blueprint_type_id,
                "blueprintName": recipe.blueprint_name,
                "activity": recipe.activity,
                "productTypeId": product_type_id,
                "productName": recipe.product_name,
                "requiredQuantity": quantity_needed,
                "outputQuantityPerRun": recipe.output_quantity,
                "runs": runs,
                "producedQuantity": produced_quantity,
                "surplusQuantity": produced_quantity - quantity_needed,
                "baseTimeSecondsPerRun": recipe.base_time_seconds,
                "totalBaseTimeSeconds": step_time,
                "recipeAlternatives": len(by_product.get(product_type_id, [])),
                "materials": direct_materials,
            }
        )
    execution_steps = [
        {**step, "sequence": sequence}
        for sequence, step in enumerate(reversed(steps), start=1)
    ]
    return {
        "state": "ready",
        "buildNumber": build_number,
        "blueprintName": root.blueprint_name,
        "productName": root.product_name,
        "steps": execution_steps,
        "grossMaterials": [
            {"typeId": type_id, "typeName": value[0], "quantity": value[1]}
            for type_id, value in sorted(
                gross.items(), key=lambda item: (item[1][0].casefold(), item[0])
            )
        ],
        "warnings": sorted(warnings, key=lambda item: (item["typeName"].casefold(), item["typeId"])),
        "cycleTypeIds": [],
        "totalBaseTimeSeconds": total_base_time,
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
            "AS owner_name,plan.blueprint_type_id,plan.activity,plan.product_type_id,"
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
        "activity": str(row["activity"]),
        "productTypeId": int(row["product_type_id"]),
        "productName": resolution["productName"],
        "targetQuantity": int(row["target_quantity"]),
        "priority": int(row["priority"]),
        "note": None if row["note"] is None else str(row["note"]),
        "state": resolution["state"],
        "buildNumber": resolution["buildNumber"],
        "steps": resolution["steps"],
        "grossMaterials": resolution["grossMaterials"],
        "warnings": resolution["warnings"],
        "cycleTypeIds": resolution["cycleTypeIds"],
        "totalBaseTimeSeconds": resolution["totalBaseTimeSeconds"],
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
    records = [
        _serialize_plan(
            row,
            resolve_production_plan(connection, row, loaded_recipes=loaded_recipes),
        )
        for row in _plan_rows(connection)
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
        "priority": lambda item: (item["priority"], item["updatedAt"], item["planId"]),
        "product": lambda item: (str(item["productName"]).casefold(), item["productTypeId"], item["planId"]),
        "owner": lambda item: (str(item["ownerName"]).casefold(), item["ownerCharacterId"], item["planId"]),
        "activity": lambda item: (item["activity"], str(item["productName"]).casefold(), item["planId"]),
        "state": lambda item: (PLAN_STATES.index(item["state"]), str(item["productName"]).casefold(), item["planId"]),
        "updated": lambda item: (item["updatedAt"], item["planId"]),
    }
    records.sort(key=sort_keys[query["sortBy"]], reverse=query["sortDirection"] == "desc")
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
        "activities": list(SUPPORTED_BLUEPRINT_ACTIVITIES),
        "states": list(PLAN_STATES),
        "summary": summary,
        "buildNumber": build_number,
        "inventoryApplied": False,
        "modifiersApplied": False,
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
        "blueprint_type_id": value["blueprintTypeId"],
        "activity": value["activity"],
        "product_type_id": value["productTypeId"],
        "target_quantity": value["targetQuantity"],
    }
    resolved = resolve_production_plan(connection, candidate)
    if resolved["state"] in {"cycle", "complexity-limit"}:
        raise ProductionPlanningError(f"production_plan_{resolved['state']}")
    try:
        connection.execute("BEGIN IMMEDIATE")
        if value["planId"] is None:
            cursor = connection.execute(
                "INSERT INTO production_plans(owner_character_id,blueprint_type_id,activity,"
                "product_type_id,target_quantity,priority,note) VALUES (?,?,?,?,?,?,?)",
                (
                    value["ownerCharacterId"], value["blueprintTypeId"], value["activity"],
                    value["productTypeId"], value["targetQuantity"], value["priority"], value["note"],
                ),
            )
            plan_id = int(cursor.lastrowid)
        else:
            cursor = connection.execute(
                "UPDATE production_plans SET owner_character_id=?,blueprint_type_id=?,activity=?,"
                "product_type_id=?,target_quantity=?,priority=?,note=?,"
                "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
                (
                    value["ownerCharacterId"], value["blueprintTypeId"], value["activity"],
                    value["productTypeId"], value["targetQuantity"], value["priority"], value["note"],
                    value["planId"],
                ),
            )
            if cursor.rowcount != 1:
                raise ProductionPlanningError("production_plan_missing")
            plan_id = int(value["planId"])
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {
        "saved": True,
        "planId": plan_id,
        "ownerCharacterId": value["ownerCharacterId"],
        "blueprintTypeId": value["blueprintTypeId"],
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
