"""Deterministic tests for the central ESI client trust boundary."""

from __future__ import annotations

import unittest
from collections.abc import Mapping

from new_eden_foundry_backend.esi_client import (
    ESI_COMPATIBILITY_DATE,
    ESI_USER_AGENT,
    EsiClient,
    EsiClientError,
    RawEsiResponse,
)


class MutableClock:
    def __init__(self, value: float = 1_000.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


class QueueTransport:
    def __init__(self, *responses: RawEsiResponse | Exception) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, str], float]] = []

    def __call__(
        self,
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> RawEsiResponse:
        self.calls.append((url, dict(headers), timeout_seconds))
        if not self.responses:
            raise AssertionError("Unexpected ESI transport call.")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class QueuePostTransport:
    def __init__(self, *responses: RawEsiResponse | Exception) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, str], bytes, float]] = []

    def __call__(
        self,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
        timeout_seconds: float,
    ) -> RawEsiResponse:
        self.calls.append((url, dict(headers), body, timeout_seconds))
        if not self.responses:
            raise AssertionError("Unexpected ESI POST transport call.")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def response(
    status: int = 200,
    body: bytes = b'{"ok":true}',
    **headers: str,
) -> RawEsiResponse:
    return RawEsiResponse(
        status=status,
        headers={name.replace("_", "-"): value for name, value in headers.items()},
        body=body,
    )


class EsiClientTests(unittest.TestCase):
    def test_posts_bounded_public_json_and_caches_by_payload(self) -> None:
        transport = QueuePostTransport(
            response(
                body=b'[{"id":34,"name":"Tritanium","category":"inventory_type"}]',
                cache_control="max-age=60",
            )
        )
        client = EsiClient(post_transport=transport, sleep=lambda _: None)

        first = client.post_json("/universe/names/", [34])
        cached = client.post_json("/universe/names/", [34])

        self.assertFalse(first.from_cache)
        self.assertTrue(cached.from_cache)
        self.assertEqual(first.payload, cached.payload)
        self.assertEqual(1, len(transport.calls))
        url, headers, body, timeout = transport.calls[0]
        self.assertEqual("https://esi.evetech.net/universe/names/", url)
        self.assertEqual("application/json", headers["Content-Type"])
        self.assertNotIn("Authorization", headers)
        self.assertEqual(b"[34]", body)
        self.assertEqual(20.0, timeout)

    def test_applies_fixed_identity_compatibility_and_character_authorization(self) -> None:
        transport = QueueTransport(response(cache_control="max-age=0"))
        provider_calls: list[tuple[int, tuple[str, ...]]] = []

        def token_provider(character_id: int, scopes: tuple[str, ...]) -> str:
            provider_calls.append((character_id, scopes))
            return "synthetic-access-token"

        client = EsiClient(
            token_provider,
            transport=transport,
            sleep=lambda _: None,
            jitter=lambda: 0.0,
        )
        result = client.get_json(
            "/latest/characters/2112345678/assets/",
            query={"page": 2, "datasource": "tranquility"},
            character_id=2_112_345_678,
            required_scopes=("esi-assets.read_assets.v1",),
        )

        self.assertEqual({"ok": True}, result.payload)
        self.assertFalse(result.from_cache)
        self.assertEqual(
            [(2_112_345_678, ("esi-assets.read_assets.v1",))],
            provider_calls,
        )
        url, headers, timeout = transport.calls[0]
        self.assertEqual(
            "https://esi.evetech.net/latest/characters/2112345678/assets/"
            "?page=2&datasource=tranquility",
            url,
        )
        self.assertEqual(ESI_COMPATIBILITY_DATE, headers["X-Compatibility-Date"])
        self.assertEqual(ESI_USER_AGENT, headers["User-Agent"])
        self.assertTrue(ESI_USER_AGENT.startswith("New-Eden-Foundry/0.0.5-preview.5 "))
        self.assertIn("Savox76/eve-test-indu", ESI_USER_AGENT)
        self.assertEqual("Bearer synthetic-access-token", headers["Authorization"])
        self.assertEqual(20.0, timeout)

    def test_fresh_cache_avoids_network_and_stale_cache_revalidates(self) -> None:
        clock = MutableClock()
        transport = QueueTransport(
            response(
                body=b'{"value":7}',
                cache_control="max-age=10",
                etag='"synthetic-etag"',
                last_modified="Thu, 10 Sep 2026 00:00:00 GMT",
            ),
            response(
                status=304,
                body=b"",
                cache_control="max-age=20",
                etag='"synthetic-etag"',
            ),
        )
        client = EsiClient(
            transport=transport,
            monotonic=clock,
            wall_clock=lambda: 1_789_001_000.0,
            sleep=lambda _: None,
            jitter=lambda: 0.0,
        )

        first = client.get_json("/latest/status/")
        first.payload["value"] = 99
        cached = client.get_json("/latest/status/")
        self.assertFalse(first.from_cache)
        self.assertTrue(cached.from_cache)
        self.assertEqual({"value": 7}, cached.payload)
        self.assertEqual(1, len(transport.calls))

        clock.value += 11
        revalidated = client.get_json("/latest/status/")
        self.assertTrue(revalidated.from_cache)
        self.assertEqual({"value": 7}, revalidated.payload)
        self.assertEqual('"synthetic-etag"', transport.calls[1][1]["If-None-Match"])
        self.assertEqual(
            "Thu, 10 Sep 2026 00:00:00 GMT",
            transport.calls[1][1]["If-Modified-Since"],
        )

    def test_keeps_authenticated_cache_entries_separate_per_character(self) -> None:
        transport = QueueTransport(
            response(body=b'{"owner":1}', cache_control="max-age=60"),
            response(body=b'{"owner":2}', cache_control="max-age=60"),
        )
        provider_calls: list[int] = []

        def token_provider(character_id: int, _scopes: tuple[str, ...]) -> str:
            provider_calls.append(character_id)
            return f"synthetic-token-{character_id}"

        client = EsiClient(
            token_provider,
            transport=transport,
            sleep=lambda _: None,
        )
        arguments = {"required_scopes": ("esi-assets.read_assets.v1",)}
        first = client.get_json(
            "/latest/characters/assets/",
            character_id=2_112_345_678,
            **arguments,
        )
        second = client.get_json(
            "/latest/characters/assets/",
            character_id=2_112_345_679,
            **arguments,
        )
        cached_first = client.get_json(
            "/latest/characters/assets/",
            character_id=2_112_345_678,
            **arguments,
        )

        self.assertEqual({"owner": 1}, first.payload)
        self.assertEqual({"owner": 2}, second.payload)
        self.assertTrue(cached_first.from_cache)
        self.assertEqual(2, len(transport.calls))
        self.assertEqual([2_112_345_678, 2_112_345_679], provider_calls)
        self.assertNotEqual(
            transport.calls[0][1]["Authorization"],
            transport.calls[1][1]["Authorization"],
        )

    def test_retries_transient_status_and_honors_retry_after(self) -> None:
        delays: list[float] = []
        transport = QueueTransport(
            response(
                status=503,
                body=b'{"error":"synthetic"}',
                retry_after="2",
                x_esi_error_limit_remain="95",
                x_esi_error_limit_reset="10",
            ),
            response(cache_control="no-store"),
        )
        client = EsiClient(
            transport=transport,
            sleep=delays.append,
            jitter=lambda: 0.0,
        )

        self.assertEqual({"ok": True}, client.get_json("/latest/status/").payload)
        self.assertEqual([2.0], delays)
        self.assertEqual(2, len(transport.calls))
        self.assertEqual(95, client.status()["errorBudgetRemaining"])

    def test_error_budget_blocks_until_server_reset_window(self) -> None:
        clock = MutableClock()
        transport = QueueTransport(
            response(
                cache_control="no-store",
                x_esi_error_limit_remain="4",
                x_esi_error_limit_reset="30",
            ),
            response(cache_control="no-store"),
        )
        client = EsiClient(
            transport=transport,
            monotonic=clock,
            sleep=lambda _: None,
        )

        client.get_json("/latest/status/")
        with self.assertRaises(EsiClientError) as blocked:
            client.get_json("/latest/status/")
        self.assertEqual("esi-error-budget-exhausted", blocked.exception.code)
        self.assertEqual(1, len(transport.calls))

        clock.value += 31
        self.assertEqual({"ok": True}, client.get_json("/latest/status/").payload)
        self.assertEqual(2, len(transport.calls))

    def test_circuit_breaker_opens_after_bounded_failures_and_recovers(self) -> None:
        clock = MutableClock()
        transport = QueueTransport(
            OSError("synthetic network failure"),
            OSError("synthetic network failure"),
            response(cache_control="no-store"),
        )
        client = EsiClient(
            transport=transport,
            max_attempts=1,
            circuit_failure_threshold=2,
            circuit_cooldown_seconds=20,
            monotonic=clock,
            sleep=lambda _: None,
        )

        for _ in range(2):
            with self.assertRaises(EsiClientError) as failed:
                client.get_json("/latest/status/")
            self.assertEqual("esi-network-unavailable", failed.exception.code)
        with self.assertRaises(EsiClientError) as opened:
            client.get_json("/latest/status/")
        self.assertEqual("esi-circuit-open", opened.exception.code)
        self.assertEqual(2, len(transport.calls))

        clock.value += 21
        self.assertEqual({"ok": True}, client.get_json("/latest/status/").payload)
        self.assertEqual("ready", client.status()["state"])

    def test_rejects_untrusted_paths_malformed_json_and_oversized_bodies(self) -> None:
        client = EsiClient(transport=QueueTransport(), sleep=lambda _: None)
        for path in (
            "latest/status/",
            "//example.invalid/path",
            "/latest/status/?redirect=https://example.invalid",
            "/latest/status/#fragment",
        ):
            with self.subTest(path=path), self.assertRaises(EsiClientError) as invalid:
                client.get_json(path)
            self.assertEqual("esi-path-invalid", invalid.exception.code)

        malformed = EsiClient(
            transport=QueueTransport(response(body=b'{"value":1,"value":2}')),
            sleep=lambda _: None,
        )
        with self.assertRaises(EsiClientError) as duplicate:
            malformed.get_json("/latest/status/")
        self.assertEqual("esi-response-invalid", duplicate.exception.code)

        oversized = EsiClient(
            transport=QueueTransport(response(body=b"x" * 1_025)),
            max_response_bytes=1_024,
            sleep=lambda _: None,
        )
        with self.assertRaises(EsiClientError) as too_large:
            oversized.get_json("/latest/status/")
        self.assertEqual("esi-response-invalid", too_large.exception.code)

    def test_keeps_access_tokens_out_of_public_errors_and_rejects_bad_auth(self) -> None:
        secret = "synthetic-secret-token"
        client = EsiClient(
            lambda _character_id, _scopes: secret,
            transport=QueueTransport(OSError(f"failure with {secret}")),
            max_attempts=1,
            sleep=lambda _: None,
        )
        with self.assertRaises(EsiClientError) as failed:
            client.get_json(
                "/latest/characters/2112345678/assets/",
                character_id=2_112_345_678,
                required_scopes=("esi-assets.read_assets.v1",),
            )
        self.assertNotIn(secret, str(failed.exception))
        self.assertNotIn(secret, repr(failed.exception))

        with self.assertRaises(EsiClientError) as invalid:
            EsiClient(
                lambda _character_id, _scopes: "token with whitespace",
                transport=QueueTransport(),
            ).get_json(
                "/latest/characters/2112345678/assets/",
                character_id=2_112_345_678,
                required_scopes=("esi-assets.read_assets.v1",),
            )
        self.assertEqual("esi-access-token-invalid", invalid.exception.code)

    def test_validates_configuration_and_cache_invalidation(self) -> None:
        with self.assertRaises(ValueError):
            EsiClient(compatibility_date="latest")
        with self.assertRaises(ValueError):
            EsiClient(user_agent="invalid\r\nheader")
        with self.assertRaises(ValueError):
            EsiClient(max_attempts=0)

        transport = QueueTransport(
            response(cache_control="max-age=60"),
            response(cache_control="no-store"),
        )
        client = EsiClient(transport=transport, sleep=lambda _: None)
        client.get_json("/latest/status/")
        self.assertEqual(1, client.status()["cachedResources"])
        client.invalidate()
        self.assertEqual(0, client.status()["cachedResources"])
        client.get_json("/latest/status/")
        self.assertEqual(2, len(transport.calls))


if __name__ == "__main__":
    unittest.main()
