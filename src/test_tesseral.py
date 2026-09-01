"""Regression tests for Earth's C22/S22 tesseral gravity model."""

from datetime import datetime, timezone
import unittest

import numpy as np

from earth_gravity import (
    earth_gravity,
    earth_harmonics_egm96,
    earth_j2,
    earth_point_mass,
    earth_rotation_angle,
    earth_tesseral_22,
)
from propagator import total_acceleration
from time_utils import utc_to_et


class TesseralGravityTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.epoch = datetime(
            2024, 12, 3, 2, 30, 0,
            tzinfo=timezone.utc,
        )
        cls.et = utc_to_et(cls.epoch)
        cls.position = np.array(
            [-38221.9974, 17805.7014, -0.732453098],
            dtype=float,
        )

    def test_rotation_angle_is_finite_and_wrapped(self):
        angle = earth_rotation_angle(self.et)
        self.assertTrue(np.isfinite(angle))
        self.assertGreaterEqual(angle, 0.0)
        self.assertLess(angle, 2.0 * np.pi)

    def test_tesseral_acceleration_is_small_and_nonzero(self):
        tesseral = earth_tesseral_22(self.position, self.et)
        central = earth_point_mass(self.position)
        self.assertEqual(tesseral.shape, (3,))
        self.assertTrue(np.all(np.isfinite(tesseral)))
        self.assertGreater(np.linalg.norm(tesseral), 0.0)
        self.assertLess(
            np.linalg.norm(tesseral),
            1.0e-3 * np.linalg.norm(central),
        )

    def test_combined_gravity_adds_exact_tesseral_term(self):
        without = earth_gravity(
            self.position,
            include_j2=True,
        )
        with_tesseral = earth_gravity(
            self.position,
            include_j2=True,
            et=self.et,
            include_tesseral=True,
        )
        np.testing.assert_allclose(
            with_tesseral - without,
            earth_tesseral_22(self.position, self.et),
            rtol=1.0e-10,
            atol=1.0e-18,
        )

    def test_propagator_default_tracks_j2_switch(self):
        point_mass = total_acceleration(
            self.et,
            self.position,
            include_j2=False,
            include_moon=False,
        )
        harmonics = total_acceleration(
            self.et,
            self.position,
            include_j2=True,
            include_moon=False,
        )
        np.testing.assert_allclose(
            point_mass,
            earth_point_mass(self.position),
        )
        np.testing.assert_allclose(
            harmonics - point_mass,
            earth_harmonics_egm96(
                self.position,
                self.et,
                max_degree=4,
            ),
            rtol=1.0e-10,
            atol=1.0e-18,
        )

    def test_optional_profile_degree_uses_existing_supported_harmonics(self):
        default = total_acceleration(
            self.et,
            self.position,
            include_j2=True,
            include_moon=False,
        )
        explicit_four = total_acceleration(
            self.et,
            self.position,
            include_j2=True,
            include_moon=False,
            earth_harmonic_degree=4,
        )
        degree_two = total_acceleration(
            self.et,
            self.position,
            include_j2=True,
            include_moon=False,
            earth_harmonic_degree=2,
        )
        np.testing.assert_array_equal(default, explicit_four)
        self.assertGreater(np.linalg.norm(default - degree_two), 0.0)
        with self.assertRaises(ValueError):
            total_acceleration(
                self.et,
                self.position,
                include_j2=True,
                include_moon=False,
                earth_harmonic_degree=5,
            )

    def test_lunar_acceleration_is_strictly_physical(self):
        earth_only = total_acceleration(
            self.et,
            self.position,
            include_j2=True,
            include_moon=False,
        )
        physical = total_acceleration(
            self.et,
            self.position,
            include_j2=True,
            include_moon=True,
        )
        self.assertGreater(np.linalg.norm(physical - earth_only), 0.0)

    def test_tesseral_requires_epoch(self):
        with self.assertRaises(ValueError):
            earth_gravity(
                self.position,
                include_tesseral=True,
            )


if __name__ == "__main__":
    unittest.main()
