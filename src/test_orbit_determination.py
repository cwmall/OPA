"""Synthetic public dataset and weighted least-squares coverage."""

from datetime import datetime, timedelta, timezone
import unittest

import numpy as np

from orbit_determination import (
    fit_weighted_least_squares,
    load_dataset,
    predict_observation,
    reference_state_at,
    reference_state_jumps,
)


class OrbitDeterminationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = load_dataset()
        cls.arc_start = cls.dataset.measurement_start

    def test_public_dataset_is_explicitly_synthetic_and_memory_only(self):
        dataset = self.dataset
        self.assertEqual(dataset.dataset_id, "synthetic-od-demo-v1")
        self.assertIn("SYNTHETIC/DEMO", dataset.display_name)
        self.assertEqual(set(dataset.stations), {"DEMO-A", "DEMO-B"})
        self.assertEqual(len(dataset.measurements), 78)
        self.assertEqual(len(dataset.reference_orbit), 13)
        self.assertEqual(dataset.source_directory.name, "SYNTHETIC_DEMO_MEMORY")
        self.assertEqual(
            dataset.measurement_start,
            datetime(2030, 1, 1, tzinfo=timezone.utc),
        )

    def test_observation_model_reproduces_generated_measurement(self):
        measurement = self.dataset.measurements[0]
        reference = reference_state_at(self.dataset, measurement.epoch)
        computed = predict_observation(
            reference,
            measurement,
            self.dataset.stations[measurement.station_id],
        )
        self.assertTrue(np.isfinite(computed))
        self.assertGreater(abs(measurement.value - computed), 1.0e-6)

    def test_synthetic_dataset_has_no_hidden_state_jumps(self):
        self.assertEqual(
            reference_state_jumps(
                self.dataset,
                self.dataset.reference_start,
                self.dataset.reference_end,
            ),
            (),
        )

    def test_weighted_least_squares_reduces_residual_rms(self):
        result = fit_weighted_least_squares(
            self.dataset,
            self.dataset.measurement_start,
            self.dataset.measurement_end,
            max_iterations=3,
        )
        self.assertLess(result.weighted_rms_postfit, result.weighted_rms_prefit)
        self.assertLess(result.weighted_rms_postfit, 1.0e-5)
        self.assertTrue(np.all(np.isfinite(result.corrected_state)))
        self.assertEqual(result.covariance.shape, (6, 6))
        self.assertEqual(
            result.noon_epoch,
            datetime(2030, 1, 1, 12, tzinfo=timezone.utc),
        )
        self.assertTrue(np.isfinite(result.noon_position_error_postfit_km))

    def test_invalid_short_arc_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "at least seven"):
            fit_weighted_least_squares(
                self.dataset,
                self.arc_start,
                self.arc_start + timedelta(seconds=1),
            )


if __name__ == "__main__":
    unittest.main()
