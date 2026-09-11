from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from new_eden_foundry_backend.database import connect_database, initialize_database
from new_eden_foundry_backend.esi_client import EsiClientError, EsiResponse
from new_eden_foundry_backend.industry_facility_sync import (
    IndustryFacilitySyncError,
    sync_industry_facilities,
    validate_industry_facilities,
    validate_industry_systems,
)
from new_eden_foundry_backend.industry_facility_view import (
    IndustryFacilityViewError,
    query_industry_facilities,
)
from new_eden_foundry_backend.industry_job_sync import sync_character_industry_jobs
from new_eden_foundry_backend.industry_job_view import query_industry_jobs
from new_eden_foundry_backend.location_resolution import STRUCTURE_SCOPE


CHARACTER_ID = 90_000_001
STATION_ID = 60_000_001
STRUCTURE_ID = 1_000_000_000_001
SYSTEM_ID = 30_000_001


def facility():
    return {
        "facility_id": STATION_ID,
        "owner_id": 1_000_001,
        "region_id": 10_000_001,
        "solar_system_id": SYSTEM_ID,
        "type_id": 1_928,
    }


def system():
    return {
        "solar_system_id": SYSTEM_ID,
        "cost_indices": [
            {"activity": "manufacturing", "cost_index": 0.0125},
            {"activity": "copying", "cost_index": 0.0042},
        ],
    }


def job(facility_id=STRUCTURE_ID):
    return {
        "activity_id": 1,
        "blueprint_id": 7_001,
        "blueprint_location_id": facility_id,
        "blueprint_type_id": 6_001,
        "completed_character_id": None,
        "completed_date": None,
        "cost": 1234.5,
        "duration": 3600,
        "end_date": "2026-09-10T11:00:00Z",
        "facility_id": facility_id,
        "installer_id": CHARACTER_ID,
        "job_id": 8_001,
        "licensed_runs": 0,
        "output_location_id": facility_id,
        "pause_date": None,
        "probability": 1.0,
        "product_type_id": 6_002,
        "runs": 2,
        "start_date": "2026-09-10T10:00:00Z",
        "station_id": facility_id,
        "status": "active",
        "successful_runs": None,
    }


class JobClient:
    def get_json(self, path, *, query, character_id, required_scopes):
        del path, query, character_id, required_scopes
        return EsiResponse(200, [job()], {}, False)


class FacilityClient:
    categories = {
        STATION_ID: "station",
        1_000_001: "corporation",
        10_000_001: "region",
        SYSTEM_ID: "solar_system",
        1_928: "inventory_type",
        2_000_001: "corporation",
        3_584_000: "inventory_type",
    }

    def __init__(self, *, structure="available", fail_systems=False):
        self.structure = structure
        self.fail_systems = fail_systems
        self.get_calls = []
        self.post_calls = []

    def get_json(self, path, *, character_id=None, required_scopes=()):
        self.get_calls.append((path, character_id, required_scopes))
        if path == "/industry/facilities/":
            return EsiResponse(200, [facility()], {}, False)
        if path == "/industry/systems/":
            if self.fail_systems:
                raise EsiClientError("esi-network-unavailable", retryable=True)
            return EsiResponse(200, [system()], {}, False)
        if path == f"/universe/structures/{STRUCTURE_ID}/":
            if self.structure == "restricted":
                raise EsiClientError("esi-request-rejected", status=403)
            return EsiResponse(
                200,
                {
                    "name": "Example Engineering Complex",
                    "owner_id": 2_000_001,
                    "solar_system_id": SYSTEM_ID,
                    "type_id": 3_584_000,
                },
                {},
                False,
            )
        raise AssertionError(path)

    def post_json(self, path, payload):
        self.post_calls.append((path, payload))
        return EsiResponse(
            200,
            [
                {
                    "id": identifier,
                    "name": f"Name {identifier}",
                    "category": self.categories[identifier],
                }
                for identifier in payload
            ],
            {},
            False,
        )


class IndustryFacilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "foundry.db"
        initialize_database(self.path)
        self.db = connect_database(self.path)
        self.db.execute(
            "INSERT INTO characters(character_id,name) VALUES(?,?)",
            (CHARACTER_ID, "Industry Pilot"),
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def _enable_structure_and_job(self):
        self.db.execute(
            "INSERT INTO character_scopes(character_id,scope) VALUES(?,?)",
            (CHARACTER_ID, STRUCTURE_SCOPE),
        )
        self.db.commit()
        sync_character_industry_jobs(self.db, JobClient(), CHARACTER_ID)

    def test_syncs_public_facilities_cost_indices_and_observed_structure(self):
        self._enable_structure_and_job()
        client = FacilityClient()
        result = sync_industry_facilities(self.db, client)
        self.assertEqual(
            (
                result.facilities,
                result.npc_facilities,
                result.observed_facilities,
                result.restricted_structures,
                result.systems,
                result.resolved_names,
            ),
            (2, 1, 1, 0, 1, 7),
        )
        self.assertIn(
            (f"/universe/structures/{STRUCTURE_ID}/", CHARACTER_ID, (STRUCTURE_SCOPE,)),
            client.get_calls,
        )
        self.assertTrue(all(len(payload) <= 1_000 for _path, payload in client.post_calls))

        page = query_industry_facilities(
            self.db,
            {
                "search": "engineering",
                "kind": "structure",
                "access": "available",
                "activity": "manufacturing",
                "usedOnly": True,
                "offset": 0,
                "limit": 100,
                "sortBy": "cost",
                "sortDirection": "asc",
            },
            now=datetime(2026, 9, 11, tzinfo=timezone.utc),
        )
        self.assertEqual(page["total"], 1)
        record = page["items"][0]
        self.assertEqual(record["facilityName"], "Example Engineering Complex")
        self.assertEqual(record["solarSystemName"], f"Name {SYSTEM_ID}")
        self.assertEqual(record["activityCostIndex"], 0.0125)
        self.assertEqual(record["usedByCharacterIds"], [CHARACTER_ID])
        self.assertEqual((record["jobCount"], record["activeJobs"]), (1, 1))
        jobs = query_industry_jobs(
            self.db,
            {
                "search": "engineering",
                "ownerCharacterId": None,
                "status": None,
                "activityId": None,
                "correlation": None,
                "offset": 0,
                "limit": 100,
                "sortBy": "end",
                "sortDirection": "desc",
            },
        )
        self.assertEqual(jobs["items"][0]["facilityName"], "Example Engineering Complex")
        self.assertEqual(jobs["items"][0]["systemCostIndex"], 0.0125)

    def test_scope_missing_and_forbidden_are_visible_states(self):
        sync_character_industry_jobs(self.db, JobClient(), CHARACTER_ID)
        missing = sync_industry_facilities(self.db, FacilityClient())
        self.assertEqual(missing.restricted_structures, 1)
        query = {
            "search": "",
            "kind": "structure",
            "access": "scope-missing",
            "activity": "manufacturing",
            "usedOnly": True,
            "offset": 0,
            "limit": 100,
            "sortBy": "facility",
            "sortDirection": "asc",
        }
        self.assertEqual(query_industry_facilities(self.db, query)["total"], 1)

        self.db.execute(
            "INSERT INTO character_scopes(character_id,scope) VALUES(?,?)",
            (CHARACTER_ID, STRUCTURE_SCOPE),
        )
        self.db.commit()
        forbidden = sync_industry_facilities(self.db, FacilityClient(structure="restricted"))
        self.assertEqual(forbidden.restricted_structures, 1)
        restricted = query_industry_facilities(
            self.db,
            {**query, "access": "restricted"},
        )
        self.assertEqual(restricted["items"][0]["errorCode"], "structure_forbidden")

    def test_failed_followup_preserves_previous_complete_snapshot(self):
        first = sync_industry_facilities(self.db, FacilityClient())
        with self.assertRaises(EsiClientError):
            sync_industry_facilities(self.db, FacilityClient(fail_systems=True))
        snapshots = self.db.execute(
            "SELECT COUNT(*) FROM cached_snapshots WHERE resource='industry_facilities'"
        ).fetchone()[0]
        self.assertEqual(snapshots, 1)
        latest = self.db.execute(
            "SELECT status,error_code FROM sync_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(tuple(latest), ("failed", "esi-network-unavailable"))
        self.assertGreater(first.sync_run_id, 0)

    def test_contract_validation_rejects_duplicates_and_bad_queries(self):
        with self.assertRaises(IndustryFacilitySyncError):
            validate_industry_facilities([facility(), facility()])
        invalid_system = system()
        invalid_system["cost_indices"] = [
            {"activity": "manufacturing", "cost_index": 0.1},
            {"activity": "manufacturing", "cost_index": 0.2},
        ]
        with self.assertRaises(IndustryFacilitySyncError):
            validate_industry_systems([invalid_system])
        with self.assertRaises(IndustryFacilityViewError):
            query_industry_facilities(self.db, {"search": ""})


if __name__ == "__main__":
    unittest.main()
