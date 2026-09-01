from __future__ import annotations

import copy

from merisor.application import ExplorationOptions, ModelExplorer
from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    Entity,
    FunctionalDependency,
    Inheritance,
    MCDModel,
    Relation,
)
from merisor.ui.main_window import MainWindow
from merisor.ui.model_explorer_dialog import ModelExplorerDialog


def commerce_model() -> MCDModel:
    model = MCDModel()
    client = Entity(
        "CLIENT",
        id="entity.client",
        attributes=[
            Attribute("id_client", True, id="attribute.client.id"),
            Attribute("email", id="attribute.client.email", unique=True),
        ],
    )
    order = Entity(
        "COMMANDE",
        id="entity.order",
        attributes=[Attribute("id_commande", True, id="attribute.order.id")],
    )
    product = Entity(
        "PRODUIT",
        id="entity.product",
        attributes=[Attribute("id_produit", True, id="attribute.product.id")],
    )
    place = Association("PASSER", id="association.place")
    contain = Association("CONTENIR", id="association.contain")
    for entity in (client, order, product):
        model.add_entity(entity)
    for association in (place, contain):
        model.add_association(association)
    for relation in (
        Relation(
            client.id,
            place.id,
            id="relation.client.place",
            cardinality=Cardinality("0", "N"),
        ),
        Relation(
            order.id,
            place.id,
            id="relation.order.place",
            cardinality=Cardinality("1", "1"),
        ),
        Relation(
            order.id,
            contain.id,
            id="relation.order.contain",
            cardinality=Cardinality("1", "N"),
        ),
        Relation(
            product.id,
            contain.id,
            id="relation.product.contain",
            cardinality=Cardinality("0", "N"),
        ),
    ):
        model.add_relation(relation)
    model.add_functional_dependency(
        FunctionalDependency(
            client.id,
            ("attribute.client.id",),
            ("attribute.client.email",),
            id="dependency.client",
        )
    )
    return model


def test_search_finds_names_and_attributes() -> None:
    model = commerce_model()
    explorer = ModelExplorer()

    assert [result.name for result in explorer.search(model, "commande")] == [
        "COMMANDE"
    ]
    attribute_match = explorer.search(model, "email")
    assert len(attribute_match) == 1
    assert attribute_match[0].name == "CLIENT"
    assert attribute_match[0].matched_attributes == ("email",)


def test_focus_projects_a_bounded_neighborhood_without_mutation() -> None:
    model = commerce_model()
    before = copy.deepcopy(model)
    result = ModelExplorer().project(
        model,
        ExplorationOptions(focus_id="entity.client", depth=2),
    )

    assert result.visible_ids == frozenset(
        {"entity.client", "association.place", "entity.order"}
    )
    assert set(result.model.entities) == {"entity.client", "entity.order"}
    assert set(result.model.associations) == {"association.place"}
    assert len(result.model.relations) == 2
    assert model.entities == before.entities
    assert model.associations == before.associations
    assert model.relations == before.relations


def test_filters_and_temporary_hiding_remove_edges_cleanly() -> None:
    model = commerce_model()
    explorer = ModelExplorer()
    entities_only = explorer.project(
        model,
        ExplorationOptions(show_associations=False, show_links=False),
    )
    assert set(entities_only.model.entities) == {
        "entity.client",
        "entity.order",
        "entity.product",
    }
    assert not entities_only.model.associations
    assert not entities_only.model.relations

    hidden = explorer.project(
        model,
        ExplorationOptions(hidden_ids=frozenset({"entity.order"})),
    )
    assert "entity.order" not in hidden.visible_ids
    assert all(
        relation.entity_id != "entity.order"
        for relation in hidden.model.relations.values()
    )


def test_query_filter_keeps_matches_and_direct_context() -> None:
    result = ModelExplorer().project(
        commerce_model(),
        ExplorationOptions(query="PRODUIT", restrict_to_query=True),
    )
    assert result.visible_ids == frozenset({"entity.product", "association.contain"})


def test_dependency_report_includes_relations_and_functional_dependencies() -> None:
    text = ModelExplorer().dependency_text(commerce_model(), "entity.client")
    assert "PASSER" in text
    assert "(0,N)" in text
    assert "id_client → email" in text


def test_explorer_projects_and_describes_isa_dependencies() -> None:
    model = MCDModel()
    person = Entity(
        "PERSONNE",
        id="entity.person",
        attributes=[Attribute("id_personne", True, id="attribute.person.id")],
    )
    client = Entity(
        "CLIENT",
        id="entity.client",
        attributes=[Attribute("numero", id="attribute.client.number")],
    )
    model.add_entity(person)
    model.add_entity(client)
    model.add_inheritance(
        Inheritance(person.id, (client.id,), "JOINED", id="inheritance.client")
    )

    explorer = ModelExplorer()
    result = explorer.project(model, ExplorationOptions(focus_id=person.id, depth=1))
    assert set(result.model.inheritances) == {"inheritance.client"}
    assert "PERSONNE → CLIENT (JOINED)" in explorer.dependency_text(model, client.id)


def test_explorer_dialog_navigates_without_mutating_source(qapp) -> None:  # type: ignore[no-untyped-def]
    model = commerce_model()
    before = copy.deepcopy(model)
    dialog = ModelExplorerDialog(model)
    dialog.search_edit.setText("CLIENT")
    dialog._focus_selected_result()
    qapp.processEvents()

    assert dialog.focus_id == "entity.client"
    assert set(dialog.controller.model.entities) == {
        "entity.client",
        "entity.order",
    }
    assert set(dialog.controller.model.associations) == {"association.place"}
    dialog._select_graph_node("entity.client")
    qapp.processEvents()
    assert "PASSER" in dialog.dependencies.toPlainText()

    dialog._hide_selected()
    assert "entity.client" in dialog.hidden_ids
    dialog._restore_hidden()
    assert not dialog.hidden_ids
    assert model.entities == before.entities
    assert model.relations == before.relations
    dialog.close()


def test_main_window_exposes_model_explorer(qapp) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()
    assert window.explore_model_action.text() == "Explorer le modèle…"
    assert window.explore_model_action.shortcut().toString()
    window.close()
