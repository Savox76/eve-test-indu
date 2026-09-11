"""Validated job-snapshot evidence shared by read models and delta correlation."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping

from .industry_job_sync import IndustryJobSyncError, validate_industry_job


class IndustryJobEvidenceError(RuntimeError):
    """Raised when persisted job evidence is incomplete or inconsistent."""


def parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value or value.strip() != value or len(value) > 64:
        raise IndustryJobEvidenceError("industry_job_snapshot_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise IndustryJobEvidenceError("industry_job_snapshot_invalid") from error
    if parsed.tzinfo is None:
        raise IndustryJobEvidenceError("industry_job_snapshot_invalid")
    return parsed.astimezone(timezone.utc)


def load_latest_job_snapshots(connection: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    """Return only the newest completed, strictly validated snapshot per character."""

    rows = connection.execute(
        """
        SELECT cached_snapshots.id AS snapshot_id,
               cached_snapshots.sync_run_id,
               cached_snapshots.payload_json,
               cached_snapshots.observed_at,
               characters.character_id,
               characters.name,
               characters.alias
        FROM characters
        JOIN cached_snapshots
          ON cached_snapshots.resource='character_industry_jobs:' || characters.character_id
        JOIN sync_runs ON sync_runs.id=cached_snapshots.sync_run_id
        WHERE characters.enabled=1
          AND sync_runs.source='character_industry_jobs'
          AND sync_runs.status='completed'
          AND cached_snapshots.id=(
            SELECT candidate.id
            FROM cached_snapshots AS candidate
            JOIN sync_runs AS candidate_run ON candidate_run.id=candidate.sync_run_id
            WHERE candidate.resource='character_industry_jobs:' || characters.character_id
              AND candidate_run.source='character_industry_jobs'
              AND candidate_run.status='completed'
            ORDER BY candidate.observed_at DESC,candidate.id DESC
            LIMIT 1
          )
        ORDER BY characters.character_id
        """
    ).fetchall()
    snapshots: dict[int, dict[str, Any]] = {}
    for row in rows:
        character_id = int(row["character_id"])
        try:
            payload = json.loads(str(row["payload_json"]))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise IndustryJobEvidenceError("industry_job_snapshot_invalid") from error
        if (
            not isinstance(payload, Mapping)
            or set(payload) != {"characterId", "includeCompleted", "jobs"}
            or payload.get("characterId") != character_id
            or payload.get("includeCompleted") is not True
            or not isinstance(payload.get("jobs"), list)
        ):
            raise IndustryJobEvidenceError("industry_job_snapshot_invalid")
        observed_at = str(row["observed_at"])
        parse_timestamp(observed_at)
        jobs: list[dict[str, Any]] = []
        try:
            jobs = [validate_industry_job(job) for job in payload["jobs"]]
        except IndustryJobSyncError as error:
            raise IndustryJobEvidenceError("industry_job_snapshot_invalid") from error
        job_ids = [int(job["job_id"]) for job in jobs]
        if (
            len(job_ids) != len(set(job_ids))
            or any(job["installer_id"] != character_id for job in jobs)
            or character_id in snapshots
        ):
            raise IndustryJobEvidenceError("industry_job_snapshot_invalid")
        snapshots[character_id] = {
            "snapshotId": int(row["snapshot_id"]),
            "syncRunId": int(row["sync_run_id"]),
            "observedAt": observed_at,
            "ownerName": str(row["alias"] or row["name"]),
            "jobs": jobs,
        }
    return snapshots


def correlate_asset_event(
    snapshots: Mapping[int, Mapping[str, Any]],
    *,
    character_id: int,
    type_id: int,
    direction: str,
    window_start: str,
    window_end: str,
    location_id_after: int | None,
) -> dict[str, object]:
    """Link inbound output deltas to completed jobs without claiming causality."""

    base: dict[str, object] = {
        "key": f"{character_id}:{type_id}",
        "direction": direction,
        "windowStart": window_start,
        "windowEnd": window_end,
        "jobIds": [],
        "candidateCount": 0,
        "locationMatched": False,
    }
    if direction != "inbound":
        return {**base, "state": "not-applicable"}
    snapshot = snapshots.get(character_id)
    if snapshot is None:
        return {**base, "state": "unavailable"}
    start = parse_timestamp(window_start)
    end = parse_timestamp(window_end)
    candidates = [
        job
        for job in snapshot["jobs"]
        if job["status"] == "delivered"
        and job["product_type_id"] == type_id
        and job["completed_date"] is not None
        and start <= parse_timestamp(job["completed_date"]) <= end
    ]
    location_candidates = [
        job for job in candidates if job["output_location_id"] == location_id_after
    ]
    selected = location_candidates or candidates
    job_ids = sorted(int(job["job_id"]) for job in selected)
    if not job_ids:
        state = "unmatched"
    elif len(job_ids) == 1:
        state = "linked"
    else:
        state = "ambiguous"
    return {
        **base,
        "state": state,
        "jobIds": job_ids[:20],
        "candidateCount": len(job_ids),
        "locationMatched": bool(location_candidates),
    }
