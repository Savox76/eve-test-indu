"""Derive honest cache-first startup states from verified local metadata."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Final


OFFLINE_ERROR_CODES: Final = frozenset(
    {
        "network-unavailable",
        "network-timeout",
        "dns-unavailable",
        "esi-unavailable",
    }
)
SYNC_STATUSES: Final = frozenset({"running", "completed", "failed", "cancelled"})
DATA_STATES: Final = frozenset(
    {"loading", "refreshing", "empty", "fresh", "stale", "offline", "error"}
)
STALE_AFTER_SECONDS: Final = 2 * 60 * 60


@dataclass(frozen=True, slots=True)
class StartupDataState:
    state: str
    has_cached_data: bool
    observed_at: str | None
    expires_at: str | None
    age_seconds: int | None
    last_sync_status: str
    error_code: str | None

    def as_api_payload(self) -> dict[str, object]:
        """Return a camel-case payload without local paths or raw failure details."""

        values = asdict(self)
        return {
            "state": values["state"],
            "hasCachedData": values["has_cached_data"],
            "observedAt": values["observed_at"],
            "expiresAt": values["expires_at"],
            "ageSeconds": values["age_seconds"],
            "lastSyncStatus": values["last_sync_status"],
            "errorCode": values["error_code"],
        }


def _parse_utc_timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("Cache timestamps must contain an explicit timezone.")
    return parsed.astimezone(UTC)


def inspect_startup_data_state(
    connection: sqlite3.Connection,
    *,
    now: datetime | None = None,
) -> StartupDataState:
    """Classify the newest complete cache without discarding it after failures."""

    reference_time = now or datetime.now(UTC)
    if reference_time.tzinfo is None:
        raise ValueError("The startup-state reference time must be timezone-aware.")
    reference_time = reference_time.astimezone(UTC)

    latest_run = connection.execute(
        """
        SELECT status, error_code
        FROM sync_runs
        ORDER BY started_at DESC, id DESC
        LIMIT 1
        """
    ).fetchone()
    latest_snapshot = connection.execute(
        """
        SELECT snapshot.observed_at, snapshot.expires_at
        FROM cached_snapshots AS snapshot
        JOIN sync_runs AS run ON run.id = snapshot.sync_run_id
        WHERE run.status = 'completed'
        ORDER BY snapshot.observed_at DESC, snapshot.id DESC
        LIMIT 1
        """
    ).fetchone()

    last_sync_status = "never" if latest_run is None else str(latest_run["status"])
    if last_sync_status != "never" and last_sync_status not in SYNC_STATUSES:
        return StartupDataState(
            state="error",
            has_cached_data=latest_snapshot is not None,
            observed_at=None,
            expires_at=None,
            age_seconds=None,
            last_sync_status="failed",
            error_code="sync-metadata-invalid",
        )

    observed_at = None if latest_snapshot is None else str(latest_snapshot["observed_at"])
    expires_at = (
        None
        if latest_snapshot is None or latest_snapshot["expires_at"] is None
        else str(latest_snapshot["expires_at"])
    )
    age_seconds: int | None = None
    cache_is_fresh = False
    if latest_snapshot is not None:
        try:
            observed_time = _parse_utc_timestamp(observed_at or "")
            age_seconds = max(0, int((reference_time - observed_time).total_seconds()))
            cache_is_fresh = age_seconds < STALE_AFTER_SECONDS or (
                expires_at is not None
                and _parse_utc_timestamp(expires_at) > reference_time
            )
        except (TypeError, ValueError, OverflowError):
            return StartupDataState(
                state="error",
                has_cached_data=True,
                observed_at=observed_at,
                expires_at=expires_at,
                age_seconds=None,
                last_sync_status=last_sync_status,
                error_code="cache-metadata-invalid",
            )

    if last_sync_status == "running":
        state = "refreshing" if latest_snapshot is not None else "loading"
        error_code = None
    elif last_sync_status == "failed":
        raw_error_code = None if latest_run is None else latest_run["error_code"]
        if isinstance(raw_error_code, str) and raw_error_code in OFFLINE_ERROR_CODES:
            state = "offline"
            error_code = "network-unavailable"
        else:
            state = "error"
            error_code = "sync-failed"
    elif latest_snapshot is None:
        state = "empty"
        error_code = None
    else:
        state = "fresh" if cache_is_fresh else "stale"
        error_code = None

    return StartupDataState(
        state=state,
        has_cached_data=latest_snapshot is not None,
        observed_at=observed_at,
        expires_at=expires_at,
        age_seconds=age_seconds,
        last_sync_status=last_sync_status,
        error_code=error_code,
    )
