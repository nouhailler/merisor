"""Règles de validation sémantique d'un MCD MERISE V0.2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from merisor.domain.mld import MLDDataTypeName
from merisor.domain.model import (
    Association,
    Attribute,
    Cardinality,
    CardinalityMaximum,
    Entity,
    InheritanceStrategy,
    MaterializationStrategy,
    MCDModel,
    Relation,
)


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    severity: ValidationSeverity
    code: str
    message: str
    element_id: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(
            issue for issue in self.issues if issue.severity is ValidationSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue.severity is ValidationSeverity.WARNING
        )

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_mcd(model: MCDModel) -> ValidationReport:
    """Analyse le modèle sans jamais le modifier."""

    issues: list[ValidationIssue] = []
    for entity in model.entities.values():
        _validate_entity(entity, issues)
    for association in model.associations.values():
        _validate_association(model, association, issues)
    _validate_relations(model, issues)
    _validate_inheritances(model, issues)
    _validate_functional_dependencies(model, issues)
    _validate_duplicate_node_names(model, issues)
    return ValidationReport(tuple(issues))


def _validate_functional_dependencies(
    model: MCDModel, issues: list[ValidationIssue]
) -> None:
    for dependency in model.functional_dependencies.values():
        try:
            owner = model.node(dependency.owner_id)
        except ValueError:
            issues.append(
                ValidationIssue(
                    ValidationSeverity.ERROR,
                    "functional_dependency.owner_missing",
                    "Une dépendance fonctionnelle référence un objet absent.",
                    dependency.id,
                )
            )
            continue
        owner_attribute_ids = {attribute.id for attribute in owner.attributes}
        referenced = set(dependency.determinant_attribute_ids) | set(
            dependency.dependent_attribute_ids
        )
        if (
            not dependency.determinant_attribute_ids
            or not dependency.dependent_attribute_ids
        ):
            issues.append(
                ValidationIssue(
                    ValidationSeverity.ERROR,
                    "functional_dependency.incomplete",
                    f"{owner.name} : une dépendance fonctionnelle est incomplète.",
                    dependency.id,
                )
            )
        if referenced - owner_attribute_ids:
            issues.append(
                ValidationIssue(
                    ValidationSeverity.ERROR,
                    "functional_dependency.attribute_missing",
                    f"{owner.name} : une dépendance fonctionnelle référence un attribut absent.",
                    dependency.id,
                )
            )
        if set(dependency.determinant_attribute_ids) & set(
            dependency.dependent_attribute_ids
        ):
            issues.append(
                ValidationIssue(
                    ValidationSeverity.ERROR,
                    "functional_dependency.trivial_overlap",
                    f"{owner.name} : le déterminant et la cible doivent être disjoints.",
                    dependency.id,
                )
            )


def _validate_entity(entity: Entity, issues: list[ValidationIssue]) -> None:
    label = entity.name.strip() or "(sans nom)"
    if not entity.name.strip():
        issues.append(
            ValidationIssue(
                ValidationSeverity.ERROR,
                "entity.name_missing",
                "Entité sans nom.",
                entity.id,
            )
        )
    if not entity.identifier_attributes:
        issues.append(
            ValidationIssue(
                ValidationSeverity.ERROR,
                "entity.identifier_missing",
                f"Entité {label} : aucun identifiant défini.",
                entity.id,
            )
        )
    _validate_attributes("Entité", label, entity.id, entity.attributes, issues)


def _validate_association(
    model: MCDModel,
    association: Association,
    issues: list[ValidationIssue],
) -> None:
    label = association.name.strip() or "(sans nom)"
    if not association.name.strip():
        issues.append(
            ValidationIssue(
                ValidationSeverity.ERROR,
                "association.name_missing",
                "Association sans nom.",
                association.id,
            )
        )
    association_relations = [
        relation
        for relation in model.relations.values()
        if relation.association_id == association.id
    ]
    valid_relations = [
        relation.entity_id
        for relation in association_relations
        if relation.entity_id in model.entities
    ]
    if len(valid_relations) < 2:
        issues.append(
            ValidationIssue(
                ValidationSeverity.ERROR,
                "association.too_few_entities",
                f"Association {label} : elle doit posséder au moins deux "
                "branches vers des entités.",
                association.id,
            )
        )
    if (
        association.is_historized
        and association.materialization_strategy is MaterializationStrategy.FORCE_FK
    ):
        issues.append(
            ValidationIssue(
                ValidationSeverity.ERROR,
                "association.historized_force_fk",
                f"Association {label} : elle est déclarée historisée mais sa "
                "stratégie de matérialisation est FORCE_FK. Utilisez AUTO ou "
                "FORCE_TABLE.",
                association.id,
            )
        )
    elif (
        association.materialization_strategy is MaterializationStrategy.FORCE_FK
        and len(association_relations) >= 3
    ):
        issues.append(
            ValidationIssue(
                ValidationSeverity.ERROR,
                "association.force_fk_nary",
                f"Association {label} : la stratégie FORCE_FK est incompatible "
                "avec une association n-aire.",
                association.id,
            )
        )
    elif (
        association.materialization_strategy is MaterializationStrategy.FORCE_FK
        and len(association_relations) == 2
        and all(
            isinstance(relation.cardinality, Cardinality)
            and relation.cardinality.maximum is CardinalityMaximum.MANY
            for relation in association_relations
        )
    ):
        issues.append(
            ValidationIssue(
                ValidationSeverity.ERROR,
                "association.force_fk_many_to_many",
                f"Association {label} : la stratégie FORCE_FK est incompatible "
                "avec une association N:N.",
                association.id,
            )
        )
    _validate_attributes(
        "Association", label, association.id, association.attributes, issues
    )


def _validate_attributes(
    kind: str,
    owner_name: str,
    owner_id: str,
    attributes: list[Attribute],
    issues: list[ValidationIssue],
) -> None:
    seen: dict[str, str] = {}
    identifier_count = sum(attribute.identifier for attribute in attributes)
    for attribute in attributes:
        clean_name = attribute.name.strip()
        if not clean_name:
            issues.append(
                ValidationIssue(
                    ValidationSeverity.ERROR,
                    "attribute.name_missing",
                    f"{kind} {owner_name} : un attribut est sans nom.",
                    owner_id,
                )
            )
            continue
        key = clean_name.casefold()
        if key in seen:
            issues.append(
                ValidationIssue(
                    ValidationSeverity.ERROR,
                    "attribute.name_duplicate",
                    f'{kind} {owner_name} : attribut "{clean_name}" dupliqué.',
                    owner_id,
                )
            )
        else:
            seen[key] = attribute.id
        if attribute.identifier and attribute.nullable is True:
            issues.append(
                ValidationIssue(
                    ValidationSeverity.ERROR,
                    "attribute.identifier_nullable",
                    f"{kind} {owner_name} : l'identifiant « {clean_name} » "
                    "ne peut pas être facultatif.",
                    owner_id,
                )
            )
        if attribute.auto_increment:
            if not attribute.identifier:
                issues.append(
                    ValidationIssue(
                        ValidationSeverity.ERROR,
                        "attribute.auto_increment_not_identifier",
                        f"{kind} {owner_name} : « {clean_name} » doit être un "
                        "identifiant pour être auto-incrémenté.",
                        owner_id,
                    )
                )
            if identifier_count != 1:
                issues.append(
                    ValidationIssue(
                        ValidationSeverity.ERROR,
                        "attribute.auto_increment_composite_key",
                        f"{kind} {owner_name} : une auto-incrémentation exige "
                        "un identifiant simple.",
                        owner_id,
                    )
                )
            if attribute.data_type is not None and attribute.data_type.name not in {
                MLDDataTypeName.INTEGER,
                MLDDataTypeName.BIGINT,
            }:
                issues.append(
                    ValidationIssue(
                        ValidationSeverity.ERROR,
                        "attribute.auto_increment_type",
                        f"{kind} {owner_name} : « {clean_name} » doit être de "
                        "type INTEGER ou BIGINT pour être auto-incrémenté.",
                        owner_id,
                    )
                )
            if attribute.default is not None:
                issues.append(
                    ValidationIssue(
                        ValidationSeverity.ERROR,
                        "attribute.auto_increment_default",
                        f"{kind} {owner_name} : « {clean_name} » ne peut pas "
                        "combiner auto-incrémentation et valeur par défaut.",
                        owner_id,
                    )
                )


def _validate_relations(model: MCDModel, issues: list[ValidationIssue]) -> None:
    grouped_relations: dict[tuple[str, str], list[Relation]] = {}
    for relation in model.relations.values():
        entity = model.entities.get(relation.entity_id)
        association = model.associations.get(relation.association_id)
        if entity is None or association is None:
            issues.append(
                ValidationIssue(
                    ValidationSeverity.ERROR,
                    "relation.endpoint_missing",
                    "Une relation référence une entité ou une association absente.",
                    relation.id,
                )
            )
        if relation.cardinality is None:
            entity_name = entity.name.strip() if entity else relation.entity_id
            issues.append(
                ValidationIssue(
                    ValidationSeverity.ERROR,
                    "relation.cardinality_missing",
                    f"Relation sur {entity_name} : cardinalité manquante.",
                    relation.id,
                )
            )
        elif not isinstance(relation.cardinality, Cardinality):
            issues.append(
                ValidationIssue(
                    ValidationSeverity.ERROR,
                    "relation.cardinality_invalid",
                    "Une relation possède une cardinalité invalide.",
                    relation.id,
                )
            )
        pair = (relation.entity_id, relation.association_id)
        grouped_relations.setdefault(pair, []).append(relation)

    for relations in grouped_relations.values():
        if len(relations) < 2:
            continue
        seen_roles: set[str] = set()
        for relation in relations:
            clean_role = relation.role.strip()
            if not clean_role:
                issues.append(
                    ValidationIssue(
                        ValidationSeverity.ERROR,
                        "relation.role_missing",
                        "Chaque branche d'une association réflexive doit avoir "
                        "un rôle distinct.",
                        relation.id,
                    )
                )
                continue
            key = clean_role.casefold()
            if key in seen_roles:
                issues.append(
                    ValidationIssue(
                        ValidationSeverity.ERROR,
                        "relation.role_duplicate",
                        f"Le rôle réflexif « {clean_role} » est utilisé plusieurs fois.",
                        relation.id,
                    )
                )
            seen_roles.add(key)


def _validate_inheritances(model: MCDModel, issues: list[ValidationIssue]) -> None:
    child_owner: dict[str, str] = {}
    adjacency: dict[str, set[str]] = {entity_id: set() for entity_id in model.entities}
    for inheritance in model.inheritances.values():
        if inheritance.parent_entity_id not in model.entities:
            issues.append(
                ValidationIssue(
                    ValidationSeverity.ERROR,
                    "inheritance.parent_missing",
                    "Un héritage référence une entité mère absente.",
                    inheritance.id,
                )
            )
            continue
        if not isinstance(inheritance.strategy, InheritanceStrategy):
            issues.append(
                ValidationIssue(
                    ValidationSeverity.ERROR,
                    "inheritance.strategy_invalid",
                    "Un héritage possède une stratégie MLD invalide.",
                    inheritance.id,
                )
            )
        for child_id in inheritance.child_entity_ids:
            if child_id not in model.entities:
                issues.append(
                    ValidationIssue(
                        ValidationSeverity.ERROR,
                        "inheritance.child_missing",
                        "Un héritage référence une entité fille absente.",
                        inheritance.id,
                    )
                )
                continue
            adjacency[inheritance.parent_entity_id].add(child_id)
            if child_id in child_owner:
                issues.append(
                    ValidationIssue(
                        ValidationSeverity.ERROR,
                        "inheritance.multiple_parent",
                        f"L'entité {model.entities[child_id].name} possède plusieurs "
                        "entités mères ; l'héritage multiple n'est pas supporté.",
                        inheritance.id,
                    )
                )
            child_owner[child_id] = inheritance.id

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(entity_id: str) -> bool:
        if entity_id in visiting:
            return True
        if entity_id in visited:
            return False
        visiting.add(entity_id)
        cyclic = any(visit(child_id) for child_id in adjacency[entity_id])
        visiting.remove(entity_id)
        visited.add(entity_id)
        return cyclic

    if any(visit(entity_id) for entity_id in sorted(adjacency)):
        issues.append(
            ValidationIssue(
                ValidationSeverity.ERROR,
                "inheritance.cycle",
                "Le graphe d'héritage contient un cycle.",
            )
        )


def _validate_duplicate_node_names(
    model: MCDModel, issues: list[ValidationIssue]
) -> None:
    for kind, nodes in (
        ("Entité", model.entities.values()),
        ("Association", model.associations.values()),
    ):
        seen: dict[str, str] = {}
        for node in nodes:
            clean_name = node.name.strip()
            if not clean_name:
                continue
            key = clean_name.casefold()
            if key in seen:
                issues.append(
                    ValidationIssue(
                        ValidationSeverity.WARNING,
                        "node.name_duplicate",
                        f'{kind} : le nom "{clean_name}" est utilisé plusieurs fois.',
                        node.id,
                    )
                )
            else:
                seen[key] = node.id
