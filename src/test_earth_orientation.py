"""Regression tests for optional offline IERS Earth orientation."""

from datetime import datetime, timezone
import unittest

import numpy as np

from earth_gravity import earth_harmonics_egm96
from earth_orientation import (
    EarthOrientationError,
    eop_values_at,
    get_eop_status,
    is_eop_enabled,
    j2000_to_itrs_rotation_from_datetime,
    set_eop_enabled,
    skyfield_time_from_datetime,
)
from time_utils import utc_to_et


class EarthOrientationTests(unittest.TestCase):

    def setUp(self):
        set_eop_enabled(False)
        self.epoch = datetime(2026, 8, 14, 4, 0, tzinfo=timezone.utc)

    def tearDown(self):
        set_eop_enabled(False)

    def test_bundled_iers_series_has_expected_provenance(self):
        status = get_eop_status()

        self.assertTrue(status["available"])
        self.assertFalse(status["enabled"])
        self.assertEqual(status["rows"], 19969)
        self.assertEqual(status["coverage_start_utc"][:10], "1973-01-02")
        self.assertEqual(status["coverage_end_utc"][:10], "2027-09-04")
        self.assertEqual(
            status["sha256"],
            "e3905ff7a74b791744704aa3e900a2161e96db97a30095d8fc442b04e4cfe058",
        )

    def test_eop_toggle_changes_itrs_rotation_and_egm96_orientation(self):
        position = np.array([42164.0, 120.0, -45.0], dtype=float)
        et = utc_to_et(self.epoch)
        baseline_rotation = j2000_to_itrs_rotation_from_datetime(self.epoch)
        baseline_acceleration = earth_harmonics_egm96(position, et)

        set_eop_enabled(True)
        eop_rotation = j2000_to_itrs_rotation_from_datetime(self.epoch)
        eop_acceleration = earth_harmonics_egm96(position, et)

        self.assertTrue(is_eop_enabled())
        self.assertGreater(
            float(np.linalg.norm(eop_rotation - baseline_rotation)),
            1.0e-10,
        )
        self.assertGreater(
            float(np.linalg.norm(eop_acceleration - baseline_acceleration)),
            1.0e-16,
        )

    def test_interpolated_eop_values_are_physical(self):
        values = eop_values_at(self.epoch)

        self.assertLess(abs(values["dut1_seconds"]), 1.0)
        self.assertLess(abs(values["xp_arcseconds"]), 1.0)
        self.assertLess(abs(values["yp_arcseconds"]), 1.0)
        self.assertGreater(
            abs(values["xp_arcseconds"]) + abs(values["yp_arcseconds"]),
            0.0,
        )

    def test_eop_mode_refuses_silent_extrapolation(self):
        set_eop_enabled(True)

        with self.assertRaises(EarthOrientationError):
            skyfield_time_from_datetime(
                datetime(2030, 1, 1, tzinfo=timezone.utc)
            )


if __name__ == "__main__":
    unittest.main()
