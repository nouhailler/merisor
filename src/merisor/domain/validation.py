"""Règles de validation sémantique d'un MCD MERISE V0.2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from merisor.domain.model import (
    Association,
    Attribute,
    Cardinality,
    CardinalityMaximum,
    Entity,
    MaterializationStrategy,
    MCDModel,
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
    _validate_duplicate_node_names(model, issues)
    return ValidationReport(tuple(issues))


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
    entity_ids = {
        relation.entity_id
        for relation in model.relations.values()
        if relation.association_id == association.id
        and relation.entity_id in model.entities
    }
    if len(entity_ids) < 2:
        issues.append(
            ValidationIssue(
                ValidationSeverity.ERROR,
                "association.too_few_entities",
                f"Association {label} : elle doit être reliée à au moins deux entités.",
                association.id,
            )
        )
    association_relations = [
        relation
        for relation in model.relations.values()
        if relation.association_id == association.id
    ]
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


def _validate_relations(model: MCDModel, issues: list[ValidationIssue]) -> None:
    seen_pairs: set[tuple[str, str]] = set()
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
        if pair in seen_pairs:
            issues.append(
                ValidationIssue(
                    ValidationSeverity.ERROR,
                    "relation.duplicate",
                    "Une entité est reliée plusieurs fois à la même association.",
                    relation.id,
                )
            )
        seen_pairs.add(pair)


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
