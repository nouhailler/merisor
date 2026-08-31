import pytest

from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    DiagramError,
    DiagramModel,
    MLDDataType,
    MLDDataTypeName,
    InheritanceStrategy,
    MaterializationStrategy,
    Position,
)


def test_create_entity_with_name_and_position() -> None:
    model = DiagramModel()

    entity = model.create_entity("PILOTE", Position(12.5, -8.0))

    assert model.entities[entity.id] is entity
    assert entity.name == "PILOTE"
    assert entity.position == Position(12.5, -8.0)


def test_create_association_and_automatic_names() -> None:
    model = DiagramModel()

    first = model.create_association("", Position())
    second = model.create_association(None, Position(1, 2))

    assert first.name == "Association_1"
    assert second.name == "Association_2"


def test_association_transformation_properties_have_safe_defaults() -> None:
    association = Association("ENGAGER")

    assert association.is_historized is False
    assert association.materialization_strategy is MaterializationStrategy.AUTO


def test_date_attributes_never_enable_historization_implicitly() -> None:
    association = Association(
        "ENGAGER",
        attributes=[Attribute("date_debut"), Attribute("date_fin")],
    )

    assert association.is_historized is False


@pytest.mark.parametrize("strategy", list(MaterializationStrategy))
def test_association_accepts_supported_materialization_strategies(
    strategy: MaterializationStrategy,
) -> None:
    association = Association(
        "ENGAGER",
        is_historized=True,
        materialization_strategy=strategy.value,
    )

    assert association.is_historized is True
    assert association.materialization_strategy is strategy


def test_association_rejects_invalid_transformation_properties() -> None:
    with pytest.raises(DiagramError, match="historisation"):
        Association("ENGAGER", is_historized="oui")  # type: ignore[arg-type]
    with pytest.raises(DiagramError, match="matérialisation"):
        Association("ENGAGER", materialization_strategy="TABLE")


def test_model_modifies_association_transformation_properties() -> None:
    model = DiagramModel()
    association = model.create_association("ENGAGER", Position())

    model.set_association_historized(association.id, True)
    model.set_association_materialization_strategy(
        association.id, MaterializationStrategy.FORCE_TABLE
    )

    assert association.is_historized
    assert (
        association.materialization_strategy
        is MaterializationStrategy.FORCE_TABLE
    )


def test_create_relation_between_entity_and_association() -> None:
    model = DiagramModel()
    entity = model.create_entity("PILOTE", Position())
    association = model.create_association("PARTICIPER", Position(100, 100))

    relation = model.create_relation(entity.id, association.id)

    assert relation.entity_id == entity.id
    assert relation.association_id == association.id
    assert model.relations[relation.id] is relation


def test_relation_rejects_unknown_endpoint_and_accepts_reflexive_roles() -> None:
    model = DiagramModel()
    entity = model.create_entity("PILOTE", Position())
    association = model.create_association("PARTICIPER", Position())

    with pytest.raises(DiagramError, match="Association inconnue"):
        model.create_relation(entity.id, "missing")

    supervisor = model.create_relation(
        entity.id, association.id, role=" superviseur "
    )
    supervised = model.create_relation(
        entity.id, association.id, role="supervisé"
    )

    assert supervisor.role == "superviseur"
    assert supervised.role == "supervisé"
    assert len(model.relations) == 2


def test_relation_role_can_be_modified() -> None:
    model = DiagramModel()
    entity = model.create_entity("EMPLOYE", Position())
    association = model.create_association("SUPERVISER", Position())
    relation = model.create_relation(entity.id, association.id)

    model.set_relation_role(relation.id, " responsable ")

    assert relation.role == "responsable"
    with pytest.raises(DiagramError, match="rôle"):
        model.set_relation_role(relation.id, 42)  # type: ignore[arg-type]


def test_removing_node_also_removes_attached_relations() -> None:
    model = DiagramModel()
    entity = model.create_entity("PILOTE", Position())
    association = model.create_association("PARTICIPER", Position())
    relation = model.create_relation(entity.id, association.id)

    removed_entity, removed_relations = model.remove_entity(entity.id)

    assert removed_entity is entity
    assert removed_relations == [relation]
    assert entity.id not in model.entities
    assert relation.id not in model.relations
    assert association.id in model.associations


def test_move_node_changes_only_its_position() -> None:
    model = DiagramModel()
    entity = model.create_entity("PILOTE", Position())

    model.move_node(entity.id, Position(250, -120))

    assert entity.position == Position(250, -120)


def test_rename_entity_and_manage_attributes() -> None:
    model = DiagramModel()
    entity = model.create_entity("PILOTE", Position())
    first = model.create_attribute(entity.id, "id_pilote")
    second = model.create_attribute(entity.id, "nom")

    model.rename_node(entity.id, "PERSONNEL_NAVIGANT")
    model.rename_attribute(entity.id, second.id, "nom_famille")
    model.set_attribute_identifier(entity.id, first.id, True)

    assert entity.name == "PERSONNEL_NAVIGANT"
    assert [attribute.name for attribute in entity.attributes] == [
        "id_pilote",
        "nom_famille",
    ]
    assert entity.identifier_attributes == [first]

    removed, index = model.remove_attribute(entity.id, second.id)
    assert removed is second
    assert index == 1
    assert entity.attributes == [first]


def test_attribute_type_can_be_explicit_or_automatic() -> None:
    model = DiagramModel()
    entity = model.create_entity("EVENEMENT", Position())
    attribute = model.create_attribute(entity.id, "date_evenement")

    assert attribute.data_type is None

    explicit_type = MLDDataType(MLDDataTypeName.DATE)
    model.set_attribute_data_type(entity.id, attribute.id, explicit_type)
    assert attribute.data_type == explicit_type

    model.set_attribute_data_type(entity.id, attribute.id, None)
    assert attribute.data_type is None


def test_attribute_rejects_an_invalid_explicit_type() -> None:
    with pytest.raises(DiagramError, match="type explicite"):
        Attribute("date_evenement", data_type="DATE")  # type: ignore[arg-type]


def test_entity_inheritance_is_a_first_class_model_object() -> None:
    model = DiagramModel()
    person = model.create_entity("PERSONNE", Position())
    client = model.create_entity("CLIENT", Position())
    supplier = model.create_entity("FOURNISSEUR", Position())

    inheritance = model.create_inheritance(
        person.id,
        (client.id, supplier.id),
        InheritanceStrategy.JOINED,
    )

    assert model.inheritances[inheritance.id] is inheritance
    assert inheritance.child_entity_ids == (client.id, supplier.id)
    assert inheritance.strategy is InheritanceStrategy.JOINED

    model.remove_entity(client.id)
    assert inheritance.id not in model.inheritances


def test_entity_supports_composite_identifier() -> None:
    model = DiagramModel()
    entity = model.create_entity("PARTICIPATION", Position())
    course_id = model.create_attribute(entity.id, "id_course", identifier=True)
    pilot_id = model.create_attribute(entity.id, "id_pilote", identifier=True)
    model.create_attribute(entity.id, "position")

    assert entity.identifier_attributes == [course_id, pilot_id]


def test_rename_association_and_manage_its_attributes() -> None:
    model = DiagramModel()
    association = model.create_association("PARTICIPER", Position())
    points = model.create_attribute(association.id, "points")

    model.rename_node(association.id, "CLASSER")
    model.rename_attribute(association.id, points.id, "score")

    assert association.name == "CLASSER"
    assert association.attributes[0].name == "score"
    model.remove_attribute(association.id, points.id)
    assert association.attributes == []


@pytest.mark.parametrize(
    ("minimum", "maximum", "label"),
    [("0", "1", "0,1"), ("0", "N", "0,N"), ("1", "1", "1,1"), ("1", "N", "1,N")],
)
def test_supported_cardinalities(minimum: str, maximum: str, label: str) -> None:
    cardinality = Cardinality(minimum, maximum)

    assert cardinality.label == label


def test_relation_cardinality_can_be_modified() -> None:
    model = DiagramModel()
    entity = model.create_entity("PILOTE", Position())
    association = model.create_association("PARTICIPER", Position())
    relation = model.create_relation(entity.id, association.id, Cardinality("0", "1"))

    model.set_relation_cardinality(relation.id, Cardinality("1", "N"))

    assert relation.cardinality == Cardinality("1", "N")


def test_invalid_cardinality_is_rejected() -> None:
    with pytest.raises(DiagramError, match="Cardinalité invalide"):
        Cardinality("2", "N")
