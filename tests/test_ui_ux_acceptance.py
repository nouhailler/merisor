from __future__ import annotations

from PySide6.QtWidgets import QApplication

from merisor.ui.application_shell import WorkflowStep
from merisor.ui.main_window import MainWindow


def test_main_workspace_remains_usable_at_supported_desktop_sizes(
    qapp: QApplication,
) -> None:
    window = MainWindow()
    window.workspace_tabs.setCurrentWidget(window.view)
    window.show()

    for width, height in ((1280, 720), (1366, 768), (1920, 1080), (2560, 1440)):
        window.resize(width, height)
        qapp.processEvents()
        assert window.workspace_tabs.width() >= 500
        assert window.workspace_tabs.height() >= 500

    window.controller.undo_stack.setClean()
    window.close()


def test_primary_navigation_and_discovery_are_keyboard_accessible(
    qapp: QApplication,
) -> None:
    window = MainWindow()

    assert window.command_palette_action.shortcut().toString() == "Ctrl+K"
    assert window.global_search_action.shortcut().toString() == "Ctrl+Shift+F"
    assert window.documentation_action.shortcut().toString() == "F1"
    assert window.undo_action.toolTip()
    assert window.redo_action.toolTip()
    assert window.visual_search.placeholderText()
    assert all(
        button.accessibleName()
        for button in window.workflow_navigation.buttons.values()
    )
    assert window.workflow_navigation.buttons[WorkflowStep.DESIGN].isChecked()

    window.controller.undo_stack.setClean()
    window.close()
