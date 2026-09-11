"""Build and install the pinned official EVE industry SDE subset."""

from __future__ import annotations

import gzip
import json
import math
import sqlite3
from pathlib import Path
from typing import Any, BinaryIO, Final, Iterable, Mapping
from zipfile import ZipFile

from .sde import SdeImportError, SdeImportResult, current_sde_blueprint_activity_build, import_industry_sde


RESOURCE_DIRECTORY: Final = Path(__file__).resolve().parent / "resources"
BUNDLED_INDUSTRY_SDE: Final = RESOURCE_DIRECTORY / "official-industry-sde.json.gz"
SUPPORTED_ACTIVITIES: Final = ("manufacturing", "reaction")


class OfficialSdeError(RuntimeError):
    """Raised when an official archive or bundled subset is invalid."""


def _positive_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _localized_name(value: Any) -> str:
    if not isinstance(value, Mapping):
        raise OfficialSdeError("official_sde_name_invalid")
    for language in ("en", "de"):
        name = value.get(language)
        if isinstance(name, str) and name.strip():
            return name.strip()
    raise OfficialSdeError("official_sde_name_invalid")


def _json_lines(archive: ZipFile, name: str) -> Iterable[dict[str, Any]]:
    try:
        stream: BinaryIO = archive.open(name)
    except KeyError as error:
        raise OfficialSdeError("official_sde_file_missing") from error
    with stream:
        for raw_line in stream:
            try:
                value = json.loads(raw_line)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise OfficialSdeError("official_sde_json_invalid") from error
            if not isinstance(value, dict):
                raise OfficialSdeError("official_sde_record_invalid")
            yield value


def build_official_industry_bundle(archive_path: Path) -> dict[str, object]:
    """Normalize the current official JSON-Lines archive to the internal contract."""

    with ZipFile(archive_path) as archive:
        metadata = list(_json_lines(archive, "_sde.jsonl"))
        if len(metadata) != 1 or metadata[0].get("_key") != "sde":
            raise OfficialSdeError("official_sde_metadata_invalid")
        build_number = metadata[0].get("buildNumber")
        if isinstance(build_number, bool) or not isinstance(build_number, int) or build_number <= 0:
            raise OfficialSdeError("official_sde_metadata_invalid")

        groups = []
        group_ids: set[int] = set()
        for row in _json_lines(archive, "groups.jsonl"):
            group_id = row.get("_key")
            if _positive_integer(group_id):
                groups.append({"group_id": group_id, "name": _localized_name(row.get("name"))})
                group_ids.add(group_id)

        types = []
        type_ids: set[int] = set()
        for row in _json_lines(archive, "types.jsonl"):
            type_id = row.get("_key")
            group_id = row.get("groupID")
            if (
                _positive_integer(type_id)
                and isinstance(group_id, int)
                and group_id in group_ids
            ):
                types.append(
                    {
                        "type_id": type_id,
                        "group_id": group_id,
                        "name": _localized_name(row.get("name")),
                    }
                )
                type_ids.add(type_id)

        locations = []
        for filename, kind, parent_key in (
            ("mapRegions.jsonl", "region", None),
            ("mapConstellations.jsonl", "constellation", "regionID"),
            ("mapSolarSystems.jsonl", "solar_system", "constellationID"),
        ):
            for row in _json_lines(archive, filename):
                location_id = row.get("_key")
                if _positive_integer(location_id):
                    parent = row.get(parent_key) if parent_key is not None else None
                    security = row.get("securityStatus") if kind == "solar_system" else None
                    if security is not None and (
                        isinstance(security, bool)
                        or not isinstance(security, (int, float))
                        or not math.isfinite(float(security))
                        or not -1 <= float(security) <= 1
                    ):
                        raise OfficialSdeError("official_sde_record_invalid")
                    locations.append(
                        {
                            "location_id": location_id,
                            "parent_location_id": str(parent) if isinstance(parent, int) else None,
                            "name": _localized_name(row.get("name")),
                            "kind": kind,
                            "security_status": None if security is None else float(security),
                        }
                    )

        blueprint_activities = []
        for row in _json_lines(archive, "blueprints.jsonl"):
            blueprint_type_id = row.get("blueprintTypeID")
            activities = row.get("activities")
            if blueprint_type_id not in type_ids or not isinstance(activities, Mapping):
                continue
            for activity_name in SUPPORTED_ACTIVITIES:
                activity = activities.get(activity_name)
                if not isinstance(activity, Mapping):
                    continue
                time_seconds = activity.get("time")
                products = activity.get("products")
                materials = activity.get("materials")
                if (
                    not _positive_integer(time_seconds)
                    or not isinstance(products, list)
                    or not isinstance(materials, list)
                ):
                    continue
                normalized_products = [
                    {"type_id": item.get("typeID"), "quantity": item.get("quantity")}
                    for item in products
                    if (
                        isinstance(item, Mapping)
                        and item.get("typeID") in type_ids
                        and _positive_integer(item.get("quantity"))
                    )
                ]
                normalized_materials = [
                    {"type_id": item.get("typeID"), "quantity": item.get("quantity")}
                    for item in materials
                    if (
                        isinstance(item, Mapping)
                        and item.get("typeID") in type_ids
                        and _positive_integer(item.get("quantity"))
                    )
                ]
                if normalized_products and normalized_materials:
                    blueprint_activities.append(
                        {
                            "blueprint_type_id": blueprint_type_id,
                            "activity": activity_name,
                            "time_seconds": time_seconds,
                            "products": normalized_products,
                            "materials": normalized_materials,
                        }
                    )

    if not groups or not types or not locations or not blueprint_activities:
        raise OfficialSdeError("official_sde_subset_empty")
    return {
        "build_number": str(build_number),
        "groups": groups,
        "types": types,
        "locations": locations,
        "blueprint_activities": blueprint_activities,
    }


def write_official_industry_bundle(bundle: Mapping[str, object], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(destination, "wt", encoding="utf-8", compresslevel=9) as stream:
        json.dump(bundle, stream, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def install_bundled_industry_sde(
    connection: sqlite3.Connection,
    resource_path: Path = BUNDLED_INDUSTRY_SDE,
) -> SdeImportResult | None:
    """Install the bundled build once; user data remains untouched."""

    if not resource_path.is_file():
        return None
    try:
        with gzip.open(resource_path, "rt", encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OfficialSdeError("bundled_sde_invalid") from error
    if not isinstance(payload, dict) or set(payload) != {
        "build_number",
        "groups",
        "types",
        "locations",
        "blueprint_activities",
    }:
        raise OfficialSdeError("bundled_sde_invalid")
    build_number = payload["build_number"]
    locations = payload["locations"]
    if (
        not isinstance(build_number, str)
        or not build_number.strip()
        or not isinstance(locations, list)
    ):
        raise OfficialSdeError("bundled_sde_invalid")
    contains_security = any(
        isinstance(location, Mapping) and location.get("security_status") is not None
        for location in locations
    )
    location_columns = {
        str(column[1]) for column in connection.execute("PRAGMA table_info(sde_locations)")
    }
    installed_security = (
        "security_status" in location_columns
        and connection.execute(
            "SELECT 1 FROM sde_locations WHERE kind='solar_system' "
            "AND security_status IS NOT NULL LIMIT 1"
        ).fetchone()
        is not None
    )
    if (
        current_sde_blueprint_activity_build(connection) == build_number
        and (not contains_security or installed_security)
    ):
        return None
    try:
        return import_industry_sde(connection, **payload)
    except (TypeError, SdeImportError) as error:
        raise OfficialSdeError("bundled_sde_invalid") from error
