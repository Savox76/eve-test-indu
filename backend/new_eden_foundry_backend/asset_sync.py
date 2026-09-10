"""Character asset synchronization with complete-run snapshot semantics."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from .esi_client import EsiClient, EsiClientError

ASSET_SCOPE = "esi-assets.read_assets.v1"


class AssetSyncError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AssetSyncResult:
    character_id: int
    sync_run_id: int
    pages: int
    assets: int


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_asset(row: Mapping[str, Any]) -> dict[str, Any]:
    required = ("item_id", "type_id", "location_id", "location_type", "location_flag", "quantity")
    if not isinstance(row, Mapping) or any(key not in row for key in required):
        raise AssetSyncError("asset_payload_invalid")
    item_id, type_id, location_id, quantity = (row["item_id"], row["type_id"], row["location_id"], row["quantity"])
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (item_id, type_id, location_id, quantity)):
        raise AssetSyncError("asset_payload_invalid")
    if item_id <= 0 or type_id <= 0 or location_id <= 0 or quantity < 0:
        raise AssetSyncError("asset_payload_invalid")
    if not isinstance(row["location_type"], str) or not isinstance(row["location_flag"], str):
        raise AssetSyncError("asset_payload_invalid")
    return dict(row)


def _pages_from_headers(headers: Mapping[str, str]) -> int:
    raw = headers.get("x-pages", "1")
    try:
        pages = int(raw)
    except (TypeError, ValueError) as exc:
        raise AssetSyncError("asset_pages_invalid") from exc
    if not 1 <= pages <= 1000:
        raise AssetSyncError("asset_pages_invalid")
    return pages


def sync_character_assets(connection: sqlite3.Connection, client: EsiClient, character_id: int) -> AssetSyncResult:
    """Fetch all asset pages and publish only a complete snapshot.

    Failed or interrupted runs are marked failed and never replace the last completed
    cached snapshot, preserving cache-first/offline behavior.
    """
    if isinstance(character_id, bool) or not isinstance(character_id, int) or character_id <= 0:
        raise ValueError("character_id must be positive")
    character = connection.execute("SELECT enabled FROM characters WHERE character_id=?", (character_id,)).fetchone()
    if character is None or not bool(character[0]):
        raise AssetSyncError("character_not_syncable")
    started = _utc_now()
    cursor = connection.execute(
        "INSERT INTO sync_runs(source,status,started_at,character_id) VALUES('character_assets','running',?,?)",
        (started, character_id),
    )
    run_id = int(cursor.lastrowid)
    try:
        first = client.get_json(f"/characters/{character_id}/assets/", query={"page": 1}, character_id=character_id, required_scopes=(ASSET_SCOPE,))
        total_pages = _pages_from_headers(first.headers)
        if not isinstance(first.payload, list):
            raise AssetSyncError("asset_payload_invalid")
        assets = [_validate_asset(row) for row in first.payload]
        for page in range(2, total_pages + 1):
            response = client.get_json(f"/characters/{character_id}/assets/", query={"page": page}, character_id=character_id, required_scopes=(ASSET_SCOPE,))
            if not isinstance(response.payload, list):
                raise AssetSyncError("asset_payload_invalid")
            assets.extend(_validate_asset(row) for row in response.payload)
        item_ids = [asset["item_id"] for asset in assets]
        if len(item_ids) != len(set(item_ids)):
            raise AssetSyncError("duplicate_asset_item")
        completed = _utc_now()
        payload = json.dumps({"characterId": character_id, "pages": total_pages, "assets": assets}, separators=(",", ":"), sort_keys=True)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) VALUES(?,?,?,?)",
            (run_id, f"character_assets:{character_id}", payload, completed),
        )
        connection.execute(
            "UPDATE sync_runs SET status='completed',completed_at=?,data_timestamp=? WHERE id=? AND status='running'",
            (completed, completed, run_id),
        )
        connection.commit()
        return AssetSyncResult(character_id, run_id, total_pages, len(assets))
    except Exception as exc:
        if connection.in_transaction:
            connection.rollback()
        completed = _utc_now()
        code = exc.code if isinstance(exc, EsiClientError) else str(exc) if isinstance(exc, AssetSyncError) else "asset_sync_failed"
        connection.execute(
            "UPDATE sync_runs SET status='failed',completed_at=?,error_code=? WHERE id=? AND status='running'",
            (completed, code[:120], run_id),
        )
        connection.commit()
        if isinstance(exc, (AssetSyncError, EsiClientError)):
            raise
        raise AssetSyncError("asset_sync_failed") from exc


def sync_enabled_characters(connection: sqlite3.Connection, client: EsiClient) -> list[AssetSyncResult]:
    """Synchronize each enabled character independently; one failure does not corrupt others."""
    rows = connection.execute("SELECT character_id FROM characters WHERE enabled=1 ORDER BY character_id").fetchall()
    results: list[AssetSyncResult] = []
    for row in rows:
        results.append(sync_character_assets(connection, client, int(row[0])))
    return results
