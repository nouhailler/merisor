import json

import pytest

from merisor.domain import (
    Cardinality,
    DiagramModel,
    Entity,
    InheritanceStrategy,
    MLDDataType,
    MLDDataTypeName,
    MaterializationStrategy,
    Position,
)
from merisor.persistence import JsonDiagramRepository, PersistenceError


def populated_model() -> tuple[DiagramModel, str, str, str]:
    model = DiagramModel()
    entity = model.create_entity("PILOTE", Position(10.25, -20.5))
    association = model.create_association("PARTICIPER", Position(300, 175))
    model.create_attribute(entity.id, "id_pilote", identifier=True)
    model.create_attribute(entity.id, "code_licence", identifier=True)
    model.create_attribute(entity.id, "nom")
    model.create_attribute(association.id, "points")
    relation = model.create_relation(
        entity.id, association.id, Cardinality("1", "N")
    )
    return model, entity.id, association.id, relation.id


def test_save_writes_versioned_json(tmp_path) -> None:
    model, entity_id, association_id, relation_id = populated_model()
    path = tmp_path / "modele.json"

    JsonDiagramRepository().save(model, path)
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["format_version"] == 2
    assert data["entities"][0]["id"] == entity_id
    assert data["entities"][0]["attributes"][0]["identifier"] is True
    assert data["associations"][0]["id"] == association_id
    assert data["associations"][0]["is_historized"] is False
    assert data["associations"][0]["materialization_strategy"] == "AUTO"
    assert data["relations"] == [
        {
            "id": relation_id,
            "entity_id": entity_id,
            "association_id": association_id,
            "cardinality": {"minimum": "1", "maximum": "N"},
            "role": "",
        }
    ]


def test_round_trip_preserves_positions_and_relations(tmp_path) -> None:
    model, entity_id, association_id, relation_id = populated_model()
    association = model.associations[association_id]
    association.is_historized = True
    association.materialization_strategy = MaterializationStrategy.FORCE_TABLE
    model.relations[relation_id].role = "participant"
    path = tmp_path / "modele.json"
    repository = JsonDiagramRepository()

    repository.save(model, path)
    loaded = repository.load(path)

    assert loaded.entities[entity_id].name == "PILOTE"
    assert loaded.entities[entity_id].position == Position(10.25, -20.5)
    assert [item.name for item in loaded.entities[entity_id].attributes] == [
        "id_pilote",
        "code_licence",
        "nom",
    ]
    assert loaded.entities[entity_id].attributes[0].identifier
    assert loaded.entities[entity_id].attributes[1].identifier
    assert loaded.associations[association_id].position == Position(300, 175)
    assert loaded.associations[association_id].attributes[0].name == "points"
    assert loaded.associations[association_id].is_historized is True
    assert (
        loaded.associations[association_id].materialization_strategy
        is MaterializationStrategy.FORCE_TABLE
    )
    assert loaded.relations[relation_id].entity_id == entity_id
    assert loaded.relations[relation_id].association_id == association_id
    assert loaded.relations[relation_id].cardinality == Cardinality("1", "N")
    assert loaded.relations[relation_id].role == "participant"


def test_round_trip_preserves_explicit_attribute_types(tmp_path) -> None:
    model = DiagramModel()
    entity = model.create_entity("FACTURE", Position())
    identifier = model.create_attribute(
        entity.id,
        "id_facture",
        identifier=True,
        data_type=MLDDataType(MLDDataTypeName.BIGINT),
    )
    amount = model.create_attribute(
        entity.id,
        "montant",
        data_type=MLDDataType(
            MLDDataTypeName.DECIMAL,
            precision=12,
            scale=2,
        ),
    )
    label = model.create_attribute(
        entity.id,
        "libelle",
        data_type=MLDDataType.varchar(180),
    )
    path = tmp_path / "types.json"

    repository = JsonDiagramRepository()
    repository.save(model, path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    loaded = repository.load(path)

    raw_attributes = saved["entities"][0]["attributes"]
    assert raw_attributes[0]["data_type"] == {"name": "BIGINT"}
    assert raw_attributes[1]["data_type"] == {
        "name": "DECIMAL",
        "precision": 12,
        "scale": 2,
    }
    assert raw_attributes[2]["data_type"] == {
        "name": "VARCHAR",
        "length": 180,
    }
    assert loaded.attribute(entity.id, identifier.id).data_type == MLDDataType(
        MLDDataTypeName.BIGINT
    )
    assert loaded.attribute(entity.id, amount.id).data_type == MLDDataType(
        MLDDataTypeName.DECIMAL,
        precision=12,
        scale=2,
    )
    assert loaded.attribute(entity.id, label.id).data_type == MLDDataType.varchar(
        180
    )


def test_loader_ignores_unknown_fields_for_forward_enrichment() -> None:
    model, *_ = populated_model()
    repository = JsonDiagramRepository()
    data = repository.to_dict(model)
    data["future_metadata"] = {"author": "test"}
    data["entities"][0]["future_attributes"] = []

    loaded = repository.from_dict(data)

    assert len(loaded.entities) == 1
    assert len(loaded.relations) == 1


def test_round_trip_preserves_entity_inheritance(tmp_path) -> None:
    model = DiagramModel()
    parent = model.create_entity("PERSONNE", Position())
    child = model.create_entity("CLIENT", Position(100, 200))
    inheritance = model.create_inheritance(
        parent.id,
        (child.id,),
        InheritanceStrategy.PARENT_ONLY,
    )
    path = tmp_path / "inheritance.json"

    repository = JsonDiagramRepository()
    repository.save(model, path)
    loaded = repository.load(path)

    restored = loaded.inheritances[inheritance.id]
    assert restored.parent_entity_id == parent.id
    assert restored.child_entity_ids == (child.id,)
    assert restored.strategy is InheritanceStrategy.PARENT_ONLY


def test_older_v02_without_inheritances_remains_compatible() -> None:
    data = {
        "format_version": 2,
        "entities": [],
        "associations": [],
        "relations": [],
    }

    assert JsonDiagramRepository().from_dict(data).inheritances == {}


def test_loader_rejects_orphan_relation() -> None:
    data = {
        "format_version": 1,
        "entities": [],
        "associations": [],
        "relations": [
            {"id": "r1", "entity_id": "e1", "association_id": "a1"}
        ],
    }

    with pytest.raises(PersistenceError, match="Entité inconnue"):
        JsonDiagramRepository().from_dict(data)


def test_loader_rejects_unknown_format_version() -> None:
    data = {
        "format_version": 99,
        "entities": [],
        "associations": [],
        "relations": [],
    }

    with pytest.raises(PersistenceError, match="non prise en charge"):
        JsonDiagramRepository().from_dict(data)


def test_loads_and_migrates_v01_without_losing_structure() -> None:
    legacy_data = {
        "format_version": 1,
        "entities": [
            {
                "id": "e1",
                "name": "PILOTE",
                "position": {"x": 12.5, "y": -8.0},
            }
        ],
        "associations": [
            {
                "id": "a1",
                "name": "PARTICIPER",
                "position": {"x": 200.0, "y": 100.0},
            }
        ],
        "relations": [
            {"id": "r1", "entity_id": "e1", "association_id": "a1"}
        ],
    }

    model = JsonDiagramRepository().from_dict(legacy_data)

    assert model.entities["e1"].name == "PILOTE"
    assert model.entities["e1"].position == Position(12.5, -8.0)
    assert model.entities["e1"].attributes == []
    assert model.associations["a1"].position == Position(200, 100)
    assert model.associations["a1"].is_historized is False
    assert (
        model.associations["a1"].materialization_strategy
        is MaterializationStrategy.AUTO
    )
    assert model.relations["r1"].entity_id == "e1"
    assert model.relations["r1"].cardinality is None
    assert model.relations["r1"].role == ""


def test_migrated_v01_is_saved_as_v02(tmp_path) -> None:
    legacy_data = {
        "format_version": 1,
        "entities": [
            {"id": "e1", "name": "E", "position": {"x": 1, "y": 2}}
        ],
        "associations": [
            {"id": "a1", "name": "A", "position": {"x": 3, "y": 4}}
        ],
        "relations": [
            {"id": "r1", "entity_id": "e1", "association_id": "a1"}
        ],
    }
    repository = JsonDiagramRepository()
    model = repository.from_dict(legacy_data)
    path = tmp_path / "migrated.json"

    repository.save(model, path)
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert saved["format_version"] == 2
    assert saved["entities"][0]["attributes"] == []
    assert saved["associations"][0]["is_historized"] is False
    assert saved["associations"][0]["materialization_strategy"] == "AUTO"
    assert saved["relations"][0]["cardinality"] is None
    assert saved["relations"][0]["role"] == ""


def test_loads_older_v02_association_with_transformation_defaults() -> None:
    legacy_v02 = {
        "format_version": 2,
        "entities": [],
        "associations": [
            {
                "id": "a1",
                "name": "ENGAGER",
                "position": {"x": 10, "y": 20},
                "attributes": [],
            }
        ],
        "relations": [],
    }

    association = JsonDiagramRepository().from_dict(legacy_v02).associations["a1"]

    assert association.is_historized is False
    assert association.materialization_strategy is MaterializationStrategy.AUTO


def test_loads_older_v02_attribute_in_automatic_type_mode() -> None:
    legacy_v02 = {
        "format_version": 2,
        "entities": [
            {
                "id": "e1",
                "name": "PILOTE",
                "position": {"x": 0, "y": 0},
                "attributes": [
                    {"id": "a1", "name": "id_pilote", "identifier": True}
                ],
            }
        ],
        "associations": [],
        "relations": [],
    }

    attribute = JsonDiagramRepository().from_dict(legacy_v02).attribute("e1", "a1")

    assert attribute.data_type is None


def test_loader_rejects_invalid_attribute_type() -> None:
    data = {
        "format_version": 2,
        "entities": [
            {
                "id": "e1",
                "name": "FACTURE",
                "position": {"x": 0, "y": 0},
                "attributes": [
                    {
                        "id": "a1",
                        "name": "montant",
                        "identifier": False,
                        "data_type": {
                            "name": "DECIMAL",
                            "precision": 2,
                            "scale": 3,
                        },
                    }
                ],
            }
        ],
        "associations": [],
        "relations": [],
    }

    with pytest.raises(PersistenceError, match="Type d'attribut invalide"):
        JsonDiagramRepository().from_dict(data)


def test_loader_rejects_unknown_materialization_strategy() -> None:
    data = {
        "format_version": 2,
        "entities": [],
        "associations": [
            {
                "id": "a1",
                "name": "ENGAGER",
                "position": {"x": 0, "y": 0},
                "attributes": [],
                "materialization_strategy": "SOMETIMES_TABLE",
            }
        ],
        "relations": [],
    }

    with pytest.raises(PersistenceError, match="materialization_strategy"):
        JsonDiagramRepository().from_dict(data)


def test_invalid_work_in_progress_can_be_saved_without_mutation(tmp_path) -> None:
    model = DiagramModel()
    entity = Entity("", Position(7, 9))
    model.add_entity(entity)
    path = tmp_path / "incomplet.json"
    repository = JsonDiagramRepository()

    repository.save(model, path)
    loaded = repository.load(path)

    assert loaded.entities[entity.id].name == ""
    assert loaded.entities[entity.id].attributes == []
    assert loaded.entities[entity.id].position == Position(7, 9)
