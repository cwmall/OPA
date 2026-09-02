"""Central Normal/Retro design tokens for the desktop application.

The default Normal theme is the established mission-operations interface.
Retro is an original Windows XP Luna-inspired presentation.  Widgets, plots
and generated style fragments read from this module so changing appearance
never touches propagation or force-model state.
"""

from __future__ import annotations


PALETTES = {
    "normal": {
        "BACKGROUND": "#080B10",
        "BACKGROUND_DEEP": "#05080C",
        "SURFACE": "#101720",
        "SURFACE_ALT": "#141D28",
        "SURFACE_RAISED": "#182431",
        "SURFACE_HOVER": "#1B2A38",
        "INPUT": "#0B1118",
        "BORDER": "#263546",
        "BORDER_STRONG": "#3B5268",
        "TEXT_PRIMARY": "#F3F6FA",
        "TEXT_SECONDARY": "#CBD5E1",
        "TEXT_MUTED": "#91A0B2",
        "TEXT_FAINT": "#667487",
        "TEXT_NOTE": "#9FB1C4",
        "ACCENT": "#3BA7E8",
        "ACCENT_HOVER": "#58B9EE",
        "ACCENT_INFO": "#2EC4D6",
        "ACCENT_SUBTLE": "#102C3B",
        "PRIMARY_BUTTON": "#126A9E",
        "PRIMARY_BUTTON_HOVER": "#1680BB",
        "SELECTION": "#174E70",
        "STATUS_OK": "#38C98A",
        "STATUS_WARNING": "#D99A2B",
        "STATUS_ERROR": "#E45B5B",
        "STATUS_ALERT": "#D86A86",
        "PLOT_FIGURE": "#0B1118",
        "PLOT_BACKGROUND": "#0E1824",
        "PLOT_GRID": "#34475B",
        "PLOT_NEUTRAL": "#E8EEF5",
        "OVERLAY": "rgba(1, 5, 9, 208)",
        "STATUS_OK_BG": "#0E2A22",
        "STATUS_OK_BORDER": "#286650",
        "PASTEL_BLUE": "#141D28",
        "PASTEL_SAGE": "#141D28",
        "PASTEL_BLUSH": "#141D28",
        "PASTEL_LAVENDER": "#141D28",
        "PASTEL_SAND": "#141D28",
        "TAB_SURFACE": "#05080C",
        "GROUP_TITLE_SURFACE": "#05080C",
        "CONTROL_ACCENT_SURFACE": "#182431",
        "TABLE_HEADER_SURFACE": "#182431",
        "SETTINGS_HEADER_SURFACE": "#141D28",
        "SETTINGS_NAV_SURFACE": "#05080C",
        "SETTINGS_CARD_SURFACE": "#141D28",
        "HERO_META_TEXT": "#91A0B2",
        "HERO_META_FAINT": "#667487",
        "HERO_CONTROL_TEXT": "#CBD5E1",
        "HERO_CONTROL_SURFACE": "transparent",
        "HERO_CONTROL_BORDER": "#3B5268",
        "BEVEL_HIGHLIGHT": "#314458",
        "BEVEL_LIGHT": "#263546",
        "BEVEL_SHADOW": "#101720",
        "BEVEL_DARK": "#05080C",
        "TITLE_BLUE": "#126A9E",
        "TITLE_BLUE_LIGHT": "#1680BB",
        "SELECTION_TEXT": "#FFFFFF",
        "DISABLED_SURFACE": "#0B1118",
        "DISABLED_TEXT": "#667487",
        "TOOLTIP_BG": "#182431",
        "TOOLTIP_TEXT": "#F3F6FA",
        "PROGRESS_GREEN": "#38C98A",
    },
    "retro": {
        "BACKGROUND": "#ECE9D8",
        "BACKGROUND_DEEP": "#D4D0C8",
        "SURFACE": "#ECE9D8",
        "SURFACE_ALT": "#F5F3E7",
        "SURFACE_RAISED": "#F8F7EE",
        "SURFACE_HOVER": "#FFF4CE",
        "INPUT": "#FFFFFF",
        "BORDER": "#ACA899",
        "BORDER_STRONG": "#7F9DB9",
        "TEXT_PRIMARY": "#000000",
        "TEXT_SECONDARY": "#202020",
        "TEXT_MUTED": "#555555",
        "TEXT_FAINT": "#808080",
        "TEXT_NOTE": "#404040",
        "ACCENT": "#0054E3",
        "ACCENT_HOVER": "#316AC5",
        "ACCENT_INFO": "#003399",
        "ACCENT_SUBTLE": "#D6E5F5",
        "PRIMARY_BUTTON": "#ECE9D8",
        "PRIMARY_BUTTON_HOVER": "#FFF4CE",
        "SELECTION": "#316AC5",
        "STATUS_OK": "#008000",
        "STATUS_WARNING": "#9A5A00",
        "STATUS_ERROR": "#C00000",
        "STATUS_ALERT": "#A00050",
        "PLOT_FIGURE": "#ECE9D8",
        "PLOT_BACKGROUND": "#FFFFFF",
        "PLOT_GRID": "#C7C7C7",
        "PLOT_NEUTRAL": "#000000",
        "OVERLAY": "rgba(0, 0, 64, 104)",
        "STATUS_OK_BG": "#E7F4E2",
        "STATUS_OK_BORDER": "#70A35A",
        "PASTEL_BLUE": "#ECE9D8",
        "PASTEL_SAGE": "#ECE9D8",
        "PASTEL_BLUSH": "#ECE9D8",
        "PASTEL_LAVENDER": "#ECE9D8",
        "PASTEL_SAND": "#ECE9D8",
        "TAB_SURFACE": "#D4D0C8",
        "GROUP_TITLE_SURFACE": "#ECE9D8",
        "CONTROL_ACCENT_SURFACE": "#ECE9D8",
        "TABLE_HEADER_SURFACE": "#ECE9D8",
        "SETTINGS_HEADER_SURFACE": "#0054E3",
        "SETTINGS_NAV_SURFACE": "#ECE9D8",
        "SETTINGS_CARD_SURFACE": "#ECE9D8",
        "HERO_META_TEXT": "#FFFFFF",
        "HERO_META_FAINT": "#DCE8FF",
        "HERO_CONTROL_TEXT": "#FFFFFF",
        "HERO_CONTROL_SURFACE": "rgba(255, 255, 255, 30)",
        "HERO_CONTROL_BORDER": "#B9D1FF",
        "BEVEL_HIGHLIGHT": "#FFFFFF",
        "BEVEL_LIGHT": "#F1EFE2",
        "BEVEL_SHADOW": "#808080",
        "BEVEL_DARK": "#404040",
        "TITLE_BLUE": "#0054E3",
        "TITLE_BLUE_LIGHT": "#3C8CF5",
        "SELECTION_TEXT": "#FFFFFF",
        "DISABLED_SURFACE": "#D4D0C8",
        "DISABLED_TEXT": "#808080",
        "TOOLTIP_BG": "#FFFFE1",
        "TOOLTIP_TEXT": "#000000",
        "PROGRESS_GREEN": "#21A121",
    },
}

CURRENT_THEME = "normal"


def set_theme(name):
    """Activate a palette and refresh the public role-based constants."""

    global CURRENT_THEME, CONDITIONING_COLOURS
    selected = str(name or "normal").strip().lower()
    if selected not in PALETTES:
        selected = "normal"
    CURRENT_THEME = selected
    for role, value in PALETTES[selected].items():
        globals()[role] = value

    globals()["FULL_SUN"] = globals()["STATUS_OK"]
    globals()["PENUMBRA"] = globals()["STATUS_WARNING"]
    globals()["UMBRA"] = globals()["STATUS_ERROR"]
    CONDITIONING_COLOURS = {
        "SHARP": globals()["STATUS_OK"],
        "SOFT": globals()["STATUS_WARNING"],
        "GRAZING": globals()["ACCENT_INFO"],
        "UNKNOWN": globals()["TEXT_FAINT"],
    }
    return CURRENT_THEME


def is_normal():
    return CURRENT_THEME == "normal"


def is_retro():
    return CURRENT_THEME == "retro"


def palette(name=None):
    selected = CURRENT_THEME if name is None else str(name).strip().lower()
    return PALETTES.get(selected, PALETTES["normal"])


def conditioning_colour(label):
    """Return the colour for a contact-conditioning label."""

    return CONDITIONING_COLOURS.get(
        str(label or "").strip().upper(),
        TEXT_FAINT,
    )


PLOT_COLOUR_ROLES = {
    "primary": {
        "normal": "#38BDF8",
        "retro": "#003399",
        "aliases": ("#38BDF8", "#0E6FAE", "#4C768A"),
    },
    "blue": {
        "normal": "#60A5FA",
        "retro": "#0054E3",
        "aliases": ("#60A5FA", "#2563EB", "#93C5FD", "#5D78A3"),
    },
    "secondary": {
        "normal": "#22D3EE",
        "retro": "#007C91",
        "aliases": ("#22D3EE", "#2EC4D6", "#087C95", "#ECFEFF"),
    },
    "reference_blue": {
        "normal": "#BAE6FD",
        "retro": "#3D6C8E",
        "aliases": ("#BAE6FD", "#2C6E9A", "#7494A5"),
    },
    "warning": {
        "normal": "#F59E0B",
        "retro": "#9A5A00",
        "aliases": ("#F59E0B", "#D99A2B", "#A96705", "#A06F3B", "#FEF3C7", "#FBBF24", "#FACC15"),
    },
    "reference_amber": {
        "normal": "#FDE68A",
        "retro": "#7A5B18",
        "aliases": ("#FDE68A", "#8A5B05", "#9B7A4A"),
    },
    "purple": {
        "normal": "#A78BFA",
        "retro": "#6A3F8D",
        "aliases": ("#A78BFA", "#6D4CC6", "#76638D", "#EDE9FE"),
    },
    "teal": {
        "normal": "#2DD4BF",
        "retro": "#087F73",
        "aliases": ("#2DD4BF", "#087F73", "#4D837B"),
    },
    "alert": {
        "normal": "#FB7185",
        "retro": "#A00050",
        "aliases": ("#FB7185", "#D86A86", "#A83B60", "#9A5F78", "#FFE4E6"),
    },
    "error": {
        "normal": "#E45B5B",
        "retro": "#C00000",
        "aliases": ("#EF4444", "#E45B5B", "#B63B3B", "#AE5A57"),
    },
    "ok": {
        "normal": "#38C98A",
        "retro": "#008000",
        "aliases": ("#10B981", "#22C55E", "#34D399", "#4ADE80", "#38C98A", "#16835B", "#4E7B63"),
    },
}


def plot_colour(colour):
    """Map established plot-series colours to a contrast-safe theme value."""

    value = str(colour or "").upper()
    for specification in PLOT_COLOUR_ROLES.values():
        if value in specification["aliases"]:
            return specification[CURRENT_THEME]
    return colour


def note_style(colour=None, size_px=None):
    """Return the style used by descriptive, non-primary interface text."""

    selected = colour or TEXT_NOTE
    rule = f"color: {selected};"
    if size_px is not None:
        rule += f" font-size: {int(size_px)}px;"
    return rule


def monospace_readout_style(colour=None):
    """Return the style used by engineering numeric read-outs."""

    selected = colour or ACCENT_INFO
    family = "'Courier New', Consolas" if is_retro() else "'Cascadia Mono', Consolas"
    return (
        f"color: {selected}; font-family: {family}; "
        "font-weight: 600; font-variant-numeric: tabular-nums;"
    )


def status_style(role="info", padding=4):
    colour = {
        "ok": STATUS_OK,
        "warning": STATUS_WARNING,
        "error": STATUS_ERROR,
        "alert": STATUS_ALERT,
        "info": ACCENT_INFO,
        "muted": TEXT_MUTED,
    }.get(str(role).lower(), TEXT_SECONDARY)
    return f"color: {colour}; font-weight: 700; padding: {int(padding)}px;"


def table_style():
    """Local table fragment for widgets that need an explicit stylesheet."""

    if is_retro():
        return f"""
            QTableWidget {{
                background-color: {INPUT}; color: {TEXT_PRIMARY};
                gridline-color: #D6D2C2; border-style: solid; border-width: 1px;
                border-color: {BEVEL_SHADOW} {BEVEL_HIGHLIGHT}
                    {BEVEL_HIGHLIGHT} {BEVEL_SHADOW}; border-radius: 0;
                selection-background-color: {SELECTION};
                selection-color: {SELECTION_TEXT};
            }}
            QTableWidget::item {{ padding: 2px 4px; }}
            QHeaderView::section {{
                background-color: {TABLE_HEADER_SURFACE}; color: {TEXT_PRIMARY};
                border-style: solid; border-width: 1px;
                border-color: {BEVEL_HIGHLIGHT} {BEVEL_SHADOW}
                    {BEVEL_SHADOW} {BEVEL_HIGHLIGHT};
                padding: 3px 5px; font-weight: 400;
            }}
        """
    return f"""
        QTableWidget {{
            background-color: {SURFACE};
            alternate-background-color: {SURFACE_ALT};
            color: {TEXT_SECONDARY};
            gridline-color: {BORDER};
            border: 1px solid {BORDER};
            border-radius: 6px;
        }}
        QTableWidget::item {{ padding: 5px 7px; }}
        QHeaderView::section {{
            background-color: {SURFACE_RAISED};
            color: {ACCENT};
            border: 0;
            border-bottom: 1px solid {BORDER};
            border-right: 1px solid {BORDER};
            padding: 6px;
            font-weight: 700;
        }}
    """


def _normal_application_stylesheet(dropdown_arrow_path=""):
    """Build the established Normal mission-control stylesheet."""

    arrow_url = str(dropdown_arrow_path or "").replace("\\", "/")
    arrow_rule = (
        f'QComboBox::down-arrow {{ image: url("{arrow_url}"); '
        "width: 12px; height: 8px; }}"
        if arrow_url
        else ""
    )
    return f"""
        QMainWindow, QDialog {{
            background-color: {BACKGROUND}; color: {TEXT_PRIMARY};
        }}
        QWidget {{
            background: transparent;
            color: {TEXT_SECONDARY};
            font-family: "Segoe UI Variable", "Segoe UI", Arial;
            font-size: 10pt;
        }}
        QDialog {{ background-color: {BACKGROUND}; }}
        QWidget#commandSurface {{ background: transparent; }}

        QFrame#productCommandBar {{
            background: {SURFACE_ALT};
            border: 1px solid {BORDER};
            border-left: 3px solid {ACCENT};
            border-radius: 7px;
        }}
        QPushButton#projectStatusButton {{
            background: transparent;
            border: none;
            color: {ACCENT_INFO};
            font-size: 8.5pt;
            font-weight: 600;
            padding: 6px 4px;
            text-align: right;
        }}
        QPushButton#projectStatusButton:hover {{
            color: {ACCENT};
            text-decoration: underline;
        }}

        QFrame#heroCard {{
            background: {SURFACE};
            border: 1px solid {BORDER_STRONG};
            border-top: 2px solid {ACCENT};
            border-radius: 8px;
        }}
        QLabel#missionEyebrow {{
            color: {ACCENT}; font-size: 8pt; font-weight: 700;
            letter-spacing: 1.8px;
        }}
        QLabel#mainTitle {{
            color: {TEXT_PRIMARY}; font-size: 24px; font-weight: 700;
            letter-spacing: 1.5px;
        }}
        QLabel#mainSubtitle {{
            color: {TEXT_MUTED}; font-size: 9pt; letter-spacing: 0.3px;
        }}
        QFrame#missionDivider {{
            background: {BORDER}; border: none; min-width: 1px; max-width: 1px;
        }}
        QLabel#heroStatus {{
            color: {STATUS_OK}; background: {STATUS_OK_BG};
            border: 1px solid {STATUS_OK_BORDER}; border-radius: 9px;
            padding: 4px 10px; font-size: 8pt; font-weight: 700;
            letter-spacing: 0.8px;
        }}
        QLabel#heroStatus[state="error"] {{
            color: {STATUS_ERROR}; background: {SURFACE_ALT};
            border-color: {STATUS_ERROR};
        }}
        QLabel#heroModel, QLabel#heroUtc {{
            color: {HERO_META_TEXT}; font-family: "Cascadia Mono", Consolas;
            font-size: 8pt; letter-spacing: 0.25px;
        }}
        QLabel#heroVersion {{
            color: {HERO_META_FAINT}; font-family: "Cascadia Mono", Consolas;
            font-size: 7pt; letter-spacing: 0.5px;
        }}

        QFrame#metricCard {{
            background: {PASTEL_BLUE}; border: 1px solid {BORDER};
            border-left: 3px solid {ACCENT}; border-radius: 7px;
        }}
        QFrame#metricCard:hover {{
            background: {SURFACE_HOVER}; border-color: {BORDER_STRONG};
            border-left-color: {ACCENT_HOVER};
        }}
        QLabel#metricCaption {{
            color: {TEXT_MUTED}; font-size: 8pt; font-weight: 700;
            letter-spacing: 1px;
        }}
        QLabel#metricValue {{
            color: {TEXT_PRIMARY}; font-family: "Cascadia Mono", Consolas;
            font-size: 18pt; font-weight: 700;
        }}
        QLabel#geoMetricValue {{
            color: {TEXT_PRIMARY}; font-family: "Cascadia Mono", Consolas;
            font-size: 11.5pt; font-weight: 650;
        }}
        QLabel#metricDetail {{ color: {ACCENT_INFO}; font-size: 8.5pt; }}

        QListWidget {{
            background: {INPUT}; color: {TEXT_SECONDARY};
            border: 1px solid {BORDER}; border-radius: 6px;
            outline: none; padding: 4px;
        }}
        QListWidget::item {{ padding: 9px 8px; border-radius: 4px; }}
        QListWidget::item:hover {{ background: {SURFACE_HOVER}; }}
        QListWidget::item:selected {{
            background: {SELECTION}; color: {TEXT_PRIMARY};
            border-left: 2px solid {ACCENT};
        }}
        QLabel#telemetryLabel {{
            color: {TEXT_MUTED}; font-size: 8.5pt; font-weight: 600;
            letter-spacing: 0.2px;
        }}
        QLabel#telemetryValue {{
            color: {TEXT_PRIMARY}; font-family: "Cascadia Mono", Consolas;
            font-size: 10pt; font-variant-numeric: tabular-nums;
        }}
        QLabel#telemetryPrimary {{
            color: {ACCENT_INFO}; font-family: "Cascadia Mono", Consolas;
            font-size: 12pt; font-weight: 700;
            font-variant-numeric: tabular-nums;
        }}
        QLabel[statusRole="ok"] {{ color: {STATUS_OK}; font-weight: 700; }}
        QLabel[statusRole="warning"] {{ color: {STATUS_WARNING}; font-weight: 700; }}
        QLabel[statusRole="error"] {{ color: {STATUS_ERROR}; font-weight: 700; }}
        QLabel[statusRole="alert"] {{ color: {STATUS_ALERT}; font-weight: 700; }}
        QLabel[statusRole="info"] {{ color: {ACCENT_INFO}; font-weight: 700; }}
        QLabel[statusRole="muted"] {{ color: {TEXT_MUTED}; font-weight: 600; }}

        QTabWidget::pane {{
            background: {BACKGROUND_DEEP}; border: 1px solid {BORDER};
            border-top: 1px solid {BORDER_STRONG}; border-radius: 6px; top: -1px;
        }}
        QTabBar::tab {{
            background: {TAB_SURFACE}; color: {TEXT_MUTED};
            border: 1px solid {BORDER}; border-bottom: 2px solid {BORDER};
            border-top-left-radius: 5px; border-top-right-radius: 5px;
            padding: 10px 14px; margin-right: 3px; min-width: 98px;
            font-size: 8.5pt; font-weight: 700; letter-spacing: 0.5px;
        }}
        QTabBar::tab:selected {{
            background: {SURFACE}; color: {TEXT_PRIMARY};
            border-color: {BORDER_STRONG}; border-bottom: 2px solid {ACCENT};
        }}
        QTabBar::tab:hover:!selected {{
            background: {PASTEL_BLUSH}; color: {TEXT_SECONDARY};
        }}

        QGroupBox {{
            background: {SURFACE}; border: 1px solid {BORDER};
            border-radius: 7px; margin-top: 17px; font-weight: 700;
            color: {TEXT_PRIMARY};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin; left: 12px; padding: 0 8px;
            color: {ACCENT}; background: {GROUP_TITLE_SURFACE}; font-size: 8pt;
            letter-spacing: 1px;
        }}
        QGroupBox[surfaceRole="blue"], QFrame#metricCard[surfaceRole="blue"] {{
            background: {PASTEL_BLUE};
        }}
        QGroupBox[surfaceRole="sage"], QFrame#metricCard[surfaceRole="sage"] {{
            background: {PASTEL_SAGE};
        }}
        QGroupBox[surfaceRole="blush"], QFrame#metricCard[surfaceRole="blush"] {{
            background: {PASTEL_BLUSH};
        }}
        QGroupBox[surfaceRole="lavender"], QFrame#metricCard[surfaceRole="lavender"] {{
            background: {PASTEL_LAVENDER};
        }}
        QGroupBox[surfaceRole="sand"], QFrame#metricCard[surfaceRole="sand"] {{
            background: {PASTEL_SAND};
        }}
        QLabel {{ background: transparent; }}

        QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
        QDateEdit, QDateTimeEdit, QTimeEdit {{
            background-color: {INPUT}; color: {TEXT_PRIMARY};
            border: 1px solid {BORDER_STRONG}; border-radius: 5px;
            padding: 6px 9px; min-height: 24px;
            selection-background-color: {SELECTION}; selection-color: {TEXT_PRIMARY};
        }}
        QLineEdit, QTextEdit {{
            font-family: "Cascadia Mono", Consolas;
            font-variant-numeric: tabular-nums;
        }}
        QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QSpinBox:hover,
        QDoubleSpinBox:hover, QDateEdit:hover, QDateTimeEdit:hover {{
            border-color: {ACCENT};
        }}
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus,
        QDoubleSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus {{
            border: 1px solid {ACCENT}; background-color: {SURFACE_ALT};
        }}
        QComboBox::drop-down, QSpinBox::down-button, QSpinBox::up-button,
        QDoubleSpinBox::down-button, QDoubleSpinBox::up-button {{
            border: none; width: 23px; background: {CONTROL_ACCENT_SURFACE};
            border-radius: 4px; margin: 2px;
        }}
        QComboBox QAbstractItemView, QMenu {{
            background: {SURFACE}; color: {TEXT_PRIMARY};
            border: 1px solid {BORDER_STRONG};
            selection-background-color: {SELECTION};
            selection-color: {TEXT_PRIMARY}; outline: none; padding: 5px;
        }}
        QMenuBar {{
            background: {SURFACE}; color: {TEXT_SECONDARY};
            border-bottom: 1px solid {BORDER}; padding: 2px 6px;
        }}
        QMenuBar::item {{
            background: transparent; padding: 6px 10px; border-radius: 4px;
        }}
        QMenuBar::item:selected, QMenuBar::item:pressed {{
            background: {SURFACE_HOVER}; color: {TEXT_PRIMARY};
        }}

        QPushButton {{
            background: {SURFACE_ALT}; color: {TEXT_SECONDARY};
            border: 1px solid {BORDER_STRONG}; border-radius: 5px;
            padding: 9px 14px; font-size: 8.5pt; font-weight: 700;
            letter-spacing: 0.55px;
        }}
        QPushButton:hover {{
            background: {SURFACE_HOVER}; color: {TEXT_PRIMARY};
            border-color: {ACCENT};
        }}
        QPushButton:pressed {{
            background: {SURFACE_RAISED}; border-color: {ACCENT_HOVER};
        }}
        QPushButton:focus {{ border: 1px solid {ACCENT}; }}
        QPushButton#primaryAction, QPushButton#settingsPrimaryButton {{
            background: {PRIMARY_BUTTON}; color: #FFFFFF;
            border: 1px solid {PRIMARY_BUTTON}; min-height: 26px;
        }}
        QPushButton#primaryAction:hover, QPushButton#settingsPrimaryButton:hover {{
            background: {PRIMARY_BUTTON_HOVER}; border-color: {PRIMARY_BUTTON_HOVER};
        }}
        QPushButton#ghostAction {{ background: transparent; }}
        QFrame#heroCard QPushButton#ghostAction {{
            color: {HERO_CONTROL_TEXT}; background: {HERO_CONTROL_SURFACE};
            border-color: {HERO_CONTROL_BORDER};
        }}
        QPushButton#dangerAction {{
            color: {STATUS_ERROR}; border-color: {STATUS_ERROR}; background: transparent;
        }}
        QPushButton:disabled {{
            background: {BACKGROUND_DEEP}; color: {TEXT_FAINT};
            border: 1px solid {BORDER};
        }}

        QCheckBox, QRadioButton {{ spacing: 8px; color: {TEXT_SECONDARY}; }}
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px; height: 16px; border: 1px solid {BORDER_STRONG};
            background: {INPUT};
        }}
        QCheckBox::indicator {{ border-radius: 3px; }}
        QRadioButton::indicator {{ border-radius: 8px; }}
        QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
            border-color: {ACCENT};
        }}
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
            background: {ACCENT}; border: 1px solid {ACCENT_HOVER};
        }}

        QSlider::groove:horizontal {{
            height: 4px; background: {BORDER}; border-radius: 2px;
        }}
        QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
        QSlider::handle:horizontal {{
            background: {SURFACE}; border: 2px solid {ACCENT}; width: 14px;
            margin: -6px 0; border-radius: 8px;
        }}

        QTableWidget, QTableView, QTreeView, QListView {{
            background: {SURFACE}; alternate-background-color: {SURFACE_ALT};
            color: {TEXT_SECONDARY}; border: 1px solid {BORDER};
            gridline-color: {BORDER}; selection-background-color: {SELECTION};
            selection-color: {TEXT_PRIMARY}; outline: none;
        }}
        QTableWidget::item, QTableView::item {{ padding: 5px 7px; }}
        QHeaderView::section {{
            background: {TABLE_HEADER_SURFACE}; color: {TEXT_SECONDARY}; border: none;
            border-right: 1px solid {BORDER}; border-bottom: 1px solid {BORDER};
            padding: 6px; font-size: 8pt; font-weight: 700;
        }}

        QTextEdit#referenceResults {{
            background: {INPUT}; border: 1px solid {BORDER};
            color: {TEXT_SECONDARY}; font-family: "Cascadia Mono", Consolas;
            font-size: 9pt;
        }}
        QScrollArea, QScrollArea > QWidget > QWidget {{
            border: none; background: transparent;
        }}
        QScrollBar:vertical {{
            background: {BACKGROUND_DEEP}; width: 9px; margin: 2px;
            border-radius: 4px;
        }}
        QScrollBar:horizontal {{
            background: {BACKGROUND_DEEP}; height: 9px; margin: 2px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
            background: {BORDER_STRONG}; min-height: 38px; min-width: 38px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
            background: {ACCENT};
        }}
        QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}

        QProgressBar {{
            background: {BACKGROUND_DEEP}; border: 1px solid {BORDER};
            border-radius: 4px; color: {TEXT_SECONDARY}; text-align: center;
            min-height: 18px; font-size: 8pt;
        }}
        QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}
        QToolTip {{
            background: {SURFACE_RAISED}; color: {TEXT_PRIMARY};
            border: 1px solid {BORDER_STRONG}; padding: 6px;
        }}
        QStatusBar {{
            background: {BACKGROUND_DEEP}; color: {TEXT_MUTED};
            border-top: 1px solid {BORDER};
            font-family: "Cascadia Mono", Consolas; font-size: 8pt;
        }}
        {arrow_rule}
    """


def _normal_settings_stylesheet():
    """Build the established Normal Settings surface."""

    return f"""
        QWidget#settingsOverlay {{ background: {OVERLAY}; }}
        QFrame#settingsPanel {{
            background: {SURFACE}; border: 1px solid {BORDER_STRONG};
            border-radius: 10px;
        }}
        QFrame#settingsHeader {{
            background: {SETTINGS_HEADER_SURFACE}; border: none;
            border-bottom: 1px solid {BORDER};
            border-top-left-radius: 10px; border-top-right-radius: 10px;
        }}
        QLabel#settingsTitle {{
            color: {TEXT_PRIMARY}; font-size: 12pt; font-weight: 700;
            letter-spacing: 1.3px;
        }}
        QPushButton#settingsCloseButton {{
            background: transparent; color: {TEXT_MUTED};
            border: 1px solid transparent; border-radius: 6px;
            font-size: 17pt; padding: 0;
        }}
        QPushButton#settingsCloseButton:hover {{
            color: {TEXT_PRIMARY}; background: {SURFACE_RAISED};
            border-color: {BORDER};
        }}
        QFrame#settingsNavigation {{
            background: {SETTINGS_NAV_SURFACE}; border: none;
            border-right: 1px solid {BORDER}; border-bottom-left-radius: 10px;
        }}
        QPushButton#settingsNavButton {{
            background: transparent; color: {TEXT_MUTED};
            border: 1px solid transparent; border-radius: 6px;
            padding: 9px 12px; text-align: left; font-size: 8.5pt;
            font-weight: 700; letter-spacing: 0.6px;
        }}
        QPushButton#settingsNavButton:hover {{
            background: {SURFACE_RAISED}; color: {TEXT_SECONDARY};
        }}
        QPushButton#settingsNavButton:checked {{
            background: {ACCENT_SUBTLE}; color: {ACCENT}; border-color: {BORDER};
            border-left: 3px solid {ACCENT};
        }}
        QStackedWidget#settingsPages {{ background: {SURFACE}; border: none; }}
        QLabel#settingsPageTitle {{
            color: {TEXT_PRIMARY}; font-size: 16pt; font-weight: 700;
        }}
        QLabel#settingsPageDescription {{ color: {TEXT_MUTED}; font-size: 8.5pt; }}
        QFrame#settingsCard, QFrame#creditCard {{
            background: {SETTINGS_CARD_SURFACE}; border: 1px solid {BORDER};
            border-radius: 7px;
        }}
        QFrame#settingsCard[surfaceRole="blue"],
        QFrame#creditCard[surfaceRole="blue"] {{ background: {PASTEL_BLUE}; }}
        QFrame#settingsCard[surfaceRole="sage"],
        QFrame#creditCard[surfaceRole="sage"] {{ background: {PASTEL_SAGE}; }}
        QFrame#settingsCard[surfaceRole="blush"],
        QFrame#creditCard[surfaceRole="blush"] {{ background: {PASTEL_BLUSH}; }}
        QFrame#settingsCard[surfaceRole="lavender"],
        QFrame#creditCard[surfaceRole="lavender"] {{ background: {PASTEL_LAVENDER}; }}
        QFrame#settingsCard[surfaceRole="sand"] {{ background: {PASTEL_SAND}; }}
        QFrame#settingsCard:hover, QFrame#creditCard:hover {{
            border-color: {BORDER_STRONG}; background: {SURFACE_HOVER};
        }}
        QLabel#settingsCaption {{
            color: {ACCENT}; font-size: 7.5pt; font-weight: 700;
            letter-spacing: 0.75px;
        }}
        QLabel#settingsValue {{
            color: {TEXT_PRIMARY}; font-family: "Cascadia Mono", Consolas;
            font-size: 8.5pt;
        }}
        QLabel#settingsApplyStatus[state="success"] {{ color: {STATUS_OK}; }}
        QLabel#settingsApplyStatus[state="error"] {{ color: {STATUS_ERROR}; }}
        QLabel#creditAvatar {{
            background: {ACCENT_SUBTLE}; color: {ACCENT};
            border: 1px solid {BORDER_STRONG}; border-radius: 22px;
            font-weight: 700;
        }}
        QLabel#creditName {{
            color: {TEXT_PRIMARY}; font-size: 10.5pt; font-weight: 700;
        }}
        QLabel#creditEmail {{ color: {ACCENT}; font-size: 8.5pt; }}
        QLabel#creditsVersion {{
            color: {TEXT_FAINT}; font-family: "Cascadia Mono", Consolas;
            font-size: 7.5pt; letter-spacing: 0.6px;
        }}
    """


def _asset_url(base_path, file_name):
    """Return a QSS-safe URL for an original theme asset."""

    import os

    directory = os.path.dirname(str(base_path or ""))
    return os.path.join(directory, file_name).replace("\\", "/")


def _retro_application_stylesheet(dropdown_arrow_path=""):
    """Build the complete Windows XP Luna-inspired widget stylesheet."""

    combo_arrow = _asset_url(dropdown_arrow_path, "retro_combo_arrow.svg")
    checkmark = _asset_url(dropdown_arrow_path, "retro_checkbox_checked.svg")
    radio = _asset_url(dropdown_arrow_path, "retro_radio_checked.svg")
    up_arrow = _asset_url(dropdown_arrow_path, "retro_arrow_up.svg")
    down_arrow = _asset_url(dropdown_arrow_path, "retro_arrow_down.svg")
    left_arrow = _asset_url(dropdown_arrow_path, "retro_arrow_left.svg")
    right_arrow = _asset_url(dropdown_arrow_path, "retro_arrow_right.svg")
    return f"""
        QMainWindow, QDialog {{
            background: {BACKGROUND}; color: {TEXT_PRIMARY};
        }}
        QWidget {{
            background: transparent; color: {TEXT_SECONDARY};
            font-family: Tahoma, "Segoe UI", Arial; font-size: 8.5pt;
        }}
        QDialog, QMessageBox, QFileDialog {{
            background: {BACKGROUND}; color: {TEXT_PRIMARY};
        }}
        QWidget#commandSurface {{ background: {BACKGROUND}; }}
        QLabel {{ background: transparent; }}

        QMenuBar {{
            background: {BACKGROUND}; color: {TEXT_PRIMARY};
            border-top: 1px solid {BEVEL_HIGHLIGHT};
            border-bottom: 1px solid {BEVEL_SHADOW}; padding: 1px 3px;
        }}
        QMenuBar::item {{
            background: transparent; padding: 3px 7px; border: 1px solid transparent;
        }}
        QMenuBar::item:selected {{
            background: {SELECTION}; color: {SELECTION_TEXT};
            border: 1px solid {ACCENT_INFO};
        }}
        QMenuBar::item:pressed {{
            background: {SELECTION}; color: {SELECTION_TEXT};
        }}
        QMenu {{
            background: {BACKGROUND}; color: {TEXT_PRIMARY};
            border: 1px solid {BEVEL_DARK}; padding: 2px;
        }}
        QMenu::item {{ padding: 3px 24px 3px 22px; min-height: 15px; }}
        QMenu::item:selected {{ background: {SELECTION}; color: {SELECTION_TEXT}; }}
        QMenu::item:disabled {{ color: {DISABLED_TEXT}; }}
        QMenu::separator {{
            height: 1px; background: {BEVEL_SHADOW}; margin: 3px 4px 3px 22px;
            border-bottom: 1px solid {BEVEL_HIGHLIGHT};
        }}
        QMenu::indicator {{ width: 13px; height: 13px; left: 4px; }}

        QToolBar#retroToolBar {{
            background: {BACKGROUND}; border: none;
            border-top: 1px solid {BEVEL_HIGHLIGHT};
            border-bottom: 1px solid {BEVEL_SHADOW}; spacing: 1px; padding: 2px;
        }}
        QToolBar#retroToolBar::separator {{
            background: {BEVEL_SHADOW}; width: 1px; margin: 3px 4px;
            border-right: 1px solid {BEVEL_HIGHLIGHT};
        }}
        QToolButton {{
            background: transparent; color: {TEXT_PRIMARY}; border: 1px solid transparent;
            padding: 3px 5px; min-width: 20px; min-height: 20px;
        }}
        QToolButton:hover {{
            background: {SURFACE_HOVER}; border: 1px solid {ACCENT_HOVER};
        }}
        QToolButton:pressed, QToolButton:checked {{
            background: {ACCENT_SUBTLE}; border: 1px solid {ACCENT_INFO};
            padding-left: 4px; padding-top: 4px;
        }}

        QFrame#heroCard {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {TITLE_BLUE}, stop:0.65 {TITLE_BLUE_LIGHT}, stop:1 {TITLE_BLUE});
            border-style: solid; border-width: 1px;
            border-color: {BEVEL_HIGHLIGHT} {BEVEL_DARK} {BEVEL_DARK} {BEVEL_HIGHLIGHT};
            border-radius: 0;
        }}
        QLabel#missionEyebrow {{
            color: #DCE8FF; font-size: 7.5pt; font-weight: 700; letter-spacing: 0;
        }}
        QLabel#mainTitle {{
            color: #FFFFFF; font-size: 14pt; font-weight: 700; letter-spacing: 0;
        }}
        QLabel#mainSubtitle {{ color: #FFFFFF; font-size: 8pt; letter-spacing: 0; }}
        QFrame#missionDivider {{
            background: #B9D1FF; border: none; min-width: 1px; max-width: 1px;
        }}
        QLabel#heroStatus {{
            color: #FFFFFF; background: #299D2E; border: 1px solid #FFFFFF;
            border-radius: 0; padding: 2px 6px; font-size: 7.5pt; font-weight: 700;
        }}
        QLabel#heroStatus[state="error"] {{ background: {STATUS_ERROR}; color: #FFFFFF; }}
        QLabel#heroModel, QLabel#heroUtc, QLabel#heroVersion {{
            color: #FFFFFF; font-family: Tahoma, "Segoe UI", Arial; font-size: 7.5pt;
            letter-spacing: 0;
        }}
        QFrame#heroCard QPushButton#ghostAction {{
            color: #000000; background: {BACKGROUND};
            border-style: solid; border-width: 1px;
            border-color: {BEVEL_HIGHLIGHT} {BEVEL_DARK} {BEVEL_DARK} {BEVEL_HIGHLIGHT};
        }}

        QFrame#productCommandBar {{
            background: {BACKGROUND}; border-style: solid; border-width: 1px;
            border-color: {BEVEL_HIGHLIGHT} {BEVEL_SHADOW} {BEVEL_SHADOW} {BEVEL_HIGHLIGHT};
            border-radius: 0;
        }}
        QFrame#productCommandBar QLabel#missionEyebrow {{ color: {ACCENT_INFO}; }}
        QPushButton#projectStatusButton {{
            background: transparent; border: none; color: {ACCENT_INFO};
            font-size: 8pt; font-weight: 400; padding: 3px; text-align: right;
        }}
        QPushButton#projectStatusButton:hover {{ color: {ACCENT}; text-decoration: underline; }}

        QTabWidget::pane {{
            background: {BACKGROUND}; border: 1px solid {BEVEL_SHADOW};
            border-top: 1px solid {BEVEL_HIGHLIGHT}; border-radius: 0; top: -1px;
        }}
        QTabBar::tab {{
            background: {BACKGROUND_DEEP}; color: {TEXT_PRIMARY};
            border-style: solid; border-width: 1px;
            border-color: {BEVEL_HIGHLIGHT} {BEVEL_SHADOW} {BEVEL_SHADOW} {BEVEL_HIGHLIGHT};
            border-bottom-color: {BEVEL_SHADOW};
            border-top-left-radius: 2px; border-top-right-radius: 2px;
            padding: 4px 8px; margin-right: 1px; min-width: 70px;
            font-size: 8pt; font-weight: 400; letter-spacing: 0;
        }}
        QTabBar::tab:selected {{
            background: {BACKGROUND}; color: {TEXT_PRIMARY};
            border-top: 2px solid #E68B2C; border-bottom-color: {BACKGROUND};
            padding-top: 3px;
        }}
        QTabBar::tab:hover:!selected {{ background: {SURFACE_HOVER}; color: {TEXT_PRIMARY}; }}
        QTabBar::tab:disabled {{ color: {DISABLED_TEXT}; background: {DISABLED_SURFACE}; }}

        QGroupBox {{
            background: {BACKGROUND}; border: 1px solid {BEVEL_SHADOW};
            border-radius: 0; margin-top: 12px; font-weight: 400; color: {TEXT_PRIMARY};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin; subcontrol-position: top left;
            left: 7px; padding: 0 4px; color: {TEXT_PRIMARY};
            background: {BACKGROUND}; font-size: 8.5pt; letter-spacing: 0;
        }}
        QGroupBox[surfaceRole], QFrame#metricCard[surfaceRole] {{ background: {BACKGROUND}; }}
        QFrame#metricCard {{
            background: {BACKGROUND}; border-style: solid; border-width: 1px;
            border-color: {BEVEL_SHADOW} {BEVEL_HIGHLIGHT} {BEVEL_HIGHLIGHT} {BEVEL_SHADOW};
            border-radius: 0;
        }}
        QFrame#metricCard:hover {{ background: {BACKGROUND}; border-color: {BEVEL_SHADOW}; }}
        QLabel#metricCaption {{
            color: {TEXT_MUTED}; font-size: 7.5pt; font-weight: 700; letter-spacing: 0;
        }}
        QLabel#metricValue {{
            color: {TEXT_PRIMARY}; font-family: "Courier New", Consolas;
            font-size: 13pt; font-weight: 700;
        }}
        QLabel#geoMetricValue {{
            color: {TEXT_PRIMARY}; font-family: "Courier New", Consolas;
            font-size: 9pt; font-weight: 700;
        }}
        QLabel#metricDetail {{ color: {ACCENT_INFO}; font-size: 8pt; }}
        QLabel#telemetryLabel {{ color: {TEXT_MUTED}; font-size: 8pt; font-weight: 400; }}
        QLabel#telemetryValue {{
            color: {TEXT_PRIMARY}; font-family: "Courier New", Consolas; font-size: 9pt;
        }}
        QLabel#telemetryPrimary {{
            color: {ACCENT_INFO}; font-family: "Courier New", Consolas;
            font-size: 10pt; font-weight: 700;
        }}
        QLabel[statusRole="ok"] {{ color: {STATUS_OK}; font-weight: 700; }}
        QLabel[statusRole="warning"] {{ color: {STATUS_WARNING}; font-weight: 700; }}
        QLabel[statusRole="error"] {{ color: {STATUS_ERROR}; font-weight: 700; }}
        QLabel[statusRole="alert"] {{ color: {STATUS_ALERT}; font-weight: 700; }}
        QLabel[statusRole="info"] {{ color: {ACCENT_INFO}; font-weight: 700; }}
        QLabel[statusRole="muted"] {{ color: {TEXT_MUTED}; font-weight: 400; }}

        QPushButton {{
            background: {BACKGROUND}; color: {TEXT_PRIMARY};
            border-style: solid; border-width: 1px;
            border-color: {BEVEL_HIGHLIGHT} {BEVEL_DARK} {BEVEL_DARK} {BEVEL_HIGHLIGHT};
            border-radius: 0; padding: 4px 9px; min-height: 18px;
            font-size: 8.5pt; font-weight: 400; letter-spacing: 0;
        }}
        QPushButton:hover {{
            background: {SURFACE_HOVER}; border-color: #FFB531 {ACCENT_INFO} {ACCENT_INFO} #FFB531;
        }}
        QPushButton:pressed, QPushButton:checked {{
            background: {ACCENT_SUBTLE};
            border-color: {BEVEL_DARK} {BEVEL_HIGHLIGHT} {BEVEL_HIGHLIGHT} {BEVEL_DARK};
            padding-left: 10px; padding-top: 5px; padding-right: 8px; padding-bottom: 3px;
        }}
        QPushButton:focus {{ border: 1px solid {ACCENT_INFO}; }}
        QPushButton#primaryAction, QPushButton#settingsPrimaryButton {{
            background: {BACKGROUND}; color: {TEXT_PRIMARY}; min-height: 18px;
            border-style: solid; border-width: 2px;
            border-color: {BEVEL_HIGHLIGHT} {BEVEL_DARK} {BEVEL_DARK} {BEVEL_HIGHLIGHT};
        }}
        QPushButton#primaryAction:hover, QPushButton#settingsPrimaryButton:hover {{ background: {SURFACE_HOVER}; }}
        QPushButton#ghostAction {{ background: {BACKGROUND}; }}
        QPushButton#dangerAction {{ color: {STATUS_ERROR}; background: {BACKGROUND}; }}
        QPushButton:disabled {{
            background: {DISABLED_SURFACE}; color: {DISABLED_TEXT};
            border-color: {BEVEL_HIGHLIGHT} {BEVEL_SHADOW} {BEVEL_SHADOW} {BEVEL_HIGHLIGHT};
        }}

        QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
        QDateEdit, QDateTimeEdit, QTimeEdit {{
            background: {INPUT}; color: {TEXT_PRIMARY};
            border-style: solid; border-width: 1px;
            border-color: {BEVEL_SHADOW} {BEVEL_HIGHLIGHT} {BEVEL_HIGHLIGHT} {BEVEL_SHADOW};
            border-radius: 0; padding: 2px 4px; min-height: 18px;
            selection-background-color: {SELECTION}; selection-color: {SELECTION_TEXT};
        }}
        QLineEdit, QTextEdit, QPlainTextEdit {{ font-family: Tahoma, "Segoe UI", Arial; }}
        QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover,
        QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover, QDateTimeEdit:hover,
        QTimeEdit:hover {{ border: 1px solid {BORDER_STRONG}; }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
        QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus,
        QTimeEdit:focus {{ border: 1px solid {ACCENT_INFO}; background: {INPUT}; }}
        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled,
        QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled,
        QDateEdit:disabled, QDateTimeEdit:disabled, QTimeEdit:disabled {{
            background: {DISABLED_SURFACE}; color: {DISABLED_TEXT};
        }}
        QComboBox {{ padding-right: 20px; }}
        QComboBox::drop-down {{
            subcontrol-origin: padding; subcontrol-position: top right; width: 18px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #FFFFFF, stop:1 #C6D6EF);
            border-left: 1px solid {BEVEL_SHADOW};
        }}
        QComboBox::drop-down:hover {{ background: {SURFACE_HOVER}; border-left-color: {ACCENT_INFO}; }}
        QComboBox::drop-down:pressed {{ background: {ACCENT_SUBTLE}; }}
        QComboBox::down-arrow {{ image: url("{combo_arrow}"); width: 9px; height: 6px; }}
        QComboBox QAbstractItemView {{
            background: {INPUT}; color: {TEXT_PRIMARY}; border: 1px solid {BEVEL_DARK};
            selection-background-color: {SELECTION}; selection-color: {SELECTION_TEXT};
            outline: none; padding: 1px;
        }}
        QComboBox QAbstractItemView::item {{ min-height: 17px; padding: 1px 3px; }}
        QAbstractSpinBox::up-button {{
            subcontrol-origin: border; subcontrol-position: top right; width: 17px;
            background: {BACKGROUND}; border-left: 1px solid {BEVEL_SHADOW};
            border-bottom: 1px solid {BEVEL_SHADOW};
        }}
        QAbstractSpinBox::down-button {{
            subcontrol-origin: border; subcontrol-position: bottom right; width: 17px;
            background: {BACKGROUND}; border-left: 1px solid {BEVEL_SHADOW};
        }}
        QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{ background: {SURFACE_HOVER}; }}
        QAbstractSpinBox::up-button:pressed, QAbstractSpinBox::down-button:pressed {{ background: {ACCENT_SUBTLE}; }}
        QAbstractSpinBox::up-arrow {{ image: url("{up_arrow}"); width: 7px; height: 4px; }}
        QAbstractSpinBox::down-arrow {{ image: url("{down_arrow}"); width: 7px; height: 4px; }}

        QCheckBox, QRadioButton {{ spacing: 5px; color: {TEXT_PRIMARY}; }}
        QCheckBox:focus, QRadioButton:focus {{ color: {ACCENT_INFO}; }}
        QCheckBox::indicator {{
            width: 12px; height: 12px; background: {INPUT}; border: 1px solid {BEVEL_SHADOW};
            border-radius: 0;
        }}
        QCheckBox::indicator:hover {{ border: 1px solid {ACCENT_HOVER}; background: {SURFACE_HOVER}; }}
        QCheckBox::indicator:checked {{ image: url("{checkmark}"); background: {INPUT}; }}
        QCheckBox::indicator:disabled {{ background: {DISABLED_SURFACE}; border-color: {BEVEL_SHADOW}; }}
        QRadioButton::indicator {{
            width: 13px; height: 13px; background: {INPUT}; border: 1px solid {BEVEL_SHADOW};
            border-radius: 7px;
        }}
        QRadioButton::indicator:hover {{ border: 1px solid {ACCENT_HOVER}; background: {SURFACE_HOVER}; }}
        QRadioButton::indicator:checked {{ image: url("{radio}"); background: {INPUT}; }}
        QRadioButton::indicator:disabled {{ background: {DISABLED_SURFACE}; border-color: {BEVEL_SHADOW}; }}

        QListWidget, QListView, QTreeView, QTableWidget, QTableView {{
            background: {INPUT}; alternate-background-color: {INPUT}; color: {TEXT_PRIMARY};
            border-style: solid; border-width: 1px;
            border-color: {BEVEL_SHADOW} {BEVEL_HIGHLIGHT} {BEVEL_HIGHLIGHT} {BEVEL_SHADOW};
            gridline-color: #D6D2C2; selection-background-color: {SELECTION};
            selection-color: {SELECTION_TEXT}; outline: none; padding: 0;
        }}
        QListWidget::item, QListView::item, QTreeView::item {{ padding: 2px 4px; min-height: 17px; }}
        QListWidget::item:hover, QListView::item:hover, QTreeView::item:hover {{ background: {SURFACE_HOVER}; color: {TEXT_PRIMARY}; }}
        QListWidget::item:selected, QListView::item:selected, QTreeView::item:selected {{
            background: {SELECTION}; color: {SELECTION_TEXT};
        }}
        QTableWidget::item, QTableView::item {{ padding: 2px 4px; }}
        QHeaderView::section {{
            background: {TABLE_HEADER_SURFACE}; color: {TEXT_PRIMARY};
            border-style: solid; border-width: 1px;
            border-color: {BEVEL_HIGHLIGHT} {BEVEL_SHADOW} {BEVEL_SHADOW} {BEVEL_HIGHLIGHT};
            padding: 3px 5px; font-size: 8pt; font-weight: 400;
        }}
        QTableCornerButton::section {{
            background: {TABLE_HEADER_SURFACE}; border-style: solid; border-width: 1px;
            border-color: {BEVEL_HIGHLIGHT} {BEVEL_SHADOW} {BEVEL_SHADOW} {BEVEL_HIGHLIGHT};
        }}

        QScrollArea {{ border: none; background: transparent; }}
        QScrollArea > QWidget > QWidget {{ background: {BACKGROUND}; }}
        QScrollBar:vertical {{
            background: #F3F1E5; width: 17px; margin: 17px 0 17px 0;
            border-left: 1px solid {BORDER};
        }}
        QScrollBar:horizontal {{
            background: #F3F1E5; height: 17px; margin: 0 17px 0 17px;
            border-top: 1px solid {BORDER};
        }}
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
            background: #C6D6EF; border-style: solid; border-width: 1px;
            border-color: {BEVEL_HIGHLIGHT} {BEVEL_SHADOW} {BEVEL_SHADOW} {BEVEL_HIGHLIGHT};
            min-height: 24px; min-width: 24px;
        }}
        QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{ background: #AFC7E8; }}
        QScrollBar::handle:vertical:pressed, QScrollBar::handle:horizontal:pressed {{ background: #91B3DE; }}
        QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical,
        QScrollBar::sub-line:horizontal, QScrollBar::add-line:horizontal {{
            background: {BACKGROUND}; border-style: solid; border-width: 1px;
            border-color: {BEVEL_HIGHLIGHT} {BEVEL_SHADOW} {BEVEL_SHADOW} {BEVEL_HIGHLIGHT};
            width: 17px; height: 17px;
        }}
        QScrollBar::sub-line:vertical {{ subcontrol-position: top; subcontrol-origin: margin; }}
        QScrollBar::add-line:vertical {{ subcontrol-position: bottom; subcontrol-origin: margin; }}
        QScrollBar::sub-line:horizontal {{ subcontrol-position: left; subcontrol-origin: margin; }}
        QScrollBar::add-line:horizontal {{ subcontrol-position: right; subcontrol-origin: margin; }}
        QScrollBar::up-arrow {{ image: url("{up_arrow}"); width: 7px; height: 4px; }}
        QScrollBar::down-arrow {{ image: url("{down_arrow}"); width: 7px; height: 4px; }}
        QScrollBar::left-arrow {{ image: url("{left_arrow}"); width: 4px; height: 7px; }}
        QScrollBar::right-arrow {{ image: url("{right_arrow}"); width: 4px; height: 7px; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: #F3F1E5; }}

        QProgressBar {{
            background: {INPUT}; color: {TEXT_PRIMARY}; border-style: solid;
            border-width: 1px; border-color: {BEVEL_SHADOW} {BEVEL_HIGHLIGHT} {BEVEL_HIGHLIGHT} {BEVEL_SHADOW};
            border-radius: 0; text-align: center; min-height: 15px; font-size: 8pt;
        }}
        QProgressBar::chunk {{ background: {PROGRESS_GREEN}; width: 7px; margin: 1px; }}
        QSlider::groove:horizontal {{
            height: 3px; background: {BEVEL_SHADOW}; border-bottom: 1px solid {BEVEL_HIGHLIGHT};
        }}
        QSlider::sub-page:horizontal {{ background: {BEVEL_SHADOW}; }}
        QSlider::handle:horizontal {{
            background: {BACKGROUND}; border-style: solid; border-width: 1px;
            border-color: {BEVEL_HIGHLIGHT} {BEVEL_DARK} {BEVEL_DARK} {BEVEL_HIGHLIGHT};
            width: 10px; height: 18px; margin: -8px 0; border-radius: 0;
        }}
        QSlider::handle:horizontal:hover {{ background: {SURFACE_HOVER}; }}
        QSplitter::handle {{ background: {BACKGROUND_DEEP}; border: 1px solid {BORDER}; }}
        QSplitter::handle:horizontal {{ width: 5px; }}
        QSplitter::handle:vertical {{ height: 5px; }}

        QCalendarWidget QWidget#qt_calendar_navigationbar {{
            background: {TITLE_BLUE}; border-bottom: 1px solid {BEVEL_DARK};
        }}
        QCalendarWidget QToolButton {{ color: #FFFFFF; font-weight: 700; }}
        QCalendarWidget QAbstractItemView {{
            background: {INPUT}; color: {TEXT_PRIMARY}; selection-background-color: {SELECTION};
            selection-color: {SELECTION_TEXT};
        }}
        QTextEdit#referenceResults {{
            background: {INPUT}; color: {TEXT_PRIMARY}; font-family: "Courier New", Consolas;
            font-size: 8.5pt;
        }}
        QToolTip {{
            background: {TOOLTIP_BG}; color: {TOOLTIP_TEXT}; border: 1px solid {BEVEL_DARK};
            padding: 2px 3px; font-family: Tahoma, "Segoe UI", Arial; font-size: 8pt;
        }}
        QStatusBar {{
            background: {BACKGROUND}; color: {TEXT_PRIMARY};
            border-top: 1px solid {BEVEL_SHADOW}; font-family: Tahoma, "Segoe UI", Arial;
            font-size: 8pt;
        }}
        QStatusBar::item {{
            border-left: 1px solid {BEVEL_SHADOW}; border-top: 1px solid {BEVEL_SHADOW};
            border-right: 1px solid {BEVEL_HIGHLIGHT}; border-bottom: 1px solid {BEVEL_HIGHLIGHT};
        }}
        QSizeGrip {{ background: {BACKGROUND}; width: 14px; height: 14px; }}
    """


def _retro_settings_stylesheet():
    """Style the in-window Settings surface like an XP property dialog."""

    return f"""
        QWidget#settingsOverlay {{ background: {OVERLAY}; }}
        QFrame#settingsPanel {{
            background: {BACKGROUND}; border-style: solid; border-width: 2px;
            border-color: {BEVEL_HIGHLIGHT} {BEVEL_DARK} {BEVEL_DARK} {BEVEL_HIGHLIGHT};
            border-radius: 0;
        }}
        QFrame#settingsHeader {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {TITLE_BLUE}, stop:0.7 {TITLE_BLUE_LIGHT}, stop:1 {TITLE_BLUE});
            border: none; border-bottom: 1px solid {BEVEL_DARK};
            border-radius: 0;
        }}
        QLabel#settingsTitle {{
            color: #FFFFFF; font-size: 10pt; font-weight: 700; letter-spacing: 0;
        }}
        QPushButton#settingsCloseButton {{
            background: #D9472A; color: #FFFFFF; border-style: solid; border-width: 1px;
            border-color: #FFFFFF #7A1909 #7A1909 #FFFFFF; border-radius: 2px;
            font-family: Tahoma; font-size: 12pt; font-weight: 700; padding: 0;
        }}
        QPushButton#settingsCloseButton:hover {{ background: #EE6548; }}
        QPushButton#settingsCloseButton:pressed {{ background: #B92B15; }}
        QFrame#settingsNavigation {{
            background: {SETTINGS_NAV_SURFACE}; border: none;
            border-right: 1px solid {BEVEL_SHADOW}; border-radius: 0;
        }}
        QPushButton#settingsNavButton {{
            background: {BACKGROUND}; color: {TEXT_PRIMARY}; border: 1px solid transparent;
            border-radius: 0; padding: 5px 7px; text-align: left;
            font-size: 8pt; font-weight: 400; letter-spacing: 0;
        }}
        QPushButton#settingsNavButton:hover {{
            background: {SURFACE_HOVER}; border: 1px solid #FFB531;
        }}
        QPushButton#settingsNavButton:checked {{
            background: {SELECTION}; color: {SELECTION_TEXT}; border: 1px solid {ACCENT_INFO};
        }}
        QStackedWidget#settingsPages {{ background: {BACKGROUND}; border: none; }}
        QLabel#settingsPageTitle {{ color: {TEXT_PRIMARY}; font-size: 11pt; font-weight: 700; }}
        QLabel#settingsPageDescription {{ color: {TEXT_MUTED}; font-size: 8pt; }}
        QFrame#settingsCard, QFrame#creditCard {{
            background: {BACKGROUND}; border: 1px solid {BEVEL_SHADOW}; border-radius: 0;
        }}
        QFrame#settingsCard[surfaceRole], QFrame#creditCard[surfaceRole] {{ background: {BACKGROUND}; }}
        QFrame#settingsCard:hover, QFrame#creditCard:hover {{
            border-color: {BEVEL_SHADOW}; background: {BACKGROUND};
        }}
        QLabel#settingsCaption {{
            color: {ACCENT_INFO}; font-size: 7.5pt; font-weight: 700; letter-spacing: 0;
        }}
        QLabel#settingsValue {{
            color: {TEXT_PRIMARY}; font-family: Tahoma, "Segoe UI", Arial; font-size: 8pt;
        }}
        QLabel#settingsApplyStatus[state="success"] {{ color: {STATUS_OK}; }}
        QLabel#settingsApplyStatus[state="error"] {{ color: {STATUS_ERROR}; }}
        QLabel#creditAvatar {{
            background: {ACCENT_SUBTLE}; color: {ACCENT_INFO};
            border: 1px solid {BEVEL_SHADOW}; border-radius: 0; font-weight: 700;
        }}
        QLabel#creditName {{ color: {TEXT_PRIMARY}; font-size: 9pt; font-weight: 700; }}
        QLabel#creditEmail {{ color: {ACCENT_INFO}; font-size: 8pt; }}
        QLabel#creditsVersion {{
            color: {TEXT_FAINT}; font-family: Tahoma, "Segoe UI", Arial;
            font-size: 7.5pt; letter-spacing: 0;
        }}
    """


def application_stylesheet(dropdown_arrow_path=""):
    """Return the complete stylesheet for the active interface theme."""

    if is_retro():
        return _retro_application_stylesheet(dropdown_arrow_path)
    return _normal_application_stylesheet(dropdown_arrow_path)


def settings_stylesheet():
    """Return the Settings stylesheet for the active interface theme."""

    if is_retro():
        return _retro_settings_stylesheet()
    return _normal_settings_stylesheet()


def file_dialog_options():
    """Use styleable Qt file dialogs only while Retro is active."""

    from PySide6.QtWidgets import QFileDialog

    if is_retro():
        return QFileDialog.Option.DontUseNativeDialog
    return QFileDialog.Option(0)


set_theme("normal")
