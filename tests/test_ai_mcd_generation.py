from __future__ import annotations

import json
from threading import Event
import time

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QDialog

from merisor.application import AiMcdService, AiMcdValidationError, OpenRouterClient
from merisor.application.controller import DiagramController
from merisor.ui.ai_mcd_dialog import AiMcdDialog, MCDPreviewDialog
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


def test_ai_generation_runs_outside_the_ui_thread(qapp, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    started = Event()
    release = Event()

    class FakeStore:
        @staticmethod
        def get() -> str:
            return "sk-or-test"

        @staticmethod
        def get_model() -> str:
            return "free/model:free"

        @staticmethod
        def is_enabled() -> bool:
            return True

    def slow_generate(*_args) -> str:  # type: ignore[no-untyped-def]
        started.set()
        release.wait(timeout=2)
        return json.dumps(valid_mcd_data())

    monkeypatch.setattr(MCDPreviewDialog, "exec", lambda _self: QDialog.DialogCode.Rejected)
    dialog = AiMcdDialog()
    dialog.store = FakeStore()  # type: ignore[assignment]
    monkeypatch.setattr(dialog.service, "generate", slow_generate)
    dialog.description_edit.setPlainText("Gérer des pilotes et des équipes")

    before = time.monotonic()
    dialog.generate()
    elapsed = time.monotonic() - before

    try:
        assert elapsed < 0.2
        assert started.wait(timeout=1)
        assert dialog._generation_thread is not None
        assert not dialog.progress_bar.isHidden()
        assert dialog.description_edit.isReadOnly()
    finally:
        release.set()

    deadline = time.monotonic() + 2
    while dialog._generation_thread is not None and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)

    assert dialog._generation_thread is None
    assert dialog.progress_bar.isHidden()
    assert not dialog.description_edit.isReadOnly()
    assert dialog.generate_button.isEnabled()
    dialog.close()
