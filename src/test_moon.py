"""Deterministic SPICE Moon-position smoke test for the public kernels."""

from datetime import datetime, timezone
import unittest

import numpy as np

from moon import get_moon_position
from time_utils import utc_to_et


class MoonEphemerisSmokeTests(unittest.TestCase):
    def test_fictional_demo_epoch_returns_a_finite_lunar_position(self):
        epoch = datetime(2030, 1, 1, tzinfo=timezone.utc)
        position = get_moon_position(utc_to_et(epoch))
        distance = float(np.linalg.norm(position))

        self.assertEqual(position.shape, (3,))
        self.assertTrue(np.all(np.isfinite(position)))
        self.assertGreater(distance, 300_000.0)
        self.assertLess(distance, 450_000.0)


if __name__ == "__main__":
    unittest.main()
