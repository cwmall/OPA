"""Settings UI coverage for the IERS EOP switch."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from earth_orientation import is_eop_enabled, set_eop_enabled
from gui.main_window import MainWindow, normalise_application_config


class EOPSettingsTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        set_eop_enabled(False)
        with patch(
            "gui.main_window.load_application_config",
            return_value=normalise_application_config(),
        ):
            self.window = MainWindow()

    def tearDown(self):
        self.window.close()
        set_eop_enabled(False)

    def test_settings_checkbox_controls_application_eop_mode(self):
        self.assertFalse(self.window.eop_enabled_checkbox.isChecked())
        self.assertFalse(is_eop_enabled())

        with patch.object(self.window, "update_data"):
            self.window.eop_enabled_checkbox.setChecked(True)
            self.assertTrue(is_eop_enabled())
            self.assertIn("EOP ACTIVE", self.window.eop_status_label.text())

            self.window.eop_enabled_checkbox.setChecked(False)
            self.assertFalse(is_eop_enabled())
            self.assertIn("EOP OFF", self.window.eop_status_label.text())


if __name__ == "__main__":
    unittest.main()
