"""Tests for shared inertial/RTN perturbation analysis."""

import unittest

import numpy as np

from perturbation_analysis import acceleration_components, rtn_basis


class PerturbationAnalysisTests(unittest.TestCase):

    def test_circular_xy_state_defines_expected_rtn_axes(self):
        state = np.array([2.0, 0.0, 0.0, 0.0, 3.0, 0.0])
        radial, along_track, normal = rtn_basis(state)
        np.testing.assert_allclose(radial, [1.0, 0.0, 0.0])
        np.testing.assert_allclose(along_track, [0.0, 1.0, 0.0])
        np.testing.assert_allclose(normal, [0.0, 0.0, 1.0])

    def test_components_preserve_inertial_and_project_rtn(self):
        state = np.array([2.0, 0.0, 0.0, 0.0, 3.0, 0.0])
        values = acceleration_components([4.0, 5.0, 6.0], state)
        self.assertAlmostEqual(values["Magnitude"], np.sqrt(77.0))
        self.assertEqual(values["ax"], 4.0)
        self.assertEqual(values["ay"], 5.0)
        self.assertEqual(values["az"], 6.0)
        self.assertEqual(values["aR"], 4.0)
        self.assertEqual(values["aT"], 5.0)
        self.assertEqual(values["aN"], 6.0)


if __name__ == "__main__":
    unittest.main()
