from __future__ import annotations

import copy
import json
from typing import Any

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QMessageBox

from merisor.application import (
    ConversationalDesignService,
    DesignSession,
    DesignSessionError,
    DiagramController,
    compare_models,
)
from merisor.domain import Attribute, Entity, MCDModel, Position, validate_mcd
from merisor.ui.canvas import DiagramScene
from merisor.ui.conversational_design_dialog import (
    ConversationalDesignDialog,
    DesignDraftPreviewDialog,
)
from merisor.ui.main_window import MainWindow


def empty_patch() -> dict[str, list[Any]]:
    return {
        "entities_to_add": [],
        "entities_to_update": [],
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


def response_payload(**changes: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "assistant_message": "J'ai identifié le concept CLIENT.",
        "detected_concepts": [{"name": "CLIENT", "kind": "entity", "confidence": 0.94}],
        "questions": [
            {
                "id": "client_email",
                "text": "L'adresse électronique est-elle unique ?",
                "choices": ["Oui", "Non"],
                "impact": "Ajoute ou non une contrainte UNIQUE.",
            }
        ],
        "assumptions": ["Un client possède une seule adresse électronique."],
        "draft_patch": empty_patch(),
        "ready_for_preview": False,
    }
    payload.update(changes)
    return payload


def client_entity_payload() -> dict[str, Any]:
    return {
        "id": "entity.client",
        "name": "CLIENT",
        "position": {"x": 100, "y": 100},
        "attributes": [
            {
                "id": "attribute.client.id",
                "name": "id_client",
                "identifier": True,
                "data_type": {"name": "INTEGER"},
                "nullable": False,
                "default": None,
                "unique": False,
                "comment": "",
                "auto_increment": True,
                "constraints": [],
            }
        ],
    }


def test_conversation_applies_strict_patch_without_mutating_source() -> None:
    source = MCDModel()
    original = Entity(
        "ORIGINAL",
        Position(10, 20),
        id="entity.original",
        attributes=[Attribute("id_original", True, id="attribute.original.id")],
    )
    source.add_entity(original)
    snapshot = copy.deepcopy(source)
    session = DesignSession(current_draft=source)
    patch = empty_patch()
    patch["entities_to_add"] = [client_entity_payload()]

    step = ConversationalDesignService().interpret(
        session, json.dumps(response_payload(draft_patch=patch))
    )

    assert set(step.draft_model.entities) == {"entity.original", "entity.client"}
    assert source.entities == snapshot.entities
    assert session.current_draft.entities == snapshot.entities
    session.accept_step("Je veux gérer des clients.", step)
    assert len(session.revisions) == 2
    assert session.current_draft is not step.draft_model
    assert session.pending_questions[0].id == "client_email"


def test_session_records_answers_and_can_rewind() -> None:
    session = DesignSession()
    patch = empty_patch()
    patch["entities_to_add"] = [client_entity_payload()]
    step = ConversationalDesignService().interpret(
        session, json.dumps(response_payload(draft_patch=patch))
    )
    session.accept_step("Des clients", step)
    session.record_answer("client_email", "Oui")

    assert session.all_pending_questions_answered
    assert "Réponse : Oui" in session.formatted_answers()
    assert session.rewind()
    assert not session.current_draft.entities
    assert len(session.revisions) == 1


def test_service_rejects_unknown_updates_and_non_strict_answers() -> None:
    session = DesignSession()
    patch = empty_patch()
    patch["entities_to_update"] = [{"id": "absent", "changes": {"name": "INCONNU"}}]
    with pytest.raises(DesignSessionError, match="absent"):
        ConversationalDesignService().interpret(
            session, json.dumps(response_payload(draft_patch=patch))
        )

    invalid = response_payload(unexpected=True)
    with pytest.raises(DesignSessionError, match="Champs racine invalides"):
        ConversationalDesignService().interpret(session, json.dumps(invalid))


def test_validation_prevents_ready_preview_when_draft_has_errors() -> None:
    session = DesignSession()
    patch = empty_patch()
    entity = client_entity_payload()
    entity["attributes"] = []
    patch["entities_to_add"] = [entity]
    step = ConversationalDesignService().interpret(
        session,
        json.dumps(
            response_payload(
                draft_patch=patch,
                questions=[],
                ready_for_preview=True,
            )
        ),
    )
    assert step.report.errors
    assert not step.response.ready_for_preview


def test_unanswered_questions_prevent_ready_preview() -> None:
    session = DesignSession()
    patch = empty_patch()
    patch["entities_to_add"] = [client_entity_payload()]
    step = ConversationalDesignService().interpret(
        session,
        json.dumps(response_payload(draft_patch=patch, ready_for_preview=True)),
    )
    assert step.report.is_valid
    assert step.response.questions
    assert not step.response.ready_for_preview


def test_model_difference_reports_logical_changes() -> None:
    current = MCDModel()
    draft = MCDModel()
    draft.add_entity(
        Entity(
            "CLIENT",
            id="entity.client",
            attributes=[Attribute("id_client", True, id="attribute.client.id")],
        )
    )
    difference = compare_models(current, draft)
    assert difference.added_entities == ("CLIENT",)
    assert "Entités ajoutées" in difference.render()


def test_confirmed_conversational_import_is_undoable(qapp) -> None:  # type: ignore[no-untyped-def]
    scene = DiagramScene()
    controller = DiagramController(scene)
    original = controller.create_entity("ORIGINAL", QPointF(10, 20))
    candidate = MCDModel()
    candidate.add_entity(
        Entity(
            "CLIENT",
            id="entity.client",
            attributes=[Attribute("id_client", True, id="attribute.client.id")],
        )
    )

    controller.import_conversational_model(candidate)
    assert set(controller.model.entities) == {"entity.client"}
    controller.undo_stack.undo()
    assert set(controller.model.entities) == {original.id}
    controller.undo_stack.redo()
    assert set(controller.model.entities) == {"entity.client"}


def test_conversational_dialog_keeps_current_model_isolated(qapp) -> None:  # type: ignore[no-untyped-def]
    source = MCDModel()
    source.add_entity(
        Entity(
            "ORIGINAL",
            id="entity.original",
            attributes=[Attribute("id_original", True, id="attribute.original.id")],
        )
    )
    dialog = ConversationalDesignDialog(source)
    patch = empty_patch()
    patch["entities_to_add"] = [client_entity_payload()]
    step = ConversationalDesignService().interpret(
        dialog.session,
        json.dumps(
            response_payload(
                draft_patch=patch,
                questions=[],
                ready_for_preview=True,
            )
        ),
    )
    dialog._pending_message = "Ajouter CLIENT"
    dialog._request_succeeded(step)
    dialog._request_finished()

    assert set(source.entities) == {"entity.original"}
    assert set(dialog.session.current_draft.entities) == {
        "entity.original",
        "entity.client",
    }
    assert dialog.preview_button.isEnabled()
    dialog.close()


def test_preview_requires_explicit_confirmation(qapp, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    draft = MCDModel()
    draft.add_entity(
        Entity(
            "CLIENT",
            id="entity.client",
            attributes=[Attribute("id_client", True, id="attribute.client.id")],
        )
    )
    dialog = DesignDraftPreviewDialog(
        MCDModel(),
        draft,
        DesignSession(current_draft=draft).current_json(),
        validate_mcd(draft),
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    dialog._confirm()
    assert dialog.import_confirmed
    dialog.close()


def test_main_window_exposes_conversational_assistant(qapp) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()
    assert "conversationnel" in window.conversational_assistant_action.text().lower()
    assert window.conversational_assistant_action.shortcut().toString()
    window.close()
