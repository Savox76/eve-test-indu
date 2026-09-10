"""Bounded read model for complete character blueprint snapshots."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping


MAX_SAFE_INTEGER = 9_007_199_254_740_991
MAX_PAGE_SIZE = 200
SORT_FIELDS = ("type", "owner", "kind", "me", "te", "runs", "age")


class BlueprintViewError(RuntimeError):
    pass


def validate_blueprint_query(payload: Any) -> dict[str, Any]:
    expected = {"search", "ownerCharacterId", "kind", "offset", "limit", "sortBy", "sortDirection"}
    if not isinstance(payload, Mapping) or set(payload) != expected:
        raise BlueprintViewError("blueprint_query_invalid")
    search = payload["search"]
    owner = payload["ownerCharacterId"]
    kind = payload["kind"]
    offset = payload["offset"]
    limit = payload["limit"]
    if (
        not isinstance(search, str) or len(search) > 120
        or owner is not None and (isinstance(owner, bool) or not isinstance(owner, int) or not 0 < owner <= MAX_SAFE_INTEGER)
        or kind not in (None, "original", "copy")
        or isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= MAX_SAFE_INTEGER
        or isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_PAGE_SIZE
        or payload["sortBy"] not in SORT_FIELDS
        or payload["sortDirection"] not in ("asc", "desc")
    ):
        raise BlueprintViewError("blueprint_query_invalid")
    return {**payload, "search": " ".join(search.strip().split())}


def _type_names(connection: sqlite3.Connection) -> dict[int, str]:
    names = {int(row[0]): str(row[1]) for row in connection.execute(
        "SELECT type_id,name FROM resolved_type_names"
    )}
    if connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sde_types'"
    ).fetchone() is not None:
        names.update({int(row[0]): str(row[1]) for row in connection.execute(
            "SELECT type_id,name FROM sde_types"
        )})
    return names


def query_blueprints(
    connection: sqlite3.Connection,
    raw_query: Any,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    query = validate_blueprint_query(raw_query)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    names = _type_names(connection)
    rows: list[dict[str, object]] = []
    owners: list[dict[str, object]] = []
    observed_values: list[str] = []
    snapshots = connection.execute(
        """
        SELECT characters.character_id,characters.name,characters.alias,
               cached_snapshots.payload_json,cached_snapshots.observed_at
        FROM characters JOIN cached_snapshots
          ON cached_snapshots.resource='character_blueprints:' || characters.character_id
        JOIN sync_runs ON sync_runs.id=cached_snapshots.sync_run_id
        WHERE sync_runs.status='completed' AND cached_snapshots.id=(
          SELECT candidate.id FROM cached_snapshots AS candidate
          JOIN sync_runs AS candidate_run ON candidate_run.id=candidate.sync_run_id
          WHERE candidate.resource='character_blueprints:' || characters.character_id
            AND candidate_run.status='completed'
          ORDER BY candidate.observed_at DESC,candidate.id DESC LIMIT 1)
        ORDER BY characters.name COLLATE NOCASE,characters.character_id
        """
    ).fetchall()
    tokens = query["search"].casefold().split()
    for snapshot in snapshots:
        character_id = int(snapshot["character_id"])
        owner_name = str(snapshot["alias"] or snapshot["name"])
        owners.append({"characterId": character_id, "name": owner_name})
        if query["ownerCharacterId"] is not None and query["ownerCharacterId"] != character_id:
            continue
        try:
            payload = json.loads(str(snapshot["payload_json"]))
            observed = datetime.fromisoformat(str(snapshot["observed_at"]).replace("Z", "+00:00"))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise BlueprintViewError("blueprint_snapshot_invalid") from error
        if not isinstance(payload, Mapping) or payload.get("characterId") != character_id or not isinstance(payload.get("blueprints"), list) or observed.tzinfo is None:
            raise BlueprintViewError("blueprint_snapshot_invalid")
        observed_text = str(snapshot["observed_at"])
        observed_values.append(observed_text)
        age = max(0, int((current - observed.astimezone(timezone.utc)).total_seconds()))
        seen: set[int] = set()
        for item in payload["blueprints"]:
            if not isinstance(item, Mapping):
                raise BlueprintViewError("blueprint_snapshot_invalid")
            try:
                item_id = int(item["item_id"])
                type_id = int(item["type_id"])
                quantity = int(item["quantity"])
                me = int(item["material_efficiency"])
                te = int(item["time_efficiency"])
                runs = int(item["runs"])
                location_id = int(item["location_id"])
                flag = str(item["location_flag"])
            except (KeyError, TypeError, ValueError) as error:
                raise BlueprintViewError("blueprint_snapshot_invalid") from error
            if item_id in seen or quantity not in (-1, -2):
                raise BlueprintViewError("blueprint_snapshot_invalid")
            seen.add(item_id)
            kind = "original" if quantity == -1 else "copy"
            if query["kind"] is not None and query["kind"] != kind:
                continue
            type_name = names.get(type_id, f"Type #{type_id}")
            if tokens and not all(token in f"{type_name} {owner_name} {item_id} {type_id} {location_id} {flag}".casefold() for token in tokens):
                continue
            rows.append({
                "itemId": item_id, "typeId": type_id, "typeName": type_name,
                "ownerCharacterId": character_id, "ownerName": owner_name,
                "kind": kind, "materialEfficiency": me, "timeEfficiency": te,
                "runs": runs, "locationId": location_id, "locationFlag": flag,
                "observedAt": observed_text, "ageSeconds": age,
            })
    getters = {
        "type": lambda row: str(row["typeName"]).casefold(),
        "owner": lambda row: str(row["ownerName"]).casefold(),
        "kind": lambda row: str(row["kind"]),
        "me": lambda row: int(row["materialEfficiency"]),
        "te": lambda row: int(row["timeEfficiency"]),
        "runs": lambda row: int(row["runs"]),
        "age": lambda row: int(row["ageSeconds"]),
    }
    rows.sort(key=lambda row: (getters[query["sortBy"]](row), int(row["itemId"])), reverse=query["sortDirection"] == "desc")
    owners.sort(key=lambda owner: (str(owner["name"]).casefold(), int(owner["characterId"])))
    total = len(rows)
    page = rows[query["offset"]:query["offset"] + query["limit"]]
    oldest = min(observed_values) if observed_values else None
    age = None
    if oldest is not None:
        parsed = datetime.fromisoformat(oldest.replace("Z", "+00:00")).astimezone(timezone.utc)
        age = max(0, int((current - parsed).total_seconds()))
    return {"items": page, "total": total, "offset": query["offset"], "limit": query["limit"], "owners": owners, "observedAt": oldest, "ageSeconds": age}
