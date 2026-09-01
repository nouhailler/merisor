from __future__ import annotations

import pytest

from merisor.application import (
    McdToMldTransformer,
    SQLTarget,
    TestDataGenerator,
)
from merisor.application import TestDataGenerationError as DataGenerationError
from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    Entity,
    MCDModel,
    MLDColumn,
    MLDDataType,
    MLDDataTypeName,
    MLDForeignKey,
    MLDModel,
    MLDTable,
    MLDTableSource,
)


def _commerce_mld() -> MLDModel:
    model = MCDModel()
    client = Entity(
        "CLIENT",
        id="client",
        attributes=[
            Attribute("id_client", True, id="client-id"),
            Attribute(
                "email",
                id="client-email",
                data_type=MLDDataType.varchar(100),
                unique=True,
            ),
        ],
    )
    order = Entity(
        "COMMANDE",
        id="order",
        attributes=[
            Attribute("id_commande", True, id="order-id"),
            Attribute(
                "payee",
                id="order-paid",
                data_type=MLDDataType(MLDDataTypeName.BOOLEAN),
            ),
        ],
    )
    association = Association("PASSER", id="place")
    model.add_entity(client)
    model.add_entity(order)
    model.add_association(association)
    model.create_relation(client.id, association.id, Cardinality("0", "N"))
    model.create_relation(order.id, association.id, Cardinality("1", "1"))
    return McdToMldTransformer().transform(model)


def _cyclic_mld(*, nullable: bool) -> MLDModel:
    a = MLDTable(
        id="a",
        name="A",
        source_element_id="a-source",
        source=MLDTableSource.ENTITY,
        columns=[
            MLDColumn("a-id", "id_a", False, MLDDataType("INTEGER")),
            MLDColumn("a-b", "id_b", nullable, MLDDataType("INTEGER")),
        ],
        primary_key=("a-id",),
    )
    b = MLDTable(
        id="b",
        name="B",
        source_element_id="b-source",
        source=MLDTableSource.ENTITY,
        columns=[
            MLDColumn("b-id", "id_b", False, MLDDataType("INTEGER")),
            MLDColumn("b-a", "id_a", nullable, MLDDataType("INTEGER")),
        ],
        primary_key=("b-id",),
    )
    a.foreign_keys.append(MLDForeignKey("a-fk", ("a-b",), "b", ("b-id",), "assoc-a"))
    b.foreign_keys.append(MLDForeignKey("b-fk", ("b-a",), "a", ("a-id",), "assoc-b"))
    return MLDModel([a, b], "fingerprint")


def _many_to_many_mld() -> MLDModel:
    model = MCDModel()
    client = Entity(
        "CLIENT",
        id="client",
        attributes=[Attribute("id_client", True, id="client-id")],
    )
    product = Entity(
        "PRODUIT",
        id="product",
        attributes=[Attribute("id_produit", True, id="product-id")],
    )
    association = Association("AIMER", id="like")
    model.add_entity(client)
    model.add_entity(product)
    model.add_association(association)
    model.create_relation(client.id, association.id, Cardinality("0", "N"))
    model.create_relation(product.id, association.id, Cardinality("0", "N"))
    return McdToMldTransformer().transform(model)


def test_insert_order_and_foreign_key_values_follow_dependencies() -> None:
    model = _commerce_mld()
    counts = {
        model.table("CLIENT").id: 2,
        model.table("COMMANDE").id: 4,
    }
    result = TestDataGenerator().generate(
        model,
        SQLTarget.POSTGRESQL,
        counts,
        project_name="Commerce",
    )

    assert result.script.index("-- Table : CLIENT") < result.script.index(
        "-- Table : COMMANDE"
    )
    assert 'INSERT INTO "CLIENT"' in result.script
    assert 'INSERT INTO "COMMANDE"' in result.script
    assert "utilisateur1@example.test" in result.script
    assert result.script.count("(1, TRUE, 1)") == 1
    assert result.generated_rows == counts


@pytest.mark.parametrize(
    ("target", "identifier", "true_literal"),
    [
        (SQLTarget.POSTGRESQL, '"COMMANDE"', "TRUE"),
        (SQLTarget.SQLITE, '"COMMANDE"', "1"),
        (SQLTarget.MYSQL, "`COMMANDE`", "TRUE"),
    ],
)
def test_each_dialect_uses_appropriate_identifiers_and_booleans(
    target: SQLTarget, identifier: str, true_literal: str
) -> None:
    model = _commerce_mld()
    result = TestDataGenerator().generate(
        model,
        target,
        {model.table("CLIENT").id: 1, model.table("COMMANDE").id: 1},
    )

    assert f"INSERT INTO {identifier}" in result.script
    assert true_literal in result.script


def test_generation_is_deterministic() -> None:
    generator = TestDataGenerator()
    model = _commerce_mld()
    counts = {
        model.table("CLIENT").id: 3,
        model.table("COMMANDE").id: 5,
    }

    first = generator.generate(model, SQLTarget.POSTGRESQL, counts)
    second = generator.generate(model, SQLTarget.POSTGRESQL, counts)

    assert first.script == second.script


def test_required_foreign_key_cannot_target_an_empty_table() -> None:
    model = _cyclic_mld(nullable=False)
    counts = {"a": 0, "b": 2}
    with pytest.raises(DataGenerationError, match="problème") as caught:
        TestDataGenerator().generate(model, SQLTarget.POSTGRESQL, counts)

    assert "aucune ligne cible" in caught.value.problems[0].message


def test_optional_foreign_key_to_an_empty_table_becomes_null_with_warning() -> None:
    model = _commerce_mld()
    counts = {
        model.table("CLIENT").id: 0,
        model.table("COMMANDE").id: 2,
    }

    result = TestDataGenerator().generate(model, SQLTarget.POSTGRESQL, counts)

    assert "NULL" in result.script
    assert any("aucune ligne cible" in warning.message for warning in result.warnings)


def test_required_foreign_key_cycle_is_rejected() -> None:
    with pytest.raises(DataGenerationError) as caught:
        TestDataGenerator().generate(
            _cyclic_mld(nullable=False),
            SQLTarget.POSTGRESQL,
            {"a": 2, "b": 2},
        )

    assert "cycle de clés étrangères obligatoires" in caught.value.problems[0].message


def test_nullable_foreign_key_cycle_is_broken_with_null_and_warning() -> None:
    result = TestDataGenerator().generate(
        _cyclic_mld(nullable=True),
        SQLTarget.POSTGRESQL,
        {"a": 2, "b": 2},
    )

    assert "NULL" in result.script
    assert any("rompre un cycle" in warning.message for warning in result.warnings)


def test_many_to_many_rows_use_distinct_cartesian_key_combinations() -> None:
    model = _many_to_many_mld()
    counts = {
        model.table("CLIENT").id: 2,
        model.table("PRODUIT").id: 3,
        model.table("AIMER").id: 6,
    }

    result = TestDataGenerator().generate(model, SQLTarget.POSTGRESQL, counts)

    association_sql = result.script.split("-- Table : AIMER", maxsplit=1)[1]
    assert (
        len(
            {
                line.strip().rstrip(",;")
                for line in association_sql.splitlines()
                if line.startswith("    (")
            }
        )
        == 6
    )


def test_many_to_many_generation_refuses_more_rows_than_unique_pairs() -> None:
    model = _many_to_many_mld()
    counts = {
        model.table("CLIENT").id: 2,
        model.table("PRODUIT").id: 3,
        model.table("AIMER").id: 7,
    }

    with pytest.raises(DataGenerationError) as caught:
        TestDataGenerator().generate(model, SQLTarget.POSTGRESQL, counts)

    assert "combinaisons disponibles" in caught.value.problems[0].message


def test_string_literals_are_escaped() -> None:
    model = MLDModel(
        [
            MLDTable(
                id="author",
                name="AUTEUR",
                source_element_id="author-source",
                source=MLDTableSource.ENTITY,
                columns=[
                    MLDColumn("author-id", "id", False, MLDDataType("INTEGER")),
                    MLDColumn(
                        "author-name",
                        "l'auteur",
                        False,
                        MLDDataType.varchar(100),
                    ),
                ],
                primary_key=("author-id",),
            )
        ],
        "fingerprint",
    )

    script = TestDataGenerator().generate(model, SQLTarget.POSTGRESQL).script

    assert "l''auteur_1" in script
