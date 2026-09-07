"""Feuille de style du thème clair MERISOR."""

from merisor.ui.theme.tokens import LIGHT_COLORS, build_stylesheet

LIGHT_STYLESHEET = build_stylesheet(LIGHT_COLORS)

__all__ = ["LIGHT_STYLESHEET"]
