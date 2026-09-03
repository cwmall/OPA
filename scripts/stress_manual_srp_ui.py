"""Exercise manual SRP editors while normal desktop timers remain active."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from gui.main_window import MainWindow  # noqa: E402
from gui.runtime_diagnostics import install_runtime_diagnostics  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-ms", type=int, default=65_000)
    parser.add_argument("--edits", type=int, default=600)
    arguments = parser.parse_args()

    install_runtime_diagnostics(ROOT)
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    window.prop_srp_model.setCurrentIndex(
        window.prop_srp_model.findData("manual")
    )
    window.prop_manual_srp_separate_panels.setChecked(True)
    window.reference_srp_source_mode.setCurrentIndex(
        window.reference_srp_source_mode.findData("manual")
    )
    window.reference_manual_srp_separate_panels.setChecked(True)

    controls = (
        window.prop_manual_srp_coefficient,
        window.prop_manual_srp_panel_coefficient,
        window.prop_manual_srp_body_coefficient,
        window.reference_manual_srp_coefficient,
        window.reference_manual_srp_panel_coefficient,
        window.reference_manual_srp_body_coefficient,
    )
    completed = {"count": 0}
    editor = QTimer()

    def edit_value():
        index = completed["count"] % len(controls)
        controls[index].setValue(
            0.75 + (completed["count"] % 500) / 1000.0
        )
        completed["count"] += 1
        if completed["count"] >= arguments.edits:
            editor.stop()

    editor.timeout.connect(edit_value)
    editor.start(10)

    def finish():
        print(f"stress_edits={completed['count']}")
        print(f"window_visible={window.isVisible()}")
        print(
            "prop_panel_cp="
            f"{window.prop_manual_srp_panel_coefficient.value():.9f}"
        )
        print(
            "reference_panel_cp="
            f"{window.reference_manual_srp_panel_coefficient.value():.9f}"
        )
        application.quit()

    QTimer.singleShot(max(1, arguments.duration_ms), finish)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
