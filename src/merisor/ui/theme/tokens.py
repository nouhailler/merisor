"""Tokens visuels partagés par toutes les surfaces Qt de MERISOR."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ColorTokens:
    primary: str
    primary_hover: str
    primary_pressed: str
    accent: str
    accent_secondary: str
    background: str
    surface: str
    surface_raised: str
    surface_muted: str
    border: str
    border_strong: str
    text: str
    text_secondary: str
    text_disabled: str
    selection: str
    selection_text: str
    success: str
    warning: str
    error: str
    info: str
    ai: str
    canvas: str
    canvas_grid: str


class Spacing:
    XXS = 2
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32


class Radii:
    SMALL = 4
    MEDIUM = 7
    LARGE = 10


class Dimensions:
    CONTROL_HEIGHT = 32
    TOOLBAR_HEIGHT = 48
    NAVIGATION_HEIGHT = 44
    SIDE_PANEL_MIN_WIDTH = 300
    SIDE_PANEL_DEFAULT_WIDTH = 360
    ICON_SMALL = 16
    ICON_MEDIUM = 20
    ICON_LARGE = 24


class Typography:
    FAMILY = "Inter, Noto Sans, DejaVu Sans, sans-serif"
    MONOSPACE = "JetBrains Mono, Noto Sans Mono, DejaVu Sans Mono, monospace"
    BODY_SIZE = 10
    CAPTION_SIZE = 9
    PAGE_TITLE_SIZE = 18
    SECTION_TITLE_SIZE = 13
    CARD_TITLE_SIZE = 11


LIGHT_COLORS = ColorTokens(
    primary="#3157D5",
    primary_hover="#294BC0",
    primary_pressed="#243FA3",
    accent="#19A996",
    accent_secondary="#7060D5",
    background="#F4F6FA",
    surface="#FFFFFF",
    surface_raised="#FFFFFF",
    surface_muted="#EEF2F7",
    border="#D7DEE9",
    border_strong="#AEB9C9",
    text="#1E293B",
    text_secondary="#5D6B7E",
    text_disabled="#94A0B2",
    selection="#DCE5FF",
    selection_text="#18358F",
    success="#16865C",
    warning="#A46500",
    error="#C43D3D",
    info="#2474C6",
    ai="#7655D5",
    canvas="#F8FAFD",
    canvas_grid="#DFE5EE",
)


DARK_COLORS = ColorTokens(
    primary="#7895F7",
    primary_hover="#8EA6FA",
    primary_pressed="#607FE5",
    accent="#3CC7B5",
    accent_secondary="#A393F0",
    background="#151A22",
    surface="#1D2430",
    surface_raised="#242D3A",
    surface_muted="#293443",
    border="#394658",
    border_strong="#56657A",
    text="#EDF2F8",
    text_secondary="#AFBAC9",
    text_disabled="#748195",
    selection="#283E75",
    selection_text="#F4F7FF",
    success="#45C18C",
    warning="#E4A83D",
    error="#F07878",
    info="#66A9EA",
    ai="#B19AF5",
    canvas="#171D26",
    canvas_grid="#2A3442",
)


def build_stylesheet(colors: ColorTokens) -> str:
    """Construit le QSS global depuis les seuls tokens du thème."""

    return f"""
QWidget {{
    color: {colors.text};
    background-color: {colors.background};
    font-family: {Typography.FAMILY};
    font-size: {Typography.BODY_SIZE}pt;
}}
QMainWindow, QDialog {{ background-color: {colors.background}; }}
QLabel {{ background: transparent; }}
QLabel[role="secondary"] {{ color: {colors.text_secondary}; }}
QLabel[role="success"] {{ color: {colors.success}; }}
QLabel[role="warning"] {{ color: {colors.warning}; }}
QLabel[role="error"] {{ color: {colors.error}; }}
QLabel[role="info"] {{ color: {colors.info}; font-weight: 650; }}
QLabel[role="pageTitle"] {{
    font-size: {Typography.PAGE_TITLE_SIZE}pt;
    font-weight: 700;
}}
QLabel[role="sectionTitle"] {{
    font-size: {Typography.SECTION_TITLE_SIZE}pt;
    font-weight: 650;
}}
QMenuBar, QMenu, QToolBar, QStatusBar {{ background-color: {colors.surface}; }}
QMenuBar {{ border-bottom: 1px solid {colors.border}; }}
QMenuBar::item {{ padding: {Spacing.SM}px {Spacing.MD}px; }}
QMenuBar::item:selected, QMenu::item:selected {{
    background-color: {colors.selection};
    color: {colors.selection_text};
}}
QMenu {{ border: 1px solid {colors.border}; padding: {Spacing.XS}px; }}
QMenu::item {{ padding: 6px 28px 6px 10px; border-radius: {Radii.SMALL}px; }}
QToolBar {{
    spacing: {Spacing.XS}px;
    padding: {Spacing.XS}px {Spacing.SM}px;
    border: 0;
    border-bottom: 1px solid {colors.border};
}}
#workflowToolbar {{
    background-color: {colors.surface};
    border-bottom: 1px solid {colors.border};
}}
QPushButton[workflowStep="true"] {{
    color: {colors.text_secondary};
    background: transparent;
    border: 0;
    border-radius: {Radii.MEDIUM}px;
    min-height: {Dimensions.NAVIGATION_HEIGHT - 8}px;
    padding: 0 {Spacing.LG}px;
    font-weight: 650;
}}
QPushButton[workflowStep="true"]:hover {{
    color: {colors.primary};
    background-color: {colors.surface_muted};
}}
QPushButton[workflowStep="true"]:checked {{
    color: {colors.selection_text};
    background-color: {colors.selection};
}}
QPushButton[workflowStep="true"][workflowState="error"] {{ color: {colors.error}; }}
QPushButton[workflowStep="true"][workflowState="warning"],
QPushButton[workflowStep="true"][workflowState="stale"] {{ color: {colors.warning}; }}
QPushButton[workflowStep="true"][workflowState="ready"] {{ color: {colors.success}; }}
QPushButton[workflowStep="true"]:checked {{ color: {colors.selection_text}; }}
#toolPalette {{ background-color: {colors.surface}; }}
#toolPalette QToolButton {{ text-align: left; border-color: transparent; }}
#modelStatusStrip {{ background: transparent; }}
#startCenter, #startCenterContent {{ background-color: {colors.background}; }}
#aiHub, #aiHubContent, #sqlWorkspace {{ background-color: {colors.background}; }}
#startBrand {{ color: {colors.primary}; font-size: 13pt; font-weight: 800; letter-spacing: 2px; }}
QFrame[role="card"] {{
    background-color: {colors.surface};
    border: 1px solid {colors.border};
    border-radius: {Radii.LARGE}px;
}}
#startCenter QListWidget {{ border: 0; background: transparent; }}
#startCenter QListWidget::item {{ padding: {Spacing.SM}px; border-radius: {Radii.SMALL}px; }}
#startCenter QListWidget::item:hover {{ background-color: {colors.surface_muted}; }}
QStatusBar {{ border-top: 1px solid {colors.border}; color: {colors.text_secondary}; }}
QDockWidget {{ color: {colors.text}; font-weight: 600; }}
QDockWidget::title {{
    background-color: {colors.surface};
    border-bottom: 1px solid {colors.border};
    padding: {Spacing.SM}px {Spacing.MD}px;
}}
QLineEdit, QPlainTextEdit, QTextEdit, QTextBrowser, QComboBox, QSpinBox,
QTreeWidget, QListWidget, QTableWidget {{
    color: {colors.text};
    background-color: {colors.surface};
    border: 1px solid {colors.border};
    border-radius: {Radii.SMALL}px;
    selection-background-color: {colors.selection};
    selection-color: {colors.selection_text};
}}
QLineEdit, QComboBox, QSpinBox {{
    min-height: {Dimensions.CONTROL_HEIGHT}px;
    padding: 0 {Spacing.SM}px;
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QTextBrowser:focus,
QComboBox:focus, QSpinBox:focus, QTreeWidget:focus, QListWidget:focus {{
    border: 2px solid {colors.primary};
}}
#sqlLineNumbers {{
    color: {colors.text_secondary};
    background-color: {colors.surface_muted};
    border-right: 1px solid {colors.border};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    color: {colors.text_disabled};
    background-color: {colors.surface_muted};
}}
QPushButton, QToolButton {{
    color: {colors.text};
    background-color: {colors.surface_raised};
    border: 1px solid {colors.border};
    border-radius: {Radii.SMALL}px;
    min-height: {Dimensions.CONTROL_HEIGHT}px;
    padding: 0 {Spacing.MD}px;
}}
QPushButton:hover, QToolButton:hover {{
    background-color: {colors.surface_muted};
    border-color: {colors.border_strong};
}}
QPushButton:pressed, QToolButton:pressed {{ background-color: {colors.selection}; }}
QPushButton:disabled, QToolButton:disabled {{
    color: {colors.text_disabled};
    background-color: {colors.surface_muted};
    border-color: {colors.border};
}}
QPushButton[role="primary"], QToolButton[role="primary"] {{
    color: white;
    background-color: {colors.primary};
    border-color: {colors.primary};
    font-weight: 650;
}}
QPushButton[role="primary"]:hover, QToolButton[role="primary"]:hover {{
    background-color: {colors.primary_hover};
    border-color: {colors.primary_hover};
}}
QPushButton[role="primary"]:pressed, QToolButton[role="primary"]:pressed {{
    background-color: {colors.primary_pressed};
}}
QPushButton[role="danger"] {{ color: {colors.error}; }}
QGroupBox {{
    font-weight: 650;
    border: 1px solid {colors.border};
    border-radius: {Radii.MEDIUM}px;
    margin-top: {Spacing.MD}px;
    padding-top: {Spacing.MD}px;
    background-color: {colors.surface};
}}
QGroupBox::title {{ subcontrol-origin: margin; left: {Spacing.MD}px; padding: 0 4px; }}
QTabWidget::pane {{ border: 1px solid {colors.border}; background: {colors.surface}; }}
QTabBar::tab {{
    background: {colors.surface_muted};
    color: {colors.text_secondary};
    border: 1px solid {colors.border};
    padding: {Spacing.SM}px {Spacing.LG}px;
}}
QTabBar::tab:selected {{
    color: {colors.primary};
    background: {colors.surface};
    border-bottom-color: {colors.surface};
    font-weight: 650;
}}
QHeaderView::section {{
    color: {colors.text_secondary};
    background-color: {colors.surface_muted};
    border: 0;
    border-bottom: 1px solid {colors.border};
    padding: {Spacing.SM}px;
    font-weight: 650;
}}
QTreeWidget, QListWidget, QTableWidget {{ alternate-background-color: {colors.surface_muted}; }}
QScrollBar:vertical, QScrollBar:horizontal {{ background: transparent; border: 0; }}
QScrollBar::handle {{ background: {colors.border_strong}; border-radius: 4px; min-height: 24px; min-width: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QSplitter::handle {{ background-color: {colors.border}; }}
QProgressBar {{
    border: 1px solid {colors.border};
    border-radius: {Radii.SMALL}px;
    background: {colors.surface_muted};
    text-align: center;
}}
QProgressBar::chunk {{ background: {colors.primary}; border-radius: {Radii.SMALL}px; }}
QToolTip {{
    color: {colors.text};
    background-color: {colors.surface_raised};
    border: 1px solid {colors.border_strong};
    padding: {Spacing.XS}px;
}}
"""
