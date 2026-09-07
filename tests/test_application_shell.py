from __future__ import annotations

from PySide6.QtWidgets import QApplication, QDockWidget, QToolBar

from merisor.ui.application_shell import (
    WorkflowNavigation,
    WorkflowState,
    WorkflowStep,
)
from merisor.ui.main_window import MainWindow


def test_workflow_navigation_exposes_all_user_steps(qapp: QApplication) -> None:
    navigation = WorkflowNavigation()

    assert tuple(navigation.buttons) == tuple(WorkflowStep)
    assert navigation.buttons[WorkflowStep.DESIGN].isChecked()
    assert all(button.accessibleName() for button in navigation.buttons.values())
    navigation.set_state(WorkflowStep.TRANSFORM, WorkflowState.STALE, "À régénérer")
    assert (
        navigation.buttons[WorkflowStep.TRANSFORM].property("workflowState") == "stale"
    )
    assert "↻" in navigation.buttons[WorkflowStep.TRANSFORM].text()


def test_main_window_uses_project_and_workflow_toolbars(qapp: QApplication) -> None:
    window = MainWindow()

    assert window.findChild(QToolBar, "diagramToolbar") is not None
    assert window.findChild(QToolBar, "workflowToolbar") is not None
    assert window.findChild(QDockWidget, "toolsDock") is window.tools_dock
    assert window.centralWidget() is window.workspace_tabs
    assert window.visual_search.parent() is window.tool_palette
    window.close()


def test_shell_status_tracks_invalid_and_stale_states(qapp: QApplication) -> None:
    window = MainWindow()

    assert "valide" in window.model_status.validation_label.text().lower()
    assert "non généré" in window.model_status.mld_label.text().lower()
    assert "non généré" in window.model_status.sql_label.text().lower()
    assert not window.workflow_navigation.buttons[WorkflowStep.PRODUCE].isEnabled()

    window.controller.create_entity("CLIENT", window.view.mapToScene(20, 20))

    assert "erreur" in window.model_status.validation_label.text().lower()
    assert "modifié" in window.model_status.document_label.text().lower()
    window.controller.undo_stack.setClean()
    window.close()
