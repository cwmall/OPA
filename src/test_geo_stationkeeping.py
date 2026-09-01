"""Analytical and synthetic GEO station-keeping coverage."""

from datetime import datetime, timezone
import unittest

import numpy as np

from geo_stationkeeping import (
    EARTH_SIDEREAL_RATE_RAD_S,
    NOMINAL_GEO_RADIUS_KM,
    NOMINAL_GEO_SPEED_KM_S,
    STANDARD_GRAVITY_M_S2,
    StationKeepingError,
    analyze_geo_trajectory,
    east_west_delta_v_m_s,
    estimate_propellant_kg,
    north_south_delta_v_m_s,
    wrap_longitude_error,
)
from orbital_elements import keplerian_to_cartesian


class GEOStationKeepingTests(unittest.TestCase):

    @staticmethod
    def _state(inclination=0.05, eccentricity=0.0002):
        return keplerian_to_cartesian(
            {
                "a_km": 42164.0,
                "e": eccentricity,
                "i_deg": inclination,
                "raan_deg": 25.0,
                "argp_deg": 40.0,
                "nu_deg": 10.0,
            }
        )

    def _analyze(
        self,
        longitudes,
        *,
        times=None,
        inclination=0.05,
        eccentricity=0.0002,
        **overrides,
    ):
        times = np.asarray(
            times if times is not None else np.arange(len(longitudes)) * 86400.0,
            dtype=float,
        )
        state = self._state(inclination=inclination, eccentricity=eccentricity)
        defaults = {
            "target_longitude_deg": 12.0,
            "station_box_half_width_deg": 0.1,
            "inclination_warning_deg": 0.08,
            "inclination_limit_deg": 0.1,
            "eccentricity_warning": 0.0007,
            "eccentricity_limit": 0.001,
        }
        defaults.update(overrides)
        return analyze_geo_trajectory(
            times,
            np.vstack([state] * len(times)),
            np.asarray(longitudes, dtype=float),
            datetime(2030, 1, 1, tzinfo=timezone.utc),
            **defaults,
        )

    def test_longitude_wrap_uses_shortest_signed_error(self):
        actual = wrap_longitude_error([179.0, -179.0], -179.0)
        np.testing.assert_allclose(actual, [-2.0, 0.0])

    def test_zero_drift_and_zero_inclination_need_no_delta_v(self):
        self.assertEqual(east_west_delta_v_m_s(0.0), 0.0)
        self.assertEqual(north_south_delta_v_m_s(0.0), 0.0)

    def test_propellant_estimate_is_positive_and_bounded(self):
        propellant = estimate_propellant_kg(10.0, 1200.0, 220.0)
        self.assertGreater(propellant, 0.0)
        self.assertLess(propellant, 1200.0)
        recovered_delta_v = 220.0 * STANDARD_GRAVITY_M_S2 * np.log(
            1200.0 / (1200.0 - propellant)
        )
        self.assertAlmostEqual(recovered_delta_v, 10.0, places=11)

    def test_ew_formula_matches_independent_kepler_impulse_derivation(self):
        drift_deg_day = 0.12
        delta_n = np.radians(drift_deg_day) / 86400.0
        fractional_da = -(2.0 / 3.0) * (-delta_n) / EARTH_SIDEREAL_RATE_RAD_S
        delta_a_km = NOMINAL_GEO_RADIUS_KM * fractional_da
        independently_derived = abs(
            NOMINAL_GEO_SPEED_KM_S * 1000.0 * delta_a_km
            / (2.0 * NOMINAL_GEO_RADIUS_KM)
        )
        self.assertAlmostEqual(
            east_west_delta_v_m_s(drift_deg_day), independently_derived, places=12
        )

    def test_ns_formula_matches_ideal_plane_change_and_small_angle_limit(self):
        inclination = 0.05
        exact = 2.0 * NOMINAL_GEO_SPEED_KM_S * 1000.0 * np.sin(
            np.radians(inclination) / 2.0
        )
        actual = north_south_delta_v_m_s(inclination)
        self.assertAlmostEqual(actual, exact, places=12)
        small_angle = NOMINAL_GEO_SPEED_KM_S * 1000.0 * np.radians(inclination)
        self.assertAlmostEqual(actual / small_angle, 1.0, places=7)

    def test_propagated_boundary_and_advisory_are_non_mutating(self):
        times = np.array([0.0, 86400.0, 172800.0])
        state = self._state()
        states = np.vstack((state, state, state))
        original = states.copy()
        result = analyze_geo_trajectory(
            times,
            states,
            np.array([12.0, 12.06, 12.12]),
            datetime(2030, 1, 1, tzinfo=timezone.utc),
            target_longitude_deg=12.0,
            station_box_half_width_deg=0.1,
            inclination_warning_deg=0.08,
            inclination_limit_deg=0.1,
            eccentricity_warning=0.0007,
            eccentricity_limit=0.001,
            mass_kg=1200.0,
            isp_s=220.0,
            annual_delta_v_budget_m_s=50.0,
        )
        self.assertEqual(result["status"], "NOMINAL")
        self.assertEqual(result["boundary_index"], 2)
        self.assertTrue(result["boundary_interpolated"])
        self.assertAlmostEqual(result["boundary_elapsed_seconds"], 144000.0)
        self.assertEqual(result["boundary_prediction_kind"], "PROPAGATED INTERPOLATION")
        self.assertAlmostEqual(result["drift_rate_deg_day"], 0.06, places=9)
        self.assertGreater(result["east_west_delta_v_m_s"], 0.0)
        self.assertGreater(result["propellant_estimate_kg"], 0.0)
        np.testing.assert_array_equal(states, original)

    def test_warning_and_outside_statuses_are_distinct(self):
        state_warning = self._state(inclination=0.09)
        state_outside = self._state(eccentricity=0.002)
        common = dict(
            elapsed_seconds=[0.0, 3600.0],
            longitudes_deg=[12.0, 12.0],
            epoch=datetime(2030, 1, 1, tzinfo=timezone.utc),
            target_longitude_deg=12.0,
            station_box_half_width_deg=0.1,
            inclination_warning_deg=0.08,
            inclination_limit_deg=0.1,
            eccentricity_warning=0.0007,
            eccentricity_limit=0.001,
        )
        warning = analyze_geo_trajectory(
            states=np.vstack((state_warning, state_warning)), **common
        )
        outside = analyze_geo_trajectory(
            states=np.vstack((state_outside, state_outside)), **common
        )
        self.assertEqual(warning["status"], "WARNING")
        self.assertEqual(outside["status"], "OUTSIDE")

    def test_eastward_and_westward_drift_report_correction_sense(self):
        eastward = self._analyze([12.0, 12.01])
        westward = self._analyze([12.0, 11.99])
        self.assertEqual(eastward["east_west_direction"], "EASTWARD")
        self.assertIn("PROGRADE", eastward["east_west_correction_direction"])
        self.assertEqual(westward["east_west_direction"], "WESTWARD")
        self.assertIn("RETROGRADE", westward["east_west_correction_direction"])

    def test_inside_warning_and_outside_station_box_are_distinct(self):
        inside = self._analyze([12.0, 12.0])
        warning = self._analyze([12.08, 12.08])
        outside = self._analyze([12.11, 12.11])
        self.assertEqual(inside["station_box_status"], "NOMINAL")
        self.assertEqual(warning["station_box_status"], "WARNING")
        self.assertEqual(outside["station_box_status"], "OUTSIDE")

    def test_no_propagated_violation_keeps_linear_estimate_separate(self):
        result = self._analyze(
            [12.0, 12.001], times=[0.0, 3600.0]
        )
        self.assertIsNone(result["boundary_utc"])
        self.assertEqual(result["boundary_prediction_kind"], "LINEAR ESTIMATE")
        self.assertIsNotNone(result["linear_boundary_utc"])
        self.assertAlmostEqual(
            result["linear_time_to_boundary_seconds"], 360000.0, places=4
        )

    def test_zero_drift_has_no_boundary_estimate(self):
        result = self._analyze([12.0, 12.0])
        self.assertEqual(result["east_west_direction"], "ZERO DRIFT")
        self.assertIsNone(result["boundary_utc"])
        self.assertIsNone(result["linear_boundary_utc"])
        self.assertEqual(result["boundary_prediction_kind"], "NO CROSSING FOUND")

    def test_missing_isp_and_missing_inventory_are_explicit(self):
        missing_isp = self._analyze([12.0, 12.01], mass_kg=1200.0)
        self.assertIsNone(missing_isp["propellant_estimate_kg"])
        self.assertIn("INSUFFICIENT DATA", missing_isp["propellant_status"])

        missing_inventory = self._analyze(
            [12.0, 12.01], mass_kg=1200.0, isp_s=220.0
        )
        self.assertGreater(missing_inventory["propellant_estimate_kg"], 0.0)
        self.assertIn("INVENTORY NOT CONFIGURED", missing_inventory["propellant_status"])

    def test_propellant_inventory_and_annual_budget_cases(self):
        result = self._analyze(
            [12.0, 13.0],
            inclination=0.0,
            mass_kg=1200.0,
            isp_s=220.0,
            available_propellant_mass_kg=0.0,
            annual_delta_v_budget_m_s=1.0,
            annual_delta_v_used_m_s=0.8,
        )
        self.assertIn("EXCEEDS CONFIGURED PROPELLANT", result["propellant_status"])
        self.assertEqual(
            result["annual_budget_status"], "ADVISORY EXCEEDS REMAINING BUDGET"
        )
        already_exceeded = self._analyze(
            [12.0, 12.0],
            inclination=0.0,
            annual_delta_v_budget_m_s=1.0,
            annual_delta_v_used_m_s=2.0,
        )
        self.assertEqual(
            already_exceeded["annual_budget_status"], "EXCEEDED BEFORE THIS ADVISORY"
        )

    def test_vector_conventions_are_finite_and_have_expected_inclination_norm(self):
        result = self._analyze([12.0, 12.0], inclination=0.05)
        vector = result["inclination_vector_rad"]
        self.assertAlmostEqual(np.linalg.norm(vector), np.radians(0.05), places=12)
        self.assertEqual(result["eccentricity_vector_xy"].shape, (2,))
        self.assertTrue(np.all(np.isfinite(result["eccentricity_vector_xy"])))

    def test_invalid_limits_and_non_finite_inputs_are_rejected(self):
        with self.assertRaises(StationKeepingError):
            self._analyze([12.0, 12.0], station_box_half_width_deg=-0.1)
        with self.assertRaises(StationKeepingError):
            self._analyze([12.0, np.nan])
        with self.assertRaises(StationKeepingError):
            self._analyze(
                [12.0, 12.0],
                annual_delta_v_budget_m_s=1.0,
                annual_delta_v_used_m_s=-0.1,
            )


if __name__ == "__main__":
    unittest.main()
