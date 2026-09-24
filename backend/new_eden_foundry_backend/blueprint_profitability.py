"""Read-only profitability grouped by owned blueprint type, without goals."""

from __future__ import annotations

from typing import Any, Mapping

from . import production_planning as p

RULE = "owned-blueprints-direct-material-purchase-per-hub-net-profit"


def _basis_key(row):
    item = row[3]
    return (item.kind == "copy" and item.runs == 0,
            -item.material_efficiency, -item.time_efficiency,
            item.kind != "original", row[1], row[2])


def _group_details(rows):
    variants = {}
    for _, owner_id, _, item, _, owner_name, observed_at in rows:
        usable = item.kind == "original" or item.runs > 0
        key = (owner_id, item.kind, item.material_efficiency, item.time_efficiency, usable)
        if key not in variants:
            variants[key] = {"ownerCharacterId": owner_id, "ownerName": owner_name,
                             "kind": item.kind, "materialEfficiency": item.material_efficiency,
                             "timeEfficiency": item.time_efficiency, "usable": usable,
                             "positionCount": 0, "observedAt": observed_at}
        variants[key]["positionCount"] += 1
    ordered = sorted(variants.values(), key=lambda v: (
        v["ownerName"].casefold(), v["ownerCharacterId"], v["kind"],
        -v["materialEfficiency"], -v["timeEfficiency"], not v["usable"]))
    return {"positionCount": len(rows), "variantCount": len(ordered),
            "omittedVariantCount": max(0, len(ordered) - 100), "variants": ordered[:100]}


def validate_settings(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    keys = {"runs", "offset", "facilityId", "facilityTaxBasisPoints", "materialBonusBasisPoints"}
    if not isinstance(value, Mapping) or set(value) != keys:
        raise p.ProductionPlanningError("production_plan_query_invalid")
    if (
        not p._positive_int(value["runs"]) or value["runs"] > 10_000
        or not p._non_negative_int(value["offset"])
        or value["facilityId"] is not None and not p._positive_int(value["facilityId"])
        or value["facilityTaxBasisPoints"] is not None and (
            not p._non_negative_int(value["facilityTaxBasisPoints"])
            or value["facilityTaxBasisPoints"] > 10_000
        )
        or not p._non_negative_int(value["materialBonusBasisPoints"])
        or value["materialBonusBasisPoints"] > 5_000
    ):
        raise p.ProductionPlanningError("production_plan_query_invalid")
    return dict(value)


def query_inventory(connection, query, loaded_recipes, facility_context, price_source):
    settings = query["inventoryAnalysis"]
    recipes_by_blueprint = {}
    for recipe in (() if loaded_recipes is None else loaded_recipes[1].values()):
        if recipe.activity in ("manufacturing", "reaction"):
            recipes_by_blueprint.setdefault(recipe.blueprint_type_id, []).append(recipe)
    owners = connection.execute(
        "SELECT character_id,COALESCE(alias,name) AS name FROM characters WHERE enabled=1"
    ).fetchall()
    candidates = []
    missing_owners = 0
    search = query["search"].casefold()
    for owner in owners:
        owner_id = int(owner["character_id"])
        if query["ownerCharacterId"] not in (None, owner_id):
            continue
        source = p._blueprint_source(connection, owner_id)
        if source is None:
            missing_owners += 1
            continue
        for item in source.items.values():
            recipes = recipes_by_blueprint.get(item.type_id, [])
            recipe = min(recipes, key=lambda r: (r.activity != "manufacturing", r.product_type_id)) if recipes else None
            name = recipe.blueprint_name if recipe else p._fallback_name(connection, item.type_id)
            product = recipe.product_name if recipe else name
            if search and not any(search in str(v).casefold() for v in (name, product, owner["name"], item.type_id, item.item_id)):
                continue
            candidates.append((name, owner_id, item.item_id, item, recipe, str(owner["name"]), source.observed_at))
    groups = {}
    for row in candidates:
        groups.setdefault(row[3].type_id, []).append(row)
    grouped = [(min(rows, key=_basis_key), rows) for rows in groups.values()]
    grouped.sort(key=lambda group: (group[0][0].casefold(), group[0][3].type_id))
    offset = min(settings["offset"], len(grouped))
    records = []
    details = {}
    type_ids = set()
    for basis, rows in grouped[offset:offset + 25]:
        name, owner_id, item_id, item, recipe, owner_name, observed_at = basis
        needed = set() if recipe is None else {recipe.product_type_id, *(m[0] for m in recipe.materials)}
        # Bound each page by the actual market API limit, without losing later items.
        if records and len(type_ids | needed) > p.MAX_MARKET_TYPE_IDS:
            break
        type_ids.update(needed)
        runs = settings["runs"] if item.kind == "original" else min(settings["runs"], item.runs)
        status = "ready" if recipe else "recipe-missing"
        if recipe and len(recipe.products) != 1:
            status = "multiple-products"
        if runs == 0:
            status = "runs-exhausted"
        if len(needed) > p.MAX_MARKET_TYPE_IDS:
            status = "market-limit"
        material_efficiency = item.material_efficiency if recipe and recipe.activity == "manufacturing" else 0
        time_efficiency = item.time_efficiency if recipe and recipe.activity == "manufacturing" else 0
        quantity = 1 if recipe is None or runs == 0 else p._checked_multiply(runs, recipe.output_quantity)
        materials = []
        installation = {"state": "not-selected", "estimatedInstallationCost": None}
        if status == "ready":
            for type_id, type_name, base_quantity in recipe.materials:
                amount = p._facility_material_quantity(base_quantity, runs, material_efficiency, settings["materialBonusBasisPoints"])
                materials.append({"typeId": type_id, "typeName": type_name, "quantity": amount,
                                  "missingQuantity": amount, "inventoryShortageQuantity": amount,
                                  "reservationConflictQuantity": 0})
            installation = p._installation_cost_for_step(
                {"facility_id": settings["facilityId"], "facility_tax_basis_points": settings["facilityTaxBasisPoints"]},
                recipe, runs, facility_context[0], facility_context[1], price_source,
            )
        product_type_id = recipe.product_type_id if recipe else item.type_id
        records.append({
            # Internal comparison key only; never persisted as a production plan.
            "planId": item_id, "ownerCharacterId": owner_id, "ownerName": owner_name,
            "blueprintTypeId": item.type_id, "blueprintName": name, "blueprintItemId": item_id,
            "productTypeId": product_type_id, "productName": recipe.product_name if recipe else name,
            "targetQuantity": quantity, "appliedMaterialEfficiency": material_efficiency,
            "appliedTimeEfficiency": time_efficiency, "state": "ready" if status == "ready" else "recipe-missing",
            "inventoryState": "shortage", "grossMaterials": materials,
            "steps": [{"productTypeId": product_type_id, "producedQuantity": quantity, "surplusQuantity": 0}],
            "installationCostState": installation["state"],
            "estimatedInstallationCost": installation["estimatedInstallationCost"],
        })
        details[item_id] = {"kind": item.kind, "runs": runs,
                            "availableRuns": None if item.kind == "original" else item.runs,
                            "status": status, "installationState": installation["state"],
                            "observedAt": observed_at, **_group_details(rows)}
    result = p._blueprint_profitability(
        connection, records, trade_cost_mode=query["tradeCostMode"],
        sales_character_id=query["salesCharacterId"], broker_fee_basis_points=query["brokerFeeBasisPoints"],
        sales_tax_basis_points=query["salesTaxBasisPoints"], inventory_market_cache=True,
    )
    for item in result["items"]:
        item["inventory"] = details[item["planId"]]
    result["rule"] = RULE
    result["inventory"] = {"offset": offset, "total": len(grouped),
                           "nextOffset": offset + len(records) if offset + len(records) < len(grouped) else None,
                           "missingOwners": missing_owners, "runs": settings["runs"]}
    if missing_owners and result["state"] == "ready":
        result["state"] = "partial"
    return result


def inventory_location_options(connection, owners, existing, facilities):
    """Include known blueprint stations even when no asset snapshot exists yet."""
    result = {(row["ownerCharacterId"], row["facilityId"]): row for row in existing}
    for owner in owners:
        source = p._blueprint_source(connection, owner["characterId"])
        if source is None:
            continue
        for item in source.items.values():
            facility = facilities.get(item.location_id)
            key = (owner["characterId"], item.location_id)
            if facility is None or key in result:
                continue
            result[key] = {"ownerCharacterId": owner["characterId"], "facilityId": item.location_id,
                           "facilityName": facility["facilityName"], "facilityKind": facility["kind"],
                           "facilityAccess": facility["access"], "locationStatus": "resolved",
                           "materialLocations": [{"locationId": item.location_id,
                                                  "locationName": facility["facilityName"],
                                                  "locationPath": facility["facilityName"], "locationKind": "facility"}]}
    return sorted(result.values(), key=lambda r: (r["facilityName"].casefold(), r["ownerCharacterId"], r["facilityId"]))[:p.MAX_PRODUCTION_FACILITIES]
