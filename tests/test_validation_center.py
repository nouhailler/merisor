from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from merisor.domain import (
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)
from merisor.ui.main_window import MainWindow
from merisor.ui.validation_center import ValidationCenter


def test_validation_center_groups_counts_and_explains_issues(
    qapp: QApplication,
) -> None:
    center = ValidationCenter()
    center.set_report(
        ValidationReport(
            (
                ValidationIssue(
                    ValidationSeverity.ERROR,
                    "entity.identifier_missing",
                    "Entité CLIENT : aucun identifiant défini.",
                    "entity-1",
                ),
                ValidationIssue(
                    ValidationSeverity.WARNING,
                    "entity.name_duplicate",
                    "Nom CLIENT dupliqué.",
                ),
            )
        )
    )

    assert center.error_count.text() == "1"
    assert center.warning_count.text() == "1"
    assert center.issue_tree.topLevelItemCount() == 2
    center._show_why()
    assert "Pourquoi" in center.details.toPlainText()
    center.close()


def test_validation_center_locates_problem_in_main_canvas(
    qapp: QApplication,
) -> None:
    window = MainWindow()
    entity = window.controller.create_entity("CLIENT", QPointF())

    window.show_validation()
    assert window.workspace_tabs.currentWidget() is window.validation_center
    window.validation_center.locate_requested.emit(entity.id)

    assert window.workspace_tabs.currentWidget() is window.view
    assert window.controller._node_items[entity.id].isSelected()
    window.controller.undo_stack.setClean()
    window.close()
