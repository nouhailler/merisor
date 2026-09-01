from __future__ import annotations

from merisor.application import McdToMldTransformer, SQLGenerator, SQLTarget
from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    Entity,
    MCDModel,
    MLDDataType,
)


def _entity(name: str, identifier_name: str, entity_id: str) -> Entity:
    return Entity(
        name,
        id=entity_id,
        attributes=[Attribute(identifier_name, True, id=f"{entity_id}-identifier")],
    )


def test_superviser_reflexive_association_reaches_mld_and_sql() -> None:
    model = MCDModel()
    employee = _entity("EMPLOYE", "id_employe", "employee")
    supervise = Association("SUPERVISER", id="supervise")
    model.add_entity(employee)
    model.add_association(supervise)
    model.create_relation(
        employee.id,
        supervise.id,
        Cardinality("0", "N"),
        role="superviseur",
    )
    model.create_relation(
        employee.id,
        supervise.id,
        Cardinality("0", "1"),
        role="supervisé",
    )

    mld = McdToMldTransformer().transform(model)
    table = mld.table("EMPLOYE")

    assert len(mld.tables) == 1
    assert len(table.foreign_keys) == 1
    foreign_key = table.foreign_keys[0]
    assert foreign_key.referenced_table_id == table.id
    assert table.column_by_id(foreign_key.column_ids[0]).name == (
        "id_employe_superviseur"
    )
    assert table.column_by_id(foreign_key.column_ids[0]).nullable is True

    sql = SQLGenerator().generate(mld, SQLTarget.POSTGRESQL)
    assert 'CREATE TABLE "EMPLOYE"' in sql
    assert '"id_employe_superviseur" INTEGER' in sql
    assert 'REFERENCES "EMPLOYE" ("id_employe")' in sql


def test_fournir_ternary_association_reaches_mld_and_all_sql_dialects() -> None:
    model = MCDModel()
    supplier = _entity("FOURNISSEUR", "id_fournisseur", "supplier")
    product = _entity("PRODUIT", "id_produit", "product")
    warehouse = _entity("ENTREPOT", "id_entrepot", "warehouse")
    provide = Association(
        "FOURNIR",
        id="provide",
        attributes=[
            Attribute(
                "prix_achat",
                id="purchase-price",
                data_type=MLDDataType("DECIMAL", precision=10, scale=2),
            ),
            Attribute("quantite", id="quantity", data_type=MLDDataType("INTEGER")),
        ],
    )
    for entity in (supplier, product, warehouse):
        model.add_entity(entity)
    model.add_association(provide)
    model.create_relation(supplier.id, provide.id, Cardinality("0", "N"))
    model.create_relation(product.id, provide.id, Cardinality("0", "N"))
    model.create_relation(warehouse.id, provide.id, Cardinality("0", "N"))

    mld = McdToMldTransformer().transform(model)
    table = mld.table("FOURNIR")

    assert [column.name for column in table.primary_key_columns] == [
        "id_entrepot",
        "id_fournisseur",
        "id_produit",
    ]
    assert len(table.foreign_keys) == 3
    assert {
        mld.table_by_id(item.referenced_table_id).name for item in table.foreign_keys
    } == {
        "FOURNISSEUR",
        "PRODUIT",
        "ENTREPOT",
    }
    assert table.column("prix_achat").data_type == MLDDataType(
        "DECIMAL", precision=10, scale=2
    )
    assert table.column("quantite").source_element_id == provide.id

    for target in SQLTarget:
        sql = SQLGenerator().generate(mld, target)
        quote = "`" if target is SQLTarget.MYSQL else '"'
        assert f"CREATE TABLE {quote}FOURNIR{quote}" in sql
        assert sql.count("FOREIGN KEY") == 3
        assert "PRIMARY KEY" in sql
        assert "prix_achat" in sql
        assert "quantite" in sql
