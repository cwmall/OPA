"""Parameter-aware chart tooltip tests."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication
from matplotlib import dates as mdates

from gui.main_window import GraphWidget


class GraphTooltipTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.graph = GraphWidget()

    def tearDown(self):
        self.graph.close()

    def test_longitude_uses_axis_parameter_and_unit(self):
        axis = self.graph.ax
        axis.set_xlabel("Elapsed time [days]")
        axis.set_ylabel("Earth-fixed longitude [deg E]")

        self.assertEqual(
            GraphWidget._format_pointer_axis_value(axis, "x", 6.82242),
            "Elapsed time: 6.82242 days",
        )
        self.assertEqual(
            GraphWidget._format_pointer_axis_value(axis, "y", 12.11429),
            "Earth-fixed longitude: 12.11429 °E",
        )

    def test_shared_subplot_uses_time_and_title_parameter(self):
        self.graph.figure.clear()
        axes = self.graph.figure.subplots(2, 3, sharex=True).ravel()
        axes[0].set_title("i — Inclination")
        axes[0].set_ylabel("deg")
        axes[3].set_xlabel("Elapsed time [days]")

        self.assertEqual(
            GraphWidget._format_pointer_axis_value(axes[0], "x", 2.5),
            "Elapsed time: 2.5 days",
        )
        self.assertEqual(
            GraphWidget._format_pointer_axis_value(axes[0], "y", 0.042),
            "i — Inclination: 0.042 °",
        )

    def test_utc_axis_displays_timestamp_not_matplotlib_day_number(self):
        axis = self.graph.ax
        axis.set_xlabel("UTC Time")
        timestamp = mdates.datestr2num("2030-08-14T12:00:00Z")

        self.assertEqual(
            GraphWidget._format_pointer_axis_value(axis, "x", timestamp),
            "UTC Time: 2030-08-14 12:00:00 UTC",
        )

    def test_live_relative_time_keeps_zero_origin_meaning(self):
        axis = self.graph.ax
        axis.set_xlabel("Time (minutes, 0 = now)")

        self.assertEqual(
            GraphWidget._format_pointer_axis_value(axis, "x", -12.5),
            "Time from now: -12.5 minutes",
        )


if __name__ == "__main__":
    unittest.main()
