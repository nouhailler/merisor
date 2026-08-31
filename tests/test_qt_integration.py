from PySide6.QtCore import QPointF, QSettings, Qt
from PySide6.QtWidgets import QToolBar

from merisor.application import DiagramController, SQLDDLImporter
from merisor.domain import (
    Cardinality,
    MaterializationStrategy,
    MCDModel,
    MLDDataType,
    MLDDataTypeName,
    Position,
)
from merisor.persistence import JsonDiagramRepository
from merisor.ui.canvas import DiagramScene
from merisor.ui.main_window import MainWindow
from merisor.ui.normalization_dialog import NormalizationAssistantDialog


def test_relation_graphic_follows_a_moved_node(qapp) -> None:  # type: ignore[no-untyped-def]
    scene = DiagramScene()
    controller = DiagramController(scene)
    entity = controller.create_entity("PILOTE", QPointF(0, 0))
    association = controller.create_association("PARTICIPER", QPointF(300, 100))
    assert controller.create_relation(entity.id, association.id)
    relation = next(iter(controller.model.relations.values()))
    relation_item = controller._relation_items[relation.id]
    original_line = relation_item.line()

    node_item = controller._node_items[entity.id]
    old_point = QPointF(node_item.pos())
    new_point = QPointF(80, 160)
    node_item.setPos(new_point)
    node_item.move_finished.emit(entity.id, old_point, new_point)
    qapp.processEvents()

    assert relation_item.line() != original_line
    assert controller.model.entities[entity.id].position == Position(80, 160)
    controller.undo_stack.undo()
    assert controller.model.entities[entity.id].position == Position(0, 0)


def test_reflexive_relations_get_roles_and_distinct_graphic_lines(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = DiagramController(DiagramScene())
    employee = controller.create_entity("EMPLOYE", QPointF(0, 0))
    supervise = controller.create_association("SUPERVISER", QPointF(300, 0))

    assert controller.create_relation(employee.id, supervise.id)
    assert controller.create_relation(employee.id, supervise.id)

    relations = list(controller.model.relations.values())
    assert {relation.role for relation in relations} == {"rôle_1", "rôle_2"}
    assert (
        controller._relation_items[relations[0].id].line()
        != controller._relation_items[relations[1].id].line()
    )
    controller.set_relation_role(relations[0].id, "superviseur")
    assert controller._relation_items[relations[0].id].role_text == "superviseur"
    controller.undo_stack.undo()
    assert relations[0].role in {"rôle_1", "rôle_2"}


def test_inheritance_graphic_follows_entities_and_is_undoable(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = DiagramController(DiagramScene())
    parent = controller.create_entity("PERSONNE", QPointF(0, 0))
    child = controller.create_entity("CLIENT", QPointF(300, 200))

    inheritance = controller.create_inheritance(parent.id, (child.id,))
    item = controller._inheritance_items[inheritance.id]
    original_bounds = item.boundingRect()
    controller.command_move_node(child.id, Position(500, 350))

    assert item.boundingRect() != original_bounds
    controller.undo_stack.undo()
    assert inheritance.id not in controller.model.inheritances
    assert inheritance.id not in controller._inheritance_items


def test_graphical_deletion_cascades_and_can_be_undone(qapp) -> None:  # type: ignore[no-untyped-def]
    scene = DiagramScene()
    controller = DiagramController(scene)
    entity = controller.create_entity("PILOTE", QPointF())
    association = controller.create_association("PARTICIPER", QPointF(200, 0))
    controller.create_relation(entity.id, association.id)
    relation_id = next(iter(controller.model.relations))
    controller._node_items[entity.id].setSelected(True)

    controller.delete_selected()

    assert entity.id not in controller.model.entities
    assert relation_id not in controller.model.relations
    controller.undo_stack.undo()
    assert entity.id in controller.model.entities
    assert relation_id in controller.model.relations


def test_main_window_starts_offscreen(qapp) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()
    window.show()
    qapp.processEvents()

    assert window.isVisible()
    assert window.import_ddl_action.text() == "Importer SQL / DDL…"
    assert window.centralWidget() is window.workspace_tabs
    assert window.workspace_tabs.widget(0) is window.view
    assert window.workspace_tabs.widget(1) is window.mld_view
    assert window.menuBar().actions()
    assert window.validate_action.text() == "Valider le MCD…"
    assert window.generate_mld_action.text() == "Générer le MLD"
    assert window.generate_sql_action.text() == "Générer SQL"
    assert window.normalization_action.text() == "Assistant de normalisation…"
    assert not window.generate_sql_action.isEnabled()
    toolbar = window.findChild(QToolBar, "diagramToolbar")
    assert toolbar is not None
    action_texts = [action.text() for action in toolbar.actions()]
    assert action_texts.index("Générer le MLD") < action_texts.index("Générer SQL")

    entity = window.controller.create_entity("TEST", QPointF())
    window.controller._node_items[entity.id].setSelected(True)
    window.controller.undo_stack.setClean()

    window.close()
    qapp.processEvents()


def test_functional_dependencies_and_decomposition_are_undoable(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = DiagramController(DiagramScene())
    employee = controller.create_entity("EMPLOYE", QPointF())
    employee_id = controller.add_attribute(employee.id, "id_employe", True)
    department_code = controller.add_attribute(employee.id, "code_service")
    department_name = controller.add_attribute(employee.id, "nom_service")
    dependency = controller.add_functional_dependency(
        employee.id, (department_code.id,), (department_name.id,)
    )

    assert dependency.id in controller.model.functional_dependencies
    proposal = controller.analyze_normalization().owners[0].proposals[0]
    controller.apply_normalization(proposal)
    assert {entity.name for entity in controller.model.entities.values()} == {
        "EMPLOYE",
        "SERVICE",
    }

    controller.undo_stack.undo()
    assert set(controller.model.entities) == {employee.id}
    assert dependency.id in controller.model.functional_dependencies
    assert controller.model.attribute(employee.id, employee_id.id).identifier

    controller.remove_attribute(employee.id, department_name.id)
    assert dependency.id not in controller.model.functional_dependencies
    controller.undo_stack.undo()
    assert dependency.id in controller.model.functional_dependencies


def test_normalization_assistant_opens_without_mutating_model(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = DiagramController(DiagramScene())
    entity = controller.create_entity("CLIENT", QPointF())
    controller.add_attribute(entity.id, "id_client", True)
    before = controller.repository.to_dict(controller.model)

    dialog = NormalizationAssistantDialog(controller)
    dialog.show()
    qapp.processEvents()

    assert dialog.isVisible()
    assert dialog.owner_combo.count() == 1
    assert "1NF" in dialog.report_text.toPlainText()
    assert controller.repository.to_dict(controller.model) == before
    dialog.close()


def test_controller_imports_reverse_engineered_mcd_and_current_mld(qapp) -> None:  # type: ignore[no-untyped-def]
    result = SQLDDLImporter().import_text(
        "CREATE TABLE pilote (id_pilote INTEGER PRIMARY KEY, nom TEXT);"
    )
    controller = DiagramController(DiagramScene())

    controller.import_reverse_engineered_model(result.mcd, result.mld)

    assert {entity.name for entity in controller.model.entities.values()} == {"pilote"}
    assert controller.mld_model is result.mld
    assert not controller.mld_is_stale
    assert controller.is_dirty


def test_recent_files_menu_persists_and_opens_existing_models(qapp, tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings = QSettings("MERISOR", "MERISOR")
    settings.remove("recent_files")
    path = tmp_path / "recent.json"
    JsonDiagramRepository().save(MCDModel(), path)

    window = MainWindow()
    window._add_recent_file(path)
    assert window.recent_menu is not None
    actions = window.recent_menu.actions()
    assert actions[0].text() == path.name
    assert actions[0].toolTip() == str(path.resolve())

    actions[0].trigger()
    assert window.controller.document_path == path
    assert window._recent_files()[0] == str(path.resolve())
    window.close()
    settings.remove("recent_files")
    qapp.processEvents()


def test_attribute_and_identifier_commands_refresh_graphics_and_undo(qapp) -> None:  # type: ignore[no-untyped-def]
    scene = DiagramScene()
    controller = DiagramController(scene)
    entity = controller.create_entity("PILOTE", QPointF())
    item = controller._node_items[entity.id]
    original_height = item.boundingRect().height()

    attribute = controller.add_attribute(entity.id, "id_pilote")
    controller.set_attribute_identifier(entity.id, attribute.id, True)
    controller.rename_attribute(entity.id, attribute.id, "pilote_id")
    controller.remove_attribute(entity.id, attribute.id)

    assert entity.attributes == []
    controller.undo_stack.undo()
    assert entity.attributes[0].name == "pilote_id"
    assert entity.attributes[0].identifier
    assert controller._node_items[entity.id].attributes == [
        ("pilote_id : INTEGER", True)
    ]
    assert item.boundingRect().height() >= original_height
    controller.undo_stack.undo()
    assert entity.attributes[0].name == "id_pilote"
    controller.undo_stack.undo()
    assert not entity.attributes[0].identifier
    controller.undo_stack.undo()
    assert entity.attributes == []


def test_properties_panel_edits_attribute_type_and_can_undo(qapp) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()
    entity = window.controller.create_entity("EVENEMENT", QPointF())
    attribute = window.controller.add_attribute(entity.id, "montant")
    window.controller._node_items[entity.id].setSelected(True)
    qapp.processEvents()

    panel = window.properties_panel
    first_attribute = panel.attribute_tree.topLevelItem(0)
    assert first_attribute is not None
    panel.attribute_tree.setCurrentItem(first_attribute)
    decimal_index = panel.attribute_type_combo.findData("DECIMAL")
    panel.attribute_type_combo.setCurrentIndex(decimal_index)
    panel.attribute_precision.setValue(12)
    panel.attribute_scale.setValue(2)
    panel.apply_attribute_type_button.click()

    assert attribute.data_type == MLDDataType(
        MLDDataTypeName.DECIMAL,
        precision=12,
        scale=2,
    )
    current_attribute = panel.attribute_tree.currentItem()
    assert current_attribute is not None
    assert current_attribute.text(2) == "DECIMAL(12,2)"

    window.controller.undo_stack.undo()
    assert attribute.data_type is None
    assert panel.attribute_tree.currentItem() is not None
    assert panel.attribute_tree.currentItem().text(2) == "AUTO → VARCHAR(100)"

    panel.attribute_type_combo.setCurrentIndex(
        panel.attribute_type_combo.findData("VARCHAR")
    )
    panel.attribute_length.setValue(180)
    panel.apply_attribute_type_button.click()
    assert attribute.data_type == MLDDataType.varchar(180)

    window.controller.undo_stack.setClean()
    window.close()
    qapp.processEvents()


def test_node_rename_updates_graphics_and_can_be_undone(qapp) -> None:  # type: ignore[no-untyped-def]
    scene = DiagramScene()
    controller = DiagramController(scene)
    entity = controller.create_entity("PILOTE", QPointF())

    controller.rename_node(entity.id, "AVIATEUR")

    assert entity.name == "AVIATEUR"
    assert controller._node_items[entity.id].name == "AVIATEUR"
    controller.undo_stack.undo()
    assert entity.name == "PILOTE"
    assert controller._node_items[entity.id].name == "PILOTE"


def test_cardinality_label_changes_and_follows_relation(qapp) -> None:  # type: ignore[no-untyped-def]
    scene = DiagramScene()
    controller = DiagramController(scene)
    entity = controller.create_entity("PILOTE", QPointF(0, 0))
    association = controller.create_association("PARTICIPER", QPointF(300, 0))
    controller.create_relation(entity.id, association.id)
    relation = next(iter(controller.model.relations.values()))
    item = controller._relation_items[relation.id]

    controller.set_relation_cardinality(relation.id, Cardinality("1", "1"))
    original_label_position = item.cardinality_label.scenePos()
    controller.command_move_node(entity.id, Position(0, 140))
    qapp.processEvents()

    assert item.cardinality_text == "1,1"
    assert item.cardinality_label.scenePos() != original_label_position
    controller.undo_stack.undo()
    assert item.cardinality_text == "0,N"


def test_properties_panel_edits_name_and_cardinality(qapp) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()
    entity = window.controller.create_entity("PILOTE", QPointF())
    association = window.controller.create_association("PARTICIPER", QPointF(250, 0))
    window.controller.create_relation(entity.id, association.id)
    relation = next(iter(window.controller.model.relations.values()))

    window.controller._node_items[entity.id].setSelected(True)
    qapp.processEvents()
    window.properties_panel.node_name.setText("AVIATEUR")
    window.properties_panel.node_name.editingFinished.emit()
    assert entity.name == "AVIATEUR"

    window.scene.clearSelection()
    window.controller._relation_items[relation.id].setSelected(True)
    qapp.processEvents()
    window.properties_panel.minimum_combo.setCurrentText("1")
    window.properties_panel.maximum_combo.setCurrentText("1")
    assert relation.cardinality == Cardinality("1", "1")
    assert window.controller._relation_items[relation.id].cardinality_text == "1,1"

    window.controller.undo_stack.setClean()
    window.close()
    qapp.processEvents()


def test_association_transformation_controls_are_contextual_and_undoable(qapp) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()
    entity = window.controller.create_entity("PILOTE", QPointF())
    association = window.controller.create_association("ENGAGER", QPointF(250, 0))

    window.controller._node_items[entity.id].setSelected(True)
    qapp.processEvents()
    assert window.properties_panel.association_transformation_group.isHidden()

    window.scene.clearSelection()
    window.controller._node_items[association.id].setSelected(True)
    qapp.processEvents()
    panel = window.properties_panel
    assert not panel.association_transformation_group.isHidden()
    assert not panel.historized_checkbox.isChecked()
    assert panel.materialization_combo.currentData() == "AUTO"

    panel.historized_checkbox.setChecked(True)
    panel.materialization_combo.setCurrentIndex(
        panel.materialization_combo.findData("FORCE_TABLE")
    )

    assert association.is_historized
    assert association.materialization_strategy is MaterializationStrategy.FORCE_TABLE
    window.controller.undo_stack.undo()
    assert association.materialization_strategy.value == "AUTO"
    window.controller.undo_stack.undo()
    assert association.is_historized is False

    window.controller.undo_stack.setClean()
    window.close()
    qapp.processEvents()


def test_association_attribute_can_be_marked_as_its_identifier(qapp) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()
    association = window.controller.create_association("ENGAGER", QPointF())
    attribute = window.controller.add_attribute(association.id, "numero_engagement")
    window.controller._node_items[association.id].setSelected(True)
    qapp.processEvents()

    item = window.properties_panel.attribute_tree.topLevelItem(0)
    assert item is not None
    item.setCheckState(0, Qt.CheckState.Checked)
    qapp.processEvents()

    assert attribute.identifier
    assert window.controller._node_items[association.id].attributes == [
        ("numero_engagement : INTEGER", True)
    ]
    window.controller.undo_stack.undo()
    assert not attribute.identifier

    window.controller.undo_stack.setClean()
    window.close()
    qapp.processEvents()
