"""Theme palette and model-provenance panel tests."""

import os
from pathlib import Path
import re
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from gui import theme
from gui.main_window import MainWindow


class ThemeTests(unittest.TestCase):

    def test_every_colour_is_a_valid_hex_triplet(self):
        for name in dir(theme):
            if name.startswith("_"):
                continue
            value = getattr(theme, name)
            if isinstance(value, str) and value.startswith("#"):
                self.assertRegex(
                    value,
                    r"^#[0-9A-Fa-f]{6}$",
                    msg=f"{name} is not a six-digit hex colour",
                )

    def test_conditioning_colours_cover_every_label(self):
        for label in ("SHARP", "SOFT", "GRAZING", "UNKNOWN"):
            self.assertIn(label, theme.CONDITIONING_COLOURS)
            self.assertTrue(
                theme.conditioning_colour(label).startswith("#")
            )
        # An unknown label must still return something drawable.
        self.assertEqual(
            theme.conditioning_colour("nonsense"),
            theme.TEXT_FAINT,
        )

    def test_note_style_can_carry_a_size(self):
        self.assertEqual(
            theme.note_style(theme.ACCENT_INFO, size_px=10),
            f"color: {theme.ACCENT_INFO}; font-size: 10px;",
        )

    def test_normal_and_retro_palettes_are_independent(self):
        self.assertEqual(set(theme.PALETTES), {"normal", "retro"})
        self.assertNotEqual(
            theme.PALETTES["normal"]["BACKGROUND"],
            theme.PALETTES["retro"]["BACKGROUND"],
        )
        original = theme.CURRENT_THEME
        try:
            theme.set_theme("retro")
            self.assertFalse(theme.is_normal())
            self.assertTrue(theme.is_retro())
            self.assertEqual(theme.BACKGROUND, "#ECE9D8")
            theme.set_theme("normal")
            self.assertTrue(theme.is_normal())
            self.assertFalse(theme.is_retro())
        finally:
            theme.set_theme(original)

    def test_retro_styles_every_desktop_control_family(self):
        original = theme.CURRENT_THEME
        try:
            theme.set_theme("retro")
            asset_root = Path(__file__).resolve().parents[1] / "assets"
            stylesheet = theme.application_stylesheet(
                str(asset_root / "dropdown_arrow.svg")
            )
            for selector in (
                "QMenuBar",
                "QMenu",
                "QToolBar#retroToolBar",
                "QToolButton",
                "QPushButton",
                "QLineEdit",
                "QComboBox::drop-down",
                "QCheckBox::indicator:checked",
                "QRadioButton::indicator:checked",
                "QTabBar::tab:selected",
                "QGroupBox::title",
                "QTableWidget",
                "QTreeView",
                "QScrollBar:vertical",
                "QScrollBar:horizontal",
                "QProgressBar::chunk",
                "QSlider::handle:horizontal",
                "QSplitter::handle",
                "QCalendarWidget",
                "QToolTip",
                "QStatusBar",
            ):
                self.assertIn(selector, stylesheet)
            for asset in (
                "retro_combo_arrow.svg",
                "retro_checkbox_checked.svg",
                "retro_radio_checked.svg",
                "retro_arrow_up.svg",
                "retro_arrow_down.svg",
                "retro_arrow_left.svg",
                "retro_arrow_right.svg",
            ):
                self.assertTrue((asset_root / asset).is_file())
        finally:
            theme.set_theme(original)


class ModelProvenanceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="opa-theme-test-")
        self.window = MainWindow(
            application_config_path=Path(self.temporary.name) / "config.json"
        )

    def tearDown(self):
        self.window.close()
        self.temporary.cleanup()

    def test_panel_states_values_read_from_the_running_model(self):
        import constants

        rows = self.window.model_provenance_rows()
        values = {quantity: value for _group, quantity, value, _source in rows}

        self.assertIn(str(constants.MU_EARTH), values["Earth GM"])
        self.assertIn(str(constants.R_EARTH), values["Earth equatorial radius"])
        self.assertIn(
            str(constants.EARTH_GRAVITY_DEGREE),
            values["Spherical-harmonic truncation"],
        )
        self.assertEqual(values["Empirical calibration"], "disabled")

    def test_panel_names_what_is_deliberately_not_modelled(self):
        groups = {group for group, *_rest in self.window.model_provenance_rows()}
        self.assertIn("NOT MODELLED", groups)

    def test_panel_follows_the_eclipse_geometry_switches(self):
        def shadow_row():
            for _group, quantity, value, _source in (
                self.window.model_provenance_rows()
            ):
                if quantity == "Earth shadow silhouette":
                    return value
            return None

        self.assertIn("sphere", shadow_row())
        self.window.eclipse_oblate_earth.setChecked(True)
        self.assertIn("oblate", shadow_row())

    def test_eclipse_page_carries_no_literal_colours(self):
        """The Eclipse page must take its colours from the theme module."""

        from pathlib import Path

        source = Path(__file__).resolve().parent / "gui" / "main_window.py"
        text = source.read_text(encoding="utf-8")
        start = text.index("    def create_eclipse_page(self):")
        end = text.index("    def create_propagation_page(self):")
        self.assertEqual(
            re.findall(r"#[0-9A-Fa-f]{6}", text[start:end]),
            [],
        )


if __name__ == "__main__":
    unittest.main()
