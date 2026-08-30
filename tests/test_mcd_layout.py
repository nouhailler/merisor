from __future__ import annotations

from merisor.application import McdAutoLayout
from merisor.application.controller import DiagramController
from merisor.domain import Association, Attribute, Cardinality, Entity, MCDModel, Relation
from merisor.ui.canvas import DiagramScene


def crowded_model() -> MCDModel:
    model = MCDModel()
    entities = [
        Entity(
            name,
            id=identifier,
            attributes=[Attribute(f"id_{identifier}", identifier=True, id=f"{identifier}.id")],
        )
        for identifier, name in (("student", "ELEVE"), ("course", "COURS"), ("teacher", "PROFESSEUR"))
    ]
    associations = [
        Association("SUIVRE", id="follow"),
        Association("ENSEIGNER", id="teach"),
    ]
    for entity in entities:
        model.add_entity(entity)
    for association in associations:
        model.add_association(association)
    for relation in (
        Relation("student", "follow", id="r1", cardinality=Cardinality("0", "N")),
        Relation("course", "follow", id="r2", cardinality=Cardinality("1", "N")),
        Relation("teacher", "teach", id="r3", cardinality=Cardinality("0", "N")),
        Relation("course", "teach", id="r4", cardinality=Cardinality("1", "1")),
    ):
        model.add_relation(relation)
    return model


def test_auto_layout_is_deterministic_and_separates_nodes() -> None:
    model = crowded_model()
    layout = McdAutoLayout()
    first = layout.calculate(model)
    second = layout.calculate(model)
    assert first == second
    assert len(set(first.values())) == 5
    for first_id, first_position in first.items():
        for second_id, second_position in first.items():
            if first_id >= second_id:
                continue
            assert not (
                abs(first_position.x - second_position.x) < 220
                and abs(first_position.y - second_position.y) < 125
            )


def test_controller_auto_layout_is_one_undoable_operation(qapp) -> None:  # type: ignore[no-untyped-def]
    controller = DiagramController(DiagramScene())
    controller.import_generated_model(crowded_model())
    nodes = (*controller.model.entities.values(), *controller.model.associations.values())
    initial = {node.id: node.position for node in nodes}
    controller.auto_layout()
    nodes = (*controller.model.entities.values(), *controller.model.associations.values())
    arranged = {node.id: node.position for node in nodes}
    assert arranged != initial
    controller.undo_stack.undo()
    nodes = (*controller.model.entities.values(), *controller.model.associations.values())
    assert {node.id: node.position for node in nodes} == initial
