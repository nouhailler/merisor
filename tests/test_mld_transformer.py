from __future__ import annotations

from copy import deepcopy

import pytest

from merisor.application import (
    McdToMldTransformer,
    MLDTransformationError,
    mcd_logical_fingerprint,
    render_mld_text,
)
from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    DiagramModel,
    Entity,
    InheritanceStrategy,
    MaterializationStrategy,
    MLDDataType,
    MLDDataTypeName,
    MLDTableSource,
    Position,
)
from merisor.persistence import JsonDiagramRepository


def add_entity(
    model: DiagramModel,
    name: str,
    identifiers: tuple[str, ...],
    attributes: tuple[str, ...] = (),
) -> Entity:
    entity = Entity(
        name,
        attributes=[
            *(Attribute(item, identifier=True) for item in identifiers),
            *(Attribute(item) for item in attributes),
        ],
    )
    model.add_entity(entity)
    return entity


def binary_model(
    first_cardinality: tuple[str, str],
    second_cardinality: tuple[str, str],
    *,
    association_attributes: tuple[str, ...] = (),
) -> tuple[DiagramModel, Entity, Entity, Association]:
    model = DiagramModel()
    first = add_entity(model, "ALPHA", ("id_alpha",), ("libelle_alpha",))
    second = add_entity(model, "BETA", ("id_beta",), ("libelle_beta",))
    association = Association(
        "LIER",
        attributes=[Attribute(name) for name in association_attributes],
    )
    model.add_association(association)
    model.create_relation(first.id, association.id, Cardinality(*first_cardinality))
    model.create_relation(second.id, association.id, Cardinality(*second_cardinality))
    return model, first, second, association


def test_entity_becomes_table_with_simple_primary_key() -> None:
    model = DiagramModel()
    entity = add_entity(model, "PILOTE", ("id_pilote",), ("nom", "prenom"))

    mld = McdToMldTransformer().transform(model)
    table = mld.table("PILOTE")

    assert table.source_element_id == entity.id
    assert [column.name for column in table.columns] == [
        "id_pilote",
        "nom",
        "prenom",
    ]
    assert [column.name for column in table.primary_key_columns] == ["id_pilote"]
    assert table.column("id_pilote").nullable is False
    assert table.column("nom").nullable is None


def test_explicit_mcd_attribute_types_are_preserved_in_the_mld() -> None:
    model = DiagramModel()
    entity = Entity(
        "EVENEMENT",
        attributes=[
            Attribute(
                "id_evenement",
                identifier=True,
                data_type=MLDDataType(MLDDataTypeName.BIGINT),
            ),
            Attribute(
                "date_evenement",
                data_type=MLDDataType(MLDDataTypeName.DATE),
            ),
            Attribute(
                "prix",
                data_type=MLDDataType(
                    MLDDataTypeName.DECIMAL,
                    precision=10,
                    scale=2,
                ),
            ),
            Attribute(
                "description",
                data_type=MLDDataType(MLDDataTypeName.TEXT),
            ),
        ],
    )
    model.add_entity(entity)

    table = McdToMldTransformer().transform(model).table("EVENEMENT")

    assert table.column("id_evenement").data_type == MLDDataType(MLDDataTypeName.BIGINT)
    assert table.column("date_evenement").data_type == MLDDataType(MLDDataTypeName.DATE)
    assert table.column("prix").data_type == MLDDataType(
        MLDDataTypeName.DECIMAL,
        precision=10,
        scale=2,
    )
    assert table.column("description").data_type == MLDDataType(MLDDataTypeName.TEXT)


def test_composite_identifier_becomes_composite_primary_key() -> None:
    model = DiagramModel()
    add_entity(
        model,
        "PARTICIPATION",
        ("id_course", "id_pilote"),
        ("position",),
    )

    table = McdToMldTransformer().transform(model).table("PARTICIPATION")

    assert [column.name for column in table.primary_key_columns] == [
        "id_course",
        "id_pilote",
    ]


def inheritance_model(
    strategy: InheritanceStrategy,
) -> tuple[DiagramModel, Entity, Entity, Entity]:
    model = DiagramModel()
    person = add_entity(model, "PERSONNE", ("id_personne",), ("nom",))
    client = add_entity(model, "CLIENT", ("id_client",), ("numero_client",))
    supplier = add_entity(
        model, "FOURNISSEUR", ("id_fournisseur",), ("raison_sociale",)
    )
    model.create_inheritance(person.id, (client.id, supplier.id), strategy)
    return model, person, client, supplier


def test_joined_inheritance_keeps_all_tables_and_adds_pk_foreign_keys() -> None:
    model, *_ = inheritance_model(InheritanceStrategy.JOINED)

    mld = McdToMldTransformer().transform(model)

    assert {table.name for table in mld.tables} == {
        "PERSONNE",
        "CLIENT",
        "FOURNISSEUR",
    }
    for child_name in ("CLIENT", "FOURNISSEUR"):
        child = mld.table(child_name)
        assert [column.name for column in child.primary_key_columns] == ["id_personne"]
        assert len(child.foreign_keys) == 1
        assert child.foreign_keys[0].referenced_table_id == mld.table("PERSONNE").id
        assert child.foreign_keys[0].column_ids == child.primary_key
        assert child.foreign_keys[0].source_inheritance_id in model.inheritances


def test_parent_only_inheritance_flattens_child_attributes_into_parent() -> None:
    model, *_ = inheritance_model(InheritanceStrategy.PARENT_ONLY)

    mld = McdToMldTransformer().transform(model)

    assert [table.name for table in mld.tables] == ["PERSONNE"]
    assert {column.name for column in mld.table("PERSONNE").columns} == {
        "id_personne",
        "nom",
        "numero_client",
        "raison_sociale",
    }


def test_children_only_inheritance_copies_parent_attributes_into_children() -> None:
    model, *_ = inheritance_model(InheritanceStrategy.CHILDREN_ONLY)

    mld = McdToMldTransformer().transform(model)

    assert {table.name for table in mld.tables} == {"CLIENT", "FOURNISSEUR"}
    assert mld.table("CLIENT").column("nom").nullable is True
    assert mld.table("FOURNISSEUR").column("nom").nullable is True


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (("0", "N"), ("0", "N")),
        (("0", "N"), ("1", "N")),
        (("1", "N"), ("0", "N")),
        (("1", "N"), ("1", "N")),
    ],
)
def test_many_to_many_creates_association_table(
    first: tuple[str, str], second: tuple[str, str]
) -> None:
    model, _alpha, _beta, _association = binary_model(first, second)

    mld = McdToMldTransformer().transform(model)
    table = mld.table("LIER")

    assert len(mld.tables) == 3
    assert [column.name for column in table.primary_key_columns] == [
        "id_alpha",
        "id_beta",
    ]
    assert len(table.foreign_keys) == 2
    assert all(len(foreign_key.column_ids) == 1 for foreign_key in table.foreign_keys)
    assert all(column.nullable is False for column in table.primary_key_columns)


def test_many_to_many_keeps_association_attributes_in_its_table() -> None:
    model, *_ = binary_model(
        ("0", "N"),
        ("1", "N"),
        association_attributes=("position", "points", "temps"),
    )

    table = McdToMldTransformer().transform(model).table("LIER")

    assert [column.name for column in table.columns] == [
        "id_alpha",
        "id_beta",
        "position",
        "points",
        "temps",
    ]


def test_association_attribute_type_is_preserved_when_materialized() -> None:
    model, _alpha, _beta, association = binary_model(
        ("0", "N"),
        ("1", "N"),
        association_attributes=("date_inscription",),
    )
    association.attributes[0].data_type = MLDDataType(MLDDataTypeName.DATE)

    table = McdToMldTransformer().transform(model).table("LIER")

    assert table.column("date_inscription").data_type == MLDDataType(
        MLDDataTypeName.DATE
    )


@pytest.mark.parametrize(
    ("many", "one", "expected_nullable"),
    [
        (("0", "N"), ("0", "1"), True),
        (("0", "N"), ("1", "1"), True),
        (("1", "N"), ("0", "1"), False),
        (("1", "N"), ("1", "1"), False),
    ],
)
def test_one_to_many_migrates_fk_to_maximum_one_side(
    many: tuple[str, str],
    one: tuple[str, str],
    expected_nullable: bool,
) -> None:
    model, alpha, beta, _association = binary_model(many, one)

    mld = McdToMldTransformer().transform(model)
    alpha_table = mld.table("ALPHA")
    beta_table = mld.table("BETA")

    assert len(mld.tables) == 2
    assert alpha_table.foreign_keys == []
    assert len(beta_table.foreign_keys) == 1
    foreign_key = beta_table.foreign_keys[0]
    assert foreign_key.referenced_table_id == alpha_table.id
    assert beta_table.column("id_alpha").nullable is expected_nullable
    assert foreign_key.source_association_id in model.associations
    assert alpha.id != beta.id


def test_one_to_many_moves_association_attributes_to_fk_holder() -> None:
    model, *_ = binary_model(
        ("0", "N"),
        ("1", "1"),
        association_attributes=("date_debut",),
    )

    mld = McdToMldTransformer().transform(model)

    assert "date_debut" not in [column.name for column in mld.table("ALPHA").columns]
    assert mld.table("BETA").column("date_debut").source_attribute_id is not None


@pytest.mark.parametrize(
    ("first", "second", "holder", "target", "nullable"),
    [
        (("0", "1"), ("0", "1"), "ALPHA", "BETA", True),
        (("0", "1"), ("1", "1"), "BETA", "ALPHA", False),
        (("1", "1"), ("0", "1"), "ALPHA", "BETA", False),
        (("1", "1"), ("1", "1"), "ALPHA", "BETA", False),
    ],
)
def test_one_to_one_adds_unique_fk_deterministically(
    first: tuple[str, str],
    second: tuple[str, str],
    holder: str,
    target: str,
    nullable: bool,
) -> None:
    model, *_ = binary_model(first, second)

    mld = McdToMldTransformer().transform(model)
    holder_table = mld.table(holder)
    target_table = mld.table(target)

    assert len(mld.tables) == 2
    assert len(holder_table.foreign_keys) == 1
    foreign_key = holder_table.foreign_keys[0]
    assert foreign_key.referenced_table_id == target_table.id
    assert len(holder_table.unique_constraints) == 1
    assert holder_table.unique_constraints[0].column_ids == foreign_key.column_ids
    assert holder_table.column_by_id(foreign_key.column_ids[0]).nullable is nullable


def test_composite_primary_key_migrates_as_one_composite_foreign_key() -> None:
    model = DiagramModel()
    parent = add_entity(model, "PARENT", ("id_un", "id_deux"))
    child = add_entity(model, "ENFANT", ("id_enfant",))
    association = Association("DEPENDRE")
    model.add_association(association)
    model.create_relation(parent.id, association.id, Cardinality("1", "N"))
    model.create_relation(child.id, association.id, Cardinality("1", "1"))

    mld = McdToMldTransformer().transform(model)
    foreign_key = mld.table("ENFANT").foreign_keys[0]

    assert len(foreign_key.column_ids) == 2
    assert len(foreign_key.referenced_column_ids) == 2
    assert [
        mld.table("ENFANT").column_by_id(column_id).name
        for column_id in foreign_key.column_ids
    ] == ["id_un", "id_deux"]


def test_multiple_associations_are_not_merged_and_names_are_disambiguated() -> None:
    model = DiagramModel()
    team = add_entity(model, "EQUIPE", ("id_equipe",))
    pilot = add_entity(model, "PILOTE", ("id_pilote",))
    for association_name in ("ENGAGER", "TESTER"):
        association = Association(association_name)
        model.add_association(association)
        model.create_relation(team.id, association.id, Cardinality("0", "N"))
        model.create_relation(pilot.id, association.id, Cardinality("1", "1"))

    pilot_table = McdToMldTransformer().transform(model).table("PILOTE")

    assert len(pilot_table.foreign_keys) == 2
    assert len({column.name for column in pilot_table.columns}) == len(
        pilot_table.columns
    )


def test_ternary_association_becomes_table_with_three_foreign_keys() -> None:
    model = DiagramModel()
    entities = [
        add_entity(model, name, (f"id_{name.lower()}",)) for name in ("A", "B", "C")
    ]
    association = Association("TERNAIRE", attributes=[Attribute("quantite")])
    model.add_association(association)
    for entity in entities:
        model.create_relation(entity.id, association.id, Cardinality("0", "N"))

    table = McdToMldTransformer().transform(model).table("TERNAIRE")

    assert [column.name for column in table.primary_key_columns] == [
        "id_a",
        "id_b",
        "id_c",
    ]
    assert len(table.foreign_keys) == 3
    assert table.column("quantite").source_element_id == association.id
    assert all(column.nullable is False for column in table.primary_key_columns)


def test_ternary_association_uses_explicit_association_identifier() -> None:
    model = DiagramModel()
    entities = [
        add_entity(model, name, (f"id_{name.lower()}",)) for name in ("A", "B", "C")
    ]
    association = Association(
        "TERNAIRE",
        attributes=[
            Attribute("numero_occurrence", identifier=True),
            Attribute("quantite"),
        ],
    )
    model.add_association(association)
    for entity in entities:
        model.create_relation(entity.id, association.id, Cardinality("0", "N"))

    table = McdToMldTransformer().transform(model).table("TERNAIRE")

    assert [column.name for column in table.primary_key_columns] == [
        "numero_occurrence"
    ]
    assert len(table.foreign_keys) == 3
    assert not any(
        column.id in table.primary_key
        for foreign_key in table.foreign_keys
        for column in (
            table.column_by_id(column_id) for column_id in foreign_key.column_ids
        )
    )


def test_force_fk_is_rejected_for_ternary_association() -> None:
    model = DiagramModel()
    entities = [
        add_entity(model, name, (f"id_{name.lower()}",)) for name in ("A", "B", "C")
    ]
    association = Association(
        "TERNAIRE",
        materialization_strategy=MaterializationStrategy.FORCE_FK,
    )
    model.add_association(association)
    for entity in entities:
        model.create_relation(entity.id, association.id, Cardinality("0", "N"))

    with pytest.raises(MLDTransformationError, match=r"FORCE_FK.*n-aire"):
        McdToMldTransformer().transform(model)


def test_reflexive_many_to_many_uses_roles_to_disambiguate_foreign_keys() -> None:
    model = DiagramModel()
    entity = add_entity(model, "EMPLOYE", ("id_employe",))
    association = Association("COLLABORER")
    model.add_association(association)
    model.create_relation(
        entity.id,
        association.id,
        Cardinality("0", "N"),
        role="mentor",
    )
    model.create_relation(
        entity.id,
        association.id,
        Cardinality("0", "N"),
        role="mentoré",
    )

    table = McdToMldTransformer().transform(model).table("COLLABORER")

    assert [column.name for column in table.primary_key_columns] == [
        "id_employe_mentor",
        "id_employe_mentoré",
    ]
    assert len(table.foreign_keys) == 2
    assert len({foreign_key.id for foreign_key in table.foreign_keys}) == 2
    assert all(
        foreign_key.referenced_table_id
        == McdToMldTransformer._entity_table_id(entity.id)
        for foreign_key in table.foreign_keys
    )


def test_reflexive_one_to_many_creates_a_self_foreign_key() -> None:
    model = DiagramModel()
    entity = add_entity(model, "EMPLOYE", ("id_employe",))
    association = Association("SUPERVISER")
    model.add_association(association)
    model.create_relation(
        entity.id,
        association.id,
        Cardinality("0", "N"),
        role="superviseur",
    )
    model.create_relation(
        entity.id,
        association.id,
        Cardinality("0", "1"),
        role="supervisé",
    )

    table = McdToMldTransformer().transform(model).table("EMPLOYE")

    assert len(table.foreign_keys) == 1
    foreign_key = table.foreign_keys[0]
    assert foreign_key.referenced_table_id == table.id
    assert table.column_by_id(foreign_key.column_ids[0]).name == (
        "id_employe_superviseur"
    )
    assert table.column_by_id(foreign_key.column_ids[0]).nullable is True


def test_reflexive_one_to_one_creates_a_unique_self_foreign_key() -> None:
    model = DiagramModel()
    entity = add_entity(model, "PERSONNE", ("id_personne",))
    association = Association("PARRAINER")
    model.add_association(association)
    model.create_relation(
        entity.id,
        association.id,
        Cardinality("0", "1"),
        role="parrain",
    )
    model.create_relation(
        entity.id,
        association.id,
        Cardinality("0", "1"),
        role="filleul",
    )

    table = McdToMldTransformer().transform(model).table("PERSONNE")

    assert len(table.foreign_keys) == 1
    assert len(table.unique_constraints) == 1
    foreign_key = table.foreign_keys[0]
    assert table.unique_constraints[0].column_ids == foreign_key.column_ids
    assert table.column_by_id(foreign_key.column_ids[0]).name in {
        "id_personne_parrain",
        "id_personne_filleul",
    }


def test_reflexive_association_requires_distinct_non_empty_roles() -> None:
    model = DiagramModel()
    entity = add_entity(model, "PERSONNE", ("id_personne",))
    association = Association("PARENTE")
    model.add_association(association)
    model.create_relation(entity.id, association.id, Cardinality("0", "N"))
    model.create_relation(entity.id, association.id, Cardinality("0", "N"))

    with pytest.raises(MLDTransformationError, match="rôle"):
        McdToMldTransformer().transform(model)


def test_one_to_one_with_attributes_is_rejected_instead_of_losing_data() -> None:
    model, *_ = binary_model(("1", "1"), ("0", "1"), association_attributes=("date",))

    with pytest.raises(MLDTransformationError, match="porte des attributs"):
        McdToMldTransformer().transform(model)


def test_transformation_does_not_modify_mcd_and_is_repeatable() -> None:
    model, *_ = binary_model(("0", "N"), ("1", "N"), association_attributes=("points",))
    repository = JsonDiagramRepository()
    before = deepcopy(repository.to_dict(model))

    first = McdToMldTransformer().transform(model)
    second = McdToMldTransformer().transform(model)

    assert repository.to_dict(model) == before
    assert first == second
    assert [table.name for table in first.tables] == ["ALPHA", "BETA", "LIER"]


def test_graphical_positions_do_not_affect_logical_fingerprint() -> None:
    model, first, *_ = binary_model(("0", "N"), ("1", "N"))
    before = mcd_logical_fingerprint(model)

    model.move_node(first.id, Position(999, -400))

    assert mcd_logical_fingerprint(model) == before


def test_text_renderer_lists_pk_fk_and_references() -> None:
    model, *_ = binary_model(("0", "N"), ("1", "N"))

    text = render_mld_text(McdToMldTransformer().transform(model))

    assert "ALPHA" in text
    assert "PK/NOT NULL" in text
    assert "PK/FK/NOT NULL" in text
    assert "FK (id_alpha) → ALPHA(id_alpha)" in text


def test_motogp_reference_model() -> None:
    model = DiagramModel()
    pilot = add_entity(model, "PILOTE", ("id_pilote",), ("nom",))
    course = add_entity(model, "COURSE", ("id_course",), ("date",))
    participate = Association(
        "PARTICIPER",
        attributes=[Attribute("position"), Attribute("points"), Attribute("temps")],
    )
    model.add_association(participate)
    model.create_relation(pilot.id, participate.id, Cardinality("0", "N"))
    model.create_relation(course.id, participate.id, Cardinality("1", "N"))

    mld = McdToMldTransformer().transform(model)
    table = mld.table("PARTICIPER")

    assert [table_item.name for table_item in mld.tables] == [
        "COURSE",
        "PARTICIPER",
        "PILOTE",
    ]
    assert [column.name for column in table.columns] == [
        "id_course",
        "id_pilote",
        "position",
        "points",
        "temps",
    ]
    assert [column.name for column in table.primary_key_columns] == [
        "id_course",
        "id_pilote",
    ]
    assert len(table.foreign_keys) == 2


def test_auto_non_historized_one_to_many_keeps_classic_fk_rule() -> None:
    model, _alpha, _beta, association = binary_model(
        ("0", "N"), ("1", "1"), association_attributes=("date_debut",)
    )

    mld = McdToMldTransformer().transform(model)

    assert association.is_historized is False
    assert association.materialization_strategy is MaterializationStrategy.AUTO
    assert len(mld.tables) == 2
    assert all(table.source is MLDTableSource.ENTITY for table in mld.tables)
    assert mld.table("BETA").column("date_debut")


def test_historized_one_to_many_auto_creates_independent_table() -> None:
    model, _alpha, _beta, association = binary_model(
        ("0", "N"),
        ("1", "1"),
        association_attributes=("date_debut", "date_fin", "role"),
    )
    association.is_historized = True

    table = McdToMldTransformer().transform(model).table("LIER")

    assert table.source is MLDTableSource.ASSOCIATION
    assert table.source_element_id == association.id
    assert table.is_historized
    assert [column.name for column in table.primary_key_columns] == ["id_lier"]
    assert table.primary_key_columns[0].generated
    assert [column.name for column in table.columns] == [
        "id_lier",
        "id_alpha",
        "id_beta",
        "date_debut",
        "date_fin",
        "role",
    ]
    assert table.column("id_alpha").nullable is True
    assert table.column("id_beta").nullable is False
    assert {foreign_key.source_cardinality for foreign_key in table.foreign_keys} == {
        ("0", "N"),
        ("1", "1"),
    }
    assert all(
        foreign_key.source_relation_id in model.relations
        for foreign_key in table.foreign_keys
    )


def test_historized_one_to_many_force_table_creates_independent_table() -> None:
    model, *_nodes, association = binary_model(("0", "N"), ("1", "1"))
    association.is_historized = True
    association.materialization_strategy = MaterializationStrategy.FORCE_TABLE

    table = McdToMldTransformer().transform(model).table("LIER")

    assert table.is_historized
    assert [column.name for column in table.primary_key_columns] == ["id_lier"]
    assert [column.name for column in table.columns] == [
        "id_lier",
        "id_alpha",
        "id_beta",
    ]
    assert len(table.foreign_keys) == 2


def test_force_table_materializes_non_historized_one_to_one_with_attributes() -> None:
    model, *_nodes, association = binary_model(
        ("0", "1"), ("1", "1"), association_attributes=("date_signature",)
    )
    association.materialization_strategy = MaterializationStrategy.FORCE_TABLE

    table = McdToMldTransformer().transform(model).table("LIER")

    assert not table.is_historized
    assert [column.name for column in table.primary_key_columns] == ["id_lier"]
    assert table.column("date_signature")
    assert len(table.foreign_keys) == 2


def test_force_fk_one_to_many_keeps_classic_fk_transformation() -> None:
    model, _alpha, _beta, association = binary_model(
        ("0", "N"), ("1", "1"), association_attributes=("date_debut",)
    )
    association.materialization_strategy = MaterializationStrategy.FORCE_FK

    mld = McdToMldTransformer().transform(model)

    assert len(mld.tables) == 2
    assert len(mld.table("BETA").foreign_keys) == 1
    assert mld.table("BETA").column("date_debut")


def test_historized_many_to_many_keeps_composite_fk_primary_key() -> None:
    model, *_nodes, association = binary_model(
        ("0", "N"), ("1", "N"), association_attributes=("date",)
    )
    association.is_historized = True

    table = McdToMldTransformer().transform(model).table("LIER")

    assert table.is_historized
    assert [column.name for column in table.primary_key_columns] == [
        "id_alpha",
        "id_beta",
    ]
    assert "id_lier" not in {column.name for column in table.columns}


def test_force_table_many_to_many_does_not_add_technical_key() -> None:
    model, *_nodes, association = binary_model(("0", "N"), ("1", "N"))
    association.materialization_strategy = MaterializationStrategy.FORCE_TABLE

    table = McdToMldTransformer().transform(model).table("LIER")

    assert [column.name for column in table.primary_key_columns] == [
        "id_alpha",
        "id_beta",
    ]
    foreign_key_columns = {
        column_id
        for foreign_key in table.foreign_keys
        for column_id in foreign_key.column_ids
    }
    assert set(table.primary_key) == foreign_key_columns
    assert len(table.foreign_keys) == 2


def test_force_fk_many_to_many_is_rejected_by_transformer() -> None:
    model, *_nodes, association = binary_model(("0", "N"), ("1", "N"))
    association.materialization_strategy = MaterializationStrategy.FORCE_FK

    with pytest.raises(MLDTransformationError, match=r"FORCE_FK.*N:N"):
        McdToMldTransformer().transform(model)


def test_historized_force_fk_contradiction_is_rejected_by_transformer() -> None:
    model, *_nodes, association = binary_model(("0", "N"), ("1", "1"))
    association.is_historized = True
    association.materialization_strategy = MaterializationStrategy.FORCE_FK

    with pytest.raises(MLDTransformationError, match=r"historisée.*FORCE_FK"):
        McdToMldTransformer().transform(model)


def test_materialized_association_uses_its_explicit_identifier() -> None:
    model, *_nodes, association = binary_model(
        ("0", "N"), ("1", "1"), association_attributes=("date_debut",)
    )
    identifier = Attribute("numero_engagement", identifier=True)
    association.attributes.insert(0, identifier)
    association.is_historized = True

    table = McdToMldTransformer().transform(model).table("LIER")

    assert [column.name for column in table.primary_key_columns] == [
        "numero_engagement"
    ]
    assert table.primary_key_columns[0].source_attribute_id == identifier.id
    assert "id_lier" not in {column.name for column in table.columns}


def test_technical_identifier_is_deterministic() -> None:
    model, *_nodes, association = binary_model(("0", "N"), ("1", "1"))
    association.is_historized = True

    first = McdToMldTransformer().transform(model).table("LIER")
    second = McdToMldTransformer().transform(model).table("LIER")

    assert first.primary_key == second.primary_key
    assert first.primary_key_columns[0] == second.primary_key_columns[0]
    assert first.primary_key_columns[0].name == "id_lier"


def test_historized_table_allows_repeated_entity_pair_occurrences() -> None:
    model, *_nodes, association = binary_model(("0", "N"), ("1", "1"))
    association.is_historized = True

    table = McdToMldTransformer().transform(model).table("LIER")
    foreign_key_columns = {
        column_id
        for foreign_key in table.foreign_keys
        for column_id in foreign_key.column_ids
    }

    assert set(table.primary_key).isdisjoint(foreign_key_columns)
    assert table.unique_constraints == []
