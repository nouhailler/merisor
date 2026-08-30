from __future__ import annotations

import json

import pytest
from PySide6.QtCore import QPointF

from merisor.application import AiMcdService, AiMcdValidationError, OpenRouterClient
from merisor.application.controller import DiagramController
from merisor.ui.ai_mcd_dialog import MCDPreviewDialog
from merisor.ui.canvas import DiagramScene


def valid_mcd_data() -> dict:
    return {
        "format_version": 2,
        "entities": [
            {
                "id": "pilot",
                "name": "PILOTE",
                "position": {"x": 100, "y": 100},
                "attributes": [
                    {"id": "pilot.id", "name": "id_pilote", "identifier": True}
                ],
            },
            {
                "id": "team",
                "name": "EQUIPE",
                "position": {"x": 500, "y": 100},
                "attributes": [
                    {"id": "team.id", "name": "id_equipe", "identifier": True}
                ],
            },
        ],
        "associations": [
            {
                "id": "engage",
                "name": "ENGAGER",
                "position": {"x": 300, "y": 300},
                "attributes": [],
                "is_historized": True,
                "materialization_strategy": "AUTO",
            }
        ],
        "relations": [
            {
                "id": "pilot.engage",
                "entity_id": "pilot",
                "association_id": "engage",
                "cardinality": {"minimum": "0", "maximum": "N"},
            },
            {
                "id": "team.engage",
                "entity_id": "team",
                "association_id": "engage",
                "cardinality": {"minimum": "1", "maximum": "1"},
            },
        ],
    }


def test_ai_service_accepts_fenced_json_and_validates_merise() -> None:
    text = "```json\n" + json.dumps(valid_mcd_data()) + "\n```"
    candidate = AiMcdService().validate_json(text)
    assert candidate.report.is_valid
    assert set(candidate.model.entities) == {"pilot", "team"}
    assert candidate.model.associations["engage"].is_historized


def test_ai_service_rejects_invalid_json_and_reports_invalid_mcd() -> None:
    service = AiMcdService()
    with pytest.raises(AiMcdValidationError, match="JSON invalide"):
        service.validate_json("{invalid}")

    data = valid_mcd_data()
    data["entities"][0]["attributes"][0]["identifier"] = False
    candidate = service.validate_json(json.dumps(data))
    assert not candidate.report.is_valid
    assert any(issue.code == "entity.identifier_missing" for issue in candidate.report.errors)


def test_openrouter_completion_extracts_assistant_content() -> None:
    client = OpenRouterClient("sk-or-test")
    captured: dict = {}

    def fake_post(path: str, data: dict) -> dict:
        captured.update(path=path, data=data)
        return {"choices": [{"message": {"content": '{"format_version": 2}'}}]}

    client._post = fake_post  # type: ignore[method-assign]
    content = client.complete("free/model:free", "system", "description")
    assert captured["path"] == "/chat/completions"
    assert captured["data"]["model"] == "free/model:free"
    assert content == '{"format_version": 2}'


def test_preview_blocks_invalid_mcd_and_accepts_corrected_json(qapp) -> None:  # type: ignore[no-untyped-def]
    data = valid_mcd_data()
    data["entities"][0]["attributes"][0]["identifier"] = False
    dialog = MCDPreviewDialog(json.dumps(data), AiMcdService())
    assert not dialog.import_button.isEnabled()

    dialog.json_edit.setPlainText(json.dumps(valid_mcd_data()))
    dialog.revalidate()
    assert dialog.import_button.isEnabled()
    assert dialog.candidate is not None
    dialog.close()


def test_controller_import_replaces_only_on_explicit_call_and_marks_dirty(qapp) -> None:  # type: ignore[no-untyped-def]
    scene = DiagramScene()
    controller = DiagramController(scene)
    original = controller.create_entity("ORIGINAL", QPointF())
    candidate = AiMcdService().validate_json(json.dumps(valid_mcd_data()))

    assert original.id in controller.model.entities
    controller.import_generated_model(candidate.model)
    assert original.id not in controller.model.entities
    assert set(controller.model.entities) == {"pilot", "team"}
    assert controller.is_dirty
