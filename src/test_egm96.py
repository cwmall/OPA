"""Verification tests for the truncated EGM96 gravity model."""

from datetime import datetime, timezone
import unittest

import numpy as np

from constants import (
    C22_EARTH,
    J2_EARTH,
    MU_EARTH,
    R_EARTH,
    S22_EARTH,
)
from earth_gravity import (
    EGM96_UNNORMALIZED_C,
    EGM96_UNNORMALIZED_S,
    earth_harmonic_acceleration_fixed,
    earth_harmonic_potential_fixed,
    earth_harmonics_egm96,
    earth_j2,
    earth_tesseral_22,
)
from time_utils import utc_to_et


class EGM96GravityTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.position = np.array(
            [-38221.9974, 17805.7014, -0.732453098],
            dtype=float,
        )
        cls.et = utc_to_et(
            datetime(2024, 12, 3, 2, 30, tzinfo=timezone.utc)
        )

    def test_normalized_coefficients_reproduce_legacy_degree_two(self):
        self.assertAlmostEqual(
            EGM96_UNNORMALIZED_C[2, 0],
            -J2_EARTH,
            places=11,
        )
        self.assertAlmostEqual(
            EGM96_UNNORMALIZED_C[2, 2],
            C22_EARTH,
            delta=5.0e-12,
        )
        self.assertAlmostEqual(
            EGM96_UNNORMALIZED_S[2, 2],
            S22_EARTH,
            delta=5.0e-12,
        )

    def test_gravity_constants_match_official_egm96_distribution(self):
        self.assertEqual(MU_EARTH, 398600.4418)
        self.assertEqual(R_EARTH, 6378.137)

    def test_analytic_acceleration_matches_potential_gradient(self):
        position_fixed = np.array([22000.0, -35000.0, 4200.0])
        analytic = earth_harmonic_acceleration_fixed(
            position_fixed,
            max_degree=4,
        )
        step = 0.01
        numerical = np.empty(3)
        for axis in range(3):
            offset = np.zeros(3)
            offset[axis] = step
            numerical[axis] = (
                earth_harmonic_potential_fixed(
                    position_fixed + offset,
                    max_degree=4,
                )
                - earth_harmonic_potential_fixed(
                    position_fixed - offset,
                    max_degree=4,
                )
            ) / (2.0 * step)
        np.testing.assert_allclose(
            analytic,
            numerical,
            rtol=2.0e-7,
            atol=2.0e-14,
        )

    def test_degree_two_agrees_with_legacy_terms(self):
        degree_two = earth_harmonics_egm96(
            self.position,
            self.et,
            max_degree=2,
        )
        legacy = (
            earth_j2(self.position)
            + earth_tesseral_22(self.position, self.et)
        )
        # The production EGM96 path uses the full J2000-to-ITRS orientation,
        # while the legacy C22/S22 path uses a Greenwich-only z rotation.
        # They should remain close in magnitude without being component-wise
        # identical once precession and nutation are represented correctly.
        self.assertLess(np.linalg.norm(degree_two - legacy), 2.0e-10)

    def test_full_earth_orientation_adds_expected_pole_component(self):
        acceleration = earth_harmonics_egm96(
            self.position,
            self.et,
            max_degree=4,
        )
        self.assertAlmostEqual(
            acceleration[2],
            3.1062987919e-11,
            delta=2.0e-16,
        )

    def test_degree_eight_is_finite_and_adds_real_signal(self):
        degree_two = earth_harmonics_egm96(
            self.position,
            self.et,
            max_degree=2,
        )
        degree_eight = earth_harmonics_egm96(
            self.position,
            self.et,
            max_degree=8,
        )
        self.assertTrue(np.all(np.isfinite(degree_eight)))
        self.assertGreater(np.linalg.norm(degree_eight - degree_two), 1.0e-12)

    def test_degree_bounds_are_enforced(self):
        with self.assertRaises(ValueError):
            earth_harmonics_egm96(self.position, self.et, max_degree=1)
        with self.assertRaises(ValueError):
            earth_harmonics_egm96(self.position, self.et, max_degree=9)


if __name__ == "__main__":
    unittest.main()
