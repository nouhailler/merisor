from PySide6.QtCore import QPointF, QSettings, Qt
from PySide6.QtWidgets import QToolBar

from merisor.application import DiagramController
from merisor.domain import Cardinality, MaterializationStrategy, Position
from merisor.ui.canvas import DiagramScene
from merisor.ui.main_window import MainWindow
from merisor.persistence import JsonDiagramRepository
from merisor.domain import MCDModel


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
    assert window.centralWidget() is window.workspace_tabs
    assert window.workspace_tabs.widget(0) is window.view
    assert window.workspace_tabs.widget(1) is window.mld_view
    assert window.menuBar().actions()
    assert window.validate_action.text() == "Valider le MCD…"
    assert window.generate_mld_action.text() == "Générer le MLD"
    assert window.generate_sql_action.text() == "Générer SQL"
    assert not window.generate_sql_action.isEnabled()
    toolbar = window.findChild(QToolBar, "diagramToolbar")
    action_texts = [action.text() for action in toolbar.actions()]
    assert action_texts.index("Générer le MLD") < action_texts.index("Générer SQL")

    entity = window.controller.create_entity("TEST", QPointF())
    window.controller._node_items[entity.id].setSelected(True)
    window.controller.undo_stack.setClean()

    window.close()
    qapp.processEvents()


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
    assert controller._node_items[entity.id].attributes == [("pilote_id", True)]
    assert item.boundingRect().height() >= original_height
    controller.undo_stack.undo()
    assert entity.attributes[0].name == "id_pilote"
    controller.undo_stack.undo()
    assert not entity.attributes[0].identifier
    controller.undo_stack.undo()
    assert entity.attributes == []


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
    association = window.controller.create_association(
        "PARTICIPER", QPointF(250, 0)
    )
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
    association = window.controller.create_association(
        "ENGAGER", QPointF(250, 0)
    )

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
    assert (
        association.materialization_strategy
        is MaterializationStrategy.FORCE_TABLE
    )
    window.controller.undo_stack.undo()
    assert association.materialization_strategy is MaterializationStrategy.AUTO
    window.controller.undo_stack.undo()
    assert association.is_historized is False

    window.controller.undo_stack.setClean()
    window.close()
    qapp.processEvents()


def test_association_attribute_can_be_marked_as_its_identifier(qapp) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()
    association = window.controller.create_association("ENGAGER", QPointF())
    attribute = window.controller.add_attribute(
        association.id, "numero_engagement"
    )
    window.controller._node_items[association.id].setSelected(True)
    qapp.processEvents()

    item = window.properties_panel.attribute_tree.topLevelItem(0)
    item.setCheckState(0, Qt.CheckState.Checked)
    qapp.processEvents()

    assert attribute.identifier
    assert window.controller._node_items[association.id].attributes == [
        ("numero_engagement", True)
    ]
    window.controller.undo_stack.undo()
    assert not attribute.identifier

    window.controller.undo_stack.setClean()
    window.close()
    qapp.processEvents()
