from __future__ import annotations

from datetime import datetime

import pytest

from merisor.application import (
    McdToMldTransformer,
    SQLGenerationError,
    SQLGenerator,
    SQLTarget,
)
from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    DiagramModel,
    Entity,
    InheritanceStrategy,
    MLDCheckConstraint,
    MLDColumn,
    MLDDataType,
    MLDDataTypeName,
    MLDForeignKey,
    MLDIndex,
    MLDModel,
    MLDReferentialAction,
    MLDTable,
    MLDTableSource,
    MLDUniqueConstraint,
)

INTEGER = MLDDataType(MLDDataTypeName.INTEGER)
VARCHAR_100 = MLDDataType.varchar(100)


def mld_column(
    column_id: str,
    name: str,
    data_type: MLDDataType = INTEGER,
    *,
    nullable: bool | None = False,
    auto_increment: bool = False,
) -> MLDColumn:
    return MLDColumn(
        id=column_id,
        name=name,
        nullable=nullable,
        data_type=data_type,
        auto_increment=auto_increment,
    )


def mld_table(
    table_id: str,
    name: str,
    columns: list[MLDColumn],
    primary_key: tuple[str, ...],
) -> MLDTable:
    return MLDTable(
        id=table_id,
        name=name,
        source_element_id=f"source:{table_id}",
        source=MLDTableSource.ENTITY,
        columns=columns,
        primary_key=primary_key,
    )


def mld_model(*tables: MLDTable) -> MLDModel:
    return MLDModel(list(tables), generated_from_fingerprint="test")


def simple_model(*, auto_increment: bool = False) -> MLDModel:
    table = mld_table(
        "pilot",
        "PILOTE",
        [
            mld_column("pilot.id", "id_pilote", auto_increment=auto_increment),
            mld_column("pilot.name", "nom", VARCHAR_100, nullable=True),
        ],
        ("pilot.id",),
    )
    return mld_model(table)


@pytest.mark.parametrize(
    ("target", "integer_type", "text_type", "quote"),
    [
        (SQLTarget.POSTGRESQL, "INTEGER", "VARCHAR(100)", '"'),
        (SQLTarget.SQLITE, "INTEGER", "TEXT", '"'),
        (SQLTarget.MYSQL, "INT", "VARCHAR(100)", "`"),
    ],
)
def test_simple_table_and_primary_key_for_each_dialect(
    target: SQLTarget, integer_type: str, text_type: str, quote: str
) -> None:
    sql = SQLGenerator().generate(
        simple_model(),
        target,
        project_name="MotoGP",
        generated_at=datetime(2026, 8, 28, 12, 0),
    )

    assert f"CREATE TABLE {quote}PILOTE{quote}" in sql
    assert f"{quote}id_pilote{quote} {integer_type} NOT NULL" in sql
    assert f"{quote}nom{quote} {text_type}" in sql
    assert f"PRIMARY KEY ({quote}id_pilote{quote})" in sql
    assert "Projet : MotoGP" in sql
    assert target.display_name in sql


def test_composite_primary_key_is_preserved_without_technical_key() -> None:
    table = mld_table(
        "participate",
        "PARTICIPER",
        [
            mld_column("pilot", "id_pilote"),
            mld_column("course", "id_course"),
            mld_column("points", "points", INTEGER, nullable=True),
        ],
        ("pilot", "course"),
    )

    sql = SQLGenerator().generate(mld_model(table), SQLTarget.POSTGRESQL)

    assert 'PRIMARY KEY ("id_pilote", "id_course")' in sql
    assert "id_participer" not in sql


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (
            SQLTarget.POSTGRESQL,
            (
                "INTEGER",
                "BIGINT",
                "DECIMAL(10,2)",
                "DOUBLE PRECISION",
                "BOOLEAN",
                "VARCHAR(42)",
                "TEXT",
                "DATE",
                "TIME",
                "TIMESTAMP",
                "TIMESTAMP",
            ),
        ),
        (
            SQLTarget.SQLITE,
            (
                "INTEGER",
                "INTEGER",
                "NUMERIC",
                "REAL",
                "INTEGER",
                "TEXT",
                "TEXT",
                "TEXT",
                "TEXT",
                "TEXT",
                "TEXT",
            ),
        ),
        (
            SQLTarget.MYSQL,
            (
                "INT",
                "BIGINT",
                "DECIMAL(10,2)",
                "DOUBLE",
                "BOOLEAN",
                "VARCHAR(42)",
                "TEXT",
                "DATE",
                "TIME",
                "DATETIME",
                "TIMESTAMP",
            ),
        ),
    ],
)
def test_all_initial_logical_types_are_mapped(
    target: SQLTarget, expected: tuple[str, ...]
) -> None:
    types = (
        MLDDataType(MLDDataTypeName.INTEGER),
        MLDDataType(MLDDataTypeName.BIGINT),
        MLDDataType(MLDDataTypeName.DECIMAL, precision=10, scale=2),
        MLDDataType(MLDDataTypeName.FLOAT),
        MLDDataType(MLDDataTypeName.BOOLEAN),
        MLDDataType.varchar(42),
        MLDDataType(MLDDataTypeName.TEXT),
        MLDDataType(MLDDataTypeName.DATE),
        MLDDataType(MLDDataTypeName.TIME),
        MLDDataType(MLDDataTypeName.DATETIME),
        MLDDataType(MLDDataTypeName.TIMESTAMP),
    )
    columns = [
        mld_column(f"c{index}", f"c{index}", data_type)
        for index, data_type in enumerate(types)
    ]
    table = mld_table("types", "TYPES_TEST", columns, ("c0",))

    sql = SQLGenerator().generate(mld_model(table), target)

    for index, sql_type in enumerate(expected):
        assert f"c{index}" in sql
        assert sql_type in sql


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (SQLTarget.POSTGRESQL, "GENERATED BY DEFAULT AS IDENTITY"),
        (SQLTarget.SQLITE, "INTEGER PRIMARY KEY AUTOINCREMENT"),
        (SQLTarget.MYSQL, "AUTO_INCREMENT"),
    ],
)
def test_generated_identifier_uses_dialect_identity_syntax(
    target: SQLTarget, expected: str
) -> None:
    sql = SQLGenerator().generate(simple_model(auto_increment=True), target)

    assert expected in sql
    if target is SQLTarget.SQLITE:
        assert sql.count("PRIMARY KEY") == 1


def relational_model() -> MLDModel:
    pilot = mld_table(
        "pilot",
        "PILOTE",
        [mld_column("pilot.id", "id_pilote")],
        ("pilot.id",),
    )
    team = mld_table(
        "team",
        "EQUIPE",
        [mld_column("team.id", "id_equipe")],
        ("team.id",),
    )
    engage = MLDTable(
        id="engage",
        name="ENGAGER",
        source_element_id="association:engager",
        source=MLDTableSource.ASSOCIATION,
        is_historized=True,
        columns=[
            mld_column("engage.id", "id_engager", auto_increment=True),
            mld_column("engage.pilot", "id_pilote", nullable=True),
            mld_column("engage.team", "id_equipe", nullable=False),
            mld_column(
                "engage.start",
                "date_debut",
                MLDDataType(MLDDataTypeName.DATE),
                nullable=True,
            ),
            mld_column(
                "engage.end",
                "date_fin",
                MLDDataType(MLDDataTypeName.DATE),
                nullable=True,
            ),
        ],
        primary_key=("engage.id",),
        foreign_keys=[
            MLDForeignKey(
                id="fk.engage.pilot",
                column_ids=("engage.pilot",),
                referenced_table_id="pilot",
                referenced_column_ids=("pilot.id",),
                source_association_id="association:engager",
            ),
            MLDForeignKey(
                id="fk.engage.team",
                column_ids=("engage.team",),
                referenced_table_id="team",
                referenced_column_ids=("team.id",),
                source_association_id="association:engager",
            ),
        ],
    )
    return mld_model(engage, pilot, team)


@pytest.mark.parametrize("target", list(SQLTarget))
def test_historized_table_generates_multiple_foreign_keys_without_pair_unique(
    target: SQLTarget,
) -> None:
    sql = SQLGenerator().generate(relational_model(), target)

    assert sql.count("FOREIGN KEY") == 2
    assert "id_pilote" in sql and "id_equipe" in sql
    assert "UNIQUE" not in sql
    assert "CREATE INDEX" not in sql
    assert "ON DELETE" not in sql and "ON UPDATE" not in sql
    assert sql.index("Table : EQUIPE") < sql.index("Table : ENGAGER")
    assert sql.index("Table : PILOTE") < sql.index("Table : ENGAGER")


def test_nullability_unique_check_index_and_referential_actions() -> None:
    model = relational_model()
    engage = model.table("ENGAGER")
    engage.unique_constraints.append(
        MLDUniqueConstraint(
            id="uq.role",
            name="uq_engager_role",
            column_ids=("engage.start",),
            source_association_id="association:engager",
        )
    )
    engage.check_constraints.append(
        MLDCheckConstraint(
            id="check.dates",
            name="ck_engager_dates",
            expression='"date_fin" IS NULL OR "date_fin" >= "date_debut"',
        )
    )
    engage.indexes.append(
        MLDIndex(
            id="index.start",
            name="idx_engager_date_debut",
            column_ids=("engage.start",),
        )
    )
    old_fk = engage.foreign_keys[0]
    engage.foreign_keys[0] = MLDForeignKey(
        id=old_fk.id,
        column_ids=old_fk.column_ids,
        referenced_table_id=old_fk.referenced_table_id,
        referenced_column_ids=old_fk.referenced_column_ids,
        source_association_id=old_fk.source_association_id,
        on_delete=MLDReferentialAction.SET_NULL,
        on_update=MLDReferentialAction.CASCADE,
    )

    sql = SQLGenerator().generate(model, SQLTarget.POSTGRESQL)

    assert '"id_equipe" INTEGER NOT NULL' in sql
    assert '    "id_pilote" INTEGER,' in sql
    assert 'CONSTRAINT "uq_engager_role" UNIQUE ("date_debut")' in sql
    assert 'CONSTRAINT "ck_engager_dates" CHECK (' in sql
    assert 'CREATE INDEX "idx_engager_date_debut"' in sql
    assert "ON DELETE SET NULL ON UPDATE CASCADE" in sql


def cyclic_model() -> MLDModel:
    first = mld_table(
        "a",
        "A",
        [mld_column("a.id", "id_a"), mld_column("a.b", "id_b", nullable=True)],
        ("a.id",),
    )
    second = mld_table(
        "b",
        "B",
        [mld_column("b.id", "id_b"), mld_column("b.a", "id_a", nullable=True)],
        ("b.id",),
    )
    first.foreign_keys.append(
        MLDForeignKey(
            id="fk.a.b",
            column_ids=("a.b",),
            referenced_table_id="b",
            referenced_column_ids=("b.id",),
            source_association_id="ab",
        )
    )
    second.foreign_keys.append(
        MLDForeignKey(
            id="fk.b.a",
            column_ids=("b.a",),
            referenced_table_id="a",
            referenced_column_ids=("a.id",),
            source_association_id="ba",
        )
    )
    return mld_model(first, second)


@pytest.mark.parametrize("target", [SQLTarget.POSTGRESQL, SQLTarget.MYSQL])
def test_cycles_use_alter_table_only_for_dialects_that_support_it(
    target: SQLTarget,
) -> None:
    sql = SQLGenerator().generate(cyclic_model(), target)

    assert sql.count("CREATE TABLE") == 2
    assert sql.count("ALTER TABLE") == 2
    create_part, alter_part = sql.split("ALTER TABLE", 1)
    assert "FOREIGN KEY" not in create_part
    assert "FOREIGN KEY" in alter_part


def test_sqlite_cycles_keep_foreign_keys_inside_create_table() -> None:
    sql = SQLGenerator().generate(cyclic_model(), SQLTarget.SQLITE)

    assert "PRAGMA foreign_keys = ON;" in sql
    assert "ALTER TABLE" not in sql
    assert sql.count("FOREIGN KEY") == 2


@pytest.mark.parametrize(
    ("target", "quoted"),
    [
        (SQLTarget.POSTGRESQL, '"USER"'),
        (SQLTarget.SQLITE, '"USER"'),
        (SQLTarget.MYSQL, "`USER`"),
    ],
)
def test_reserved_identifiers_are_warned_and_escaped(
    target: SQLTarget, quoted: str
) -> None:
    table = mld_table("user", "USER", [mld_column("user.id", "order")], ("user.id",))
    generator = SQLGenerator()

    report = generator.validate(mld_model(table), target)
    sql = generator.generate(mld_model(table), target)

    assert report.is_valid
    assert len(report.warnings) == 2
    assert quoted in sql


def test_missing_primary_key_blocks_generation_with_business_message() -> None:
    table = mld_table("pilot", "PILOTE", [mld_column("pilot.id", "id_pilote")], ())

    with pytest.raises(SQLGenerationError) as captured:
        SQLGenerator().generate(mld_model(table), SQLTarget.POSTGRESQL)

    assert any(
        issue.code == "table.primary_key_missing"
        and "ne possède pas de clé primaire" in issue.message
        for issue in captured.value.report.errors
    )


def test_legacy_mld_column_metadata_receives_safe_defaults() -> None:
    column = MLDColumn(id="legacy.id", name="id", nullable=False)

    assert column.data_type == MLDDataType.varchar(100)
    assert column.default is None
    assert not column.auto_increment


def test_missing_foreign_table_and_unknown_type_are_reported() -> None:
    model = simple_model()
    table = model.table("PILOTE")
    table.foreign_keys.append(
        MLDForeignKey(
            id="fk.missing",
            column_ids=("pilot.id",),
            referenced_table_id="missing",
            referenced_column_ids=("missing.id",),
            source_association_id="missing",
        )
    )
    object.__setattr__(table.columns[1], "data_type", "UNKNOWN")

    report = SQLGenerator().validate(model, SQLTarget.SQLITE)

    assert {issue.code for issue in report.errors} >= {
        "foreign_key.table_missing",
        "column.type_unknown",
    }


def test_complete_motogp_chain_mcd_to_mld_to_all_sql_dialects() -> None:
    mcd = DiagramModel()
    pilot = Entity(
        "PILOTE",
        attributes=[Attribute("id_pilote", identifier=True), Attribute("nom")],
    )
    team = Entity(
        "EQUIPE",
        attributes=[Attribute("id_equipe", identifier=True), Attribute("nom")],
    )
    engage = Association(
        "ENGAGER",
        attributes=[Attribute("date_debut"), Attribute("date_fin")],
        is_historized=True,
    )
    mcd.add_entity(pilot)
    mcd.add_entity(team)
    mcd.add_association(engage)
    mcd.create_relation(pilot.id, engage.id, Cardinality("0", "N"))
    mcd.create_relation(team.id, engage.id, Cardinality("1", "1"))

    mld = McdToMldTransformer().transform(mcd)
    engage_table = mld.table("ENGAGER")

    assert engage_table.primary_key_columns[0].auto_increment
    assert len(engage_table.foreign_keys) == 2
    for target in SQLTarget:
        sql = SQLGenerator().generate(mld, target, project_name="MotoGP")
        assert sql.count("CREATE TABLE") == 3
        assert sql.count("FOREIGN KEY") == 2
        assert "date_debut" in sql and "date_fin" in sql
        assert "UNIQUE" not in sql


@pytest.mark.parametrize(
    ("target", "quote", "expected_types"),
    [
        (
            SQLTarget.POSTGRESQL,
            '"',
            {
                "id_evenement": "BIGINT",
                "date_evenement": "DATE",
                "montant": "DECIMAL(10,2)",
                "description": "TEXT",
                "actif": "BOOLEAN",
                "code": "VARCHAR(40)",
            },
        ),
        (
            SQLTarget.SQLITE,
            '"',
            {
                "id_evenement": "INTEGER",
                "date_evenement": "TEXT",
                "montant": "NUMERIC",
                "description": "TEXT",
                "actif": "INTEGER",
                "code": "TEXT",
            },
        ),
        (
            SQLTarget.MYSQL,
            "`",
            {
                "id_evenement": "BIGINT",
                "date_evenement": "DATE",
                "montant": "DECIMAL(10,2)",
                "description": "TEXT",
                "actif": "BOOLEAN",
                "code": "VARCHAR(40)",
            },
        ),
    ],
)
def test_explicit_mcd_types_reach_each_sql_dialect(
    target: SQLTarget,
    quote: str,
    expected_types: dict[str, str],
) -> None:
    mcd = DiagramModel()
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
                "montant",
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
            Attribute(
                "actif",
                data_type=MLDDataType(MLDDataTypeName.BOOLEAN),
            ),
            Attribute("code", data_type=MLDDataType.varchar(40)),
        ],
    )
    mcd.add_entity(entity)

    mld = McdToMldTransformer().transform(mcd)
    sql = SQLGenerator().generate(mld, target)

    for column_name, sql_type in expected_types.items():
        assert f"{quote}{column_name}{quote} {sql_type}" in sql


def test_joined_isa_chain_generates_pk_foreign_key_in_all_dialects() -> None:
    mcd = DiagramModel()
    person = Entity("PERSONNE", attributes=[Attribute("id_personne", identifier=True)])
    client = Entity(
        "CLIENT",
        attributes=[
            Attribute("id_client", identifier=True),
            Attribute("numero_client"),
        ],
    )
    mcd.add_entity(person)
    mcd.add_entity(client)
    mcd.create_inheritance(person.id, (client.id,), InheritanceStrategy.JOINED)

    mld = McdToMldTransformer().transform(mcd)
    for target in SQLTarget:
        sql = SQLGenerator().generate(mld, target, project_name="ISA")
        assert sql.count("CREATE TABLE") == 2
        assert sql.count("FOREIGN KEY") == 1
        assert "PERSONNE" in sql and "CLIENT" in sql
        assert "id_personne" in sql
