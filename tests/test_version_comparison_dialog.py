from __future__ import annotations

from PySide6.QtWidgets import QPlainTextEdit, QTreeWidget

from merisor.application import ModelVersionComparator
from merisor.domain import Attribute, Entity, MCDModel
from merisor.ui.version_comparison_dialog import VersionComparisonDialog


def test_version_comparison_dialog_lists_changes_and_impacts(qapp: object) -> None:
    reference = MCDModel()
    reference.add_entity(
        Entity("CLIENT", id="client", attributes=[Attribute("id", True, id="id")])
    )
    current = MCDModel()
    comparison = ModelVersionComparator().compare(reference, current)

    dialog = VersionComparisonDialog(comparison, "ancienne-version.json")
    tree = dialog.findChild(QTreeWidget)
    impact = dialog.findChild(QPlainTextEdit)

    assert tree is not None
    assert tree.topLevelItemCount() == 1
    first_item = tree.topLevelItem(0)
    assert first_item is not None
    assert first_item.text(1) == "CLIENT"
    assert impact is not None
    assert "IMPACT DU CHANGEMENT" in impact.toPlainText()
