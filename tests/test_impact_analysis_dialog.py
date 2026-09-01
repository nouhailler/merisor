from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QTreeWidget

from merisor.domain import Attribute, Entity, MCDModel
from merisor.ui.impact_analysis_dialog import ImpactAnalysisDialog


def test_impact_dialog_selects_requested_attribute(qapp: object) -> None:
    model = MCDModel()
    attribute = Attribute("id_client", True, id="client-id")
    model.add_entity(Entity("CLIENT", id="client", attributes=[attribute]))

    dialog = ImpactAnalysisDialog(model, attribute.id)
    combo = dialog.findChild(QComboBox)
    tree = dialog.findChild(QTreeWidget)

    assert combo is not None
    assert combo.currentData() == attribute.id
    assert tree is not None
    assert tree.topLevelItemCount() == 2
