"""Persisted desktop configuration coverage."""

import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from application_config import (
    CONFIG_SCHEMA_VERSION,
    DEFAULT_APPLICATION_CONFIG,
    APPLICATION_DIRECTORY_NAME,
    default_application_config_path,
    load_application_config,
    normalise_application_config,
    save_application_config,
)


class ApplicationConfigTests(unittest.TestCase):

    @unittest.skipUnless(os.name == "nt", "Windows LOCALAPPDATA path is required")
    def test_default_windows_path_is_stable_before_qt_application_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            previous_override = os.environ.pop("OPA_CONFIG_PATH", None)
            previous_local = os.environ.get("LOCALAPPDATA")
            try:
                os.environ["LOCALAPPDATA"] = directory
                self.assertEqual(
                    default_application_config_path(),
                    Path(directory) / APPLICATION_DIRECTORY_NAME / "config.json",
                )
            finally:
                if previous_override is not None:
                    os.environ["OPA_CONFIG_PATH"] = previous_override
                if previous_local is None:
                    os.environ.pop("LOCALAPPDATA", None)
                else:
                    os.environ["LOCALAPPDATA"] = previous_local

    def test_missing_or_invalid_file_uses_safe_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "opa_config.json")
            self.assertEqual(
                load_application_config(path),
                normalise_application_config(DEFAULT_APPLICATION_CONFIG),
            )
            with open(path, "w", encoding="utf-8") as config_file:
                config_file.write("not json")
            self.assertEqual(
                load_application_config(path),
                normalise_application_config(DEFAULT_APPLICATION_CONFIG),
            )

    def test_save_round_trip_keeps_retro_and_numerical_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "opa_config.json")
            saved = save_application_config(
                {
                    "theme": "retro",
                    "language": "az",
                    "integrator_rtol": "2.5e-10",
                    "integrator_atol": "4e-12",
                    "integrator_max_step": 120,
                    "validation_minutes": 90,
                    "eop_enabled": True,
                    "active_profile_id": "synthetic_geo_demo",
                    "window_geometry": [100, 120, 1366, 768],
                    "window_maximized": True,
                    "active_module": 2,
                    "active_tab": 5,
                },
                path,
            )
            self.assertEqual(saved, load_application_config(path))
            self.assertEqual(saved["theme"], "retro")
            self.assertEqual(saved["language"], "az")
            self.assertEqual(saved["integrator_rtol"], "2.5e-10")
            self.assertTrue(saved["eop_enabled"])
            self.assertEqual(saved["active_profile_id"], "synthetic_geo_demo")
            self.assertEqual(saved["window_geometry"], [100, 120, 1366, 768])
            self.assertTrue(saved["window_maximized"])
            self.assertEqual(saved["active_module"], 2)
            self.assertEqual(saved["active_tab"], 5)
            self.assertNotIn("recent_projects", saved)
            with open(path, "r", encoding="utf-8") as config_file:
                self.assertEqual(
                    json.load(config_file)["config_version"],
                    CONFIG_SCHEMA_VERSION,
                )

    def test_invalid_values_are_normalised_before_they_reach_widgets(self):
        config = normalise_application_config(
            {
                "theme": "sepia",
                "language": "de",
                "integrator_rtol": -1,
                "integrator_atol": "nan",
                "integrator_max_step": 99999,
                "validation_minutes": 0,
                "eop_enabled": "false",
            }
        )
        self.assertEqual(config["theme"], "normal")
        self.assertEqual(config["language"], "en")
        self.assertEqual(config["integrator_rtol"], "1e-11")
        self.assertEqual(config["integrator_atol"], "1e-12")
        self.assertEqual(config["integrator_max_step"], 3600)
        self.assertEqual(config["validation_minutes"], 1)
        self.assertFalse(config["eop_enabled"])
        self.assertEqual(config["active_profile_id"], "synthetic_geo_demo")

    def test_historical_non_default_appearance_migrates_to_retro(self):
        migrated = normalise_application_config(
            {
                "visual_theme": "mission",
                "color_theme": "light",
            }
        )
        self.assertEqual(migrated["theme"], "retro")
        self.assertNotIn("visual_theme", migrated)
        self.assertNotIn("color_theme", migrated)

    def test_retired_leo_profile_migrates_to_geo(self):
        migrated = normalise_application_config(
            {"active_profile_id": "synthetic_leo_demo"}
        )
        self.assertEqual(migrated["active_profile_id"], "synthetic_geo_demo")

    def test_private_and_secret_fields_are_dropped(self):
        config = normalise_application_config(
            {
                "active_profile_id": "admin-private-profile",
                "password": "must-not-survive",
                "admin_unlocked": True,
                "private_path": "hidden",
                "recent_projects": ["hidden.opa"],
            }
        )
        self.assertEqual(config["active_profile_id"], "synthetic_geo_demo")
        self.assertNotIn("password", config)
        self.assertNotIn("admin_unlocked", config)
        self.assertNotIn("private_path", config)
        self.assertNotIn("recent_projects", config)

    def test_corrupt_primary_recovers_previous_atomic_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "config.json")
            save_application_config({"theme": "retro", "language": "az"}, path)
            save_application_config({"theme": "normal", "language": "en"}, path)
            with open(path, "w", encoding="utf-8") as stream:
                stream.write("{broken")
            recovered = load_application_config(path)
            self.assertEqual(recovered["theme"], "retro")
            self.assertEqual(recovered["language"], "az")


if __name__ == "__main__":
    unittest.main()
