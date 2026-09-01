"""OPA project schema and safe round-trip coverage."""

import json
import os
import tempfile
import unittest

from opa_project import (
    PROJECT_SCHEMA_VERSION,
    ProjectValidationError,
    load_project,
    new_project,
    save_project,
    validate_project,
)
from satellite_profiles import BUILTIN_DEMO_GEO_ID, BUILTIN_PROFILES


class OPAProjectTests(unittest.TestCase):

    def setUp(self):
        self.profile = BUILTIN_PROFILES[BUILTIN_DEMO_GEO_ID]

    def test_project_round_trip_keeps_profile_snapshot(self):
        project = new_project(self.profile, "2.24.0")
        project["name"] = "Station Keeping Test"
        project["propagation"]["duration_days"] = 7.0
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "mission.opa")
            saved = save_project(project, path)
            loaded = load_project(path)
        self.assertEqual(saved, loaded)
        self.assertEqual(loaded["satellite_profile_id"], self.profile.profile_id)
        self.assertEqual(
            loaded["satellite_profile_snapshot"]["mass_kg"],
            self.profile.mass_kg,
        )

    def test_malformed_and_future_projects_fail_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "bad.opa")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("not json")
            with self.assertRaises(ProjectValidationError):
                load_project(path)
        project = new_project(self.profile, "2.24.0")
        project["schema_version"] = PROJECT_SCHEMA_VERSION + 1
        with self.assertRaises(ProjectValidationError):
            validate_project(project)

    def test_missing_optional_fields_receive_safe_defaults(self):
        project = new_project(self.profile, "2.24.0")
        project.pop("notes")
        project.pop("view")
        validated = validate_project(project)
        self.assertEqual(validated["notes"], "")
        self.assertEqual(validated["view"]["active_tab"], 0)
        self.assertIn("eclipse", validated)
        self.assertIn("initial_state", validated)

    def test_schema_one_document_migrates_to_current_schema(self):
        project = new_project(self.profile, "2.25.0")
        project["schema_version"] = 1
        project.pop("initial_state")
        project.pop("eclipse")
        project["view"] = {"active_tab": 2, "manual_chart": "velocity"}
        migrated = validate_project(project)
        self.assertEqual(migrated["schema_version"], PROJECT_SCHEMA_VERSION)
        self.assertEqual(
            migrated["initial_state"]["state_j2000"],
            migrated["propagation"]["state_j2000"],
        )
        self.assertEqual(migrated["eclipse"]["duration_days"], 30)
        self.assertEqual(migrated["view"]["active_tab"], 2)

    def test_schema_two_migrates_with_safe_geo_budget_usage_default(self):
        project = new_project(self.profile, "2.26.0")
        project["schema_version"] = 2
        project["geo_operations"].pop("annual_delta_v_used_m_s")
        migrated = validate_project(project)
        self.assertEqual(migrated["schema_version"], PROJECT_SCHEMA_VERSION)
        self.assertEqual(migrated["geo_operations"]["annual_delta_v_used_m_s"], 0.0)

    def test_geo_budget_usage_round_trips_and_rejects_negative_values(self):
        project = new_project(self.profile, "2.27.0")
        project["geo_operations"]["annual_delta_v_budget_m_s"] = 48.0
        project["geo_operations"]["annual_delta_v_used_m_s"] = 12.5
        validated = validate_project(project)
        self.assertEqual(
            validated["geo_operations"]["annual_delta_v_used_m_s"], 12.5
        )
        project["geo_operations"]["annual_delta_v_used_m_s"] = -1.0
        with self.assertRaises(ProjectValidationError):
            validate_project(project)

    def test_invalid_timestamp_boolean_and_provenance_are_rejected(self):
        project = new_project(self.profile, "2.25.0")
        project["created_utc"] = "not-a-date"
        with self.assertRaises(ProjectValidationError):
            validate_project(project)

        project = new_project(self.profile, "2.25.0")
        project["propagation"]["include_moon"] = "false"
        with self.assertRaises(ProjectValidationError):
            validate_project(project)

        project = new_project(self.profile, "2.25.0")
        project["provenance"] = [{"nested": {"unsafe": "shape"}}]
        with self.assertRaises(ProjectValidationError):
            validate_project(project)


if __name__ == "__main__":
    unittest.main()
