from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.startup_state import inspect_startup_data_state


NOW = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)


class CacheFirstStartupStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "foundry.sqlite3"
        initialize_database(self.database_path)
        self.connection = connect_database(self.database_path)

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary_directory.cleanup()

    def add_run(
        self,
        status: str,
        *,
        error_code: str | None = None,
        observed_at: str | None = None,
        expires_at: str | None = None,
    ) -> int:
        completed_at = None if status == "running" else "2026-09-09T11:59:00Z"
        cursor = self.connection.execute(
            """
            INSERT INTO sync_runs (
                source, status, started_at, completed_at, data_timestamp, error_code
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "synthetic-assets",
                status,
                "2026-09-09T11:58:00Z",
                completed_at,
                observed_at,
                error_code,
            ),
        )
        run_id = int(cursor.lastrowid)
        if observed_at is not None:
            self.connection.execute(
                """
                INSERT INTO cached_snapshots (
                    sync_run_id, resource, payload_json, observed_at, expires_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    "assets",
                    json.dumps({"synthetic": True}),
                    observed_at,
                    expires_at,
                ),
            )
        return run_id

    def test_new_database_starts_with_an_honest_empty_state(self) -> None:
        state = inspect_startup_data_state(self.connection, now=NOW)

        self.assertEqual(state.state, "empty")
        self.assertFalse(state.has_cached_data)
        self.assertEqual(state.last_sync_status, "never")
        self.assertIsNone(state.age_seconds)

    def test_unexpired_completed_snapshot_is_fresh(self) -> None:
        self.add_run(
            "completed",
            observed_at="2026-09-09T11:54:00Z",
            expires_at="2026-09-09T12:04:00Z",
        )

        state = inspect_startup_data_state(self.connection, now=NOW)

        self.assertEqual(state.state, "fresh")
        self.assertTrue(state.has_cached_data)
        self.assertEqual(state.age_seconds, 360)
        self.assertEqual(state.last_sync_status, "completed")

    def test_snapshot_without_expiry_stays_fresh_for_two_hours(self) -> None:
        self.add_run(
            "completed",
            observed_at="2026-09-09T10:00:01Z",
        )

        state = inspect_startup_data_state(self.connection, now=NOW)

        self.assertEqual(state.state, "fresh")
        self.assertEqual(state.age_seconds, 7_199)

    def test_snapshot_without_expiry_becomes_stale_at_two_hours(self) -> None:
        self.add_run(
            "completed",
            observed_at="2026-09-09T10:00:00Z",
        )

        state = inspect_startup_data_state(self.connection, now=NOW)

        self.assertEqual(state.state, "stale")
        self.assertEqual(state.age_seconds, 7_200)

    def test_expired_snapshot_remains_available_and_is_marked_stale(self) -> None:
        self.add_run(
            "completed",
            observed_at="2026-09-09T09:00:00Z",
            expires_at="2026-09-09T09:05:00Z",
        )

        state = inspect_startup_data_state(self.connection, now=NOW)

        self.assertEqual(state.state, "stale")
        self.assertTrue(state.has_cached_data)
        self.assertEqual(state.age_seconds, 10_800)

    def test_network_failure_keeps_the_last_complete_snapshot_for_offline_start(self) -> None:
        completed_run = self.add_run(
            "completed",
            observed_at="2026-09-09T09:00:00Z",
            expires_at="2026-09-09T09:05:00Z",
        )
        self.connection.execute(
            """
            INSERT INTO sync_runs (
                source, status, started_at, completed_at, error_code
            ) VALUES (?, 'failed', ?, ?, 'network-timeout')
            """,
            (
                "synthetic-assets",
                "2026-09-09T11:59:30Z",
                "2026-09-09T11:59:45Z",
            ),
        )

        state = inspect_startup_data_state(self.connection, now=NOW)

        self.assertEqual(state.state, "offline")
        self.assertEqual(state.error_code, "network-unavailable")
        self.assertTrue(state.has_cached_data)
        snapshot_run = self.connection.execute(
            "SELECT sync_run_id FROM cached_snapshots"
        ).fetchone()[0]
        self.assertEqual(snapshot_run, completed_run)

    def test_non_network_failure_is_sanitized_without_erasing_cache(self) -> None:
        self.add_run(
            "completed",
            observed_at="2026-09-09T10:00:00Z",
            expires_at="2026-09-09T10:05:00Z",
        )
        self.connection.execute(
            """
            INSERT INTO sync_runs (
                source, status, started_at, completed_at, error_code
            ) VALUES (?, 'failed', ?, ?, ?)
            """,
            (
                "synthetic-assets",
                "2026-09-09T11:59:30Z",
                "2026-09-09T11:59:45Z",
                "synthetic-sensitive-detail",
            ),
        )

        state = inspect_startup_data_state(self.connection, now=NOW)

        self.assertEqual(state.state, "error")
        self.assertEqual(state.error_code, "sync-failed")
        self.assertNotIn("sensitive", str(state.as_api_payload()))
        self.assertTrue(state.has_cached_data)

    def test_running_refresh_keeps_completed_cache_visible(self) -> None:
        self.add_run(
            "completed",
            observed_at="2026-09-09T11:54:00Z",
            expires_at="2026-09-09T12:04:00Z",
        )
        self.add_run("running")

        state = inspect_startup_data_state(self.connection, now=NOW)

        self.assertEqual(state.state, "refreshing")
        self.assertTrue(state.has_cached_data)
        self.assertEqual(state.last_sync_status, "running")

    def test_invalid_cache_timestamp_becomes_a_visible_error(self) -> None:
        self.add_run(
            "completed",
            observed_at="not-a-timestamp",
            expires_at="2026-09-09T12:04:00Z",
        )

        state = inspect_startup_data_state(self.connection, now=NOW)

        self.assertEqual(state.state, "error")
        self.assertEqual(state.error_code, "cache-metadata-invalid")
        self.assertTrue(state.has_cached_data)
        self.assertIsNone(state.age_seconds)


if __name__ == "__main__":
    unittest.main()
