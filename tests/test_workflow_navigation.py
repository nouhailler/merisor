from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from merisor.ui.application_shell import WorkflowState, WorkflowStep
from merisor.ui.main_window import MainWindow


def test_invalid_transformation_redirects_to_validation_center(
    qapp: QApplication,
) -> None:
    window = MainWindow()
    window.controller.create_entity("CLIENT", QPointF())

    window.generate_mld()

    assert window.workspace_tabs.currentWidget() is window.validation_center
    assert (
        window.workflow_navigation.buttons[WorkflowStep.VERIFY].property(
            "workflowState"
        )
        == WorkflowState.ERROR.value
    )
    window.controller.undo_stack.setClean()
    window.close()


def test_workflow_marks_mld_ready_and_enables_production(
    qapp: QApplication,
) -> None:
    window = MainWindow()
    entity = window.controller.create_entity("CLIENT", QPointF())
    window.controller.add_attribute(entity.id, "id_client", True)

    window.generate_mld()

    transform = window.workflow_navigation.buttons[WorkflowStep.TRANSFORM]
    produce = window.workflow_navigation.buttons[WorkflowStep.PRODUCE]
    assert transform.property("workflowState") == WorkflowState.READY.value
    assert produce.isEnabled()
    assert window.workspace_tabs.currentWidget() is window.mld_view
    window.controller.undo_stack.setClean()
    window.close()
