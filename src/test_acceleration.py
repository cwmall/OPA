"""Deterministic total-acceleration unit tests with fictional vectors."""

import unittest

import numpy as np

from acceleration import total_acceleration
from earth_gravity import earth_gravity
from moon_perturbation import moon_perturbation
from sun_perturbation import sun_perturbation


class TotalAccelerationTests(unittest.TestCase):
    def setUp(self):
        self.satellite = np.array([42164.0, 120.0, -45.0])
        self.moon = np.array([360000.0, 90000.0, 45000.0])
        self.sun = np.array([149597870.7, -100000.0, 25000.0])

    def test_earth_and_moon_sum_matches_independent_components(self):
        actual = total_acceleration(self.satellite, self.moon)
        expected = earth_gravity(self.satellite) + moon_perturbation(
            self.satellite, self.moon
        )
        np.testing.assert_allclose(actual, expected, rtol=0.0, atol=0.0)

    def test_optional_sun_term_is_added_without_mutating_inputs(self):
        satellite = self.satellite.copy()
        actual = total_acceleration(self.satellite, self.moon, self.sun)
        expected = (
            earth_gravity(self.satellite)
            + moon_perturbation(self.satellite, self.moon)
            + sun_perturbation(self.satellite, self.sun)
        )
        np.testing.assert_allclose(actual, expected, rtol=0.0, atol=0.0)
        np.testing.assert_array_equal(self.satellite, satellite)


if __name__ == "__main__":
    unittest.main()
