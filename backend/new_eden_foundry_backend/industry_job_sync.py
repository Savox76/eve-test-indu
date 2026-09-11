"""Character industry-job synchronization with complete snapshot semantics."""

from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .esi_client import EsiClient, EsiClientError


INDUSTRY_JOB_SCOPE = "esi-industry.read_character_jobs.v1"
MAX_SAFE_INTEGER = 9_007_199_254_740_991
JOB_STATUSES = ("active", "cancelled", "delivered", "paused", "ready", "reverted")
ACTIVITY_IDS = (1, 3, 4, 5, 7, 8, 9, 11)
REQUIRED_FIELDS = (
    "activity_id",
    "blueprint_id",
    "blueprint_location_id",
    "blueprint_type_id",
    "duration",
    "end_date",
    "facility_id",
    "installer_id",
    "job_id",
    "output_location_id",
    "runs",
    "start_date",
    "station_id",
    "status",
)
OPTIONAL_INTEGER_FIELDS = (
    "completed_character_id",
    "licensed_runs",
    "product_type_id",
    "successful_runs",
)
OPTIONAL_DATE_FIELDS = ("completed_date", "pause_date")


class IndustryJobSyncError(RuntimeError):
    """Raised when an ESI response cannot publish a trustworthy job snapshot."""


@dataclass(frozen=True, slots=True)
class IndustryJobSyncResult:
    character_id: int
    sync_run_id: int
    jobs: int
    active: int
    completed: int
    type_ids: tuple[int, ...]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _positive_integer(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= MAX_SAFE_INTEGER:
        raise IndustryJobSyncError("industry_job_payload_invalid")
    return value


def _non_negative_integer(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SAFE_INTEGER:
        raise IndustryJobSyncError("industry_job_payload_invalid")
    return value


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value or value.strip() != value or len(value) > 64:
        raise IndustryJobSyncError("industry_job_payload_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise IndustryJobSyncError("industry_job_payload_invalid") from error
    if parsed.tzinfo is None:
        raise IndustryJobSyncError("industry_job_payload_invalid")
    return parsed.astimezone(timezone.utc)


def validate_industry_job(row: Any) -> dict[str, Any]:
    """Validate and normalize one documented character-industry-job record."""

    if not isinstance(row, Mapping) or any(field not in row for field in REQUIRED_FIELDS):
        raise IndustryJobSyncError("industry_job_payload_invalid")
    job: dict[str, Any] = {}
    for field in (
        "blueprint_id",
        "blueprint_location_id",
        "blueprint_type_id",
        "facility_id",
        "installer_id",
        "job_id",
        "output_location_id",
        "station_id",
    ):
        job[field] = _positive_integer(row[field])
    activity_id = _positive_integer(row["activity_id"])
    if activity_id not in ACTIVITY_IDS:
        raise IndustryJobSyncError("industry_job_payload_invalid")
    job["activity_id"] = activity_id
    job["duration"] = _non_negative_integer(row["duration"])
    job["runs"] = _positive_integer(row["runs"])
    status = row["status"]
    if not isinstance(status, str) or status not in JOB_STATUSES:
        raise IndustryJobSyncError("industry_job_payload_invalid")
    job["status"] = status

    start = _timestamp(row["start_date"])
    end = _timestamp(row["end_date"])
    if start > end:
        raise IndustryJobSyncError("industry_job_payload_invalid")
    job["start_date"] = str(row["start_date"])
    job["end_date"] = str(row["end_date"])

    for field in OPTIONAL_INTEGER_FIELDS:
        value = row.get(field)
        if value is None:
            job[field] = None
        elif field in ("licensed_runs", "successful_runs"):
            job[field] = _non_negative_integer(value)
        else:
            job[field] = _positive_integer(value)
    if job["successful_runs"] is not None and job["successful_runs"] > job["runs"]:
        raise IndustryJobSyncError("industry_job_payload_invalid")

    for field in OPTIONAL_DATE_FIELDS:
        value = row.get(field)
        if value is None:
            job[field] = None
            continue
        parsed = _timestamp(value)
        if parsed < start:
            raise IndustryJobSyncError("industry_job_payload_invalid")
        job[field] = str(value)

    for field in ("cost", "probability"):
        value = row.get(field)
        if value is None:
            job[field] = None
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise IndustryJobSyncError("industry_job_payload_invalid")
        normalized = float(value)
        maximum = 1.0 if field == "probability" else float(MAX_SAFE_INTEGER)
        if not math.isfinite(normalized) or not 0 <= normalized <= maximum:
            raise IndustryJobSyncError("industry_job_payload_invalid")
        job[field] = normalized

    return {field: job[field] for field in sorted(job)}


def sync_character_industry_jobs(
    connection: sqlite3.Connection,
    client: EsiClient,
    character_id: int,
) -> IndustryJobSyncResult:
    """Fetch ESI's active and retained completed jobs and atomically publish them."""

    if isinstance(character_id, bool) or not isinstance(character_id, int) or character_id <= 0:
        raise ValueError("character_id must be positive")
    character = connection.execute(
        "SELECT enabled FROM characters WHERE character_id=?", (character_id,)
    ).fetchone()
    if character is None or not bool(character[0]):
        raise IndustryJobSyncError("character_not_syncable")

    started = _utc_now()
    run = connection.execute(
        "INSERT INTO sync_runs(source,status,started_at,character_id) "
        "VALUES('character_industry_jobs','running',?,?)",
        (started, character_id),
    )
    run_id = int(run.lastrowid)
    try:
        response = client.get_json(
            f"/characters/{character_id}/industry/jobs/",
            query={"include_completed": "true"},
            character_id=character_id,
            required_scopes=(INDUSTRY_JOB_SCOPE,),
        )
        if not isinstance(response.payload, list):
            raise IndustryJobSyncError("industry_job_payload_invalid")
        jobs = [validate_industry_job(row) for row in response.payload]
        job_ids = [int(job["job_id"]) for job in jobs]
        if len(job_ids) != len(set(job_ids)) or any(
            job["installer_id"] != character_id for job in jobs
        ):
            raise IndustryJobSyncError("industry_job_payload_invalid")

        jobs.sort(key=lambda job: int(job["job_id"]))
        completed_at = _utc_now()
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (
                run_id,
                f"character_industry_jobs:{character_id}",
                json.dumps(
                    {
                        "characterId": character_id,
                        "includeCompleted": True,
                        "jobs": jobs,
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                completed_at,
            ),
        )
        connection.execute(
            "UPDATE sync_runs SET status='completed',completed_at=?,data_timestamp=? "
            "WHERE id=? AND status='running'",
            (completed_at, completed_at, run_id),
        )
        connection.commit()
        type_ids = {
            int(type_id)
            for job in jobs
            for type_id in (job["blueprint_type_id"], job["product_type_id"])
            if type_id is not None
        }
        active = sum(job["status"] in ("active", "paused", "ready") for job in jobs)
        return IndustryJobSyncResult(
            character_id=character_id,
            sync_run_id=run_id,
            jobs=len(jobs),
            active=active,
            completed=len(jobs) - active,
            type_ids=tuple(sorted(type_ids)),
        )
    except Exception as error:
        if connection.in_transaction:
            connection.rollback()
        completed_at = _utc_now()
        code = (
            error.code
            if isinstance(error, EsiClientError)
            else str(error)
            if isinstance(error, IndustryJobSyncError)
            else "industry_job_sync_failed"
        )
        connection.execute(
            "UPDATE sync_runs SET status='failed',completed_at=?,error_code=? "
            "WHERE id=? AND status='running'",
            (completed_at, code[:120], run_id),
        )
        connection.commit()
        if isinstance(error, (IndustryJobSyncError, EsiClientError)):
            raise
        raise IndustryJobSyncError("industry_job_sync_failed") from error
