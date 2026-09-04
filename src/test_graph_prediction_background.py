"""Regression checks for responsive Perturbation prediction work."""

from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from graph_prediction import compute_perturbation_prediction
from gui.main_window import MainWindow
from perturbation_analysis import PERTURBATION_PARAMETERS


class GraphPredictionComputationTests(unittest.TestCase):

    def test_prediction_keeps_four_pass_sampling_and_source_values(self):
        epoch = datetime(2030, 1, 1, tzinfo=timezone.utc)
        calls = []

        def fake_propagate(**kwargs):
            calls.append(kwargs)
            relaxed = kwargs["rtol"] > 1.0e-11
            delta = 0.25 if relaxed else 0.0
            if kwargs["duration_seconds"] < 0:
                times = np.asarray([0.0, -60.0])
                states = np.asarray(
                    [[1.0 + delta, 0, 0, 0, 1, 0], [2.0 + delta, 0, 0, 0, 1, 0]]
                )
            else:
                times = np.asarray([0.0, 60.0])
                states = np.asarray(
                    [[1.0 + delta, 0, 0, 0, 1, 0], [3.0 + delta, 0, 0, 0, 1, 0]]
                )
            return times, states

        def components(acceleration, _state):
            return {
                name: float(np.asarray(acceleration)[0])
                for name in PERTURBATION_PARAMETERS
            }

        with (
            patch("graph_prediction.propagate_trajectory", fake_propagate),
            patch("graph_prediction.utc_to_et", return_value=0.0),
            patch("graph_prediction.get_moon_position", return_value=np.ones(3)),
            patch("graph_prediction.get_sun_position", return_value=np.ones(3)),
            patch(
                "graph_prediction.moon_perturbation",
                side_effect=lambda state, _body: np.asarray([state[0], 0.0, 0.0]),
            ),
            patch(
                "graph_prediction.sun_perturbation",
                return_value=np.asarray([2.0, 0.0, 0.0]),
            ),
            patch(
                "graph_prediction.solar_radiation_pressure",
                return_value=np.asarray([3.0, 0.0, 0.0]),
            ),
            patch("graph_prediction.acceleration_components", components),
        ):
            result = compute_perturbation_prediction(
                initial_state=np.asarray([1.0, 0, 0, 0, 1, 0]),
                epoch=epoch,
                duration_seconds=60.0,
                output_step=60.0,
                requested_sources=("Moon", "Sun β", "SRP", "Combined"),
                propagate_moon=True,
                propagate_sun=True,
                propagate_srp=True,
                srp_coefficient=1.0,
                srp_area_m2=42.0,
                srp_mass_kg=900.0,
                numerical_settings={"rtol": 1.0e-12, "atol": 1.0e-14, "max_step": 60.0},
            )

        self.assertEqual(len(calls), 4)
        self.assertTrue(
            all(
                call["srp_area_m2"] == 42.0
                and call["srp_mass_kg"] == 900.0
                for call in calls
            )
        )
        self.assertEqual(result["point_count"], 3)
        self.assertEqual(set(result["values"]), {"Moon", "Sun β", "SRP", "Combined"})
        # The centre prediction sample uses the exact selected live state:
        # Moon 1 + Sun 2 + SRP 3 = Combined 6 at t=0.
        self.assertEqual(result["values"]["Combined"]["Magnitude"][1], 6.0)
        np.testing.assert_allclose(
            result["uncertainty"]["Moon"]["Magnitude"], 0.25
        )


class GraphPredictionThreadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_main_event_loop_remains_responsive_during_prediction(self):
        temporary = tempfile.TemporaryDirectory(prefix="opa-graph-thread-")
        window = MainWindow(
            application_config_path=Path(temporary.name) / "config.json"
        )
        window.tabs.setCurrentIndex(window.graph_tab_index)
        event_seen = []
        ui_released_worker = threading.Event()
        epoch = datetime(2030, 1, 1, tzinfo=timezone.utc)
        selected_state = np.arange(6, dtype=float)
        worker_inputs = {}

        def slow_prediction(**kwargs):
            worker_inputs.update(kwargs)
            if not ui_released_worker.wait(1.5):
                raise RuntimeError("Qt event loop did not release background work")
            empty = {
                source: {
                    name: np.asarray([1.0]) for name in PERTURBATION_PARAMETERS
                }
                for source in ("Moon", "Sun β", "SRP", "Combined")
            }
            return {
                "epoch": epoch,
                "times": [epoch],
                "values": empty,
                "uncertainty": empty,
                "point_count": 1,
            }

        try:
            with (
                patch("gui.main_window.compute_perturbation_prediction", slow_prediction),
                patch.object(
                    window,
                    "active_spacecraft_state",
                    return_value=(selected_state, epoch),
                ),
                patch(
                    "gui.main_window.resolved_solar_pressure_coefficient",
                    return_value=(1.0, "TEST"),
                ),
            ):
                window.run_graph_prediction()
                def release_from_ui_thread():
                    event_seen.append(True)
                    ui_released_worker.set()

                QTimer.singleShot(20, release_from_ui_thread)
                deadline = time.monotonic() + 2.0
                while not event_seen and time.monotonic() < deadline:
                    self.application.processEvents()
                    time.sleep(0.005)
                self.assertTrue(event_seen)

                while (
                    window.graph_prediction_thread is not None
                    and time.monotonic() < deadline
                ):
                    self.application.processEvents()
                    time.sleep(0.005)
                self.assertIsNone(window.graph_prediction_thread)
                self.assertEqual(window.predict_graph_button.text(), "PREDICT PAST + FUTURE")
                np.testing.assert_array_equal(
                    worker_inputs["initial_state"], selected_state
                )
                self.assertEqual(worker_inputs["epoch"], epoch)
                self.assertGreaterEqual(len(window.history_time), 1)
                self.assertEqual(
                    len(window._graph_prediction_lines["Combined"].get_ydata()),
                    1,
                )
                self.assertEqual(window.graph.ax.get_legend()._ncols, 2)
        finally:
            window.close()
            self.application.processEvents()
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
