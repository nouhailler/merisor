from __future__ import annotations

from PySide6.QtCore import QSettings

from merisor.application import OpenRouterKeyStore
from merisor.ui.main_window import MainWindow
from merisor.ui.openrouter_settings_dialog import OpenRouterSettingsDialog


def test_openrouter_key_store_round_trip(qapp) -> None:  # type: ignore[no-untyped-def]
    settings = QSettings("MERISOR", "MERISOR")
    settings.remove("openrouter/api_key")
    store = OpenRouterKeyStore(settings)
    store.set(" sk-or-v1-test ")
    assert store.get() == "sk-or-v1-test"
    store.set("")
    assert store.get() == ""


def test_openrouter_settings_dialog_saves_key(qapp) -> None:  # type: ignore[no-untyped-def]
    settings = QSettings("MERISOR", "MERISOR")
    settings.remove("openrouter/api_key")
    dialog = OpenRouterSettingsDialog()
    dialog.key_edit.setText("sk-or-v1-dialog")
    dialog._save()
    assert dialog.result() == dialog.DialogCode.Accepted
    assert OpenRouterKeyStore(settings).get() == "sk-or-v1-dialog"
    settings.remove("openrouter/api_key")
    dialog.close()


def test_main_window_exposes_openrouter_settings_menu(qapp) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()
    assert window.openrouter_settings_action.text() == "Paramètres OpenRouter…"
    assert any(action.text() == "Paramètres" for action in window.menuBar().actions())
    window.close()
