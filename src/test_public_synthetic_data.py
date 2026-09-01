"""Public-mode data boundary and synthetic scientific smoke tests."""

from datetime import datetime, timezone
from pathlib import Path
import unittest

import numpy as np

import constants
from eclipse_references import (
    available_eclipse_reference_specs,
    load_eclipse_reference_dataset,
)
from reference_comparison import (
    DEFAULT_REFERENCE_DATASET_ID,
    get_reference_dataset,
    list_reference_datasets,
    load_reference_scenario,
    run_reference_scenario,
)
from satellite_profiles import (
    BUILTIN_DEMO_GEO_ID,
    BUILTIN_PROFILES,
)
from solar_radiation_pressure import (
    resolved_solar_pressure_coefficient,
    solar_pressure_coefficient_for_epoch,
    solar_radiation_pressure,
)


class PublicSyntheticDataTests(unittest.TestCase):
    def test_only_explicit_synthetic_profiles_are_built_in(self):
        self.assertEqual(
            set(BUILTIN_PROFILES),
            {BUILTIN_DEMO_GEO_ID},
        )
        for profile in BUILTIN_PROFILES.values():
            self.assertIn("SYNTHETIC", profile.display_name)
            self.assertEqual(profile.orbit_source, "cartesian")
            self.assertIsNone(profile.norad_id)
            self.assertEqual(profile.tle_name, "")
            self.assertIn("SYNTHETIC/DEMO", profile.source_description)
            self.assertEqual(profile.parsed_epoch.year, 2030)

    def test_public_reference_catalogue_is_synthetic_and_reproducible(self):
        metadata = list_reference_datasets()
        self.assertGreaterEqual(len(metadata), 4)
        self.assertTrue(
            all("SYNTHETIC" in item["label"] for item in metadata)
        )
        scenario = load_reference_scenario(
            True, DEFAULT_REFERENCE_DATASET_ID, include_srp=False
        )
        self.assertEqual(scenario["states"].shape, (25, 6))
        self.assertFalse(scenario["states"].flags.writeable)
        self.assertEqual(scenario["epoch"].year, 2030)
        self.assertTrue(np.all(np.isfinite(scenario["states"])))
        self.assertIn("demo_data", str(scenario["path"]))

    def test_synthetic_reference_run_matches_its_generated_model(self):
        result = run_reference_scenario(
            include_moon=False,
            include_sun=False,
            dataset_id=DEFAULT_REFERENCE_DATASET_ID,
            rtol=1.0e-10,
            atol=1.0e-12,
            max_step=300.0,
        )
        self.assertLess(result["metrics"]["rms_position_error_km"], 1.0e-4)

    def test_eclipse_reference_is_in_memory_and_fictional(self):
        specs = available_eclipse_reference_specs()
        self.assertEqual(len(specs), 1)
        self.assertIn("SYNTHETIC/DEMO", specs[0].label)
        self.assertEqual(specs[0].source_format, "synthetic_memory")
        dataset = load_eclipse_reference_dataset(specs[0].dataset_id)
        self.assertEqual(len(dataset.events), 2)
        self.assertTrue(all(event.shadow_body == "EARTH" for event in dataset.events))

    def test_public_srp_uses_fictional_geometry_without_calibration_table(self):
        epoch = datetime(2030, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(solar_pressure_coefficient_for_epoch(epoch), 1.0)
        coefficient, mode = resolved_solar_pressure_coefficient(epoch)
        self.assertEqual(coefficient, 1.0)
        self.assertEqual(mode, "NOMINAL / PUBLIC DEMO")
        acceleration = solar_radiation_pressure(
            np.asarray([42164.0, 0.0, 0.0]),
            np.asarray([149597870.7, 0.0, 0.0]),
            coefficient,
        )
        self.assertEqual(acceleration.shape, (3,))
        self.assertTrue(np.all(np.isfinite(acceleration)))


if __name__ == "__main__":
    unittest.main()
