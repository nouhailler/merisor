from __future__ import annotations

from PySide6.QtCore import QPointF

from merisor.application import DiagramController
from merisor.domain import Cardinality, ModelDomain, Position
from merisor.ui.canvas import DiagramScene, MiniMapView


def _controller() -> DiagramController:
    return DiagramController(DiagramScene())


def test_grid_snapping_and_alignment_guides_are_configurable(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = _controller()
    first = controller.create_entity("CLIENT", QPointF(100, 100))
    second = controller.create_entity("COMMANDE", QPointF(300, 200))
    scene = controller.scene
    scene.configure_canvas(grid_visible=True, snap_enabled=True, guides_enabled=True)

    constrained = scene.constrain_position(
        controller._node_items[second.id], QPointF(108, 163)
    )

    assert scene.grid_visible
    assert constrained == QPointF(100, 175)
    assert scene._guide_x == 100
    scene.clear_guides()
    assert scene._guide_x is None
    assert controller.model.entities[first.id].position == Position(100, 100)


def test_alignment_and_distribution_are_undoable(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = _controller()
    nodes = [
        controller.create_entity("A", QPointF(0, 0)),
        controller.create_entity("B", QPointF(180, 80)),
        controller.create_entity("C", QPointF(500, 170)),
    ]
    for node in nodes:
        controller._node_items[node.id].setSelected(True)

    controller.align_selected("top")

    assert {node.position.y for node in controller.model.entities.values()} == {0}
    assert controller.undo_stack.undoText() == "Aligner la sélection"
    controller.undo_stack.undo()
    assert [node.position.y for node in nodes] == [0, 80, 170]

    controller.align_selected("distribute_horizontal")
    assert [node.position.x for node in nodes] == [0, 250, 500]


def test_multiple_drag_is_recorded_as_one_undoable_operation(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = _controller()
    first = controller.create_entity("A", QPointF(0, 0))
    second = controller.create_entity("B", QPointF(100, 100))
    controller.undo_stack.setClean()
    first_item = controller._node_items[first.id]
    second_item = controller._node_items[second.id]
    first_item.setSelected(True)
    second_item.setSelected(True)
    first_item.setPos(40, 30)
    second_item.setPos(140, 130)

    controller._node_move_finished(first.id, QPointF(0, 0), QPointF(40, 30))

    assert first.position == Position(40, 30)
    assert second.position == Position(140, 130)
    assert controller.undo_stack.undoText() == "Déplacer la sélection"
    controller.undo_stack.undo()
    assert first.position == Position(0, 0)
    assert second.position == Position(100, 100)


def test_copy_paste_and_duplication_preserve_internal_relations(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = _controller()
    entity = controller.create_entity("CLIENT", QPointF(0, 0))
    controller.add_attribute(entity.id, "id_client", True)
    association = controller.create_association("PASSER", QPointF(250, 0))
    assert controller.create_relation(entity.id, association.id)
    relation = next(iter(controller.model.relations.values()))
    controller.set_relation_cardinality(relation.id, Cardinality("1", "N"))
    controller._node_items[entity.id].setSelected(True)
    controller._node_items[association.id].setSelected(True)

    assert controller.copy_selected()
    created = controller.paste_copied()

    assert len(created) == 2
    assert len(controller.model.entities) == 2
    assert len(controller.model.associations) == 2
    assert len(controller.model.relations) == 2
    assert {item.name for item in controller.model.entities.values()} == {
        "CLIENT",
        "CLIENT_copie",
    }
    copied_relation = next(
        item for item in controller.model.relations.values() if item.id != relation.id
    )
    assert copied_relation.cardinality == Cardinality("1", "N")
    controller.undo_stack.undo()
    assert len(controller.model.entities) == 1
    assert len(controller.model.relations) == 1


def test_folding_search_and_domain_colors_are_transient(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = _controller()
    client = controller.create_entity("CLIENT", QPointF())
    controller.add_attribute(client.id, "email")
    order = controller.create_entity("COMMANDE", QPointF(400, 0))
    controller.model.add_domain(ModelDomain("Commerce", (client.id,)))
    controller.apply_canvas_style(dark=False)
    client_item = controller._node_items[client.id]
    order_item = controller._node_items[order.id]

    assert client_item._fill_color is not None
    assert order_item._fill_color is None
    client_item.setSelected(True)
    controller.toggle_selected_fold()
    assert not client_item.attributes_visible
    controller.toggle_selected_fold()
    assert client_item.attributes_visible

    assert controller.apply_visual_search("email") == 1
    assert client_item.opacity() == 1.0
    assert order_item.opacity() < 1.0
    assert controller.apply_visual_search("") == 0
    assert order_item.opacity() == 1.0


def test_minimap_shares_the_scene_and_tracks_the_main_view(qapp) -> None:  # type: ignore[no-untyped-def]
    from merisor.ui.canvas import DiagramView

    scene = DiagramScene()
    main_view = DiagramView(scene)
    minimap = MiniMapView(main_view)
    controller = DiagramController(scene)
    controller.create_entity("CLIENT", QPointF())
    minimap.show()
    qapp.processEvents()

    assert minimap.scene() is scene
    assert minimap.main_view is main_view
    assert minimap.isVisible()
    minimap.close()
