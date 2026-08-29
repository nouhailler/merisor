from __future__ import annotations

from PySide6.QtCore import QPointF

from merisor.domain import (
    MLDColumn,
    MLDDataType,
    MLDDataTypeName,
    MLDModel,
    MLDTable,
    MLDTableSource,
)
from merisor.ui.main_window import MainWindow
from merisor.ui.mld_view import MLDTableGraphicsItem, MLDView
from merisor.ui.sql_dialog import SQLPreviewDialog


def preview_model(*, primary_key: bool = True) -> MLDModel:
    identifier = MLDColumn(
        id="pilot.id",
        name="id_pilote",
        nullable=False,
        data_type=MLDDataType(MLDDataTypeName.INTEGER),
    )
    table = MLDTable(
        id="pilot",
        name="PILOTE",
        source_element_id="entity:pilot",
        source=MLDTableSource.ENTITY,
        columns=[identifier],
        primary_key=(identifier.id,) if primary_key else (),
    )
    return MLDModel([table], generated_from_fingerprint="test")


def test_sql_preview_switches_dialect_copies_and_exports(qapp, tmp_path) -> None:  # type: ignore[no-untyped-def]
    dialog = SQLPreviewDialog(preview_model(), "MotoGP")

    assert "PostgreSQL" in dialog.script
    dialog.target_combo.setCurrentIndex(
        dialog.target_combo.findData("sqlite")
    )
    assert "PRAGMA foreign_keys = ON;" in dialog.script
    dialog.copy_sql()
    assert qapp.clipboard().text() == dialog.script

    exported = dialog.export_to(tmp_path / "motogp_sqlite")
    assert exported.suffix == ".sql"
    assert exported.read_text(encoding="utf-8") == dialog.script

    dialog.target_combo.setCurrentIndex(dialog.target_combo.findData("mysql"))
    assert "MariaDB / MySQL" in dialog.script
    assert "`PILOTE`" in dialog.script
    dialog.close()


def test_sql_preview_displays_readable_mld_errors(qapp) -> None:  # type: ignore[no-untyped-def]
    dialog = SQLPreviewDialog(preview_model(primary_key=False), "Invalide")

    assert "Impossible de générer le SQL" in dialog.script
    assert "ne possède pas de clé primaire" in dialog.script
    assert not dialog.copy_button.isEnabled()
    assert not dialog.save_button.isEnabled()
    dialog.close()


def test_generate_sql_action_tracks_current_mld_and_uses_only_it(
    qapp, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()
    assert not window.generate_sql_action.isEnabled()
    entity = window.controller.create_entity("PILOTE", QPointF())
    identifier = window.controller.add_attribute(entity.id, "id_pilote")
    window.controller.set_attribute_identifier(entity.id, identifier.id, True)

    generated = window.controller.generate_mld()
    qapp.processEvents()
    assert window.generate_sql_action.isEnabled()

    captured: dict[str, object] = {}

    class FakeSQLPreviewDialog:
        def __init__(self, model, project_name, parent) -> None:  # type: ignore[no-untyped-def]
            captured.update(
                model=model,
                project_name=project_name,
                parent=parent,
            )

        def exec(self) -> int:
            captured["executed"] = True
            return 0

    monkeypatch.setattr(
        "merisor.ui.main_window.SQLPreviewDialog", FakeSQLPreviewDialog
    )
    window.generate_sql()

    assert captured["model"] is generated
    assert captured["executed"] is True
    window.controller.rename_node(entity.id, "AVIATEUR")
    assert not window.generate_sql_action.isEnabled()
    window.controller.undo_stack.undo()
    assert window.generate_sql_action.isEnabled()

    window.controller.undo_stack.setClean()
    window.close()
    qapp.processEvents()


def test_mld_graphics_view_supports_zoom_controls(qapp) -> None:  # type: ignore[no-untyped-def]
    view = MLDView()
    view.set_model(preview_model())
    graphics = view.graphics_view
    initial = graphics.transform().m11()

    graphics.zoom_in()
    assert graphics.transform().m11() > initial
    graphics.zoom_out()
    assert abs(graphics.transform().m11() - initial) < 1e-9
    graphics.reset_zoom()
    assert graphics.sceneRect().isValid()

    assert view.zoom_in_button.isEnabled()
    assert view.zoom_out_button.isEnabled()
    assert view.reset_zoom_button.isEnabled()
    view.close()


def test_mld_table_selection_displays_properties(qapp) -> None:  # type: ignore[no-untyped-def]
    view = MLDView()
    view.set_model(preview_model())
    selected: list[object] = []
    view.graphics_view.table_selected.connect(selected.append)
    item = next(
        graphics_item
        for graphics_item in view.graphics_view.mld_scene.items()
        if isinstance(graphics_item, MLDTableGraphicsItem)
    )
    item.setSelected(True)
    qapp.processEvents()
    assert selected and selected[-1].name == "PILOTE"
    view.close()
