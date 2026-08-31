import copy
from typing import cast

import pytest

from merisor.application.ai_normalization_service import AiNormalizationService
from merisor.application.openrouter_client import OpenRouterClient
from merisor.domain import (
    DiagramError,
    DiagramModel,
    FunctionalDependency,
    FunctionalDependencyOrigin,
    NormalFormStatus,
    Position,
    analyze_normalization,
    apply_normalization_proposal,
    attribute_closure,
    candidate_keys,
)
from merisor.persistence import JsonDiagramRepository


def _student_model() -> tuple[DiagramModel, str, dict[str, str]]:
    model = DiagramModel()
    entity = model.create_entity("INSCRIPTION", Position(10, 20))
    attributes = {
        name: model.create_attribute(
            entity.id,
            name,
            identifier=name in {"id_etudiant", "id_cours"},
        ).id
        for name in ("id_etudiant", "id_cours", "nom_etudiant", "note")
    }
    return model, entity.id, attributes


def test_functional_dependency_defaults_and_integrity() -> None:
    model, owner_id, attributes = _student_model()
    dependency = model.create_functional_dependency(
        owner_id,
        (attributes["id_etudiant"],),
        (attributes["nom_etudiant"],),
    )

    assert dependency.origin is FunctionalDependencyOrigin.USER
    assert model.functional_dependencies_for(owner_id) == [dependency]
    with pytest.raises(DiagramError, match="attribut inconnu"):
        model.create_functional_dependency(
            owner_id, ("missing",), (attributes["note"],)
        )


def test_functional_dependency_json_round_trip_and_legacy_default() -> None:
    model, owner_id, attributes = _student_model()
    dependency = model.create_functional_dependency(
        owner_id,
        (attributes["id_etudiant"],),
        (attributes["nom_etudiant"],),
        FunctionalDependencyOrigin.AI,
    )
    repository = JsonDiagramRepository()

    payload = repository.to_dict(model)
    loaded = repository.from_dict(payload)
    legacy_payload = copy.deepcopy(payload)
    del legacy_payload["functional_dependencies"]
    legacy = repository.from_dict(legacy_payload)

    assert loaded.functional_dependencies[dependency.id] == dependency
    assert legacy.functional_dependencies == {}


def test_attribute_closure_and_candidate_keys() -> None:
    dependencies = (
        FunctionalDependency("owner", ("a",), ("b",)),
        FunctionalDependency("owner", ("b",), ("c",)),
    )

    assert attribute_closure(("a",), dependencies) == {"a", "b", "c"}
    assert candidate_keys(("a", "b", "c"), dependencies) == (("a",),)


def test_formal_2nf_detects_partial_dependency() -> None:
    model, owner_id, attributes = _student_model()
    model.create_functional_dependency(
        owner_id,
        (attributes["id_etudiant"],),
        (attributes["nom_etudiant"],),
    )

    report = analyze_normalization(model).owners[0]

    assert report.second_normal_form.status is NormalFormStatus.VIOLATION
    assert report.second_normal_form.violations[0].code == "PARTIAL_DEPENDENCY"
    assert report.proposals[0].can_apply is False


def test_formal_3nf_detects_transitive_dependency_and_builds_preview() -> None:
    model = DiagramModel()
    owner = model.create_entity("EMPLOYE", Position())
    employee_id = model.create_attribute(owner.id, "id_employe", True)
    department_code = model.create_attribute(owner.id, "code_service")
    department_name = model.create_attribute(owner.id, "nom_service")
    model.create_functional_dependency(
        owner.id,
        (department_code.id,),
        (department_name.id,),
    )

    owner_report = analyze_normalization(model).owners[0]
    proposal = owner_report.proposals[0]
    transformed = apply_normalization_proposal(model, proposal)

    assert owner_report.third_normal_form.status is NormalFormStatus.VIOLATION
    assert proposal.can_apply is True
    assert set(model.entities) == {owner.id}
    assert {entity.name for entity in transformed.entities.values()} == {
        "EMPLOYE",
        "SERVICE",
    }
    transformed_owner = transformed.entities[owner.id]
    assert [attribute.name for attribute in transformed_owner.attributes] == [
        employee_id.name
    ]
    service = next(
        entity for entity in transformed.entities.values() if entity.name == "SERVICE"
    )
    assert [(item.name, item.identifier) for item in service.attributes] == [
        ("code_service", True),
        ("nom_service", False),
    ]
    assert len(transformed.associations) == 1
    assert len(transformed.relations) == 2


def test_1nf_repeating_group_is_explicitly_heuristic() -> None:
    model = DiagramModel()
    owner = model.create_entity("CLIENT", Position())
    model.create_attribute(owner.id, "id_client", True)
    model.create_attribute(owner.id, "telephone_1")
    model.create_attribute(owner.id, "telephone_2")

    assessment = analyze_normalization(model).owners[0].first_normal_form

    assert assessment.status is NormalFormStatus.VIOLATION
    assert any(item.code == "REPEATING_GROUP" for item in assessment.violations)
    assert "heuristiques" in assessment.explanation


def test_removing_attribute_cascades_functional_dependency() -> None:
    model, owner_id, attributes = _student_model()
    model.create_functional_dependency(
        owner_id,
        (attributes["id_etudiant"],),
        (attributes["nom_etudiant"],),
    )

    model.remove_attribute(owner_id, attributes["nom_etudiant"])

    assert model.functional_dependencies == {}


def test_ai_dependency_service_accepts_only_known_attribute_names() -> None:
    model, owner_id, attributes = _student_model()
    owner = model.entities[owner_id]

    class FakeClient:
        @staticmethod
        def complete(_model_id: str, _system: str, _user: str) -> str:
            return """```json
            {"dependencies":[{
              "determinants":["id_etudiant"],
              "dependents":["nom_etudiant"],
              "explanation":"Un étudiant possède un nom."
            }]}
            ```"""

    suggestions = AiNormalizationService().suggest(
        cast(OpenRouterClient, FakeClient()), "free/model:free", owner
    )

    assert suggestions[0].determinant_attribute_ids == (attributes["id_etudiant"],)
    assert suggestions[0].dependent_attribute_ids == (attributes["nom_etudiant"],)
