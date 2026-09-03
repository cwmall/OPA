"""Regression coverage for the current two-module application shell."""

import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from app_version import APP_VERSION
from gui.main_window import MainWindow


class ModuleNavigationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="opa-nav-test-")
        self.window = MainWindow(
            application_config_path=Path(self.temporary.name) / "config.json"
        )
        self.window.timer.stop()
        self.window.localization_refresh_timer.stop()

    def tearDown(self):
        self.window.close()
        self.application.processEvents()
        self.temporary.cleanup()

    def test_top_level_modules_and_legacy_page_mapping(self):
        self.assertEqual(
            [
                self.window.module_tabs.tabBar().tabData(index)
                for index in range(self.window.module_tabs.count())
            ],
            ["PROPAGATION", "ECLIPSE"],
        )
        inner_labels = [
            self.window.tabs.tabText(index)
            for index in range(self.window.tabs.count())
        ]
        self.assertEqual(inner_labels[:3], [
            "LIVE TELEMETRY", "PERTURBATION", "ORBITAL VIEW"
        ])
        self.assertIn(inner_labels[3], {"SETTINGS", "SYSTEM / VALIDATION"})
        self.assertEqual(inner_labels[4:], [
            "REFERENCE LAB", "PROPAGATION", "GEO OPERATIONS"
        ])
        self.assertIs(
            self.window.module_tabs.widget(self.window.eclipse_module_index),
            self.window.eclipse_page,
        )

    def test_navigation_routes_nested_and_top_level_pages(self):
        self.assertTrue(self.window.select_tab_by_label("REFERENCE LAB"))
        self.assertEqual(
            self.window.module_tabs.currentIndex(),
            self.window.propagation_module_index,
        )
        self.assertEqual(
            self.window.tabs.tabText(self.window.tabs.currentIndex()),
            "REFERENCE LAB",
        )

        self.assertTrue(self.window.select_tab_by_label("ECLIPSE"))
        self.assertEqual(
            self.window.module_tabs.currentIndex(),
            self.window.eclipse_module_index,
        )
        self.assertFalse(self.window.select_tab_by_label("ORBIT DETERMINATION"))
        self.assertFalse(self.window.select_module_by_label("ORBIT DETERMINATION"))

        self.window.open_integrity_page()
        self.assertEqual(
            self.window.module_tabs.currentIndex(),
            self.window.propagation_module_index,
        )
        self.assertEqual(
            self.window.tabs.currentIndex(),
            self.window.integrity_tab_index,
        )

    def test_od_workspace_is_not_exposed_or_created(self):
        self.assertEqual(self.window.orbit_determination_module_index, -1)
        self.assertFalse(hasattr(self.window, "orbit_determination_page"))
        self.assertFalse(hasattr(self.window, "od_tabs"))
        self.window.apply_language("az")
        self.assertFalse(self.window.select_tab_by_label("ORBİT TƏYİNİ"))
        self.assertTrue(self.window.select_tab_by_label("ECLIPSE"))

    def test_theme_switch_keeps_module_and_version_state(self):
        self.window.select_module_by_label("ECLIPSE")
        self.window.apply_interface_theme("retro")
        self.window.apply_interface_theme("normal")
        self.assertEqual(
            self.window.module_tabs.currentIndex(),
            self.window.eclipse_module_index,
        )
        self.assertEqual(self.window.mission_version_label.text(), f"v{APP_VERSION}")


if __name__ == "__main__":
    unittest.main()
