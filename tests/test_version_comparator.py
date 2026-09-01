from __future__ import annotations

from copy import deepcopy

from merisor.application import ChangeKind, ModelVersionComparator
from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    Entity,
    MCDModel,
    MLDDataType,
    MLDDataTypeName,
)


def _entity(name: str, entity_id: str, *attributes: Attribute) -> Entity:
    return Entity(name=name, id=entity_id, attributes=list(attributes))


def test_comparator_reports_attribute_add_remove_and_type_change() -> None:
    reference = MCDModel()
    reference.add_entity(
        _entity(
            "CLIENT",
            "entity-client",
            Attribute("id_client", True, id="attribute-id"),
            Attribute(
                "email",
                id="attribute-email",
                data_type=MLDDataType.varchar(100),
            ),
            Attribute("adresse", id="attribute-address"),
        )
    )
    current = deepcopy(reference)
    client = current.entities["entity-client"]
    client.attributes = [
        attribute
        for attribute in client.attributes
        if attribute.id != "attribute-address"
    ]
    client.attributes[1].data_type = MLDDataType.varchar(255)
    client.attributes.extend(
        (
            Attribute("telephone", id="attribute-phone"),
            Attribute(
                "date_naissance",
                id="attribute-birth-date",
                data_type=MLDDataType(MLDDataTypeName.DATE),
            ),
        )
    )

    comparison = ModelVersionComparator().compare(reference, current)
    rendered = comparison.render()

    assert "+ CLIENT.telephone [attribut]" in rendered
    assert "+ CLIENT.date_naissance [attribut]" in rendered
    assert "~ CLIENT.email [type] : VARCHAR(100) → VARCHAR(255)" in rendered
    assert "- CLIENT.adresse [attribut]" in rendered
    assert comparison.count(ChangeKind.ADDED) == 2
    assert comparison.count(ChangeKind.MODIFIED) == 1
    assert comparison.count(ChangeKind.REMOVED) == 1


def test_removed_entity_reports_connected_mcd_and_derived_mld_impacts() -> None:
    reference = MCDModel()
    product = _entity(
        "PRODUIT",
        "entity-product",
        Attribute("id_produit", True, id="attribute-product-id"),
    )
    reference.add_entity(product)
    for index in range(3):
        other = _entity(
            f"AUTRE_{index}",
            f"entity-other-{index}",
            Attribute(f"id_autre_{index}", True, id=f"attribute-other-id-{index}"),
        )
        association = Association(f"LIER_{index}", id=f"association-{index}")
        reference.add_entity(other)
        reference.add_association(association)
        reference.create_relation(product.id, association.id, Cardinality("0", "N"))
        reference.create_relation(other.id, association.id, Cardinality("1", "N"))

    current = deepcopy(reference)
    current.remove_entity(product.id)
    comparison = ModelVersionComparator().compare(reference, current)
    deletion = next(
        change
        for change in comparison.changes
        if change.kind is ChangeKind.REMOVED
        and change.category == "Entité"
        and change.path == "PRODUIT"
    )

    assert deletion.impact.associations == ("LIER_0", "LIER_1", "LIER_2")
    assert set(deletion.impact.mld_tables) == {
        "PRODUIT",
        "LIER_0",
        "LIER_1",
        "LIER_2",
    }
    assert len(deletion.impact.foreign_keys) == 6
    assert "⚠ 3 association(s) MCD" in deletion.impact.render()
    assert "IMPACT DU CHANGEMENT" in comparison.render_detailed()


def test_relation_cardinality_change_is_explicit() -> None:
    reference = MCDModel()
    first = _entity(
        "CLIENT", "entity-client", Attribute("id_client", True, id="id-client")
    )
    second = _entity(
        "COMMANDE", "entity-order", Attribute("id_commande", True, id="id-order")
    )
    association = Association("PASSER", id="association-order")
    reference.add_entity(first)
    reference.add_entity(second)
    reference.add_association(association)
    relation = reference.create_relation(
        first.id, association.id, Cardinality("0", "N")
    )
    reference.create_relation(second.id, association.id, Cardinality("1", "1"))
    current = deepcopy(reference)
    current.relations[relation.id].cardinality = Cardinality("1", "N")

    comparison = ModelVersionComparator().compare(reference, current)

    assert any(
        change.kind is ChangeKind.MODIFIED
        and change.category == "relation"
        and "0,N" in change.before
        and "1,N" in change.after
        for change in comparison.changes
    )


def test_comparison_does_not_mutate_either_model() -> None:
    reference = MCDModel()
    reference.add_entity(
        _entity("CLIENT", "client", Attribute("id", True, id="client-id"))
    )
    current = deepcopy(reference)
    before_reference = deepcopy(reference)
    before_current = deepcopy(current)

    result = ModelVersionComparator().compare(reference, current)

    assert result.identical
    assert reference.entities == before_reference.entities
    assert current.entities == before_current.entities
