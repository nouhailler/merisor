from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from merisor.ui.theme import DARK_COLORS, LIGHT_COLORS, ThemeManager, ThemeMode
from merisor.ui.theme.dark_theme import DARK_STYLESHEET
from merisor.ui.theme.light_theme import LIGHT_STYLESHEET


def test_theme_tokens_cover_light_and_dark_semantics() -> None:
    assert LIGHT_COLORS.primary == "#3157D5"
    assert DARK_COLORS.primary != LIGHT_COLORS.primary
    assert LIGHT_COLORS.error
    assert DARK_COLORS.warning
    assert LIGHT_COLORS.ai


def test_stylesheets_expose_shared_widget_states() -> None:
    for stylesheet in (LIGHT_STYLESHEET, DARK_STYLESHEET):
        assert 'QPushButton[role="primary"]' in stylesheet
        assert "QLineEdit:focus" in stylesheet
        assert "QPushButton:disabled" in stylesheet
        assert "QToolTip" in stylesheet


def test_theme_manager_applies_and_persists_mode(
    qapp: QApplication, tmp_path: Path
) -> None:
    settings_path = tmp_path / "theme.ini"
    settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
    manager = ThemeManager(settings)

    assert manager.apply(qapp, ThemeMode.DARK)
    assert manager.mode is ThemeMode.DARK
    assert manager.colors is DARK_COLORS
    assert settings.value(ThemeManager.SETTINGS_KEY) == "dark"
    assert qapp.styleSheet() == DARK_STYLESHEET

    assert not manager.apply(qapp, ThemeMode.LIGHT)
    assert manager.colors is LIGHT_COLORS
    assert qapp.styleSheet() == LIGHT_STYLESHEET


def test_theme_manager_recovers_from_unknown_setting(
    qapp: QApplication, tmp_path: Path
) -> None:
    settings = QSettings(str(tmp_path / "theme.ini"), QSettings.Format.IniFormat)
    settings.setValue(ThemeManager.SETTINGS_KEY, "neon")

    manager = ThemeManager(settings)

    assert manager.mode is ThemeMode.SYSTEM
    manager.apply_configured(qapp)
    assert settings.value(ThemeManager.SETTINGS_KEY) == "system"
