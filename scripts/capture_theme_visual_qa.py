"""Capture every major Normal/Retro surface for deterministic visual QA."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFileDialog


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from gui import theme  # noqa: E402
from gui.main_window import MainWindow, UtcEpochPickerDialog  # noqa: E402
from gui.profile_dialogs import SatelliteProfileManager  # noqa: E402


def _safe_name(value):
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _save(widget, path, application):
    application.processEvents()
    image = widget.grab()
    if not image.save(str(path)):
        raise RuntimeError(f"Could not save visual-QA capture: {path}")


def main():
    output = ROOT / "outputs" / "theme_visual_qa"
    output.mkdir(parents=True, exist_ok=True)
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.timer.stop()
    window.localization_refresh_timer.stop()
    window.resize(1366, 768)
    window.show()

    for selected_theme in ("normal", "retro"):
        window.apply_interface_theme(selected_theme)
        window.select_module_by_label("PROPAGATION")
        application.processEvents()
        for index in range(window.tabs.count()):
            if not window.tabs.tabBar().isTabVisible(index):
                continue
            window.tabs.setCurrentIndex(index)
            application.processEvents()
            _save(
                window,
                output
                / f"{selected_theme}_{index:02d}_{_safe_name(window.tabs.tabText(index))}.png",
                application,
            )

        for module_label in ("ECLIPSE",):
            window.select_module_by_label(module_label)
            application.processEvents()
            _save(
                window,
                output / f"{selected_theme}_module_{_safe_name(module_label)}.png",
                application,
            )

        window.prop_srp_model.setCurrentIndex(
            window.prop_srp_model.findData("manual")
        )
        window.prop_manual_srp_separate_panels.setChecked(True)
        window.select_tab_by_label("PROPAGATION")
        window.propagation_scroll.ensureWidgetVisible(
            window.prop_manual_srp_box, 20, 20
        )
        _save(
            window,
            output / f"{selected_theme}_manual_srp_propagation.png",
            application,
        )

        window.reference_srp_source_mode.setCurrentIndex(
            window.reference_srp_source_mode.findData("manual")
        )
        window.reference_manual_srp_separate_panels.setChecked(True)
        window.select_tab_by_label("REFERENCE LAB")
        window.reference_scroll.ensureWidgetVisible(
            window.reference_srp_box, 20, 20
        )
        _save(
            window,
            output / f"{selected_theme}_manual_srp_reference.png",
            application,
        )

        window.settings_overlay.show_overlay()
        _save(
            window,
            output / f"{selected_theme}_settings.png",
            application,
        )
        window.settings_overlay._select_page(1)
        _save(
            window,
            output / f"{selected_theme}_credits.png",
            application,
        )
        window.settings_overlay.hide()

        profile_dialog = SatelliteProfileManager(
            window.profile_store,
            window.active_profile_id,
            window,
        )
        profile_dialog.resize(960, 640)
        profile_dialog.show()
        _save(
            profile_dialog,
            output / f"{selected_theme}_profile_manager.png",
            application,
        )
        profile_dialog.close()

        epoch_dialog = UtcEpochPickerDialog(
            datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc),
            window,
        )
        epoch_dialog.show()
        _save(
            epoch_dialog,
            output / f"{selected_theme}_date_time_dialog.png",
            application,
        )
        epoch_dialog.close()

        file_dialog = QFileDialog(window, "Open OPA Project")
        file_dialog.setNameFilter("OPA Project (*.opa)")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setOptions(theme.file_dialog_options())
        file_dialog.resize(820, 520)
        file_dialog.show()
        _save(
            file_dialog,
            output / f"{selected_theme}_file_dialog.png",
            application,
        )
        file_dialog.close()

    window.close()
    print(output)


if __name__ == "__main__":
    main()
