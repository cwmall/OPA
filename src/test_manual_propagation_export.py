"""Regression coverage for the user-facing manual Propagator CSV."""

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


class ManualPropagationExportTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = TemporaryDirectory(prefix="opa-export-test-")
        self.window = MainWindow(
            application_config_path=Path(self.temporary.name) / "config.json"
        )

    def tearDown(self):
        self.window.close()
        self.temporary.cleanup()

    def test_first_csv_row_preserves_manually_entered_j2000_state(self):
        epoch = datetime(
            2030,
            1,
            1,
            4,
            0,
            0,
            125000,
            tzinfo=timezone.utc,
        )
        initial_state = np.array(
            [
                42164.123456789,
                120.987654321,
                -45.125,
                -0.008765432109,
                3.074654321098,
                0.000223456789,
            ],
            dtype=float,
        )
        self.window.last_prop_epoch = epoch
        self.window.last_prop_times = np.array([0.0, 60.0], dtype=float)
        self.window.last_prop_states = np.vstack(
            (initial_state, initial_state + 1.0)
        )
        self.window.last_prop_include_j2 = True
        self.window.last_prop_include_moon = True
        self.window.last_prop_include_sun = True
        self.window.last_prop_include_srp = False
        self.window.last_prop_run_number = 1

        with TemporaryDirectory() as directory:
            path = Path(directory) / "propagation.csv"
            with patch(
                "gui.main_window.QFileDialog.getSaveFileName",
                return_value=(str(path), "CSV Files (*.csv)"),
            ):
                self.window.save_propagation_csv()
            with path.open(newline="", encoding="utf-8-sig") as handle:
                rows = list(csv.reader(handle))

        self.assertEqual(rows[0][0:2], ["01/01/2030", "04:00:00.125"])
        self.assertEqual(
            rows[0][2:],
            [
                f"{initial_state[0]:.9f}",
                f"{initial_state[1]:.9f}",
                f"{initial_state[2]:.9f}",
                f"{initial_state[3]:.12f}",
                f"{initial_state[4]:.12f}",
                f"{initial_state[5]:.12f}",
            ],
        )

    def test_manual_kepler_history_keeps_j2000_initial_state(self):
        epoch = datetime(2030, 1, 1, 4, 0, tzinfo=timezone.utc)
        states = np.array(
            [
                [42164.0, 10.0, 1.0, 0.0, 3.074, 0.001],
                [42163.0, 194.0, 1.1, -0.014, 3.073, 0.001],
            ],
            dtype=float,
        )
        self.window.propagation_kepler_widget.update_trajectory(
            states,
            np.array([0.0, 60.0]),
            epoch,
            frame_label="J2000",
            rotate_to_tod_fk5=False,
        )

        np.testing.assert_array_equal(
            self.window.propagation_kepler_widget._trajectory_states[0],
            states[0],
        )


if __name__ == "__main__":
    unittest.main()
