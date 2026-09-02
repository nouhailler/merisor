from __future__ import annotations

from typing import Any

from PySide6.QtTest import QSignalSpy

from merisor.application import (
    McdToMldTransformer,
    MldTransformationExplainer,
    TransformationExplanationReport,
)
from merisor.domain import Attribute, Entity, MCDModel, MLDTable
from merisor.ui.mld_properties_panel import MLDPropertiesPanel
from merisor.ui.transformation_explanation_dialog import (
    TransformationExplanationDialog,
)


def _report() -> tuple[MLDTable, TransformationExplanationReport]:
    model = MCDModel()
    model.add_entity(Entity("CLIENT", attributes=[Attribute("id_client", True)]))
    mld = McdToMldTransformer().transform(model)
    table = mld.table("CLIENT")
    return table, MldTransformationExplainer().explain_table(model, mld, table)


def test_mld_properties_exposes_why_only_for_a_selected_table(qapp: Any) -> None:
    table, _report_value = _report()
    panel = MLDPropertiesPanel()
    spy = QSignalSpy(panel.why_requested)

    assert not panel.why_button.isEnabled()
    panel.display(table)
    assert panel.why_button.isEnabled()

    panel.why_button.click()
    assert spy.count() == 1
    assert spy.at(0)[0] is table

    panel.set_stale(True)
    assert not panel.why_button.isEnabled()
    assert "Régénérez" in panel.why_button.toolTip()
    panel.set_stale(False)
    assert panel.why_button.isEnabled()

    panel.clear()
    assert not panel.why_button.isEnabled()


def test_explanation_dialog_lists_rules_and_details(qapp: Any) -> None:
    _table, report = _report()
    dialog = TransformationExplanationDialog(report)

    assert dialog.windowTitle() == "Pourquoi ? — CLIENT"
    assert dialog.decisions.topLevelItemCount() >= 3
    assert "Règle appliquée" in dialog.details.toPlainText()
    assert "Provenance MCD" in dialog.details.toPlainText()
