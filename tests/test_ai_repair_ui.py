from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import QPointF, Qt

from merisor.application import AiRepairService, DiagramController
from merisor.domain import Attribute, Entity, MCDModel
from merisor.persistence import JsonDiagramRepository
from merisor.ui.ai_repair_dialog import AiRepairDialog
from merisor.ui.canvas import DiagramScene


def _report_model() -> tuple[MCDModel, str]:
    model = MCDModel()
    entity = Entity(
        "CLIENT",
        attributes=[Attribute("id_client", True), Attribute("email")],
    )
    model.add_entity(entity)
    payload = JsonDiagramRepository().to_dict(model)
    raw_entity = payload["entities"][0]
    attributes = raw_entity["attributes"]
    attributes[1]["unique"] = True
    patch = {
        "entities_to_add": [],
        "entities_to_update": [
            {"id": entity.id, "changes": {"attributes": attributes}}
        ],
        "entity_ids_to_remove": [],
        "associations_to_add": [],
        "associations_to_update": [],
        "association_ids_to_remove": [],
        "relations_to_add": [],
        "relations_to_update": [],
        "relation_ids_to_remove": [],
        "inheritances_to_add": [],
        "inheritances_to_update": [],
        "inheritance_ids_to_remove": [],
        "functional_dependencies_to_add": [],
        "functional_dependencies_to_update": [],
        "functional_dependency_ids_to_remove": [],
    }
    raw = json.dumps(
        {
            "summary": "Une amélioration",
            "proposals": [
                {
                    "id": "unique_email",
                    "title": "Email unique",
                    "description": "CLIENT.email devrait être UNIQUE.",
                    "rationale": "Un email identifie souvent un compte.",
                    "confidence": "medium",
                    "patch": patch,
                }
            ],
        }
    )
    return model, raw


def test_repair_dialog_lists_validated_proposals_and_can_ignore_them(
    qapp: Any,
) -> None:
    model, raw = _report_model()
    dialog = AiRepairDialog(model)
    dialog.display_report(AiRepairService().interpret(model, raw))

    item = dialog.proposals.topLevelItem(0)
    assert item is not None
    assert item.checkState(0) == Qt.CheckState.Checked
    assert item.text(2) == "Email unique"
    assert dialog.summary_label.text() == "Une amélioration"
    assert "Pourquoi ?" in dialog.details.toPlainText()
    assert dialog.apply_button.isEnabled()

    dialog.ignore_selected()
    assert item.checkState(0) == Qt.CheckState.Unchecked
    assert item.text(3) == "Ignorée"
    assert not dialog.apply_button.isEnabled()


def test_confirmed_repair_is_a_single_undoable_model_replacement(qapp: Any) -> None:
    model, raw = _report_model()
    candidate = AiRepairService().interpret(model, raw).proposals[0].candidate
    controller = DiagramController(DiagramScene())
    controller.create_entity("EXISTANT", QPointF())
    before = JsonDiagramRepository().to_dict(controller.model)

    controller.apply_ai_repair_model(candidate)

    assert {item.name for item in controller.model.entities.values()} == {"CLIENT"}
    assert controller.undo_stack.undoText() == "Appliquer les améliorations IA"
    controller.undo_stack.undo()
    assert JsonDiagramRepository().to_dict(controller.model) == before
