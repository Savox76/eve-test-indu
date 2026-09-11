"""Industry-facility and system-cost synchronization with complete snapshots."""

from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from .esi_client import EsiClient, EsiClientError
from .industry_job_evidence import IndustryJobEvidenceError, load_latest_job_snapshots
from .location_resolution import STRUCTURE_ID_MINIMUM, STRUCTURE_SCOPE


MAX_SAFE_INTEGER = 9_007_199_254_740_991
UNIVERSE_NAME_BATCH_SIZE = 1_000
INDUSTRY_COST_ACTIVITIES = (
    "copying",
    "duplicating",
    "invention",
    "manufacturing",
    "none",
    "reaction",
    "researching_material_efficiency",
    "researching_technology",
    "researching_time_efficiency",
    "reverse_engineering",
)
UNIVERSE_NAME_CATEGORIES = (
    "alliance",
    "character",
    "constellation",
    "corporation",
    "faction",
    "inventory_type",
    "region",
    "solar_system",
    "station",
)


class IndustryFacilitySyncError(RuntimeError):
    """Raised when a complete, trustworthy facility snapshot cannot be published."""


@dataclass(frozen=True, slots=True)
class IndustryFacilitySyncResult:
    sync_run_id: int
    facilities: int
    npc_facilities: int
    observed_facilities: int
    restricted_structures: int
    systems: int
    resolved_names: int


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _positive_integer(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= MAX_SAFE_INTEGER:
        raise IndustryFacilitySyncError("industry_facility_payload_invalid")
    return value


def _bounded_text(value: Any, limit: int = 200) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > limit
    ):
        raise IndustryFacilitySyncError("industry_facility_payload_invalid")
    return value


def _rate(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise IndustryFacilitySyncError("industry_facility_payload_invalid")
    normalized = float(value)
    if not math.isfinite(normalized) or not 0 <= normalized <= 1:
        raise IndustryFacilitySyncError("industry_facility_payload_invalid")
    return normalized


def validate_industry_facilities(payload: Any) -> list[dict[str, Any]]:
    """Validate the official public NPC industry-facility catalog."""

    if not isinstance(payload, list) or not payload:
        raise IndustryFacilitySyncError("industry_facility_payload_invalid")
    facilities: list[dict[str, Any]] = []
    for row in payload:
        required = {"facility_id", "owner_id", "region_id", "solar_system_id", "type_id"}
        if not isinstance(row, Mapping) or not required.issubset(row):
            raise IndustryFacilitySyncError("industry_facility_payload_invalid")
        facilities.append(
            {
                "facility_id": _positive_integer(row["facility_id"]),
                "owner_id": _positive_integer(row["owner_id"]),
                "region_id": _positive_integer(row["region_id"]),
                "solar_system_id": _positive_integer(row["solar_system_id"]),
                "tax": None if row.get("tax") is None else _rate(row["tax"]),
                "type_id": _positive_integer(row["type_id"]),
            }
        )
    facility_ids = [facility["facility_id"] for facility in facilities]
    if len(facility_ids) != len(set(facility_ids)):
        raise IndustryFacilitySyncError("industry_facility_payload_invalid")
    facilities.sort(key=lambda facility: int(facility["facility_id"]))
    return facilities


def validate_industry_systems(payload: Any) -> list[dict[str, Any]]:
    """Validate the official system-cost-index catalog."""

    if not isinstance(payload, list) or not payload:
        raise IndustryFacilitySyncError("industry_system_payload_invalid")
    systems: list[dict[str, Any]] = []
    for row in payload:
        if (
            not isinstance(row, Mapping)
            or not {"solar_system_id", "cost_indices"}.issubset(row)
            or not isinstance(row["cost_indices"], list)
        ):
            raise IndustryFacilitySyncError("industry_system_payload_invalid")
        indices: list[dict[str, Any]] = []
        for index in row["cost_indices"]:
            if not isinstance(index, Mapping) or not {"activity", "cost_index"}.issubset(index):
                raise IndustryFacilitySyncError("industry_system_payload_invalid")
            activity = index["activity"]
            if activity not in INDUSTRY_COST_ACTIVITIES:
                raise IndustryFacilitySyncError("industry_system_payload_invalid")
            indices.append({"activity": str(activity), "cost_index": _rate(index["cost_index"])})
        activities = [index["activity"] for index in indices]
        if len(activities) != len(set(activities)):
            raise IndustryFacilitySyncError("industry_system_payload_invalid")
        indices.sort(key=lambda index: str(index["activity"]))
        systems.append(
            {
                "solar_system_id": _positive_integer(row["solar_system_id"]),
                "cost_indices": indices,
            }
        )
    system_ids = [system["solar_system_id"] for system in systems]
    if len(system_ids) != len(set(system_ids)):
        raise IndustryFacilitySyncError("industry_system_payload_invalid")
    systems.sort(key=lambda system: int(system["solar_system_id"]))
    return systems


def _observed_facilities(connection: sqlite3.Connection) -> dict[int, tuple[int, ...]]:
    try:
        snapshots = load_latest_job_snapshots(connection)
    except IndustryJobEvidenceError as error:
        raise IndustryFacilitySyncError("industry_job_snapshot_invalid") from error
    observed: dict[int, set[int]] = {}
    for character_id, snapshot in snapshots.items():
        for job in snapshot["jobs"]:
            observed.setdefault(int(job["facility_id"]), set()).add(character_id)
    return {
        facility_id: tuple(sorted(character_ids))
        for facility_id, character_ids in observed.items()
    }


def _structure_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or not {
        "name",
        "owner_id",
        "solar_system_id",
    }.issubset(payload):
        raise IndustryFacilitySyncError("industry_structure_payload_invalid")
    return {
        "name": _bounded_text(payload["name"]),
        "owner_id": _positive_integer(payload["owner_id"]),
        "solar_system_id": _positive_integer(payload["solar_system_id"]),
        "type_id": (
            None if payload.get("type_id") is None else _positive_integer(payload["type_id"])
        ),
    }


def _unresolved_structure(
    facility_id: int,
    observers: tuple[int, ...],
    *,
    access: str,
    error_code: str,
) -> dict[str, Any]:
    return {
        "facility_id": facility_id,
        "name": None,
        "owner_id": None,
        "solar_system_id": None,
        "type_id": None,
        "access": access,
        "error_code": error_code,
        "observed_by_character_ids": list(observers),
    }


def _resolve_observed_facilities(
    connection: sqlite3.Connection,
    client: EsiClient,
    observed: Mapping[int, tuple[int, ...]],
    public_ids: set[int],
) -> list[dict[str, Any]]:
    scopes = {
        int(row[0]): set(
            str(scope_row[0])
            for scope_row in connection.execute(
                "SELECT scope FROM character_scopes WHERE character_id=?", (int(row[0]),)
            )
        )
        for row in connection.execute("SELECT character_id FROM characters WHERE enabled=1")
    }
    structures: list[dict[str, Any]] = []
    for facility_id, observers in sorted(observed.items()):
        if facility_id in public_ids:
            continue
        if facility_id < STRUCTURE_ID_MINIMUM:
            structures.append(
                _unresolved_structure(
                    facility_id,
                    observers,
                    access="unknown",
                    error_code="facility_not_in_public_catalog",
                )
            )
            continue
        authorized = [
            character_id
            for character_id in observers
            if STRUCTURE_SCOPE in scopes.get(character_id, set())
        ]
        if not authorized:
            structures.append(
                _unresolved_structure(
                    facility_id,
                    observers,
                    access="scope-missing",
                    error_code="structure_scope_missing",
                )
            )
            continue
        resolved: dict[str, Any] | None = None
        not_found = False
        for character_id in authorized:
            try:
                response = client.get_json(
                    f"/universe/structures/{facility_id}/",
                    character_id=character_id,
                    required_scopes=(STRUCTURE_SCOPE,),
                )
            except EsiClientError as error:
                if error.status == 403:
                    continue
                if error.status == 404:
                    not_found = True
                    break
                raise
            resolved = _structure_payload(response.payload)
            break
        if resolved is None:
            structures.append(
                _unresolved_structure(
                    facility_id,
                    observers,
                    access="unknown" if not_found else "restricted",
                    error_code="structure_not_found" if not_found else "structure_forbidden",
                )
            )
            continue
        structures.append(
            {
                "facility_id": facility_id,
                **resolved,
                "access": "available",
                "error_code": None,
                "observed_by_character_ids": list(observers),
            }
        )
    return structures


def _required_names(
    facilities: Iterable[Mapping[str, Any]],
    structures: Iterable[Mapping[str, Any]],
) -> dict[int, str]:
    expected: dict[int, str] = {}

    def add(value: Any, category: str) -> None:
        if value is None:
            return
        identifier = _positive_integer(value)
        if identifier in expected and expected[identifier] != category:
            raise IndustryFacilitySyncError("industry_facility_payload_invalid")
        expected[identifier] = category

    for facility in facilities:
        add(facility["facility_id"], "station")
        add(facility["owner_id"], "corporation")
        add(facility["region_id"], "region")
        add(facility["solar_system_id"], "solar_system")
        add(facility["type_id"], "inventory_type")
    for structure in structures:
        add(structure["owner_id"], "corporation")
        add(structure["solar_system_id"], "solar_system")
        add(structure["type_id"], "inventory_type")
    return expected


def _resolve_names(client: EsiClient, expected: Mapping[int, str]) -> list[dict[str, Any]]:
    identifiers = sorted(expected)
    names: list[dict[str, Any]] = []
    for start in range(0, len(identifiers), UNIVERSE_NAME_BATCH_SIZE):
        batch = identifiers[start : start + UNIVERSE_NAME_BATCH_SIZE]
        response = client.post_json("/universe/names/", batch)
        if not isinstance(response.payload, list):
            raise IndustryFacilitySyncError("industry_facility_names_invalid")
        for row in response.payload:
            if not isinstance(row, Mapping) or not {"id", "name", "category"}.issubset(row):
                raise IndustryFacilitySyncError("industry_facility_names_invalid")
            identifier = _positive_integer(row["id"])
            category = row["category"]
            if identifier not in expected or category != expected[identifier]:
                raise IndustryFacilitySyncError("industry_facility_names_invalid")
            names.append(
                {
                    "id": identifier,
                    "name": _bounded_text(row["name"]),
                    "category": str(category),
                }
            )
    if len(names) != len(expected) or {row["id"] for row in names} != set(expected):
        raise IndustryFacilitySyncError("industry_facility_names_invalid")
    names.sort(key=lambda row: int(row["id"]))
    return names


def validate_industry_reference(payload: Any) -> dict[str, Any]:
    """Validate a stored reference snapshot before it reaches a read model."""

    if not isinstance(payload, Mapping) or set(payload) != {
        "facilities",
        "names",
        "structures",
        "systems",
    }:
        raise IndustryFacilitySyncError("industry_facility_snapshot_invalid")
    facilities = validate_industry_facilities(payload["facilities"])
    systems = validate_industry_systems(payload["systems"])
    structures: list[dict[str, Any]] = []
    if not isinstance(payload["structures"], list):
        raise IndustryFacilitySyncError("industry_facility_snapshot_invalid")
    for row in payload["structures"]:
        expected_fields = {
            "access",
            "error_code",
            "facility_id",
            "name",
            "observed_by_character_ids",
            "owner_id",
            "solar_system_id",
            "type_id",
        }
        if not isinstance(row, Mapping) or set(row) != expected_fields:
            raise IndustryFacilitySyncError("industry_facility_snapshot_invalid")
        access = row["access"]
        error_code = row["error_code"]
        observers = row["observed_by_character_ids"]
        if (
            access not in {"available", "restricted", "scope-missing", "unknown"}
            or not isinstance(observers, list)
            or not observers
            or any(_positive_integer(value) is None for value in observers)
            or len(observers) != len(set(observers))
            or observers != sorted(observers)
        ):
            raise IndustryFacilitySyncError("industry_facility_snapshot_invalid")
        available = access == "available"
        if available:
            if error_code is not None:
                raise IndustryFacilitySyncError("industry_facility_snapshot_invalid")
            name = _bounded_text(row["name"])
            owner_id = _positive_integer(row["owner_id"])
            solar_system_id = _positive_integer(row["solar_system_id"])
            type_id = None if row["type_id"] is None else _positive_integer(row["type_id"])
        else:
            if (
                row["name"] is not None
                or row["owner_id"] is not None
                or row["solar_system_id"] is not None
                or row["type_id"] is not None
                or not isinstance(error_code, str)
                or not error_code
            ):
                raise IndustryFacilitySyncError("industry_facility_snapshot_invalid")
            name = owner_id = solar_system_id = type_id = None
        structures.append(
            {
                "facility_id": _positive_integer(row["facility_id"]),
                "name": name,
                "owner_id": owner_id,
                "solar_system_id": solar_system_id,
                "type_id": type_id,
                "access": str(access),
                "error_code": error_code,
                "observed_by_character_ids": list(observers),
            }
        )
    structure_ids = [structure["facility_id"] for structure in structures]
    if (
        len(structure_ids) != len(set(structure_ids))
        or set(structure_ids).intersection(facility["facility_id"] for facility in facilities)
    ):
        raise IndustryFacilitySyncError("industry_facility_snapshot_invalid")
    structures.sort(key=lambda structure: int(structure["facility_id"]))

    required_names = _required_names(facilities, structures)
    if not isinstance(payload["names"], list):
        raise IndustryFacilitySyncError("industry_facility_snapshot_invalid")
    names: list[dict[str, Any]] = []
    for row in payload["names"]:
        if not isinstance(row, Mapping) or set(row) != {"category", "id", "name"}:
            raise IndustryFacilitySyncError("industry_facility_snapshot_invalid")
        identifier = _positive_integer(row["id"])
        category = row["category"]
        if category not in UNIVERSE_NAME_CATEGORIES or required_names.get(identifier) != category:
            raise IndustryFacilitySyncError("industry_facility_snapshot_invalid")
        names.append(
            {"id": identifier, "name": _bounded_text(row["name"]), "category": str(category)}
        )
    if len(names) != len(required_names) or {row["id"] for row in names} != set(required_names):
        raise IndustryFacilitySyncError("industry_facility_snapshot_invalid")
    names.sort(key=lambda row: int(row["id"]))
    return {
        "facilities": facilities,
        "names": names,
        "structures": structures,
        "systems": systems,
    }


def sync_industry_facilities(
    connection: sqlite3.Connection,
    client: EsiClient,
) -> IndustryFacilitySyncResult:
    """Publish facilities, observed structures, names and cost indices atomically."""

    started = _utc_now()
    run = connection.execute(
        "INSERT INTO sync_runs(source,status,started_at) "
        "VALUES('industry_facilities','running',?)",
        (started,),
    )
    run_id = int(run.lastrowid)
    try:
        facilities = validate_industry_facilities(
            client.get_json("/industry/facilities/").payload
        )
        systems = validate_industry_systems(client.get_json("/industry/systems/").payload)
        observed = _observed_facilities(connection)
        public_ids = {facility["facility_id"] for facility in facilities}
        structures = _resolve_observed_facilities(
            connection,
            client,
            observed,
            public_ids,
        )
        names = _resolve_names(client, _required_names(facilities, structures))
        payload = validate_industry_reference(
            {
                "facilities": facilities,
                "names": names,
                "structures": structures,
                "systems": systems,
            }
        )
        completed = _utc_now()
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO cached_snapshots(sync_run_id,resource,payload_json,observed_at) "
            "VALUES(?,?,?,?)",
            (
                run_id,
                "industry_facilities",
                json.dumps(payload, separators=(",", ":"), sort_keys=True),
                completed,
            ),
        )
        connection.execute(
            "UPDATE sync_runs SET status='completed',completed_at=?,data_timestamp=? "
            "WHERE id=? AND status='running'",
            (completed, completed, run_id),
        )
        connection.commit()
        return IndustryFacilitySyncResult(
            sync_run_id=run_id,
            facilities=len(facilities) + len(structures),
            npc_facilities=len(facilities),
            observed_facilities=len(structures),
            restricted_structures=sum(
                structure["access"] in {"restricted", "scope-missing"}
                for structure in structures
            ),
            systems=len(systems),
            resolved_names=len(names),
        )
    except Exception as error:
        if connection.in_transaction:
            connection.rollback()
        completed = _utc_now()
        code = (
            error.code
            if isinstance(error, EsiClientError)
            else str(error)
            if isinstance(error, IndustryFacilitySyncError)
            else "industry_facility_sync_failed"
        )
        connection.execute(
            "UPDATE sync_runs SET status='failed',completed_at=?,error_code=? "
            "WHERE id=? AND status='running'",
            (completed, code[:120], run_id),
        )
        connection.commit()
        if isinstance(error, (IndustryFacilitySyncError, EsiClientError)):
            raise
        raise IndustryFacilitySyncError("industry_facility_sync_failed") from error
