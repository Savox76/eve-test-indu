from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.esi_client import EsiClientError, EsiResponse
from new_eden_foundry_backend.market_prices import (
    MARKET_HUBS,
    MarketPriceError,
    latest_market_price_snapshot,
    market_hub,
    sync_market_prices,
    validate_market_price_sync_request,
)


def order(
    order_id: int,
    type_id: int,
    price: float,
    volume: int,
    *,
    location_id: int = 60_003_760,
    system_id: int = 30_000_142,
) -> dict:
    return {
        "duration": 90,
        "is_buy_order": False,
        "issued": "2026-09-20T08:00:00Z",
        "location_id": location_id,
        "min_volume": 1,
        "order_id": order_id,
        "price": price,
        "range": "region",
        "system_id": system_id,
        "type_id": type_id,
        "volume_remain": volume,
        "volume_total": volume,
    }


class FakeMarketClient:
    def __init__(self, pages: dict[int, list[list[dict]]], fail: tuple[int, int] | None = None):
        self.pages = pages
        self.fail = fail
        self.calls: list[tuple[str, dict]] = []

    def get_json(self, path: str, *, query: dict) -> EsiResponse:
        self.calls.append((path, query))
        type_id = int(query["type_id"])
        page = int(query["page"])
        if self.fail == (type_id, page):
            raise EsiClientError("esi-network-unavailable", retryable=True)
        pages = self.pages[type_id]
        return EsiResponse(200, pages[page - 1], {"x-pages": str(len(pages))}, False)


class MarketPriceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        path = Path(self.temp.name) / "foundry.db"
        initialize_database(path)
        self.db = connect_database(path)

    def tearDown(self) -> None:
        self.db.close()
        self.temp.cleanup()

    def test_profiles_are_stable_and_jita_is_the_default_priority(self) -> None:
        self.assertEqual(
            [hub["hubId"] for hub in MARKET_HUBS],
            ["jita", "amarr", "dodixie", "hek", "rens"],
        )
        self.assertEqual(market_hub("jita")["stationId"], 60_003_760)
        self.assertEqual(
            validate_market_price_sync_request(
                {"hubId": "amarr", "typeIds": [901, 900]}
            )["typeIds"],
            [900, 901],
        )
        with self.assertRaises(MarketPriceError):
            validate_market_price_sync_request(
                {"hubId": "unknown", "typeIds": [900]}
            )

    def test_syncs_all_pages_filters_station_and_publishes_atomically(self) -> None:
        client = FakeMarketClient(
            {
                900: [
                    [
                        order(1, 900, 100.0, 10),
                        order(2, 900, 50.0, 999, location_id=60_000_001),
                    ],
                    [order(3, 900, 125.5, 20)],
                ],
                901: [[order(4, 901, 2.0, 50, location_id=60_000_002)]],
            }
        )
        result = sync_market_prices(
            self.db,
            client,  # type: ignore[arg-type]
            {"hubId": "jita", "typeIds": [901, 900]},
        )
        self.assertEqual(
            (result.hub_id, result.type_count, result.order_count, result.page_count),
            ("jita", 2, 2, 3),
        )
        self.assertEqual(len(client.calls), 3)
        snapshot = latest_market_price_snapshot(
            self.db,
            "jita",
            now=datetime.now(timezone.utc),
        )
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot["requestedTypeIds"], {900, 901})
        self.assertEqual(
            [item["priceCents"] for item in snapshot["ordersByType"][900]],
            [10_000, 12_550],
        )
        self.assertNotIn(901, snapshot["ordersByType"])

    def test_failed_refresh_keeps_last_complete_snapshot(self) -> None:
        first = FakeMarketClient({900: [[order(1, 900, 100.0, 10)]]})
        original = sync_market_prices(
            self.db,
            first,  # type: ignore[arg-type]
            {"hubId": "jita", "typeIds": [900]},
        )
        failing = FakeMarketClient(
            {900: [[order(2, 900, 90.0, 10)], [order(3, 900, 95.0, 10)]]},
            fail=(900, 2),
        )
        with self.assertRaises(EsiClientError):
            sync_market_prices(
                self.db,
                failing,  # type: ignore[arg-type]
                {"hubId": "jita", "typeIds": [900]},
            )
        snapshot = latest_market_price_snapshot(self.db, "jita")
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot["syncRunId"], original.sync_run_id)
        self.assertEqual(snapshot["ordersByType"][900][0]["priceCents"], 10_000)
        self.assertEqual(
            tuple(self.db.execute(
                "SELECT status,error_code FROM sync_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()),
            ("failed", "esi-network-unavailable"),
        )

    def test_rejects_duplicate_orders_and_fractional_cents(self) -> None:
        duplicate = FakeMarketClient(
            {900: [[order(1, 900, 100.0, 10)], [order(1, 900, 101.0, 10)]]}
        )
        with self.assertRaises(MarketPriceError):
            sync_market_prices(
                self.db,
                duplicate,  # type: ignore[arg-type]
                {"hubId": "jita", "typeIds": [900]},
            )
        fractional = FakeMarketClient({900: [[order(2, 900, 1.001, 10)]]})
        with self.assertRaises(MarketPriceError):
            sync_market_prices(
                self.db,
                fractional,  # type: ignore[arg-type]
                {"hubId": "jita", "typeIds": [900]},
            )


if __name__ == "__main__":
    unittest.main()
