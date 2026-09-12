"""Exercices MERISE déterministes et évaluations pédagogiques explicables."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

from merisor.domain import Association, Cardinality, Entity, MCDModel


class StudentCriterionStatus(str, Enum):
    PASSED = "passed"
    NEEDS_WORK = "needs_work"

    @property
    def label(self) -> str:
        return {
            StudentCriterionStatus.PASSED: "Acquis",
            StudentCriterionStatus.NEEDS_WORK: "À revoir",
        }[self]


@dataclass(frozen=True, slots=True)
class CardinalityExpectation:
    entity_name: str
    cardinality: Cardinality
    why: str


@dataclass(frozen=True, slots=True)
class AssociationExpectation:
    label: str
    first_entity: str
    second_entity: str
    cardinalities: tuple[CardinalityExpectation, ...] = ()


@dataclass(frozen=True, slots=True)
class StudentExercise:
    id: str
    title: str
    statement: str
    entity_names: tuple[str, ...]
    associations: tuple[AssociationExpectation, ...]
    assumptions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StudentCriterion:
    code: str
    label: str
    status: StudentCriterionStatus
    explanation: str
    why: str
    element_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StudentExerciseReport:
    exercise: StudentExercise
    criteria: tuple[StudentCriterion, ...]

    @property
    def passed_count(self) -> int:
        return sum(
            criterion.status is StudentCriterionStatus.PASSED
            for criterion in self.criteria
        )

    @property
    def score(self) -> int:
        if not self.criteria:
            return 0
        return round(100 * self.passed_count / len(self.criteria))

    def render(self) -> str:
        lines = [
            f"MODE ÉTUDIANT — {self.exercise.title}",
            "=" * 60,
            self.exercise.statement,
            "",
            f"Résultat : {self.passed_count}/{len(self.criteria)} "
            f"critères acquis ({self.score} %)",
            "",
        ]
        for criterion in self.criteria:
            icon = "✓" if criterion.status is StudentCriterionStatus.PASSED else "⚠"
            lines.extend(
                (
                    f"{icon} {criterion.label}",
                    f"  {criterion.explanation}",
                    f"  Pourquoi ? {criterion.why}",
                    "",
                )
            )
        lines.append(
            "Ce résultat évalue le MCD selon le barème affiché ; il ne constitue "
            "pas une vérité métier universelle."
        )
        return "\n".join(lines)


COMMAND_ORDER_EXERCISE = StudentExercise(
    id="client-orders",
    title="Clients, commandes et produits",
    statement=(
        "Un client peut passer plusieurs commandes. Une commande appartient à "
        "un seul client. Une commande contient plusieurs produits."
    ),
    entity_names=("CLIENT", "COMMANDE", "PRODUIT"),
    associations=(
        AssociationExpectation(
            "Association CLIENT-COMMANDE",
            "CLIENT",
            "COMMANDE",
            (
                CardinalityExpectation(
                    "CLIENT",
                    Cardinality("0", "N"),
                    "Un client peut n'avoir encore passé aucune commande, puis en "
                    "passer plusieurs.",
                ),
                CardinalityExpectation(
                    "COMMANDE",
                    Cardinality("1", "1"),
                    "Chaque commande appartient obligatoirement à un seul client.",
                ),
            ),
        ),
        AssociationExpectation(
            "Association COMMANDE-PRODUIT",
            "COMMANDE",
            "PRODUIT",
            (
                CardinalityExpectation(
                    "COMMANDE",
                    Cardinality("1", "N"),
                    "Une commande contient au moins un produit et peut en contenir "
                    "plusieurs.",
                ),
                CardinalityExpectation(
                    "PRODUIT",
                    Cardinality("0", "N"),
                    "Dans le barème, un produit peut exister avant toute commande et "
                    "figurer dans plusieurs commandes.",
                ),
            ),
        ),
    ),
    assumptions=(
        "Un client peut exister sans commande.",
        "Une commande contient au moins un produit.",
        "Un produit peut exister sans commande et être commandé plusieurs fois.",
    ),
)

STUDENT_EXERCISES = (COMMAND_ORDER_EXERCISE,)


class StudentExerciseEvaluator:
    """Compare un MCD à un barème déclaré sans déductions opaques ni IA."""

    def evaluate(
        self, model: MCDModel, exercise: StudentExercise
    ) -> StudentExerciseReport:
        entities = {
            _normalized(entity.name): entity for entity in model.entities.values()
        }
        criteria: list[StudentCriterion] = []
        for expected_name in exercise.entity_names:
            entity = entities.get(_normalized(expected_name))
            criteria.append(self._entity_criterion(expected_name, entity))
            criteria.append(self._identifier_criterion(expected_name, entity))
        for expected in exercise.associations:
            first = entities.get(_normalized(expected.first_entity))
            second = entities.get(_normalized(expected.second_entity))
            association = self._association_between(model, first, second)
            criteria.append(self._association_criterion(expected, association))
            for cardinality in expected.cardinalities:
                entity = entities.get(_normalized(cardinality.entity_name))
                criteria.append(
                    self._cardinality_criterion(
                        model, expected, association, entity, cardinality
                    )
                )
        return StudentExerciseReport(exercise, tuple(criteria))

    @staticmethod
    def _entity_criterion(
        expected_name: str, entity: Entity | None
    ) -> StudentCriterion:
        if entity is not None:
            return StudentCriterion(
                f"entity:{expected_name}",
                f"Entité {expected_name}",
                StudentCriterionStatus.PASSED,
                f"L'entité {entity.name} est présente.",
                "Un concept possédant une identité et des propriétés propres est "
                "représenté par une entité.",
                (entity.id,),
            )
        return StudentCriterion(
            f"entity:{expected_name}",
            f"Entité {expected_name}",
            StudentCriterionStatus.NEEDS_WORK,
            f"Aucune entité nommée {expected_name} n'a été trouvée.",
            "Ce concept métier doit pouvoir être identifié indépendamment.",
        )

    @staticmethod
    def _identifier_criterion(
        expected_name: str, entity: Entity | None
    ) -> StudentCriterion:
        identifiers = (
            tuple(attribute for attribute in entity.attributes if attribute.identifier)
            if entity is not None
            else ()
        )
        if identifiers:
            assert entity is not None
            names = ", ".join(attribute.name for attribute in identifiers)
            return StudentCriterion(
                f"identifier:{expected_name}",
                f"Identifiant de {expected_name}",
                StudentCriterionStatus.PASSED,
                f"Identifiant trouvé : {names}.",
                "Une occurrence d'entité doit être distinguable de toutes les autres.",
                (entity.id, *(attribute.id for attribute in identifiers)),
            )
        return StudentCriterion(
            f"identifier:{expected_name}",
            f"Identifiant de {expected_name}",
            StudentCriterionStatus.NEEDS_WORK,
            "Aucun attribut identifiant n'est défini."
            if entity is not None
            else "L'entité doit d'abord être créée.",
            "Sans identifiant, les occurrences ne peuvent pas être référencées de "
            "façon fiable.",
            (entity.id,) if entity is not None else (),
        )

    @staticmethod
    def _association_between(
        model: MCDModel, first: Entity | None, second: Entity | None
    ) -> Association | None:
        if first is None or second is None:
            return None
        for association in model.associations.values():
            entity_ids = {
                relation.entity_id
                for relation in model.relations.values()
                if relation.association_id == association.id
            }
            if {first.id, second.id}.issubset(entity_ids):
                return association
        return None

    @staticmethod
    def _association_criterion(
        expected: AssociationExpectation, association: Association | None
    ) -> StudentCriterion:
        if association is not None:
            return StudentCriterion(
                f"association:{expected.first_entity}:{expected.second_entity}",
                expected.label,
                StudentCriterionStatus.PASSED,
                f"L'association {association.name} relie les deux entités.",
                "Une association représente le fait métier qui relie des occurrences "
                "d'entités.",
                (association.id,),
            )
        return StudentCriterion(
            f"association:{expected.first_entity}:{expected.second_entity}",
            expected.label,
            StudentCriterionStatus.NEEDS_WORK,
            "Aucune association commune ne relie les deux entités.",
            "Le lien métier doit être explicite dans le MCD, et pas seulement suggéré "
            "par le nom d'un attribut.",
        )

    @staticmethod
    def _cardinality_criterion(
        model: MCDModel,
        expected_association: AssociationExpectation,
        association: Association | None,
        entity: Entity | None,
        expectation: CardinalityExpectation,
    ) -> StudentCriterion:
        relation = next(
            (
                relation
                for relation in model.relations.values()
                if association is not None
                and entity is not None
                and relation.association_id == association.id
                and relation.entity_id == entity.id
            ),
            None,
        )
        expected = expectation.cardinality
        if relation is not None and relation.cardinality == expected:
            return StudentCriterion(
                f"cardinality:{expected_association.label}:{expectation.entity_name}",
                f"Cardinalité {expectation.entity_name} {expected}",
                StudentCriterionStatus.PASSED,
                f"La branche porte bien {expected}.",
                expectation.why,
                (relation.id,),
            )
        actual = (
            str(relation.cardinality)
            if relation is not None and relation.cardinality is not None
            else "absente"
        )
        return StudentCriterion(
            f"cardinality:{expected_association.label}:{expectation.entity_name}",
            f"Cardinalité {expectation.entity_name} {expected}",
            StudentCriterionStatus.NEEDS_WORK,
            f"Cardinalité attendue : {expected} ; cardinalité trouvée : {actual}.",
            expectation.why,
            (relation.id,) if relation is not None else (),
        )


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]", "", ascii_value.casefold())
