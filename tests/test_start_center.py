from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from merisor.ui.main_window import MainWindow
from merisor.ui.start_center import StartCenter


def test_start_center_presents_primary_and_import_paths(qapp: QApplication) -> None:
    center = StartCenter()

    assert center.new_button.property("role") == "primary"
    assert "Nouveau" in center.new_button.text()
    assert "IA" in center.ai_button.text()
    assert center.import_ddl_button.isEnabled()
    assert center.import_pwa_button.isEnabled()
    center.close()


def test_start_center_populates_recent_files_and_examples(
    qapp: QApplication, tmp_path: Path
) -> None:
    center = StartCenter()
    recent = tmp_path / "client.json"
    example = tmp_path / "moto_gp.json"

    center.set_recent_files([str(recent)])
    center.set_examples([example])

    assert center.recent_list.item(0).text() == "client"
    assert center.recent_list.item(0).data(Qt.ItemDataRole.UserRole) == str(recent)
    assert center.example_list.item(0).text() == "Moto Gp"
    center.close()


def test_main_window_starts_on_welcome_without_reordering_legacy_tabs(
    qapp: QApplication,
) -> None:
    window = MainWindow()

    assert window.workspace_tabs.widget(0) is window.view
    assert window.workspace_tabs.widget(1) is window.mld_view
    assert window.workspace_tabs.currentWidget() is window.start_center

    window.new_document()

    assert window.workspace_tabs.currentWidget() is window.view
    window.close()
