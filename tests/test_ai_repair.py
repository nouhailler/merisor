from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from merisor.application import AiRepairError, AiRepairService
from merisor.domain import Attribute, Entity, MCDModel, MLDDataType, MLDDataTypeName
from merisor.persistence import JsonDiagramRepository


def _model() -> MCDModel:
    model = MCDModel()
    model.add_entity(
        Entity(
            "CLIENT",
            attributes=[
                Attribute(
                    "id_client",
                    True,
                    data_type=MLDDataType(MLDDataTypeName.INTEGER),
                ),
                Attribute("email", data_type=MLDDataType.varchar(100)),
            ],
        )
    )
    model.add_entity(
        Entity(
            "PRODUIT",
            attributes=[
                Attribute(
                    "id_produit",
                    True,
                    data_type=MLDDataType(MLDDataTypeName.INTEGER),
                ),
                Attribute("prix"),
            ],
        )
    )
    return model


def _empty_patch() -> dict[str, list[Any]]:
    return {
        "entities_to_add": [],
        "entities_to_update": [],
        "entity_ids_to_remove": [],
        "associations_to_add": [],
        "associations_to_update": [],
        "association_ids_to_remove": [],
        "relations_to_add": [],
        "relations_to_update": [],
        "relation_ids_to_remove": [],
        "inheritances_to_add": [],
        "inheritances_to_update": [],
        "inheritance_ids_to_remove": [],
        "functional_dependencies_to_add": [],
        "functional_dependencies_to_update": [],
        "functional_dependency_ids_to_remove": [],
    }


def _attribute_update(
    model: MCDModel, entity_name: str, attribute_name: str, **changes: object
) -> dict[str, list[Any]]:
    repository = JsonDiagramRepository()
    payload = repository.to_dict(model)
    raw_entity = next(
        item for item in payload["entities"] if item["name"] == entity_name
    )
    attributes = copy.deepcopy(raw_entity["attributes"])
    raw_attribute = next(item for item in attributes if item["name"] == attribute_name)
    raw_attribute.update(changes)
    patch = _empty_patch()
    patch["entities_to_update"] = [
        {"id": raw_entity["id"], "changes": {"attributes": attributes}}
    ]
    return patch


def _proposal(
    proposal_id: str,
    title: str,
    patch: dict[str, list[Any]],
    confidence: str = "medium",
) -> dict[str, object]:
    return {
        "id": proposal_id,
        "title": title,
        "description": title,
        "rationale": "Déduction à confirmer par l'utilisateur.",
        "confidence": confidence,
        "patch": patch,
    }


def _response(*proposals: dict[str, object]) -> str:
    return json.dumps(
        {"summary": f"{len(proposals)} amélioration(s)", "proposals": proposals},
        ensure_ascii=False,
    )


def test_ai_repair_interprets_a_valid_patch_without_mutating_source() -> None:
    model = _model()
    before = JsonDiagramRepository().to_dict(model)
    raw = _response(
        _proposal(
            "unique_email",
            "Rendre CLIENT.email unique",
            _attribute_update(model, "CLIENT", "email", unique=True),
            "high",
        )
    )

    report = AiRepairService().interpret(model, raw)

    assert len(report.proposals) == 1
    proposal = report.proposals[0]
    assert proposal.confidence.value == "high"
    client = next(
        item for item in proposal.candidate.entities.values() if item.name == "CLIENT"
    )
    email = next(item for item in client.attributes if item.name == "email")
    assert email.unique
    assert proposal.validation.is_valid
    assert JsonDiagramRepository().to_dict(model) == before


@pytest.mark.parametrize(
    ("ai_type", "expected_label"),
    (
        ("DATE", "DATE"),
        ("VARCHAR(255)", "VARCHAR(255)"),
        ("DECIMAL(10,2)", "DECIMAL(10,2)"),
    ),
)
def test_ai_repair_normalizes_safe_textual_data_types(
    ai_type: str, expected_label: str
) -> None:
    model = _model()
    report = AiRepairService().interpret(
        model,
        _response(
            _proposal(
                "fix_date_types",
                "Corriger le type",
                _attribute_update(model, "CLIENT", "email", data_type=ai_type),
            )
        ),
    )

    proposal = report.proposals[0]
    client = next(
        item for item in proposal.candidate.entities.values() if item.name == "CLIENT"
    )
    data_type = next(
        item for item in client.attributes if item.name == "email"
    ).data_type

    assert data_type is not None
    assert data_type.label == expected_label
    assert "normalisés au format MERISOR" in proposal.patch_summary


def test_ai_repair_still_rejects_an_unknown_textual_data_type() -> None:
    model = _model()
    raw = _response(
        _proposal(
            "unknown_type",
            "Type inconnu",
            _attribute_update(model, "CLIENT", "email", data_type="MONEY"),
        )
    )

    with pytest.raises(AiRepairError, match="type d'attribut doit être un objet"):
        AiRepairService().interpret(model, raw)


def test_ai_repair_removes_a_redundant_unchanged_id_from_changes() -> None:
    model = _model()
    patch = _attribute_update(model, "CLIENT", "email", unique=True)
    update = patch["entities_to_update"][0]
    update["changes"]["id"] = update["id"]

    proposal = (
        AiRepairService()
        .interpret(
            model,
            _response(_proposal("redundant_id", "Email unique", patch)),
        )
        .proposals[0]
    )

    client = next(
        item for item in proposal.candidate.entities.values() if item.name == "CLIENT"
    )
    assert next(item for item in client.attributes if item.name == "email").unique
    assert "sans modifier les identifiants" in proposal.patch_summary


def test_ai_repair_normalizes_a_flat_update_shape() -> None:
    model = _model()
    patch = _attribute_update(model, "CLIENT", "email", unique=True)
    update = patch["entities_to_update"][0]
    patch["entities_to_update"][0] = {"id": update["id"], **update["changes"]}

    proposal = (
        AiRepairService()
        .interpret(
            model,
            _response(_proposal("flat_update", "Email unique", patch)),
        )
        .proposals[0]
    )

    client = next(
        item for item in proposal.candidate.entities.values() if item.name == "CLIENT"
    )
    assert next(item for item in client.attributes if item.name == "email").unique


def test_ai_repair_rejects_a_nested_id_that_differs_from_the_target() -> None:
    model = _model()
    patch = _attribute_update(model, "CLIENT", "email", unique=True)
    patch["entities_to_update"][0]["changes"]["id"] = "entity_other"

    with pytest.raises(AiRepairError, match="sans modifier l'ID"):
        AiRepairService().interpret(
            model,
            _response(_proposal("changed_id", "Changer l'ID", patch)),
        )


def test_ai_repair_rejects_invented_targets_and_empty_changes() -> None:
    model = _model()
    invented = _empty_patch()
    invented["entities_to_update"] = [{"id": "absent", "changes": {"name": "INVENTE"}}]

    with pytest.raises(AiRepairError, match="élément absent"):
        AiRepairService().interpret(
            model, _response(_proposal("invented", "Invalide", invented))
        )

    client = next(item for item in model.entities.values() if item.name == "CLIENT")
    unchanged = _empty_patch()
    unchanged["entities_to_update"] = [{"id": client.id, "changes": {"name": "CLIENT"}}]
    with pytest.raises(AiRepairError, match="ne change rien"):
        AiRepairService().interpret(
            model, _response(_proposal("unchanged", "Sans effet", unchanged))
        )


def test_combining_independent_proposals_preserves_both_changes() -> None:
    model = _model()
    service = AiRepairService()
    report = service.interpret(
        model,
        _response(
            _proposal(
                "unique_email",
                "Email unique",
                _attribute_update(model, "CLIENT", "email", unique=True),
            ),
            _proposal(
                "price_type",
                "Type du prix",
                _attribute_update(
                    model,
                    "PRODUIT",
                    "prix",
                    data_type={"name": "DECIMAL", "precision": 10, "scale": 2},
                ),
            ),
        ),
    )

    candidate, validation, summary = service.combine(
        model, report, {"unique_email", "price_type"}
    )

    client = next(item for item in candidate.entities.values() if item.name == "CLIENT")
    product = next(
        item for item in candidate.entities.values() if item.name == "PRODUIT"
    )
    assert next(item for item in client.attributes if item.name == "email").unique
    price_type = next(
        item for item in product.attributes if item.name == "prix"
    ).data_type
    assert price_type is not None
    assert price_type.label == "DECIMAL(10,2)"
    assert validation.is_valid
    assert "Email unique" in summary and "Type du prix" in summary


def test_combining_competing_updates_is_blocked_explicitly() -> None:
    model = _model()
    service = AiRepairService()
    report = service.interpret(
        model,
        _response(
            _proposal(
                "unique_email",
                "Email unique",
                _attribute_update(model, "CLIENT", "email", unique=True),
            ),
            _proposal(
                "long_email",
                "Email plus long",
                _attribute_update(
                    model,
                    "CLIENT",
                    "email",
                    data_type={"name": "VARCHAR", "length": 255},
                ),
            ),
        ),
    )

    with pytest.raises(AiRepairError, match="Appliquez-les séparément"):
        service.combine(model, report, {"unique_email", "long_email"})


def test_ai_repair_response_schema_is_strict() -> None:
    with pytest.raises(AiRepairError, match="summary et proposals"):
        AiRepairService().interpret(_model(), '{"proposals":[],"extra":true}')


def test_user_prompt_contains_model_and_local_signals_without_writing_files(
    tmp_path: Path,
) -> None:
    service = AiRepairService()
    before = set(tmp_path.iterdir())

    prompt = service._user_prompt(_model())

    assert '"mcd"' in prompt
    assert '"local_quality_signals"' in prompt
    assert "CLIENT" in prompt
    assert set(tmp_path.iterdir()) == before
