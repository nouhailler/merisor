from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    DiagramModel,
    Entity,
    MaterializationStrategy,
    Position,
    validate_mcd,
)


def valid_model() -> DiagramModel:
    model = DiagramModel()
    pilot = Entity(
        "PILOTE",
        Position(0, 0),
        attributes=[Attribute("id_pilote", identifier=True), Attribute("nom")],
    )
    course = Entity(
        "COURSE",
        Position(400, 0),
        attributes=[Attribute("id_course", identifier=True)],
    )
    association = Association(
        "PARTICIPER",
        Position(200, 180),
        attributes=[Attribute("position")],
    )
    model.add_entity(pilot)
    model.add_entity(course)
    model.add_association(association)
    model.create_relation(pilot.id, association.id, Cardinality("0", "N"))
    model.create_relation(course.id, association.id, Cardinality("1", "N"))
    return model


def issue_codes(model: DiagramModel) -> set[str]:
    return {issue.code for issue in validate_mcd(model).issues}


def test_valid_mcd_has_no_issue() -> None:
    report = validate_mcd(valid_model())

    assert report.is_valid
    assert report.issues == ()


def test_entity_without_identifier_is_reported() -> None:
    model = valid_model()
    entity = next(iter(model.entities.values()))
    for attribute in entity.attributes:
        attribute.identifier = False

    assert "entity.identifier_missing" in issue_codes(model)


def test_entity_without_name_is_reported() -> None:
    model = valid_model()
    next(iter(model.entities.values())).name = ""

    assert "entity.name_missing" in issue_codes(model)


def test_duplicate_entity_attributes_are_reported() -> None:
    model = valid_model()
    entity = next(iter(model.entities.values()))
    entity.attributes.append(Attribute("NOM"))

    assert "attribute.name_duplicate" in issue_codes(model)


def test_duplicate_association_attributes_are_reported() -> None:
    model = valid_model()
    association = next(iter(model.associations.values()))
    association.attributes.append(Attribute("POSITION"))

    assert "attribute.name_duplicate" in issue_codes(model)


def test_association_without_name_is_reported() -> None:
    model = valid_model()
    next(iter(model.associations.values())).name = ""

    assert "association.name_missing" in issue_codes(model)


def test_association_linked_to_fewer_than_two_entities_is_reported() -> None:
    model = valid_model()
    relation_id = next(iter(model.relations))
    model.remove_relation(relation_id)

    assert "association.too_few_entities" in issue_codes(model)


def test_missing_and_invalid_cardinality_are_reported() -> None:
    model = valid_model()
    relations = list(model.relations.values())
    relations[0].cardinality = None
    relations[1].cardinality = "invalid"  # type: ignore[assignment]

    codes = issue_codes(model)
    assert "relation.cardinality_missing" in codes
    assert "relation.cardinality_invalid" in codes


def test_duplicate_node_names_are_warnings() -> None:
    model = valid_model()
    entities = list(model.entities.values())
    entities[1].name = entities[0].name

    report = validate_mcd(model)

    assert report.is_valid
    assert any(issue.code == "node.name_duplicate" for issue in report.warnings)


def test_force_fk_is_blocked_for_many_to_many_association() -> None:
    model = valid_model()
    association = next(iter(model.associations.values()))
    association.materialization_strategy = MaterializationStrategy.FORCE_FK

    report = validate_mcd(model)

    assert not report.is_valid
    assert "association.force_fk_many_to_many" in {
        issue.code for issue in report.errors
    }


def test_auto_and_force_table_remain_valid_for_many_to_many_association() -> None:
    for strategy in (
        MaterializationStrategy.AUTO,
        MaterializationStrategy.FORCE_TABLE,
    ):
        model = valid_model()
        association = next(iter(model.associations.values()))
        association.materialization_strategy = strategy

        assert validate_mcd(model).is_valid


def test_force_fk_is_allowed_for_one_to_many_association() -> None:
    model = valid_model()
    association = next(iter(model.associations.values()))
    association.materialization_strategy = MaterializationStrategy.FORCE_FK
    next(iter(model.relations.values())).cardinality = Cardinality("0", "1")

    assert validate_mcd(model).is_valid


def test_historized_force_fk_contradiction_is_blocking() -> None:
    model = valid_model()
    association = next(iter(model.associations.values()))
    association.is_historized = True
    association.materialization_strategy = MaterializationStrategy.FORCE_FK

    report = validate_mcd(model)

    assert "association.historized_force_fk" in {
        issue.code for issue in report.errors
    }
