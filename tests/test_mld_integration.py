from __future__ import annotations

import pytest
from PySide6.QtCore import QPointF

from merisor.application import DiagramController, MLDGenerationBlocked
from merisor.domain import Cardinality, MLDDataType, MLDDataTypeName, Position
from merisor.ui.canvas import DiagramScene
from merisor.ui.main_window import MainWindow
from merisor.ui.mld_view import MLDTableGraphicsItem, MLDView


def build_valid_controller(controller: DiagramController) -> None:
    pilot = controller.create_entity("PILOTE", QPointF(0, 0))
    pilot_id = controller.add_attribute(pilot.id, "id_pilote")
    controller.set_attribute_identifier(pilot.id, pilot_id.id, True)
    controller.add_attribute(pilot.id, "nom")

    course = controller.create_entity("COURSE", QPointF(400, 0))
    course_id = controller.add_attribute(course.id, "id_course")
    controller.set_attribute_identifier(course.id, course_id.id, True)
    controller.add_attribute(course.id, "date")

    association = controller.create_association("PARTICIPER", QPointF(200, 180))
    controller.add_attribute(association.id, "points")
    assert controller.create_relation(pilot.id, association.id)
    assert controller.create_relation(course.id, association.id)
    relations = list(controller.model.relations.values())
    controller.set_relation_cardinality(relations[0].id, Cardinality("0", "N"))
    controller.set_relation_cardinality(relations[1].id, Cardinality("1", "N"))


def build_historized_motogp_controller(controller: DiagramController) -> str:
    pilot = controller.create_entity("PILOTE", QPointF(0, 0))
    pilot_id = controller.add_attribute(pilot.id, "id_pilote")
    controller.set_attribute_identifier(pilot.id, pilot_id.id, True)
    controller.add_attribute(pilot.id, "nom")

    team = controller.create_entity("EQUIPE", QPointF(400, 0))
    team_id = controller.add_attribute(team.id, "id_equipe")
    controller.set_attribute_identifier(team.id, team_id.id, True)
    controller.add_attribute(team.id, "nom")

    engage = controller.create_association("ENGAGER", QPointF(200, 180))
    controller.add_attribute(engage.id, "date_debut")
    controller.add_attribute(engage.id, "date_fin")
    controller.set_association_historized(engage.id, True)
    assert controller.create_relation(pilot.id, engage.id)
    assert controller.create_relation(team.id, engage.id)
    relations = list(controller.model.relations.values())
    controller.set_relation_cardinality(relations[0].id, Cardinality("0", "N"))
    controller.set_relation_cardinality(relations[1].id, Cardinality("1", "1"))
    return engage.id


def test_controller_blocks_generation_when_mcd_has_errors(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = DiagramController(DiagramScene())
    controller.create_entity("PILOTE", QPointF())

    with pytest.raises(MLDGenerationBlocked) as captured:
        controller.generate_mld()

    assert any(
        issue.code == "entity.identifier_missing"
        for issue in captured.value.report.errors
    )
    assert controller.mld_model is None


def test_controller_blocks_historized_force_fk_contradiction(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = DiagramController(DiagramScene())
    association_id = build_historized_motogp_controller(controller)
    controller.set_association_materialization_strategy(association_id, "FORCE_FK")

    with pytest.raises(MLDGenerationBlocked) as captured:
        controller.generate_mld()

    assert any(
        issue.code == "association.historized_force_fk"
        for issue in captured.value.report.errors
    )
    assert controller.mld_model is None


def test_controller_tracks_current_and_stale_mld(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = DiagramController(DiagramScene())
    build_valid_controller(controller)
    generated = controller.generate_mld()
    pilot = next(
        entity
        for entity in controller.model.entities.values()
        if entity.name == "PILOTE"
    )

    assert controller.mld_model is generated
    assert not controller.mld_is_stale

    controller.command_move_node(pilot.id, Position(700, -120))
    assert not controller.mld_is_stale

    controller.rename_node(pilot.id, "AVIATEUR")
    assert controller.mld_is_stale
    controller.undo_stack.undo()
    assert not controller.mld_is_stale


def test_association_transformation_change_marks_derived_mld_stale(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = DiagramController(DiagramScene())
    build_valid_controller(controller)
    controller.generate_mld()
    association = next(iter(controller.model.associations.values()))

    controller.set_association_historized(association.id, True)

    assert controller.mld_is_stale
    controller.undo_stack.undo()
    assert not controller.mld_is_stale


def test_attribute_type_change_marks_mld_stale_and_is_undoable(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = DiagramController(DiagramScene())
    build_valid_controller(controller)
    controller.generate_mld()
    pilot = next(
        entity
        for entity in controller.model.entities.values()
        if entity.name == "PILOTE"
    )
    name_attribute = next(
        attribute for attribute in pilot.attributes if attribute.name == "nom"
    )

    controller.set_attribute_data_type(
        pilot.id,
        name_attribute.id,
        MLDDataType(MLDDataTypeName.TEXT),
    )

    assert controller.mld_is_stale
    controller.undo_stack.undo()
    assert name_attribute.data_type is None
    assert not controller.mld_is_stale


def test_regeneration_replaces_stale_mld_deterministically(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = DiagramController(DiagramScene())
    build_valid_controller(controller)
    first = controller.generate_mld()
    pilot = next(
        entity
        for entity in controller.model.entities.values()
        if entity.name == "PILOTE"
    )
    controller.rename_node(pilot.id, "AVIATEUR")

    second = controller.generate_mld()
    third = controller.generate_mld()

    assert first != second
    assert second == third
    assert not controller.mld_is_stale
    assert second.table("AVIATEUR")


def test_mld_view_displays_copies_and_exports_text(qapp, tmp_path) -> None:  # type: ignore[no-untyped-def]
    controller = DiagramController(DiagramScene())
    build_valid_controller(controller)
    model = controller.generate_mld()
    view = MLDView()

    view.set_model(model)
    view.copy_text()
    path = tmp_path / "mld.txt"
    view.export_to(path)

    assert "PARTICIPER" in view.text
    assert "FK (id_course)" in view.text
    assert qapp.clipboard().text() == view.text
    assert path.read_text(encoding="utf-8") == view.text
    assert "MLD à jour" in view.status_label.text()

    view.set_stale(True)
    assert "obsolète" in view.status_label.text()


def test_main_window_generate_button_opens_mld_tab(qapp) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()
    build_valid_controller(window.controller)

    window.generate_mld()
    qapp.processEvents()

    assert window.workspace_tabs.currentWidget() is window.mld_view
    assert window.mld_view.model is window.controller.mld_model
    assert window.mld_view.graphics_view.mld_scene.items()
    assert "PILOTE" in window.mld_view.text

    window.controller.undo_stack.setClean()
    window.close()
    qapp.processEvents()


def test_reload_clears_derived_mld_and_allows_regeneration(qapp, tmp_path) -> None:  # type: ignore[no-untyped-def]
    controller = DiagramController(DiagramScene())
    build_valid_controller(controller)
    first = controller.generate_mld()
    path = tmp_path / "project.json"
    controller.save(path)

    controller.new_document()
    assert controller.mld_model is None
    controller.load(path)
    assert controller.mld_model is None

    regenerated = controller.generate_mld()
    assert regenerated == first


def test_historized_motogp_generation_is_visible_in_both_mld_views(qapp) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()
    association_id = build_historized_motogp_controller(window.controller)

    window.generate_mld()
    qapp.processEvents()

    assert window.controller.mld_model is not None
    table = window.controller.mld_model.table("ENGAGER")
    assert table.source_element_id == association_id
    assert [column.name for column in table.primary_key_columns] == ["id_engager"]
    assert [column.name for column in table.columns] == [
        "id_engager",
        "id_equipe",
        "id_pilote",
        "date_debut",
        "date_fin",
    ]
    assert "[Association historisée]" in window.mld_view.text
    assert window.workspace_tabs.currentWidget() is window.mld_view
    assert any(
        isinstance(item, MLDTableGraphicsItem)
        and item.table.name == "ENGAGER"
        and item.header_height > item.HEADER_HEIGHT
        for item in window.mld_view.graphics_view.mld_scene.items()
    )

    window.controller.undo_stack.setClean()
    window.close()
    qapp.processEvents()
