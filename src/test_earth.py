"""Deterministic Earth-gravity tests with a fictional Cartesian state."""

import unittest

import numpy as np

from constants import MU_EARTH
from earth_gravity import earth_gravity, earth_point_mass


class EarthGravitySmokeTests(unittest.TestCase):
    def test_point_mass_matches_inverse_square_law(self):
        position = np.array([42164.0, 0.0, 0.0])
        acceleration = earth_point_mass(position)
        self.assertAlmostEqual(acceleration[0], -MU_EARTH / 42164.0**2, places=15)
        self.assertEqual(acceleration[1], 0.0)
        self.assertEqual(acceleration[2], 0.0)

    def test_default_gravity_is_finite_and_points_inward(self):
        position = np.array([42164.0, 120.0, -45.0])
        acceleration = earth_gravity(position)
        self.assertTrue(np.all(np.isfinite(acceleration)))
        self.assertLess(float(np.dot(position, acceleration)), 0.0)


if __name__ == "__main__":
    unittest.main()
