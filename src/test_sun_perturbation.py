import unittest
from datetime import datetime, timezone

import numpy as np

from constants import MU_SUN
from moon import get_sun_position
from propagator import total_acceleration
from sun_perturbation import sun_perturbation
from time_utils import utc_to_et


class SunPerturbationTests(unittest.TestCase):

    def test_origin_has_zero_differential_solar_acceleration(self):
        r_sun = np.array([1.4e8, -3.2e7, 8.0e6])
        np.testing.assert_allclose(
            sun_perturbation(np.zeros(3), r_sun),
            np.zeros(3),
            atol=1.0e-20,
        )

    def test_matches_differential_third_body_equation(self):
        r_sat = np.array([42164.0, -1200.0, 800.0])
        r_sun = np.array([1.46e8, 2.1e7, -8.4e6])
        delta = r_sun - r_sat
        expected = MU_SUN * (
            delta / np.linalg.norm(delta) ** 3
            - r_sun / np.linalg.norm(r_sun) ** 3
        )
        np.testing.assert_allclose(
            sun_perturbation(r_sat, r_sun),
            expected,
            rtol=1.0e-14,
            atol=1.0e-20,
        )

    def test_propagator_sun_switch_adds_exact_solar_term(self):
        epoch = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
        et = utc_to_et(epoch)
        r_sat = np.array([42164.0, 50.0, -20.0])
        without_sun = total_acceleration(
            et,
            r_sat,
            include_j2=True,
            include_moon=True,
            include_sun=False,
        )
        with_sun = total_acceleration(
            et,
            r_sat,
            include_j2=True,
            include_moon=True,
            include_sun=True,
        )
        expected_delta = sun_perturbation(r_sat, get_sun_position(et))
        np.testing.assert_allclose(
            with_sun - without_sun,
            expected_delta,
            rtol=1.0e-11,
            atol=1.0e-18,
        )


if __name__ == "__main__":
    unittest.main()
