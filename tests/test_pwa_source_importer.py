from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from merisor.application import (
    InferenceConfidence,
    PwaImportError,
    PwaImportResult,
    PwaSourceImporter,
)
from merisor.domain import Attribute, Entity, MLDDataTypeName
from merisor.persistence import JsonDiagramRepository

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEXIE_SOURCE = """
import Dexie from "dexie";

const database = new Dexie("CommercePWA");
database.version(1).stores({
  clients: "++id, &email, nom",
  commandes: "++id, clientId, dateCommande"
});

interface Client {
  id: number;
  email: string;
  nom: string;
}

interface Commande {
  id: number;
  clientId: number;
  dateCommande: Date;
  commentaire?: string;
}
"""


def _entity(result: PwaImportResult, name: str) -> Entity:
    return next(item for item in result.mcd.entities.values() if item.name == name)


def _attribute(entity: Entity, name: str) -> Attribute:
    return next(item for item in entity.attributes if item.name == name)


def test_dexie_and_typescript_sources_build_a_typed_valid_mcd(
    tmp_path: Path,
) -> None:
    (tmp_path / "database.ts").write_text(DEXIE_SOURCE, encoding="utf-8")

    result = PwaSourceImporter().import_path(tmp_path)

    assert result.database_names == ("CommercePWA",)
    assert result.validation.is_valid
    assert {item.name for item in result.mcd.entities.values()} == {
        "CLIENT",
        "COMMANDE",
    }
    client = _entity(result, "CLIENT")
    command = _entity(result, "COMMANDE")
    assert client.identifier_attributes[0].name == "id"
    assert client.identifier_attributes[0].auto_increment
    assert _attribute(client, "email").unique
    date_type = _attribute(command, "dateCommande").data_type
    assert date_type is not None
    assert date_type.name is MLDDataTypeName.DATETIME
    assert _attribute(command, "commentaire").nullable
    assert len(result.mcd.associations) == 1
    association = next(iter(result.mcd.associations.values()))
    cardinalities = {
        result.mcd.entities[relation.entity_id].name: relation.cardinality.label
        for relation in result.mcd.connected_relations(association.id)
        if relation.cardinality is not None
    }
    assert cardinalities == {"CLIENT": "0,N", "COMMANDE": "1,1"}
    assert any(
        item.confidence is InferenceConfidence.CERTAIN for item in result.evidence
    )
    assert any(item.path == "database.ts" for item in result.evidence)


def test_native_indexeddb_reflexive_index_gets_distinct_roles(
    tmp_path: Path,
) -> None:
    source = """
    const request = indexedDB.open("Personnel", 1);
    const employees = db.createObjectStore(
      "employees", { keyPath: "id", autoIncrement: true }
    );
    employees.createIndex("managerId", "managerId", { unique: false });
    interface Employee { id: number; managerId?: number; nom: string; }
    """
    (tmp_path / "storage.ts").write_text(source, encoding="utf-8")

    result = PwaSourceImporter().import_path(tmp_path)

    assert result.validation.is_valid
    assert result.database_names == ("Personnel",)
    entity = _entity(result, "EMPLOYEE")
    assert entity.identifier_attributes[0].auto_increment
    assert entity.identifier_attributes[0].data_type is not None
    assert entity.identifier_attributes[0].data_type.name is MLDDataTypeName.INTEGER
    assert len(result.mcd.associations) == 1
    association = next(iter(result.mcd.associations.values()))
    assert {
        relation.role for relation in result.mcd.connected_relations(association.id)
    } == {
        "porteur_managerId",
        "référencé_managerId",
    }


def test_missing_key_path_gets_an_explicit_technical_identifier_proposal(
    tmp_path: Path,
) -> None:
    (tmp_path / "db.js").write_text('db.createObjectStore("logs");', encoding="utf-8")

    result = PwaSourceImporter().import_path(tmp_path)

    entity = _entity(result, "LOG")
    assert entity.identifier_attributes[0].name == "id_log"
    assert entity.identifier_attributes[0].auto_increment
    assert result.warnings
    assert any(item.confidence is InferenceConfidence.LOW for item in result.evidence)


def test_zip_is_supported_and_generated_directories_are_ignored(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "project.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("pwa/src/database.ts", DEXIE_SOURCE)
        output.writestr(
            "pwa/node_modules/fake.ts",
            'new Dexie("Fake").version(1).stores({ fake: "++id" });',
        )

    result = PwaSourceImporter().import_path(archive)

    assert result.scanned_files == 1
    assert result.database_names == ("CommercePWA",)
    assert len(result.mcd.entities) == 2


@pytest.mark.parametrize(
    "source",
    (
        PROJECT_ROOT / "examples/indexeddb-demo-pwa",
        PROJECT_ROOT / "examples/indexeddb-demo-pwa.zip",
    ),
)
def test_packaged_indexeddb_demo_builds_the_expected_mcd(source: Path) -> None:
    result = PwaSourceImporter().import_path(source)

    assert result.database_names == ("MerisorIndexedDbDemo",)
    assert result.validation.is_valid
    assert {entity.name for entity in result.mcd.entities.values()} == {
        "CUSTOMER",
        "ORDER",
    }
    assert len(result.mcd.associations) == 1
    order = _entity(result, "ORDER")
    assert _attribute(order, "customerId").data_type is not None
    assert _attribute(order, "createdAt").data_type is not None


def test_import_is_deterministic(tmp_path: Path) -> None:
    (tmp_path / "database.ts").write_text(DEXIE_SOURCE, encoding="utf-8")
    importer = PwaSourceImporter()
    repository = JsonDiagramRepository()

    first = importer.import_path(tmp_path)
    second = importer.import_path(tmp_path)

    assert repository.to_dict(first.mcd) == repository.to_dict(second.mcd)
    assert first.evidence == second.evidence


def test_source_without_indexeddb_schema_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "app.ts").write_text(
        "export const applicationName = 'Demo';", encoding="utf-8"
    )

    with pytest.raises(PwaImportError, match="Aucun object store"):
        PwaSourceImporter().import_path(tmp_path)
