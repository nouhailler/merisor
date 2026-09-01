from __future__ import annotations

import pytest

from merisor.application.query_generator import (
    QueryGenerationError as GenerationError,
)
from merisor.application.query_generator import QueryTarget, SQLQueryGenerator
from merisor.domain import (
    MLDColumn,
    MLDDataType,
    MLDForeignKey,
    MLDModel,
    MLDTable,
    MLDTableSource,
)


def _sales_model() -> MLDModel:
    client = MLDTable(
        id="client",
        name="CLIENT",
        source_element_id="client-source",
        source=MLDTableSource.ENTITY,
        columns=[
            MLDColumn("client-id", "id_client", False, MLDDataType("INTEGER")),
            MLDColumn("client-name", "nom", False, MLDDataType.varchar(100)),
        ],
        primary_key=("client-id",),
    )
    order = MLDTable(
        id="order",
        name="COMMANDE",
        source_element_id="order-source",
        source=MLDTableSource.ENTITY,
        columns=[
            MLDColumn("order-id", "id_commande", False, MLDDataType("INTEGER")),
            MLDColumn("order-client", "id_client", False, MLDDataType("INTEGER")),
        ],
        primary_key=("order-id",),
        foreign_keys=[
            MLDForeignKey(
                "order-client-fk",
                ("order-client",),
                "client",
                ("client-id",),
                "place",
            )
        ],
    )
    line = MLDTable(
        id="line",
        name="LIGNE_COMMANDE",
        source_element_id="line-source",
        source=MLDTableSource.ENTITY,
        columns=[
            MLDColumn("line-id", "id_ligne", False, MLDDataType("INTEGER")),
            MLDColumn("line-order", "id_commande", False, MLDDataType("INTEGER")),
            MLDColumn(
                "line-amount",
                "montant",
                False,
                MLDDataType("DECIMAL", precision=10, scale=2),
            ),
        ],
        primary_key=("line-id",),
        foreign_keys=[
            MLDForeignKey(
                "line-order-fk",
                ("line-order",),
                "order",
                ("order-id",),
                "contain",
            )
        ],
    )
    return MLDModel([line, order, client], "fingerprint")


def test_top_clients_query_uses_fk_path_measure_grouping_and_limit() -> None:
    result = SQLQueryGenerator().generate(
        _sales_model(),
        "Afficher les 10 meilleurs clients selon le montant total de leurs commandes.",
        QueryTarget.POSTGRESQL,
    )

    assert result.used_tables == ("CLIENT", "COMMANDE", "LIGNE_COMMANDE")
    assert 'FROM "CLIENT" AS t1' in result.sql
    assert 'JOIN "COMMANDE" AS t2' in result.sql
    assert 'JOIN "LIGNE_COMMANDE" AS t3' in result.sql
    assert 'SUM(t3."montant")' in result.sql
    assert 'GROUP BY t1."id_client", t1."nom"' in result.sql
    assert 'ORDER BY SUM(t3."montant") DESC' in result.sql
    assert result.sql.endswith("LIMIT 10;\n")
    assert any("clés étrangères" in item for item in result.explanation)


@pytest.mark.parametrize(
    ("target", "quoted_client"),
    [
        (QueryTarget.POSTGRESQL, '"CLIENT"'),
        (QueryTarget.SQLITE, '"CLIENT"'),
        (QueryTarget.MYSQL, "`CLIENT`"),
        (QueryTarget.MARIADB, "`CLIENT`"),
    ],
)
def test_four_query_dialects_use_their_identifier_quoting(
    target: QueryTarget, quoted_client: str
) -> None:
    result = SQLQueryGenerator().generate(
        _sales_model(), "Afficher les clients", target
    )

    assert f"FROM {quoted_client}" in result.sql
    assert result.target is target


def test_count_per_client_selects_client_as_grouping_subject() -> None:
    result = SQLQueryGenerator().generate(
        _sales_model(),
        "Afficher le nombre de commandes par client",
        QueryTarget.SQLITE,
    )

    assert result.used_tables == ("CLIENT", "COMMANDE")
    assert result.sql.startswith('SELECT\n    t1."id_client"')
    assert 'COUNT(t2."id_commande")' in result.sql
    assert 'GROUP BY t1."id_client", t1."nom"' in result.sql


def test_unknown_business_concept_is_rejected() -> None:
    with pytest.raises(GenerationError, match="problème") as caught:
        SQLQueryGenerator().generate(
            _sales_model(), "Afficher les fournisseurs", QueryTarget.POSTGRESQL
        )

    assert "Aucune table" in caught.value.problems[0]


def test_ranking_without_measure_is_rejected_instead_of_inventing_one() -> None:
    with pytest.raises(GenerationError) as caught:
        SQLQueryGenerator().generate(
            _sales_model(), "Afficher les meilleurs clients", QueryTarget.POSTGRESQL
        )

    assert "aucune mesure" in caught.value.problems[0]


def test_disconnected_tables_are_not_joined_by_guessing() -> None:
    model = _sales_model()
    supplier = MLDTable(
        id="supplier",
        name="FOURNISSEUR",
        source_element_id="supplier-source",
        source=MLDTableSource.ENTITY,
        columns=[MLDColumn("supplier-id", "id", False, MLDDataType("INTEGER"))],
        primary_key=("supplier-id",),
    )
    model.tables.append(supplier)

    with pytest.raises(GenerationError) as caught:
        SQLQueryGenerator().generate(
            model,
            "Afficher les clients et fournisseurs",
            QueryTarget.POSTGRESQL,
        )

    assert "Aucune chaîne de clés étrangères" in caught.value.problems[0]


def test_same_request_is_deterministic() -> None:
    generator = SQLQueryGenerator()
    model = _sales_model()
    description = "Afficher les 10 meilleurs clients selon le montant total"

    first = generator.generate(model, description, QueryTarget.POSTGRESQL)
    second = generator.generate(model, description, QueryTarget.POSTGRESQL)

    assert first == second
