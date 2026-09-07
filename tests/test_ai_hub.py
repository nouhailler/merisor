from __future__ import annotations

from PySide6.QtWidgets import QPushButton

from merisor.ui.ai_hub import AIHub
from merisor.ui.application_shell import WorkflowStep
from merisor.ui.main_window import MainWindow


def test_ai_hub_exposes_guided_actions(qapp) -> None:  # type: ignore[no-untyped-def]
    hub = AIHub()
    requested: list[str] = []
    hub.action_requested.connect(requested.append)

    buttons = hub.findChildren(QPushButton)
    assert len(buttons) == 6
    buttons[0].click()
    assert requested == ["conversation"]
    hub.close()


def test_ai_workflow_opens_integrated_hub(qapp) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()

    window.workflow_navigation.buttons[WorkflowStep.AI].click()

    assert window.workspace_tabs.currentWidget() is window.ai_hub
    assert not window.properties_dock.isVisible()
    window.controller.undo_stack.setClean()
    window.close()
