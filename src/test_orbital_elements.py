"""High-precision regression tests for Cartesian/Keplerian conversion."""

import unittest

import numpy as np

from orbital_elements import cartesian_to_keplerian, keplerian_to_cartesian


class OrbitalElementTests(unittest.TestCase):

    def test_october_earth_moon_export_state(self):
        """Regression for the final TOD/FK5 row checked in Reference Lab."""

        state = np.array([
            -40648.324664267,
            11171.561111126,
            30.870467292,
            -0.814611119864,
            -2.965360150591,
            0.002093245923,
        ])
        actual = cartesian_to_keplerian(state)
        expected = {
            "a_km": 42162.20348994727,
            "e": 0.0001958132246610723,
            "i_deg": 0.05728736820957748,
            "raan_deg": 117.54405823834439,
            "argp_deg": 83.48526781191335,
            "nu_deg": 323.60325426045347,
        }
        self.assertAlmostEqual(actual["a_km"], expected["a_km"], places=8)
        self.assertAlmostEqual(actual["e"], expected["e"], places=14)
        for key in ("i_deg", "raan_deg", "argp_deg", "nu_deg"):
            self.assertAlmostEqual(actual[key], expected[key], places=9)
        np.testing.assert_allclose(
            keplerian_to_cartesian(actual),
            state,
            rtol=0.0,
            atol=2.0e-9,
        )

    def test_october_export_matches_rounded_gm_web_calculator(self):
        state = np.array([
            -40648.324664267,
            11171.561111126,
            30.870467292,
            -0.814611119864,
            -2.965360150591,
            0.002093245923,
        ])
        actual = cartesian_to_keplerian(state, mu=398600.0)
        expected = {
            "a_km": 42162.25023644872,
            "e": 0.0001967067061719625,
            "i_deg": 0.057287368209577486,
            "raan_deg": 117.54405823834438,
            "argp_deg": 83.293700856241,
            "nu_deg": 323.7948212161258,
        }
        self.assertAlmostEqual(actual["a_km"], expected["a_km"], places=8)
        self.assertAlmostEqual(actual["e"], expected["e"], places=14)
        for key in ("i_deg", "raan_deg", "argp_deg", "nu_deg"):
            self.assertAlmostEqual(actual[key], expected[key], places=9)

    def test_known_elliptic_elements_round_trip(self):
        expected = {
            "a_km": 42166.314,
            "e": 0.00137,
            "i_deg": 4.125,
            "raan_deg": 287.75,
            "argp_deg": 132.2,
            "nu_deg": 17.4,
        }
        state = keplerian_to_cartesian(expected)
        actual = cartesian_to_keplerian(state)
        self.assertAlmostEqual(actual["a_km"], expected["a_km"], places=8)
        self.assertAlmostEqual(actual["e"], expected["e"], places=13)
        for key in ("i_deg", "raan_deg", "argp_deg", "nu_deg"):
            self.assertAlmostEqual(actual[key], expected[key], places=10)
        np.testing.assert_allclose(
            keplerian_to_cartesian(actual),
            state,
            rtol=0.0,
            atol=2.0e-10,
        )

    def test_retrograde_orbit_quadrants(self):
        expected = {
            "a_km": 26560.0,
            "e": 0.72,
            "i_deg": 116.4,
            "raan_deg": 355.2,
            "argp_deg": 275.8,
            "nu_deg": 221.3,
        }
        actual = cartesian_to_keplerian(
            keplerian_to_cartesian(expected)
        )
        for key, value in expected.items():
            self.assertAlmostEqual(actual[key], value, places=9)

    def test_circular_equatorial_singularity_is_explicit(self):
        state = np.array([42164.0, 0.0, 0.0, 0.0, 3.074666284, 0.0])
        elements = cartesian_to_keplerian(state)
        self.assertTrue(elements["equatorial"])
        self.assertIsNone(elements["raan_deg"])
        # This rounded speed is not mathematically circular, therefore ω/ν
        # remain defined; exact singular behavior is exercised below.
        exact = keplerian_to_cartesian({
            "a_km": 42164.0,
            "e": 0.0,
            "i_deg": 0.0,
            "raan_deg": 0.0,
            "argp_deg": 0.0,
            "nu_deg": 47.0,
        })
        singular = cartesian_to_keplerian(exact)
        self.assertTrue(singular["circular"])
        self.assertIsNone(singular["raan_deg"])
        self.assertIsNone(singular["argp_deg"])
        self.assertAlmostEqual(singular["nu_deg"], 47.0, places=10)
        self.assertEqual(singular["anomaly_kind"], "true_longitude")


if __name__ == "__main__":
    unittest.main()
