"""Exécute réellement le SQL généré sur les trois moteurs pris en charge."""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess

import pytest

from merisor.application import McdToMldTransformer, SQLGenerator, SQLTarget
from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    Entity,
    MCDModel,
    MLDDataType,
    MLDDataTypeName,
)

pytestmark = pytest.mark.sql_runtime


def _motogp_mcd() -> MCDModel:
    model = MCDModel()
    pilot = Entity(
        "PILOTE",
        id="pilot",
        attributes=[
            Attribute(
                "id_pilote",
                identifier=True,
                id="pilot-id",
                data_type=MLDDataType(MLDDataTypeName.INTEGER),
            ),
            Attribute("nom", id="pilot-name", data_type=MLDDataType.varchar(100)),
        ],
    )
    team = Entity(
        "EQUIPE",
        id="team",
        attributes=[
            Attribute(
                "id_equipe",
                identifier=True,
                id="team-id",
                data_type=MLDDataType(MLDDataTypeName.INTEGER),
            ),
            Attribute("nom", id="team-name", data_type=MLDDataType.varchar(100)),
        ],
    )
    engage = Association(
        "ENGAGER",
        id="engage",
        attributes=[
            Attribute(
                "date_debut",
                id="start-date",
                data_type=MLDDataType(MLDDataTypeName.DATE),
            ),
            Attribute(
                "date_fin",
                id="end-date",
                data_type=MLDDataType(MLDDataTypeName.DATE),
                nullable=True,
            ),
        ],
        is_historized=True,
    )
    model.add_entity(pilot)
    model.add_entity(team)
    model.add_association(engage)
    model.create_relation(pilot.id, engage.id, Cardinality("0", "N"))
    model.create_relation(team.id, engage.id, Cardinality("1", "1"))
    return model


def _generated_sql(target: SQLTarget) -> str:
    mld = McdToMldTransformer().transform(_motogp_mcd())
    return SQLGenerator().generate(mld, target, project_name="MotoGP runtime")


def test_sqlite_executes_generated_schema_and_enforces_foreign_keys() -> None:
    connection = sqlite3.connect(":memory:")
    connection.executescript(_generated_sql(SQLTarget.SQLITE))

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
        if not str(row[0]).startswith("sqlite_")
    }
    foreign_keys = tuple(connection.execute('PRAGMA foreign_key_list("ENGAGER")'))
    primary_keys = {
        table: tuple(
            row[1]
            for row in connection.execute(f'PRAGMA table_info("{table}")')
            if row[5]
        )
        for table in tables
    }
    assert tables == {"PILOTE", "EQUIPE", "ENGAGER"}
    assert len(foreign_keys) == 2
    assert primary_keys == {
        "PILOTE": ("id_pilote",),
        "EQUIPE": ("id_equipe",),
        "ENGAGER": ("id_engager",),
    }

    connection.execute(
        'INSERT INTO "PILOTE" ("id_pilote", "nom") VALUES (1, \'Rossi\')'
    )
    connection.execute(
        'INSERT INTO "EQUIPE" ("id_equipe", "nom") VALUES (10, \'Yamaha\')'
    )
    connection.execute(
        'INSERT INTO "ENGAGER" ("id_pilote", "id_equipe", "date_debut") '
        "VALUES (1, 10, '2026-01-01')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            'INSERT INTO "ENGAGER" ("id_pilote", "id_equipe", "date_debut") '
            "VALUES (999, 10, '2026-01-02')"
        )
    connection.close()


def _external_setting(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    if os.environ.get("MERISOR_REQUIRE_EXTERNAL_SQL") == "1":
        pytest.fail(f"La variable CI obligatoire {name} est absente.")
    pytest.skip(f"{name} absent : moteur externe non demandé localement.")


def _client(name: str) -> str:
    executable = shutil.which(name)
    if executable is not None:
        return executable
    if os.environ.get("MERISOR_REQUIRE_EXTERNAL_SQL") == "1":
        pytest.fail(f"Le client SQL obligatoire {name} est introuvable.")
    pytest.skip(f"Client {name} absent : test externe ignoré localement.")


def _run(
    command: list[str],
    *,
    sql: str | None = None,
    environment: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        input=sql,
        text=True,
        capture_output=True,
        check=check,
        env=environment,
        timeout=20,
    )


def test_postgresql_executes_generated_schema_and_enforces_foreign_keys() -> None:
    dsn = _external_setting("MERISOR_POSTGRES_DSN")
    psql = _client("psql")
    base = [psql, "--no-psqlrc", "--set", "ON_ERROR_STOP=1", "--dbname", dsn]
    _run([*base, "--file", "-"], sql=_generated_sql(SQLTarget.POSTGRESQL))

    tables = _run(
        [
            *base,
            "--tuples-only",
            "--no-align",
            "--command",
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name",
        ]
    ).stdout.split()
    foreign_key_count = _run(
        [
            *base,
            "--tuples-only",
            "--no-align",
            "--command",
            "SELECT count(*) FROM information_schema.table_constraints "
            "WHERE table_schema = 'public' AND table_name = 'ENGAGER' "
            "AND constraint_type = 'FOREIGN KEY'",
        ]
    ).stdout.strip()
    primary_key_count = _run(
        [
            *base,
            "--tuples-only",
            "--no-align",
            "--command",
            "SELECT count(*) FROM information_schema.table_constraints "
            "WHERE table_schema = 'public' AND constraint_type = 'PRIMARY KEY'",
        ]
    ).stdout.strip()
    assert tables == ["ENGAGER", "EQUIPE", "PILOTE"]
    assert foreign_key_count == "2"
    assert primary_key_count == "3"

    _run(
        [*base, "--file", "-"],
        sql="""INSERT INTO "PILOTE" VALUES (1, 'Rossi');
INSERT INTO "EQUIPE" VALUES (10, 'Yamaha');
INSERT INTO "ENGAGER" ("id_pilote", "id_equipe", "date_debut")
VALUES (1, 10, '2026-01-01');""",
    )
    rejected = _run(
        [*base, "--file", "-"],
        sql="""INSERT INTO "ENGAGER" ("id_pilote", "id_equipe", "date_debut")
VALUES (999, 10, '2026-01-02');""",
        check=False,
    )
    assert rejected.returncode != 0
    assert "foreign key" in rejected.stderr.casefold()


def test_mariadb_executes_generated_schema_and_enforces_foreign_keys() -> None:
    host = _external_setting("MERISOR_MARIADB_HOST")
    password = _external_setting("MERISOR_MARIADB_PASSWORD")
    mariadb = _client("mariadb")
    environment = {**os.environ, "MYSQL_PWD": password}
    base = [
        mariadb,
        "--batch",
        "--skip-column-names",
        "--host",
        host,
        "--port",
        os.environ.get("MERISOR_MARIADB_PORT", "3306"),
        "--user",
        os.environ.get("MERISOR_MARIADB_USER", "merisor"),
        "--database",
        os.environ.get("MERISOR_MARIADB_DATABASE", "merisor"),
    ]
    _run(
        base,
        sql=_generated_sql(SQLTarget.MYSQL),
        environment=environment,
    )

    tables = _run(
        [*base, "--execute", "SHOW TABLES"], environment=environment
    ).stdout.split()
    foreign_key_count = _run(
        [
            *base,
            "--execute",
            "SELECT count(*) FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'ENGAGER' "
            "AND CONSTRAINT_TYPE = 'FOREIGN KEY'",
        ],
        environment=environment,
    ).stdout.strip()
    primary_key_count = _run(
        [
            *base,
            "--execute",
            "SELECT count(*) FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE CONSTRAINT_SCHEMA = DATABASE() "
            "AND CONSTRAINT_TYPE = 'PRIMARY KEY'",
        ],
        environment=environment,
    ).stdout.strip()
    assert set(tables) == {"ENGAGER", "EQUIPE", "PILOTE"}
    assert foreign_key_count == "2"
    assert primary_key_count == "3"

    _run(
        base,
        sql="""INSERT INTO `PILOTE` VALUES (1, 'Rossi');
INSERT INTO `EQUIPE` VALUES (10, 'Yamaha');
INSERT INTO `ENGAGER` (`id_pilote`, `id_equipe`, `date_debut`)
VALUES (1, 10, '2026-01-01');""",
        environment=environment,
    )
    rejected = _run(
        base,
        sql="""INSERT INTO `ENGAGER` (`id_pilote`, `id_equipe`, `date_debut`)
VALUES (999, 10, '2026-01-02');""",
        environment=environment,
        check=False,
    )
    assert rejected.returncode != 0
    assert "foreign key" in rejected.stderr.casefold()
