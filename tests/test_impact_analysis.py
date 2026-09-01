from __future__ import annotations

from merisor.application import ImpactCertainty, ModelImpactAnalyzer
from merisor.domain import Association, Attribute, Cardinality, Entity, MCDModel


def _entity(name: str, entity_id: str, *attributes: Attribute) -> Entity:
    return Entity(name, id=entity_id, attributes=list(attributes))


def test_identifier_impact_follows_migrated_columns_foreign_keys_and_relations() -> (
    None
):
    model = MCDModel()
    identifier = Attribute("id_client", True, id="client-id")
    client = _entity("CLIENT", "client", identifier)
    model.add_entity(client)
    for index, name in enumerate(("COMMANDE", "ADRESSE", "FACTURE")):
        dependent = _entity(
            name,
            f"dependent-{index}",
            Attribute(f"id_{name.lower()}", True, id=f"dependent-id-{index}"),
        )
        association = Association(f"LIER_{name}", id=f"association-{index}")
        model.add_entity(dependent)
        model.add_association(association)
        model.create_relation(client.id, association.id, Cardinality("0", "N"))
        model.create_relation(dependent.id, association.id, Cardinality("1", "1"))

    report = ModelImpactAnalyzer().analyze(model, identifier.id)
    exact_labels = {reference.label for reference in report.certain}

    assert report.relation_count == 3
    assert {"COMMANDE.id_client", "ADRESSE.id_client", "FACTURE.id_client"}.issubset(
        exact_labels
    )
    assert sum(item.category == "Contrainte FK" for item in report.certain) == 3
    assert report.risk_level == "Élevé"


def test_business_attribute_separates_constraints_from_name_matches() -> None:
    model = MCDModel()
    price = Attribute(
        "prix",
        id="product-price",
        unique=True,
        constraints=("prix >= 0",),
    )
    model.add_entity(
        _entity(
            "PRODUIT",
            "product",
            Attribute("id_produit", True, id="product-id"),
            price,
        )
    )
    for index, name in enumerate(("LIGNE_COMMANDE", "FACTURE")):
        model.add_entity(
            _entity(
                name,
                f"other-{index}",
                Attribute(f"id_{index}", True, id=f"other-id-{index}"),
                Attribute("prix", id=f"other-price-{index}"),
            )
        )

    report = ModelImpactAnalyzer().analyze(model, price.id)

    assert report.constraint_count == 2
    assert {item.label for item in report.potential} == {
        "FACTURE.prix",
        "LIGNE_COMMANDE.prix",
    }
    assert all(item.certainty is ImpactCertainty.POTENTIAL for item in report.potential)


def test_functional_dependency_is_reported_as_certain() -> None:
    model = MCDModel()
    code = Attribute("code", True, id="code")
    label = Attribute("libelle", id="label")
    entity = _entity("PRODUIT", "product", code, label)
    model.add_entity(entity)
    dependency = model.create_functional_dependency(entity.id, (code.id,), (label.id,))

    report = ModelImpactAnalyzer().analyze(model, label.id)

    assert any(
        item.category == "Contrainte fonctionnelle"
        and dependency.id in model.functional_dependencies
        and "code → libelle" in item.label
        for item in report.certain
    )


def test_invalid_mcd_keeps_mcd_impacts_and_explains_missing_mld() -> None:
    model = MCDModel()
    attribute = Attribute("nom", id="name")
    model.add_entity(_entity("CLIENT", "client", attribute))

    report = ModelImpactAnalyzer().analyze(model, attribute.id)

    assert not report.mld_available
    assert "ne permet pas de reconstruire un MLD valide" in report.render()
