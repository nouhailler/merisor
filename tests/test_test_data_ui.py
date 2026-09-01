from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from merisor.domain import MLDColumn, MLDDataType, MLDModel, MLDTable, MLDTableSource
from merisor.ui.main_window import MainWindow
from merisor.ui.test_data_dialog import TestDataDialog as DataDialog


def _preview_model() -> MLDModel:
    identifier = MLDColumn("pilot-id", "id_pilote", False, MLDDataType("INTEGER"))
    name = MLDColumn("pilot-name", "nom", False, MLDDataType.varchar(100))
    table = MLDTable(
        id="pilot",
        name="PILOTE",
        source_element_id="entity:pilot",
        source=MLDTableSource.ENTITY,
        columns=[identifier, name],
        primary_key=(identifier.id,),
    )
    return MLDModel([table], "fingerprint")


def test_dialog_generates_copies_and_exports_without_execution(
    qapp: QApplication, tmp_path: Path
) -> None:
    dialog = DataDialog(_preview_model(), "MotoGP")
    dialog._count_editors["pilot"].setValue(3)

    assert dialog.generate_preview()
    assert dialog.script.count("(") >= 3
    assert 'INSERT INTO "PILOTE"' in dialog.script
    assert "n'a pas été exécuté" in dialog.script
    dialog.copy_script()
    assert qapp.clipboard().text() == dialog.script

    exported = dialog.export_to(tmp_path / "motogp_data")
    assert exported.suffix == ".sql"
    assert exported.read_text(encoding="utf-8") == dialog.script
    dialog.close()


def test_test_data_action_tracks_the_current_mld(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow()
    assert not window.generate_test_data_action.isEnabled()
    entity = window.controller.create_entity("PILOTE", QPointF())
    identifier = window.controller.add_attribute(entity.id, "id_pilote")
    window.controller.set_attribute_identifier(entity.id, identifier.id, True)
    generated = window.controller.generate_mld()
    qapp.processEvents()
    assert window.generate_test_data_action.isEnabled()

    captured: dict[str, object] = {}

    class FakeTestDataDialog:
        def __init__(self, model, project_name, parent) -> None:  # type: ignore[no-untyped-def]
            captured.update(model=model, project_name=project_name, parent=parent)

        def exec(self) -> int:
            captured["executed"] = True
            return 0

    monkeypatch.setattr("merisor.ui.main_window.TestDataDialog", FakeTestDataDialog)
    window.generate_test_data()

    assert captured["model"] is generated
    assert captured["executed"] is True
    assert window.generate_test_data_action.shortcut().toString() == "Ctrl+Alt+T"
    window.controller.rename_node(entity.id, "AVIATEUR")
    assert not window.generate_test_data_action.isEnabled()

    window.controller.undo_stack.setClean()
    window.close()
    qapp.processEvents()
