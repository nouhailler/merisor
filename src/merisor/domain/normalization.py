"""Analyse formelle et pédagogique de la normalisation d'un MCD.

Les vérifications 2NF/3NF reposent exclusivement sur les dépendances
fonctionnelles déclarées. La 1NF reste une heuristique : l'atomicité dépend de
la signification métier et ne peut pas être prouvée à partir des seuls noms.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from itertools import combinations

from merisor.domain.model import (
    Association,
    Cardinality,
    Entity,
    FunctionalDependency,
    MCDModel,
    Position,
)


class NormalFormStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    VIOLATION = "VIOLATION"
    UNDETERMINED = "UNDETERMINED"


@dataclass(frozen=True, slots=True)
class NormalizationViolation:
    code: str
    normal_form: str
    owner_id: str
    determinant_attribute_ids: tuple[str, ...]
    dependent_attribute_ids: tuple[str, ...]
    message: str
    explanation: str


@dataclass(frozen=True, slots=True)
class NormalFormAssessment:
    normal_form: str
    status: NormalFormStatus
    summary: str
    explanation: str
    violations: tuple[NormalizationViolation, ...] = ()


@dataclass(frozen=True, slots=True)
class NormalizationProposal:
    owner_id: str
    title: str
    explanation: str
    determinant_attribute_ids: tuple[str, ...]
    dependent_attribute_ids: tuple[str, ...]
    suggested_entity_name: str
    can_apply: bool
    limitation: str = ""


@dataclass(frozen=True, slots=True)
class OwnerNormalizationReport:
    owner_id: str
    owner_name: str
    candidate_keys: tuple[tuple[str, ...], ...]
    first_normal_form: NormalFormAssessment
    second_normal_form: NormalFormAssessment
    third_normal_form: NormalFormAssessment
    proposals: tuple[NormalizationProposal, ...]


@dataclass(frozen=True, slots=True)
class NormalizationReport:
    owners: tuple[OwnerNormalizationReport, ...]

    @property
    def violation_count(self) -> int:
        return sum(
            len(assessment.violations)
            for owner in self.owners
            for assessment in (
                owner.first_normal_form,
                owner.second_normal_form,
                owner.third_normal_form,
            )
        )


def attribute_closure(
    seed: Iterable[str], dependencies: Iterable[FunctionalDependency]
) -> frozenset[str]:
    """Calcule X+ par application répétée des axiomes d'Armstrong."""

    closure = set(seed)
    changed = True
    dependency_list = tuple(dependencies)
    while changed:
        changed = False
        for dependency in dependency_list:
            if set(dependency.determinant_attribute_ids) <= closure:
                before = len(closure)
                closure.update(dependency.dependent_attribute_ids)
                changed = changed or len(closure) != before
    return frozenset(closure)


def candidate_keys(
    attribute_ids: Iterable[str],
    dependencies: Iterable[FunctionalDependency],
    declared_identifier: Iterable[str] = (),
) -> tuple[tuple[str, ...], ...]:
    """Retourne toutes les clés minimales déductibles, dans un ordre stable."""

    universe = tuple(dict.fromkeys(attribute_ids))
    universe_set = set(universe)
    if not universe:
        return ()
    dependency_list = tuple(dependencies)
    results: list[tuple[str, ...]] = []

    declared = tuple(item for item in declared_identifier if item in universe_set)
    if declared:
        results.append(tuple(sorted(declared)))

    rhs = {
        attribute_id
        for dependency in dependency_list
        for attribute_id in dependency.dependent_attribute_ids
    }
    mandatory = tuple(sorted(universe_set - rhs))
    optional = tuple(sorted(universe_set - set(mandatory)))
    for optional_count in range(len(optional) + 1):
        for supplement in combinations(optional, optional_count):
            candidate = tuple(sorted((*mandatory, *supplement)))
            candidate_set = set(candidate)
            if any(set(existing) <= candidate_set for existing in results):
                continue
            if attribute_closure(candidate, dependency_list) >= universe_set:
                results.append(candidate)

    return tuple(sorted(set(results), key=lambda key: (len(key), key)))


_REPEATING_SUFFIX = re.compile(r"(?:_|\b)(?:1|2|3|01|02|03)$", re.IGNORECASE)
_REPEATING_WORDS = re.compile(
    r"(?:liste|list|csv|json|tableau|array|emails?|telephones?|tags?)",
    re.IGNORECASE,
)
_COMPOUND_WORDS = re.compile(
    r"(?:adresse_complete|coordonnees|nom_complet|full_name)", re.IGNORECASE
)


def analyze_normalization(model: MCDModel) -> NormalizationReport:
    owners: tuple[Entity | Association, ...] = (
        *model.entities.values(),
        *model.associations.values(),
    )
    reports = tuple(
        _analyze_owner(model, owner)
        for owner in sorted(
            owners,
            key=lambda item: (item.name.casefold(), item.id),
        )
    )
    return NormalizationReport(reports)


def _analyze_owner(
    model: MCDModel, owner: Entity | Association
) -> OwnerNormalizationReport:
    dependencies = tuple(model.functional_dependencies_for(owner.id))
    attribute_ids = tuple(attribute.id for attribute in owner.attributes)
    declared_identifier = tuple(
        attribute.id for attribute in owner.attributes if attribute.identifier
    )
    keys = candidate_keys(attribute_ids, dependencies, declared_identifier)
    first = _assess_first_normal_form(owner)
    second = _assess_second_normal_form(owner, dependencies, keys)
    third = _assess_third_normal_form(owner, dependencies, keys)
    proposals = _build_proposals(owner, (*second.violations, *third.violations))
    return OwnerNormalizationReport(
        owner.id,
        owner.name,
        keys,
        first,
        second,
        third,
        proposals,
    )


def _assess_first_normal_form(
    owner: Entity | Association,
) -> NormalFormAssessment:
    violations: list[NormalizationViolation] = []
    numbered_groups: dict[str, list[str]] = {}
    for attribute in owner.attributes:
        normalized = attribute.name.strip().casefold()
        if _REPEATING_WORDS.search(normalized):
            violations.append(
                NormalizationViolation(
                    "POSSIBLE_COLLECTION",
                    "1NF",
                    owner.id,
                    (),
                    (attribute.id,),
                    f"« {attribute.name} » semble contenir plusieurs valeurs.",
                    "La 1NF demande une valeur atomique par cellule. Vérifiez si "
                    "ces valeurs devraient devenir des occurrences séparées.",
                )
            )
        if _COMPOUND_WORDS.search(normalized):
            violations.append(
                NormalizationViolation(
                    "POSSIBLE_COMPOUND_VALUE",
                    "1NF",
                    owner.id,
                    (),
                    (attribute.id,),
                    f"« {attribute.name} » peut regrouper plusieurs informations.",
                    "Selon les usages métier, séparer les composants (par exemple "
                    "rue, code postal et ville) facilite validation et recherche.",
                )
            )
        base = _REPEATING_SUFFIX.sub("", normalized)
        if base != normalized:
            numbered_groups.setdefault(base, []).append(attribute.id)
    for base, ids in numbered_groups.items():
        if len(ids) >= 2:
            violations.append(
                NormalizationViolation(
                    "REPEATING_GROUP",
                    "1NF",
                    owner.id,
                    (),
                    tuple(ids),
                    f"Le groupe numéroté « {base}… » semble répétitif.",
                    "Des colonnes numérotées limitent le nombre d'occurrences ; "
                    "une entité reliée est généralement plus évolutive.",
                )
            )
    if violations:
        return NormalFormAssessment(
            "1NF",
            NormalFormStatus.VIOLATION,
            "Atomicité à vérifier",
            "Ces alertes sont heuristiques : confirmez-les avec la sémantique métier.",
            tuple(violations),
        )
    return NormalFormAssessment(
        "1NF",
        NormalFormStatus.UNDETERMINED,
        "Aucune anomalie évidente",
        "L'atomicité ne peut pas être prouvée par les seuls noms d'attributs.",
    )


def _assess_second_normal_form(
    owner: Entity | Association,
    dependencies: Sequence[FunctionalDependency],
    keys: Sequence[tuple[str, ...]],
) -> NormalFormAssessment:
    if not dependencies:
        return NormalFormAssessment(
            "2NF",
            NormalFormStatus.UNDETERMINED,
            "Dépendances manquantes",
            "Déclarez les dépendances fonctionnelles pour effectuer un contrôle formel.",
        )
    prime = {attribute_id for key in keys for attribute_id in key}
    violations: list[NormalizationViolation] = []
    seen: set[tuple[frozenset[str], str]] = set()
    for key in keys:
        if len(key) < 2:
            continue
        for subset_size in range(1, len(key)):
            for subset in combinations(key, subset_size):
                closure = attribute_closure(subset, dependencies)
                for dependent_id in sorted((closure - set(subset)) - prime):
                    marker = (frozenset(subset), dependent_id)
                    if marker in seen:
                        continue
                    seen.add(marker)
                    violations.append(
                        NormalizationViolation(
                            "PARTIAL_DEPENDENCY",
                            "2NF",
                            owner.id,
                            tuple(subset),
                            (dependent_id,),
                            "Un attribut non-clé dépend d'une partie seulement "
                            "d'une clé composée.",
                            "En 2NF, tout attribut non-clé doit dépendre de la clé "
                            "complète, et non d'un sous-ensemble propre.",
                        )
                    )
    if violations:
        return NormalFormAssessment(
            "2NF",
            NormalFormStatus.VIOLATION,
            "Dépendance partielle détectée",
            "Une décomposition est recommandée pour séparer les faits concernés.",
            tuple(violations),
        )
    return NormalFormAssessment(
        "2NF",
        NormalFormStatus.COMPLIANT,
        "Aucune dépendance partielle détectée",
        "Le résultat est établi à partir des dépendances actuellement déclarées.",
    )


def _assess_third_normal_form(
    owner: Entity | Association,
    dependencies: Sequence[FunctionalDependency],
    keys: Sequence[tuple[str, ...]],
) -> NormalFormAssessment:
    if not dependencies:
        return NormalFormAssessment(
            "3NF",
            NormalFormStatus.UNDETERMINED,
            "Dépendances manquantes",
            "Déclarez les dépendances fonctionnelles pour effectuer un contrôle formel.",
        )
    universe = {attribute.id for attribute in owner.attributes}
    prime = {attribute_id for key in keys for attribute_id in key}
    violations: list[NormalizationViolation] = []
    for dependency in dependencies:
        determinant = set(dependency.determinant_attribute_ids)
        is_superkey = attribute_closure(determinant, dependencies) >= universe
        for dependent_id in dependency.dependent_attribute_ids:
            if dependent_id in determinant or is_superkey or dependent_id in prime:
                continue
            violations.append(
                NormalizationViolation(
                    "TRANSITIVE_DEPENDENCY",
                    "3NF",
                    owner.id,
                    dependency.determinant_attribute_ids,
                    (dependent_id,),
                    "Une dépendance transitive vers un attribut non-clé est possible.",
                    "En 3NF, pour chaque X → A non triviale, X doit être une "
                    "superclé ou A un attribut premier.",
                )
            )
    if violations:
        return NormalFormAssessment(
            "3NF",
            NormalFormStatus.VIOLATION,
            "Dépendance transitive détectée",
            "Isolez le déterminant et ses attributs dépendants dans une entité dédiée.",
            tuple(violations),
        )
    return NormalFormAssessment(
        "3NF",
        NormalFormStatus.COMPLIANT,
        "Aucune dépendance transitive détectée",
        "Le résultat est établi à partir des dépendances actuellement déclarées.",
    )


def _build_proposals(
    owner: Entity | Association, violations: Sequence[NormalizationViolation]
) -> tuple[NormalizationProposal, ...]:
    grouped: dict[tuple[tuple[str, ...], str], list[str]] = {}
    explanations: dict[tuple[tuple[str, ...], str], str] = {}
    for violation in violations:
        key = (
            tuple(sorted(violation.determinant_attribute_ids)),
            violation.normal_form,
        )
        grouped.setdefault(key, []).extend(violation.dependent_attribute_ids)
        explanations[key] = violation.explanation
    proposals: list[NormalizationProposal] = []
    attribute_by_id = {attribute.id: attribute for attribute in owner.attributes}
    identifier_ids = {
        attribute.id for attribute in owner.attributes if attribute.identifier
    }
    for (determinants, normal_form), dependent_ids in grouped.items():
        if not determinants:
            continue
        determinant_names = [attribute_by_id[item].name for item in determinants]
        suggested_name = _suggest_entity_name(determinant_names[0])
        is_partial_identifier = set(determinants) < identifier_ids
        can_apply = isinstance(owner, Entity) and not is_partial_identifier
        limitation = ""
        if isinstance(owner, Association):
            limitation = (
                "L'application automatique sur une association serait ambiguë ; "
                "l'aperçu reste disponible."
            )
        elif is_partial_identifier:
            limitation = (
                "Cette décomposition 2NF implique une entité faible ou une "
                "identification relative ; elle doit être appliquée manuellement."
            )
        proposals.append(
            NormalizationProposal(
                owner.id,
                f"Extraire {suggested_name} ({normal_form})",
                explanations[(determinants, normal_form)],
                determinants,
                tuple(dict.fromkeys(dependent_ids)),
                suggested_name,
                can_apply,
                limitation,
            )
        )
    return tuple(proposals)


def _suggest_entity_name(attribute_name: str) -> str:
    normalized = re.sub(
        r"^(?:id|code|numero|num)_?", "", attribute_name.strip(), flags=re.IGNORECASE
    )
    normalized = re.sub(r"\W+", "_", normalized).strip("_")
    return (normalized or "REFERENCE").upper()


def apply_normalization_proposal(
    model: MCDModel, proposal: NormalizationProposal
) -> MCDModel:
    """Construit un nouveau MCD ; le modèle fourni reste strictement inchangé."""

    if not proposal.can_apply:
        raise ValueError(
            proposal.limitation or "Cette proposition n'est pas applicable."
        )
    result = copy.deepcopy(model)
    owner = result.entities.get(proposal.owner_id)
    if owner is None:
        raise ValueError("La proposition ne cible plus une entité existante.")
    moved_ids = set(proposal.determinant_attribute_ids) | set(
        proposal.dependent_attribute_ids
    )
    source_attributes = {
        attribute.id: attribute
        for attribute in owner.attributes
        if attribute.id in moved_ids
    }
    if set(proposal.determinant_attribute_ids) - set(source_attributes):
        raise ValueError(
            "Les attributs déterminants ont été modifiés depuis l'analyse."
        )

    name = proposal.suggested_entity_name
    existing_names = {entity.name.casefold() for entity in result.entities.values()}
    suffix = 2
    while name.casefold() in existing_names:
        name = f"{proposal.suggested_entity_name}_{suffix}"
        suffix += 1
    new_entity = result.create_entity(
        name, Position(owner.position.x + 360.0, owner.position.y)
    )
    for attribute_id in (
        *proposal.determinant_attribute_ids,
        *proposal.dependent_attribute_ids,
    ):
        source = source_attributes.get(attribute_id)
        if source is None:
            continue
        result.create_attribute(
            new_entity.id,
            source.name,
            identifier=attribute_id in proposal.determinant_attribute_ids,
            data_type=source.data_type,
        )
    for attribute_id in moved_ids:
        if any(attribute.id == attribute_id for attribute in owner.attributes):
            result.remove_attribute(owner.id, attribute_id)

    association = result.create_association(
        f"LIER_{owner.name}_{new_entity.name}",
        Position(owner.position.x + 180.0, owner.position.y + 80.0),
    )
    result.create_relation(owner.id, association.id, Cardinality("1", "1"))
    result.create_relation(new_entity.id, association.id, Cardinality("0", "N"))
    return result
