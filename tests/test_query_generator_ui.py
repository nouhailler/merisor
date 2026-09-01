from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from merisor.domain import (
    MLDColumn,
    MLDDataType,
    MLDForeignKey,
    MLDModel,
    MLDTable,
    MLDTableSource,
)
from merisor.ui.main_window import MainWindow
from merisor.ui.query_generator_dialog import QueryGeneratorDialog


def _model() -> MLDModel:
    client = MLDTable(
        "client",
        "CLIENT",
        "client-source",
        MLDTableSource.ENTITY,
        columns=[
            MLDColumn("client-id", "id_client", False, MLDDataType("INTEGER")),
            MLDColumn("client-name", "nom", False, MLDDataType.varchar(100)),
        ],
        primary_key=("client-id",),
    )
    order = MLDTable(
        "order",
        "COMMANDE",
        "order-source",
        MLDTableSource.ENTITY,
        columns=[
            MLDColumn("order-id", "id_commande", False, MLDDataType("INTEGER")),
            MLDColumn("order-client", "id_client", False, MLDDataType("INTEGER")),
            MLDColumn(
                "order-amount",
                "montant",
                False,
                MLDDataType("DECIMAL", precision=10, scale=2),
            ),
        ],
        primary_key=("order-id",),
        foreign_keys=[
            MLDForeignKey(
                "order-client-fk",
                ("order-client",),
                "client",
                ("client-id",),
                "place",
            )
        ],
    )
    return MLDModel([client, order], "fingerprint")


def test_dialog_generates_explains_copies_and_exports(
    qapp: QApplication, tmp_path: Path
) -> None:
    dialog = QueryGeneratorDialog(_model(), "Commerce")
    dialog.description_edit.setPlainText(
        "Afficher les 5 meilleurs clients selon le montant total des commandes"
    )

    assert dialog.generate_preview()
    assert 'SUM(t2."montant")' in dialog.query
    assert dialog.query.endswith("LIMIT 5;\n")
    assert "CLIENT, COMMANDE" in dialog.tables_label.text()
    dialog.copy_query()
    assert qapp.clipboard().text() == dialog.query

    destination = dialog.export_to(tmp_path / "clients_top")
    assert destination.suffix == ".sql"
    assert destination.read_text(encoding="utf-8") == dialog.query
    dialog.close()


def test_query_action_tracks_current_mld(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow()
    assert not window.generate_query_action.isEnabled()
    entity = window.controller.create_entity("CLIENT", QPointF())
    identifier = window.controller.add_attribute(entity.id, "id_client")
    window.controller.set_attribute_identifier(entity.id, identifier.id, True)
    generated = window.controller.generate_mld()
    qapp.processEvents()
    assert window.generate_query_action.isEnabled()

    captured: dict[str, object] = {}

    class FakeQueryGeneratorDialog:
        def __init__(self, model, project_name, parent) -> None:  # type: ignore[no-untyped-def]
            captured.update(model=model, project_name=project_name, parent=parent)

        def exec(self) -> int:
            captured["executed"] = True
            return 0

    monkeypatch.setattr(
        "merisor.ui.main_window.QueryGeneratorDialog", FakeQueryGeneratorDialog
    )
    window.generate_query()

    assert captured["model"] is generated
    assert captured["executed"] is True
    assert window.generate_query_action.shortcut().toString() == "Ctrl+Alt+R"
    window.controller.rename_node(entity.id, "ACHETEUR")
    assert not window.generate_query_action.isEnabled()

    window.controller.undo_stack.setClean()
    window.close()
    qapp.processEvents()
