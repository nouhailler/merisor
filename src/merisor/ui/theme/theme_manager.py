"""Sélection, résolution et application du thème global."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from merisor.ui.theme.dark_theme import DARK_STYLESHEET
from merisor.ui.theme.light_theme import LIGHT_STYLESHEET
from merisor.ui.theme.tokens import DARK_COLORS, LIGHT_COLORS, ColorTokens


class ThemeMode(str, Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class ThemeManager(QObject):
    """Applique une apparence globale et persiste le choix de l'utilisateur."""

    changed = Signal(str, bool)
    SETTINGS_KEY = "appearance/theme"

    def __init__(self, settings: QSettings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._mode = self._read_mode()
        self._dark = False

    @property
    def mode(self) -> ThemeMode:
        return self._mode

    @property
    def is_dark(self) -> bool:
        return self._dark

    @property
    def colors(self) -> ColorTokens:
        return DARK_COLORS if self._dark else LIGHT_COLORS

    def apply(self, application: QApplication, mode: ThemeMode | str) -> bool:
        try:
            selected = mode if isinstance(mode, ThemeMode) else ThemeMode(mode)
        except ValueError:
            selected = ThemeMode.SYSTEM
        dark = self._resolve_dark(application, selected)
        application.setStyleSheet(DARK_STYLESHEET if dark else LIGHT_STYLESHEET)
        self._mode = selected
        self._dark = dark
        self._settings.setValue(self.SETTINGS_KEY, selected.value)
        self.changed.emit(selected.value, dark)
        return dark

    def apply_configured(self, application: QApplication) -> bool:
        return self.apply(application, self._read_mode())

    def _read_mode(self) -> ThemeMode:
        configured = str(
            self._settings.value(self.SETTINGS_KEY, ThemeMode.SYSTEM.value)
        )
        try:
            return ThemeMode(configured)
        except ValueError:
            return ThemeMode.SYSTEM

    @staticmethod
    def _resolve_dark(application: QApplication, mode: ThemeMode) -> bool:
        if mode is ThemeMode.DARK:
            return True
        if mode is ThemeMode.LIGHT:
            return False
        return application.palette().color(QPalette.ColorRole.Window).lightness() < 128
