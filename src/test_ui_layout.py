"""Focused responsive-layout and localization regression checks."""

import os
import tempfile
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication, QScrollArea

from gui.main_window import (
    APP_ICON_PATH,
    APP_LOGO_PATH,
    HERO_BACKGROUND_DARK_PATH,
    MainWindow,
)


class ResponsiveLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="opa-layout-test-")
        self.window = MainWindow(
            application_config_path=Path(self.temporary.name) / "config.json"
        )
        self.window.show()
        self.application.processEvents()

    def tearDown(self):
        self.window.close()
        self.application.processEvents()
        self.temporary.cleanup()

    @staticmethod
    def _contained(child, ancestor):
        top_left = child.mapTo(ancestor, QPoint(0, 0))
        return ancestor.rect().contains(top_left) and ancestor.rect().contains(
            top_left + QPoint(max(0, child.width() - 1), max(0, child.height() - 1))
        )

    def test_major_shell_remains_contained_at_supported_sizes(self):
        for width, height in ((640, 360), (1366, 768), (1920, 1080)):
            with self.subTest(size=(width, height)):
                self.window.resize(width, height)
                self.application.processEvents()
                self.assertTrue(self._contained(self.window.module_tabs, self.window))
                self.assertGreater(self.window.module_tabs.width(), 0)
                self.assertGreater(self.window.module_tabs.height(), 0)

    def test_live_telemetry_uses_a_responsive_scroll_surface(self):
        self.window.resize(1366, 768)
        self.window.module_tabs.setCurrentIndex(0)
        self.window.tabs.setCurrentIndex(0)
        self.application.processEvents()
        self.assertTrue(self.window.monitor_page_scroll.widgetResizable())
        self.assertGreater(
            self.window.live_perturbation_box.sizeHint().height(),
            0,
        )
        self.assertGreaterEqual(
            self.window.monitor_page_scroll.widget().minimumSizeHint().height(),
            self.window.monitor_page_scroll.viewport().height(),
        )

    def test_settings_pages_are_scrollable_and_panel_is_not_fixed(self):
        self.window.resize(640, 360)
        self.window.settings_overlay.show_overlay()
        self.window.settings_overlay._select_page(1)
        self.application.processEvents()
        panel = self.window.settings_overlay.panel
        self.assertTrue(self._contained(panel, self.window.settings_overlay))
        self.assertLessEqual(panel.width(), self.window.settings_overlay.width())
        self.assertLessEqual(panel.height(), self.window.settings_overlay.height())
        self.assertTrue(
            all(page.widgetResizable() for page in panel.findChildren(QScrollArea))
        )
        # The panel may temporarily fill all available space, but the
        # implementation must not use Qt's fixed-size flag.
        self.window.resize(1366, 768)
        self.window.settings_overlay.show_overlay()
        self.application.processEvents()
        self.assertNotEqual(panel.minimumSize(), panel.maximumSize())

    def test_normal_retro_and_azerbaijani_admin_labels_switch_live(self):
        for selected_theme in ("normal", "retro"):
            self.window.apply_interface_theme(selected_theme)
            self.assertEqual(self.window.interface_theme, selected_theme)
        self.window.apply_language("az")
        self.window.settings_overlay.show_overlay()
        self.application.processEvents()
        self.assertEqual(
            self.window.settings_overlay.admin_nav_button.text(), "ADMİN GİRİŞİ"
        )
        self.window.apply_language("en")
        self.assertEqual(
            self.window.settings_overlay.admin_nav_button.text(), "ADMIN ACCESS"
        )

    def test_established_opa_brand_assets_load_in_the_header(self):
        for asset_path in (APP_ICON_PATH, APP_LOGO_PATH, HERO_BACKGROUND_DARK_PATH):
            with self.subTest(asset=Path(asset_path).name):
                self.assertTrue(Path(asset_path).is_file())
        self.assertFalse(self.window.hero_logo_pixmap.isNull())
        self.assertFalse(self.window.hero_card._background.isNull())


if __name__ == "__main__":
    unittest.main()
