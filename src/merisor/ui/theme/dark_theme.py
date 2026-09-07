"""Feuille de style du thème sombre MERISOR."""

from merisor.ui.theme.tokens import DARK_COLORS, build_stylesheet

DARK_STYLESHEET = build_stylesheet(DARK_COLORS)

__all__ = ["DARK_STYLESHEET"]
