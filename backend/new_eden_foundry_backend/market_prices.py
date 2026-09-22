"""Validated public market snapshots for the five configured trade hubs."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .esi_client import EsiClient, EsiClientError
from .sde import MAX_SAFE_INTEGER


MARKET_PRICE_MAX_AGE_SECONDS = 15 * 60
MAX_MARKET_TYPE_IDS = 250
MAX_MARKET_PAGES_PER_TYPE = 1_000
MAX_MARKET_ORDERS = 250_000
MARKET_PRICE_RULE = "selected-hub-lowest-sell-orders-volume-weighted-cents"

MARKET_HUBS: tuple[dict[str, Any], ...] = (
    {
        "hubId": "jita",
        "name": "Jita",
        "stationId": 60_003_760,
        "stationName": "Jita IV - Moon 4 - Caldari Navy Assembly Plant",
        "stationOwnerCorporationId": 1_000_035,
        "stationOwnerCorporationName": "Caldari Navy",
        "stationOwnerFactionId": 500_001,
        "stationOwnerFactionName": "Caldari State",
        "solarSystemId": 30_000_142,
        "regionId": 10_000_002,
        "priority": 0,
    },
    {
        "hubId": "amarr",
        "name": "Amarr",
        "stationId": 60_008_494,
        "stationName": "Amarr VIII (Oris) - Emperor Family Academy",
        "stationOwnerCorporationId": 1_000_086,
        "stationOwnerCorporationName": "Emperor Family",
        "stationOwnerFactionId": 500_003,
        "stationOwnerFactionName": "Amarr Empire",
        "solarSystemId": 30_002_187,
        "regionId": 10_000_043,
        "priority": 1,
    },
    {
        "hubId": "dodixie",
        "name": "Dodixie",
        "stationId": 60_011_866,
        "stationName": "Dodixie IX - Moon 20 - Federation Navy Assembly Plant",
        "stationOwnerCorporationId": 1_000_120,
        "stationOwnerCorporationName": "Federation Navy",
        "stationOwnerFactionId": 500_004,
        "stationOwnerFactionName": "Gallente Federation",
        "solarSystemId": 30_002_659,
        "regionId": 10_000_032,
        "priority": 2,
    },
    {
        "hubId": "hek",
        "name": "Hek",
        "stationId": 60_005_686,
        "stationName": "Hek VIII - Moon 12 - Boundless Creation Factory",
        "stationOwnerCorporationId": 1_000_057,
        "stationOwnerCorporationName": "Boundless Creation",
        "stationOwnerFactionId": 500_002,
        "stationOwnerFactionName": "Minmatar Republic",
        "solarSystemId": 30_002_053,
        "regionId": 10_000_042,
        "priority": 3,
    },
    {
        "hubId": "rens",
        "name": "Rens",
        "stationId": 60_004_588,
        "stationName": "Rens VI - Moon 8 - Brutor Tribe Treasury",
        "stationOwnerCorporationId": 1_000_049,
        "stationOwnerCorporationName": "Brutor Tribe",
        "stationOwnerFactionId": 500_002,
        "stationOwnerFactionName": "Minmatar Republic",
        "solarSystemId": 30_002_510,
        "regionId": 10_000_030,
        "priority": 4,
    },
)
MARKET_HUB_INDEX = {str(hub["hubId"]): hub for hub in MARKET_HUBS}


class MarketPriceError(RuntimeError):
    """Raised when a market request or persisted snapshot is untrustworthy."""


@dataclass(frozen=True, slots=True)
class MarketPriceSyncResult:
    sync_run_id: int
    hub_id: str
    type_count: int
    order_count: int
    page_count: int
    observed_at: str


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _positive_int(value: Any) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 < value <= MAX_SAFE_INTEGER
    ):
        raise MarketPriceError("market_price_payload_invalid")
    return value


def _price_cents(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MarketPriceError("market_price_payload_invalid")
    try:
        price = Decimal(str(value))
        cents = price * 100
    except (InvalidOperation, ValueError) as error:
        raise MarketPriceError("market_price_payload_invalid") from error
    if (
        not price.is_finite()
        or price <= 0
        or cents != cents.to_integral_value()
        or cents > MAX_SAFE_INTEGER
    ):
        raise MarketPriceError("market_price_payload_invalid")
    return int(cents)


def market_hub(hub_id: Any) -> dict[str, Any]:
    if not isinstance(hub_id, str) or hub_id not in MARKET_HUB_INDEX:
        raise MarketPriceError("market_price_hub_invalid")
    return dict(MARKET_HUB_INDEX[hub_id])


def validate_market_price_sync_request(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != {"hubId", "typeIds"}:
        raise MarketPriceError("market_price_request_invalid")
    hub = market_hub(payload["hubId"])
    type_ids = payload["typeIds"]
    if (
        not isinstance(type_ids, list)
        or not 1 <= len(type_ids) <= MAX_MARKET_TYPE_IDS
        or any(
            isinstance(type_id, bool)
            or not isinstance(type_id, int)
            or not 0 < type_id <= MAX_SAFE_INTEGER
            for type_id in type_ids
        )
        or len(type_ids) != len(set(type_ids))
    ):
        raise MarketPriceError("market_price_request_invalid")
    return {"hub": hub, "typeIds": sorted(type_ids)}


def _page_count(headers: Mapping[str, str]) -> int:
    try:
        pages = int(headers.get("x-pages", "1"))
    except (TypeError, ValueError) as error:
        raise MarketPriceError("market_price_pages_invalid") from error
    if not 1 <= pages <= MAX_MARKET_PAGES_PER_TYPE:
        raise MarketPriceError("market_price_pages_invalid")
    return pages


def _validated_orders(payload: Any, expected_type_id: int) -> list[dict[str, int]]:
    required = {
        "duration",
        "is_buy_order",
        "issued",
        "location_id",
        "min_volume",
        "order_id",
        "price",
        "range",
        "system_id",
        "type_id",
        "volume_remain",
        "volume_total",
    }
    if not isinstance(payload, list):
        raise MarketPriceError("market_price_payload_invalid")
    orders: list[dict[str, int]] = []
    for row in payload:
        if not isinstance(row, Mapping) or set(row) != required:
            raise MarketPriceError("market_price_payload_invalid")
        duration = row["duration"]
        issued = row["issued"]
        order_range = row["range"]
        if (
            isinstance(duration, bool)
            or not isinstance(duration, int)
            or not 0 <= duration <= 365
            or row["is_buy_order"] is not False
            or not isinstance(issued, str)
            or not 1 <= len(issued) <= 64
            or not isinstance(order_range, str)
            or not 1 <= len(order_range) <= 32
        ):
            raise MarketPriceError("market_price_payload_invalid")
        type_id = _positive_int(row["type_id"])
        volume_remain = _positive_int(row["volume_remain"])
        volume_total = _positive_int(row["volume_total"])
        if (
            type_id != expected_type_id
            or volume_remain > volume_total
            or _positive_int(row["min_volume"]) > volume_total
        ):
            raise MarketPriceError("market_price_payload_invalid")
        orders.append(
            {
                "orderId": _positive_int(row["order_id"]),
                "typeId": type_id,
                "locationId": _positive_int(row["location_id"]),
                "systemId": _positive_int(row["system_id"]),
                "priceCents": _price_cents(row["price"]),
                "volumeRemain": volume_remain,
            }
        )
    return orders


def validate_market_price_snapshot(payload: Any) -> dict[str, Any]:
    if (
        not isinstance(payload, Mapping)
        or set(payload)
        != {"formatVersion", "hubId", "requestedTypeIds", "pageCount", "orders"}
        or payload["formatVersion"] != 1
    ):
        raise MarketPriceError("market_price_snapshot_invalid")
    hub = market_hub(payload["hubId"])
    requested = payload["requestedTypeIds"]
    page_count = payload["pageCount"]
    raw_orders = payload["orders"]
    if (
        not isinstance(requested, list)
        or not 1 <= len(requested) <= MAX_MARKET_TYPE_IDS
        or any(
            isinstance(type_id, bool)
            or not isinstance(type_id, int)
            or not 0 < type_id <= MAX_SAFE_INTEGER
            for type_id in requested
        )
        or requested != sorted(set(requested))
        or isinstance(page_count, bool)
        or not isinstance(page_count, int)
        or not len(requested) <= page_count <= len(requested) * MAX_MARKET_PAGES_PER_TYPE
        or not isinstance(raw_orders, list)
        or len(raw_orders) > MAX_MARKET_ORDERS
    ):
        raise MarketPriceError("market_price_snapshot_invalid")
    orders: list[dict[str, int]] = []
    seen_order_ids: set[int] = set()
    for row in raw_orders:
        if not isinstance(row, Mapping) or set(row) != {
            "orderId",
            "typeId",
            "locationId",
            "systemId",
            "priceCents",
            "volumeRemain",
        }:
            raise MarketPriceError("market_price_snapshot_invalid")
        try:
            order = {key: _positive_int(row[key]) for key in row}
        except MarketPriceError as error:
            raise MarketPriceError("market_price_snapshot_invalid") from error
        if (
            order["orderId"] in seen_order_ids
            or order["typeId"] not in requested
            or order["locationId"] != hub["stationId"]
            or order["systemId"] != hub["solarSystemId"]
        ):
            raise MarketPriceError("market_price_snapshot_invalid")
        seen_order_ids.add(order["orderId"])
        orders.append(order)
    expected_order = sorted(
        orders,
        key=lambda order: (
            order["typeId"],
            order["priceCents"],
            order["orderId"],
        ),
    )
    if orders != expected_order:
        raise MarketPriceError("market_price_snapshot_invalid")
    return {
        "formatVersion": 1,
        "hubId": str(hub["hubId"]),
        "requestedTypeIds": list(requested),
        "pageCount": int(page_count),
        "orders": orders,
    }


def sync_market_prices(
    connection: sqlite3.Connection,
    client: EsiClient,
    raw_request: Any,
) -> MarketPriceSyncResult:
    """Publish one complete selected-hub snapshot for the requested item types."""

    request = validate_market_price_sync_request(raw_request)
    hub = request["hub"]
    type_ids = request["typeIds"]
    started = _utc_now()
    source = f"market_prices:{hub['hubId']}"
    run = connection.execute(
        "INSERT INTO sync_runs(source,status,started_at) VALUES(?,?,?)",
        (source, "running", started),
    )
    run_id = int(run.lastrowid)
    try:
        orders: list[dict[str, int]] = []
        page_count = 0
        seen_order_ids: set[int] = set()
        for type_id in type_ids:
            path = f"/markets/{hub['regionId']}/orders/"
            first = client.get_json(
                path,
                query={"order_type": "sell", "type_id": type_id, "page": 1},
            )
            pages = _page_count(first.headers)
            page_count += pages
            responses = [first]
            for page in range(2, pages + 1):
                responses.append(
                    client.get_json(
                        path,
                        query={"order_type": "sell", "type_id": type_id, "page": page},
                    )
                )
            for response in responses:
                for order in _validated_orders(response.payload, type_id):
                    if order["orderId"] in seen_order_ids:
                        raise MarketPriceError("market_price_snapshot_invalid")
                    seen_order_ids.add(order["orderId"])
                    if (
                        order["locationId"] == hub["stationId"]
                        and order["systemId"] == hub["solarSystemId"]
                    ):
                        orders.append(order)
                    if len(orders) > MAX_MARKET_ORDERS:
                        raise MarketPriceError("market_price_snapshot_invalid")
        orders.sort(
            key=lambda order: (
                order["typeId"],
                order["priceCents"],
                order["orderId"],
            )
        )
        payload = validate_market_price_snapshot(
            {
                "formatVersion": 1,
                "hubId": hub["hubId"],
                "requestedTypeIds": type_ids,
                "pageCount": page_count,
                "orders": orders,
            }
        )
        completed = _utc_now()
        expires = (
            datetime.fromisoformat(completed.replace("Z", "+00:00"))
            + timedelta(seconds=MARKET_PRICE_MAX_AGE_SECONDS)
        ).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO cached_snapshots("
            "sync_run_id,resource,payload_json,observed_at,expires_at"
            ") VALUES(?,?,?,?,?)",
            (
                run_id,
                source,
                json.dumps(payload, separators=(",", ":"), sort_keys=True),
                completed,
                expires,
            ),
        )
        connection.execute(
            "UPDATE sync_runs SET status='completed',completed_at=?,data_timestamp=? "
            "WHERE id=? AND status='running'",
            (completed, completed, run_id),
        )
        connection.commit()
        return MarketPriceSyncResult(
            sync_run_id=run_id,
            hub_id=str(hub["hubId"]),
            type_count=len(type_ids),
            order_count=len(orders),
            page_count=page_count,
            observed_at=completed,
        )
    except Exception as error:
        if connection.in_transaction:
            connection.rollback()
        completed = _utc_now()
        code = (
            error.code
            if isinstance(error, EsiClientError)
            else str(error)
            if isinstance(error, MarketPriceError)
            else "market_price_sync_failed"
        )
        connection.execute(
            "UPDATE sync_runs SET status='failed',completed_at=?,error_code=? "
            "WHERE id=? AND status='running'",
            (completed, code[:120], run_id),
        )
        connection.commit()
        if isinstance(error, (MarketPriceError, EsiClientError)):
            raise
        raise MarketPriceError("market_price_sync_failed") from error


def latest_market_price_snapshot(
    connection: sqlite3.Connection,
    hub_id: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Return the latest complete validated market snapshot for one hub."""

    hub = market_hub(hub_id)
    source = f"market_prices:{hub_id}"
    row = connection.execute(
        """
        SELECT cached_snapshots.id,cached_snapshots.sync_run_id,
               cached_snapshots.payload_json,cached_snapshots.observed_at
        FROM cached_snapshots
        JOIN sync_runs ON sync_runs.id=cached_snapshots.sync_run_id
        WHERE cached_snapshots.resource=?
          AND sync_runs.source=?
          AND sync_runs.status='completed'
        ORDER BY cached_snapshots.observed_at DESC,cached_snapshots.id DESC
        LIMIT 1
        """,
        (source, source),
    ).fetchone()
    if row is None:
        return None
    try:
        payload = validate_market_price_snapshot(json.loads(str(row["payload_json"])))
        observed = datetime.fromisoformat(str(row["observed_at"]).replace("Z", "+00:00"))
    except (ValueError, TypeError, json.JSONDecodeError, MarketPriceError) as error:
        raise MarketPriceError("market_price_snapshot_invalid") from error
    if observed.tzinfo is None:
        raise MarketPriceError("market_price_snapshot_invalid")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age_seconds = max(0, int((current - observed.astimezone(timezone.utc)).total_seconds()))
    orders_by_type: dict[int, list[dict[str, int]]] = {}
    for order in payload["orders"]:
        orders_by_type.setdefault(int(order["typeId"]), []).append(order)
    return {
        "hub": hub,
        "snapshotId": int(row["id"]),
        "syncRunId": int(row["sync_run_id"]),
        "observedAt": str(row["observed_at"]),
        "ageSeconds": age_seconds,
        "stale": age_seconds > MARKET_PRICE_MAX_AGE_SECONDS,
        "requestedTypeIds": set(int(value) for value in payload["requestedTypeIds"]),
        "ordersByType": orders_by_type,
    }
