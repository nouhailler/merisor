from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from merisor.domain import (
    MLDColumn,
    MLDDataType,
    MLDDataTypeName,
    MLDModel,
    MLDTable,
    MLDTableSource,
)
from merisor.ui.sql_workspace import SQLWorkspace


def sql_model(*, primary_key: bool = True) -> MLDModel:
    identifier = MLDColumn(
        id="pilot.id",
        name="id_pilote",
        nullable=False,
        data_type=MLDDataType(MLDDataTypeName.INTEGER),
    )
    return MLDModel(
        [
            MLDTable(
                id="pilot",
                name="PILOTE",
                source_element_id="entity:pilot",
                source=MLDTableSource.ENTITY,
                columns=[identifier],
                primary_key=(identifier.id,) if primary_key else (),
            )
        ],
        generated_from_fingerprint="test",
    )


def test_sql_workspace_generates_searches_copies_and_exports(
    qapp: QApplication, tmp_path: Path
) -> None:
    workspace = SQLWorkspace()

    assert workspace.set_model(sql_model(), "MotoGP")
    assert "PostgreSQL" in workspace.script
    assert workspace.code_editor.line_numbers.toPlainText().startswith("1\n2")
    workspace.search_field.setText("PILOTE")
    assert "occurrence" in workspace.result_label.text()
    workspace.copy_sql()
    assert qapp.clipboard().text() == workspace.script
    exported = workspace.export_to(tmp_path / "motogp")
    assert exported.suffix == ".sql"

    workspace.target_combo.setCurrentIndex(workspace.target_combo.findData("sqlite"))
    assert "PRAGMA foreign_keys = ON" in workspace.script
    workspace.close()


def test_sql_workspace_blocks_invalid_mld(qapp: QApplication) -> None:
    workspace = SQLWorkspace()

    assert not workspace.set_model(sql_model(primary_key=False), "Invalide")
    assert "Impossible de générer le SQL" in workspace.script
    assert not workspace.copy_button.isEnabled()
    assert not workspace.export_button.isEnabled()
    workspace.close()
