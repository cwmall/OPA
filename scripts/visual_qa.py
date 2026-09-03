"""Capture the public UI matrix for manual clipping and overlap review."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def _capture(app, window, destination: Path) -> None:
    app.processEvents()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not window.grab().save(str(destination)):
        raise RuntimeError(f"Could not save visual QA image: {destination.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.expanduser().resolve()

    with tempfile.TemporaryDirectory(prefix="opa-visual-qa-") as temporary:
        config_path = Path(temporary) / "config.json"
        app = QApplication.instance() or QApplication([])
        window = MainWindow(application_config_path=config_path)
        window.resize(1366, 768)
        window.show()
        app.processEvents()

        window.apply_language("en")
        window.apply_interface_theme("normal")
        window.module_tabs.setCurrentIndex(0)
        window.tabs.setCurrentIndex(0)
        _capture(app, window, output / "1366_normal_en_propagation.png")

        window.module_tabs.setCurrentIndex(1)
        _capture(app, window, output / "1366_normal_en_eclipse.png")

        window.module_tabs.setCurrentIndex(0)
        window.apply_language("az")
        window.settings_overlay.show_overlay()
        window.settings_overlay._select_page(0)
        _capture(app, window, output / "1366_normal_az_settings.png")
        window.settings_overlay._select_page(1)
        _capture(app, window, output / "1366_normal_az_admin.png")
        window.settings_overlay.hide()

        window.apply_language("en")
        window.apply_interface_theme("retro")
        window.tabs.setCurrentIndex(0)
        _capture(app, window, output / "1366_retro_en_propagation.png")

        window.apply_language("az")
        window.settings_overlay.show_overlay()
        window.settings_overlay._select_page(1)
        _capture(app, window, output / "1366_retro_az_admin.png")
        window.settings_overlay.hide()

        window.apply_language("en")
        window.apply_interface_theme("normal")
        window.resize(1920, 1080)
        window.module_tabs.setCurrentIndex(0)
        window.tabs.setCurrentIndex(0)
        _capture(app, window, output / "1920_normal_en_propagation.png")

        window.close()
        app.processEvents()

    print(f"VISUAL QA CAPTURE PASSED: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
