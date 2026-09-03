"""Offscreen public-mode launch, navigation, localization, and theme smoke test."""

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="opa-public-smoke-") as temporary:
        os.environ["OPA_CONFIG_PATH"] = str(Path(temporary) / "config.json")
        app = QApplication.instance() or QApplication([])
        window = MainWindow(application_config_path=Path(temporary) / "config.json")
        window.resize(1366, 768)
        window.show()
        app.processEvents()
        assert window.admin_session.unlocked is False
        assert [
            window.module_tabs.tabText(i)
            for i in range(window.module_tabs.count())
        ] == ["PROPAGATION", "ECLIPSE"]
        for module_index in range(window.module_tabs.count()):
            window.module_tabs.setCurrentIndex(module_index)
            app.processEvents()
        window.module_tabs.setCurrentIndex(0)
        for tab_index in range(window.tabs.count()):
            window.tabs.setCurrentIndex(tab_index)
            app.processEvents()
        for language in ("en", "az"):
            window.apply_language(language)
            for selected_theme in ("normal", "retro"):
                window.apply_interface_theme(selected_theme)
                app.processEvents()
        window.apply_language("en")
        window.apply_interface_theme("normal")
        window.module_tabs.setCurrentIndex(0)
        window.tabs.setCurrentIndex(0)
        app.processEvents()
        if args.screenshot:
            destination = args.screenshot.expanduser().resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not window.grab().save(str(destination)):
                raise RuntimeError("Screenshot could not be saved.")
        window.close()
        app.processEvents()
    print("HEADLESS PUBLIC SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
