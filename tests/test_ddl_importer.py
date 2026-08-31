from __future__ import annotations

import pytest

from merisor.application import DDLImportError, SQLDDLImporter, SQLGenerator, SQLTarget
from merisor.domain import MLDDataTypeName, validate_mcd
from merisor.persistence import JsonDiagramRepository

POSTGRESQL_DDL = """
CREATE TABLE pilote (
    id_pilote BIGSERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    actif BOOLEAN DEFAULT TRUE
);
CREATE TABLE course (
    id_course INTEGER PRIMARY KEY,
    date_course DATE NOT NULL
);
CREATE TABLE participer (
    id_pilote BIGINT NOT NULL,
    id_course INTEGER NOT NULL,
    points DECIMAL(5,2),
    PRIMARY KEY (id_pilote, id_course),
    CONSTRAINT fk_pilote FOREIGN KEY (id_pilote) REFERENCES pilote(id_pilote),
    CONSTRAINT fk_course FOREIGN KEY (id_course) REFERENCES course(id_course),
    CHECK (points >= 0)
);
CREATE INDEX idx_pilote_nom ON pilote(nom);
"""


def test_postgresql_ddl_builds_faithful_mld_and_association_mcd() -> None:
    result = SQLDDLImporter().import_text(POSTGRESQL_DDL)

    assert {table.name for table in result.mld.tables} == {
        "pilote",
        "course",
        "participer",
    }
    pilot = result.mld.table("pilote")
    participate = result.mld.table("participer")
    assert pilot.column("id_pilote").auto_increment
    assert pilot.column("nom").data_type.name is MLDDataTypeName.VARCHAR
    assert pilot.column("actif").default == "TRUE"
    assert len(pilot.indexes) == 1
    assert len(participate.foreign_keys) == 2
    assert len(participate.primary_key) == 2
    assert len(participate.check_constraints) == 1
    assert {entity.name for entity in result.mcd.entities.values()} == {
        "pilote",
        "course",
    }
    assert {item.name for item in result.mcd.associations.values()} == {"participer"}
    assert validate_mcd(result.mcd).is_valid


def test_sqlite_inline_foreign_key_reconstructs_one_to_many() -> None:
    ddl = """
    PRAGMA foreign_keys = ON;
    CREATE TABLE equipe (
        id_equipe INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT
    );
    CREATE TABLE pilote (
        id_pilote INTEGER PRIMARY KEY,
        id_equipe INTEGER REFERENCES equipe(id_equipe),
        nom TEXT NOT NULL
    );
    """

    result = SQLDDLImporter().import_text(ddl)

    assert result.mld.table("equipe").column("id_equipe").auto_increment
    assert len(result.mcd.entities) == 2
    assert len(result.mcd.associations) == 1
    association = next(iter(result.mcd.associations.values()))
    relations = result.mcd.connected_relations(association.id)
    cardinalities = [relation.cardinality for relation in relations]
    assert all(cardinality is not None for cardinality in cardinalities)
    assert {
        cardinality.label for cardinality in cardinalities if cardinality is not None
    } == {"0,N", "0,1"}
    assert validate_mcd(result.mcd).is_valid


def test_alter_table_foreign_key_and_unique_are_imported() -> None:
    ddl = """
    CREATE TABLE personne (id_personne INTEGER PRIMARY KEY);
    CREATE TABLE passeport (
        id_passeport INTEGER PRIMARY KEY,
        id_personne INTEGER NOT NULL,
        CONSTRAINT uq_personne UNIQUE (id_personne)
    );
    ALTER TABLE passeport ADD CONSTRAINT fk_personne
      FOREIGN KEY (id_personne) REFERENCES personne(id_personne)
      ON DELETE CASCADE ON UPDATE RESTRICT;
    """

    result = SQLDDLImporter().import_text(ddl)
    passport = result.mld.table("passeport")

    assert len(passport.foreign_keys) == 1
    assert passport.foreign_keys[0].name == "fk_personne"
    assert passport.foreign_keys[0].on_delete is not None
    assert passport.foreign_keys[0].on_update is not None
    assert passport.foreign_keys[0].on_delete.value == "CASCADE"
    assert passport.foreign_keys[0].on_update.value == "RESTRICT"
    assert len(passport.unique_constraints) == 1


def test_primary_key_foreign_key_is_recognized_as_joined_isa() -> None:
    ddl = """
    CREATE TABLE personne (id_personne INTEGER PRIMARY KEY, nom TEXT);
    CREATE TABLE client (
        id_personne INTEGER PRIMARY KEY,
        numero_client TEXT,
        FOREIGN KEY (id_personne) REFERENCES personne(id_personne)
    );
    """

    result = SQLDDLImporter().import_text(ddl)

    assert len(result.mcd.inheritances) == 1
    inheritance = next(iter(result.mcd.inheritances.values()))
    assert result.mcd.entities[inheritance.parent_entity_id].name == "personne"
    assert result.mcd.entities[inheritance.child_entity_ids[0]].name == "client"


def test_reflexive_foreign_key_gets_roles_and_remains_valid() -> None:
    ddl = """
    CREATE TABLE employe (
        id_employe INTEGER PRIMARY KEY,
        responsable_id INTEGER,
        FOREIGN KEY (responsable_id) REFERENCES employe(id_employe)
    );
    """

    result = SQLDDLImporter().import_text(ddl)
    relations = list(result.mcd.relations.values())

    assert {relation.role for relation in relations} == {"référencé", "porteur"}
    assert validate_mcd(result.mcd).is_valid


def test_imported_mld_can_be_exported_again_to_all_sql_dialects() -> None:
    mld = SQLDDLImporter().import_text(POSTGRESQL_DDL).mld

    for target in SQLTarget:
        generated = SQLGenerator().generate(mld, target, project_name="Import")
        assert generated.count("CREATE TABLE") == 3
        assert generated.count("FOREIGN KEY") == 2


def test_reverse_engineering_is_deterministic() -> None:
    importer = SQLDDLImporter()
    repository = JsonDiagramRepository()

    first = importer.import_text(POSTGRESQL_DDL)
    second = importer.import_text(POSTGRESQL_DDL)

    assert first.mld == second.mld
    assert repository.to_dict(first.mcd) == repository.to_dict(second.mcd)


@pytest.mark.parametrize(
    ("ddl", "message"),
    [
        ("SELECT 1;", "Aucune instruction CREATE TABLE"),
        ("CREATE TABLE sans_pk (nom TEXT);", "PK absente"),
        ("CREATE TABLE x (id UUID PRIMARY KEY);", "Type SQL non pris en charge"),
    ],
)
def test_invalid_or_unsupported_ddl_is_rejected(ddl: str, message: str) -> None:
    with pytest.raises(DDLImportError, match=message):
        SQLDDLImporter().import_text(ddl)
