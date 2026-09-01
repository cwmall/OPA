"""Generate deterministic Mission Control GEO Operations visual-QA captures."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt6.QtWidgets import QApplication


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from geo_stationkeeping import EARTH_SIDEREAL_RATE_RAD_S  # noqa: E402
from gui.main_window import MainWindow  # noqa: E402
from orbital_elements import keplerian_to_cartesian  # noqa: E402
from reference_comparison import earth_fixed_longitude_degrees  # noqa: E402


def synthetic_geo_arc():
    epoch = datetime(2026, 8, 21, 6, 0, tzinfo=timezone.utc)
    times = np.arange(0.0, 7.0 * 86400.0 + 1.0, 3.0 * 3600.0)
    inertial_rate_deg_s = np.degrees(EARTH_SIDEREAL_RATE_RAD_S) + 0.03 / 86400.0
    states = np.vstack(
        [
            keplerian_to_cartesian(
                {
                    "a_km": 42164.35,
                    "e": 0.00028 + 0.000018 * np.sin(2.0 * np.pi * time / (7.0 * 86400.0)),
                    "i_deg": 0.045 + 0.002 * np.sin(2.0 * np.pi * time / (14.0 * 86400.0)),
                    "raan_deg": 24.0,
                    "argp_deg": 18.0,
                    "nu_deg": (42.0 + inertial_rate_deg_s * time) % 360.0,
                }
            )
            for time in times
        ]
    )
    return epoch, times, states


def capture(
    window, application, output, theme_name, width, height, *, scroll_to_bottom=False
):
    window.apply_interface_theme(theme_name)
    window.resize(width, height)
    window.show()
    application.processEvents()
    scroll_bar = window.geo_operations_scroll.verticalScrollBar()
    scroll_bar.setValue(scroll_bar.maximum() if scroll_to_bottom else 0)
    application.processEvents()
    image = window.grab()
    if not image.save(str(output)):
        raise RuntimeError(f"Could not save screenshot: {output}")


def main():
    output_directory = ROOT / "docs" / "screenshots"
    output_directory.mkdir(parents=True, exist_ok=True)
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.timer.stop()
    epoch, times, states = synthetic_geo_arc()
    longitudes = earth_fixed_longitude_degrees(states, epoch, times)
    window.last_prop_epoch = epoch
    window.last_prop_times = times
    window.last_prop_states = states
    window.geo_target_longitude.setText(f"{longitudes[0]:.10f}")
    window.geo_station_box.setText("0.1")
    window.geo_inc_warning.setText("0.08")
    window.geo_inc_limit.setText("0.10")
    window.geo_ecc_warning.setText("0.0007")
    window.geo_ecc_limit.setText("0.001")
    window.geo_annual_budget.setText("50")
    window.geo_annual_used.setText("12")
    if not window.run_geo_stationkeeping_analysis():
        raise RuntimeError(window.geo_output.toPlainText())
    window.tabs.setCurrentIndex(window.geo_tab_index)

    for theme_name in ("normal", "retro"):
        for width, height in ((1366, 768), (1920, 1080)):
            destination = output_directory / (
                f"geo_operations_{theme_name}_{width}x{height}.png"
            )
            capture(
                window,
                application,
                destination,
                theme_name,
                width,
                height,
            )
            print(destination)
            bottom_destination = output_directory / (
                f"geo_operations_{theme_name}_{width}x{height}_bottom.png"
            )
            capture(
                window,
                application,
                bottom_destination,
                theme_name,
                width,
                height,
                scroll_to_bottom=True,
            )
            print(bottom_destination)
    window.close()


if __name__ == "__main__":
    main()
