"""Full close/reopen persistence integration test."""

import os
from pathlib import Path
import shutil
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_ROOT = Path(tempfile.mkdtemp(prefix="opa-settings-restart-"))
os.environ["OPA_CONFIG_PATH"] = str(_ROOT / "config.json")
os.environ["OPA_PROFILE_DIR"] = str(_ROOT / "profiles")

from PySide6.QtWidgets import QApplication

from application_config import save_application_config
from gui.main_window import MainWindow


class SettingsRestartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(_ROOT, ignore_errors=True)

    def test_save_configuration_survives_complete_window_recreation(self):
        config_path = _ROOT / "config.json"
        first = MainWindow(application_config_path=config_path)
        first.show()
        self.app.processEvents()
        self.assertTrue(first.activate_profile("synthetic_geo_demo"))
        first.setGeometry(120, 140, 1366, 768)
        first.module_tabs.setCurrentIndex(first.eclipse_module_index)
        propagation_tab_index = next(
            index
            for index in range(first.tabs.count())
            if first.tabs.tabText(index) == "PROPAGATION"
        )
        first.tabs.setCurrentIndex(propagation_tab_index)

        settings = first.settings_overlay
        settings.sync_configuration()
        settings.settings_retro_theme.setChecked(True)
        settings.settings_language.setCurrentIndex(
            settings.settings_language.findData("az")
        )
        settings.settings_rtol.setText("2e-10")
        settings.settings_atol.setText("3e-12")
        settings.settings_max_step.setValue(120)
        settings.settings_eop.setChecked(True)
        first.validation_minutes.setValue(90)
        self.assertTrue(settings.save_configuration() is None)
        first.close()
        self.app.processEvents()

        second = MainWindow(application_config_path=config_path)
        second.show()
        self.app.processEvents()
        try:
            self.assertEqual(second.interface_theme, "retro")
            self.assertEqual(second.language, "az")
            self.assertEqual(second.integrator_rtol.text(), "2e-10")
            self.assertEqual(second.integrator_atol.text(), "3e-12")
            self.assertEqual(second.integrator_max_step.value(), 120)
            self.assertEqual(second.validation_minutes.value(), 90)
            self.assertTrue(second.eop_enabled_checkbox.isChecked())
            self.assertEqual(second.active_profile_id, "synthetic_geo_demo")
            self.assertEqual(
                second.module_tabs.currentIndex(),
                second.eclipse_module_index,
            )
            self.assertEqual(second.tabs.currentIndex(), propagation_tab_index)
            geometry = second.geometry()
            self.assertGreaterEqual(geometry.width(), 1366)
            self.assertGreaterEqual(geometry.height(), 768)
            self.assertFalse(second.admin_session.unlocked)
        finally:
            second.close()
            self.app.processEvents()

    def test_removed_od_module_index_returns_to_propagation(self):
        config_path = _ROOT / "removed_od_config.json"
        save_application_config({"active_module": 2}, config_path)
        window = MainWindow(application_config_path=config_path)
        try:
            self.assertEqual(
                window.module_tabs.currentIndex(),
                window.propagation_module_index,
            )
            self.assertEqual(window.orbit_determination_module_index, -1)
        finally:
            window.close()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
