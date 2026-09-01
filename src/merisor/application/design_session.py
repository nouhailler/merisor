"""État local et versionné d'une conception MERISE conversationnelle."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from merisor.domain import MCDModel, ValidationReport, validate_mcd
from merisor.persistence import JsonDiagramRepository, PersistenceError


class DesignSessionError(ValueError):
    """Réponse ou patch incompatible avec une session de conception."""


class ConceptKind(str, Enum):
    ENTITY = "entity"
    ASSOCIATION = "association"
    ATTRIBUTE = "attribute"


@dataclass(frozen=True, slots=True)
class DetectedConcept:
    name: str
    kind: ConceptKind
    confidence: float


@dataclass(frozen=True, slots=True)
class DesignQuestion:
    id: str
    text: str
    choices: tuple[str, ...] = ()
    impact: str = ""


@dataclass(frozen=True, slots=True)
class DesignTurn:
    user_message: str
    assistant_message: str


@dataclass(frozen=True, slots=True)
class DraftRevision:
    number: int
    json_text: str
    report: ValidationReport
    summary: str


@dataclass(frozen=True, slots=True)
class DraftPatch:
    additions: dict[str, tuple[dict[str, Any], ...]]
    updates: dict[str, tuple[dict[str, Any], ...]]
    removals: dict[str, tuple[str, ...]]

    @property
    def empty(self) -> bool:
        return not any(
            (*self.additions.values(), *self.updates.values(), *self.removals.values())
        )


@dataclass(frozen=True, slots=True)
class DesignAssistantResponse:
    assistant_message: str
    detected_concepts: tuple[DetectedConcept, ...]
    questions: tuple[DesignQuestion, ...]
    assumptions: tuple[str, ...]
    draft_patch: DraftPatch
    ready_for_preview: bool


@dataclass(frozen=True, slots=True)
class DesignStep:
    response: DesignAssistantResponse
    draft_model: MCDModel
    draft_json: str
    report: ValidationReport
    patch_summary: str


@dataclass(frozen=True, slots=True)
class ModelDifference:
    added_entities: tuple[str, ...] = ()
    removed_entities: tuple[str, ...] = ()
    changed_entities: tuple[str, ...] = ()
    added_associations: tuple[str, ...] = ()
    removed_associations: tuple[str, ...] = ()
    changed_associations: tuple[str, ...] = ()
    added_relations: int = 0
    removed_relations: int = 0

    def render(self) -> str:
        lines = ["DIFFÉRENCES AVEC LE MCD COURANT", "=" * 38]
        groups = (
            ("Entités ajoutées", self.added_entities),
            ("Entités supprimées", self.removed_entities),
            ("Entités modifiées", self.changed_entities),
            ("Associations ajoutées", self.added_associations),
            ("Associations supprimées", self.removed_associations),
            ("Associations modifiées", self.changed_associations),
        )
        for label, values in groups:
            if values:
                lines.append(f"\n{label} :")
                lines.extend(f"  • {value}" for value in values)
        if self.added_relations or self.removed_relations:
            lines.append(
                f"\nRelations : +{self.added_relations} / -{self.removed_relations}"
            )
        if len(lines) == 2:
            lines.append("\nAucune différence logique détectée.")
        return "\n".join(lines)


_COLLECTIONS = (
    "entities",
    "associations",
    "relations",
    "inheritances",
    "functional_dependencies",
)


@dataclass(slots=True)
class DesignSession:
    """Brouillon isolé ; aucune méthode ne modifie le document de l'éditeur."""

    repository: JsonDiagramRepository = field(default_factory=JsonDiagramRepository)
    current_draft: MCDModel = field(default_factory=MCDModel)
    turns: list[DesignTurn] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    pending_questions: list[DesignQuestion] = field(default_factory=list)
    answered_questions: dict[str, str] = field(default_factory=dict)
    detected_concepts: list[DetectedConcept] = field(default_factory=list)
    revisions: list[DraftRevision] = field(default_factory=list)
    ready_for_preview: bool = False

    def __post_init__(self) -> None:
        self.current_draft = copy.deepcopy(self.current_draft)
        if not self.revisions:
            self._append_revision("Brouillon initial")

    def accept_step(self, user_message: str, step: DesignStep) -> None:
        self.current_draft = copy.deepcopy(step.draft_model)
        self.turns.append(
            DesignTurn(user_message.strip(), step.response.assistant_message)
        )
        for assumption in step.response.assumptions:
            if assumption not in self.assumptions:
                self.assumptions.append(assumption)
        self.pending_questions = list(step.response.questions)
        self.detected_concepts = list(step.response.detected_concepts)
        self.ready_for_preview = step.response.ready_for_preview
        self._append_revision(step.patch_summary, step.report, step.draft_json)

    def record_answer(self, question_id: str, answer: str) -> None:
        if question_id not in {question.id for question in self.pending_questions}:
            raise DesignSessionError(f"Question inconnue : {question_id}")
        clean_answer = answer.strip()
        if not clean_answer:
            raise DesignSessionError("Une réponse ne peut pas être vide.")
        self.answered_questions[question_id] = clean_answer

    def formatted_answers(self) -> str:
        lines = []
        for question in self.pending_questions:
            answer = self.answered_questions.get(question.id)
            if answer:
                lines.append(f"- {question.text}\n  Réponse : {answer}")
        return "Réponses aux questions :\n" + "\n".join(lines)

    @property
    def all_pending_questions_answered(self) -> bool:
        return bool(self.pending_questions) and all(
            question.id in self.answered_questions
            for question in self.pending_questions
        )

    def rewind(self) -> bool:
        if len(self.revisions) <= 1:
            return False
        self.revisions.pop()
        previous = self.revisions[-1]
        try:
            self.current_draft = self.repository.from_dict(
                json.loads(previous.json_text)
            )
        except (json.JSONDecodeError, PersistenceError) as error:
            raise DesignSessionError(
                "Impossible de restaurer la révision précédente."
            ) from error
        if self.turns:
            self.turns.pop()
        self.pending_questions.clear()
        self.ready_for_preview = False
        return True

    def current_json(self) -> str:
        return (
            json.dumps(
                self.repository.to_dict(self.current_draft),
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )

    def _append_revision(
        self,
        summary: str,
        report: ValidationReport | None = None,
        json_text: str | None = None,
    ) -> None:
        self.revisions.append(
            DraftRevision(
                len(self.revisions),
                json_text or self.current_json(),
                report or validate_mcd(self.current_draft),
                summary,
            )
        )


class DraftPatchApplier:
    """Applique un patch sur un dictionnaire JSON isolé, puis recharge le domaine."""

    def __init__(self, repository: JsonDiagramRepository | None = None) -> None:
        self.repository = repository or JsonDiagramRepository()

    def apply(self, model: MCDModel, patch: DraftPatch) -> tuple[MCDModel, str]:
        payload = copy.deepcopy(self.repository.to_dict(model))
        summaries: list[str] = []
        for collection in _COLLECTIONS:
            raw_items = payload.get(collection, [])
            if not isinstance(raw_items, list):
                raise DesignSessionError(f"Collection interne invalide : {collection}")
            by_id = {
                item["id"]: item
                for item in raw_items
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            }
            for item_id in patch.removals.get(collection, ()):
                if item_id not in by_id:
                    raise DesignSessionError(
                        f"Le patch tente de supprimer un élément absent : {item_id}."
                    )
                del by_id[item_id]
                summaries.append(f"- {collection}:{item_id}")
            for update in patch.updates.get(collection, ()):
                update_id = update.get("id")
                changes = update.get("changes")
                if not isinstance(update_id, str) or update_id not in by_id:
                    raise DesignSessionError(
                        f"Le patch tente de modifier un élément absent dans {collection}."
                    )
                if not isinstance(changes, dict) or "id" in changes:
                    raise DesignSessionError(
                        "Une mise à jour doit contenir 'changes' sans modifier l'ID."
                    )
                by_id[update_id].update(copy.deepcopy(changes))
                summaries.append(f"~ {collection}:{update_id}")
            for addition in patch.additions.get(collection, ()):
                addition_id = addition.get("id")
                if not isinstance(addition_id, str) or not addition_id.strip():
                    raise DesignSessionError(
                        f"Un ajout dans {collection} ne possède pas d'ID valide."
                    )
                if addition_id in by_id:
                    raise DesignSessionError(
                        f"Identifiant déjà présent : {addition_id}"
                    )
                by_id[addition_id] = copy.deepcopy(addition)
                summaries.append(f"+ {collection}:{addition_id}")
            payload[collection] = list(by_id.values())
        try:
            draft = self.repository.from_dict(payload)
        except PersistenceError as error:
            raise DesignSessionError(f"Patch MCD invalide : {error}") from error
        return draft, "\n".join(summaries) or "Aucun changement structurel"


def compare_models(current: MCDModel, draft: MCDModel) -> ModelDifference:
    def node_changes(
        current_items: dict[str, Any], draft_items: dict[str, Any]
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        added = tuple(
            draft_items[item_id].name
            for item_id in sorted(draft_items.keys() - current_items.keys())
        )
        removed = tuple(
            current_items[item_id].name
            for item_id in sorted(current_items.keys() - draft_items.keys())
        )
        changed = tuple(
            draft_items[item_id].name
            for item_id in sorted(current_items.keys() & draft_items.keys())
            if current_items[item_id] != draft_items[item_id]
        )
        return added, removed, changed

    entity_diff = node_changes(current.entities, draft.entities)
    association_diff = node_changes(current.associations, draft.associations)
    return ModelDifference(
        *entity_diff,
        *association_diff,
        added_relations=len(draft.relations.keys() - current.relations.keys()),
        removed_relations=len(current.relations.keys() - draft.relations.keys()),
    )
