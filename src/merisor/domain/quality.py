"""Analyse heuristique, locale et explicable de la qualité d'un MCD."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum
from itertools import combinations

from merisor.domain.mld import MLDDataType, MLDDataTypeName
from merisor.domain.model import Association, Attribute, Entity, MCDModel
from merisor.domain.validation import (
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
    validate_mcd,
)


class QualityCategory(str, Enum):
    TYPE_SUGGESTION = "type_suggestion"
    UNIQUENESS = "uniqueness"
    SIMILAR_ENTITY = "similar_entity"
    NAMING = "naming"
    NORMALIZATION = "normalization"

    @property
    def label(self) -> str:
        return CATEGORY_LABELS[self]


class QualityConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def label(self) -> str:
        return {
            QualityConfidence.HIGH: "Élevée",
            QualityConfidence.MEDIUM: "Moyenne",
            QualityConfidence.LOW: "Faible",
        }[self]


class QualityDimension(str, Enum):
    STRUCTURE = "structure"
    IDENTIFIERS = "identifiers"
    CARDINALITIES = "cardinalities"
    TYPING = "typing"
    SEMANTICS = "semantics"
    NORMALIZATION = "normalization"


DIMENSION_LABELS = {
    QualityDimension.STRUCTURE: "Structure MERISE",
    QualityDimension.IDENTIFIERS: "Identifiants",
    QualityDimension.CARDINALITIES: "Cardinalités",
    QualityDimension.TYPING: "Typage",
    QualityDimension.SEMANTICS: "Cohérence sémantique",
    QualityDimension.NORMALIZATION: "Normalisation et nommage",
}

DIMENSION_WEIGHTS = {
    QualityDimension.STRUCTURE: 25,
    QualityDimension.IDENTIFIERS: 15,
    QualityDimension.CARDINALITIES: 15,
    QualityDimension.TYPING: 15,
    QualityDimension.SEMANTICS: 15,
    QualityDimension.NORMALIZATION: 15,
}

CATEGORY_DIMENSIONS = {
    QualityCategory.TYPE_SUGGESTION: QualityDimension.TYPING,
    QualityCategory.UNIQUENESS: QualityDimension.SEMANTICS,
    QualityCategory.SIMILAR_ENTITY: QualityDimension.SEMANTICS,
    QualityCategory.NAMING: QualityDimension.NORMALIZATION,
    QualityCategory.NORMALIZATION: QualityDimension.NORMALIZATION,
}

CATEGORY_LABELS = {
    QualityCategory.TYPE_SUGGESTION: "Typage suggéré",
    QualityCategory.UNIQUENESS: "Unicité suggérée",
    QualityCategory.SIMILAR_ENTITY: "Entités similaires",
    QualityCategory.NAMING: "Convention de nommage",
    QualityCategory.NORMALIZATION: "Normalisation",
}


@dataclass(frozen=True, slots=True)
class QualityFinding:
    code: str
    category: QualityCategory
    message: str
    rationale: str
    confidence: QualityConfidence
    element_ids: tuple[str, ...]
    suggested_value: str | None = None
    penalty: int = 5

    @property
    def dimension(self) -> QualityDimension:
        return CATEGORY_DIMENSIONS[self.category]


@dataclass(frozen=True, slots=True)
class QualityDimensionScore:
    dimension: QualityDimension
    label: str
    weight: int
    score: int
    deductions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ModelQualityReport:
    overall_score: int
    dimensions: tuple[QualityDimensionScore, ...]
    findings: tuple[QualityFinding, ...]
    validation_report: ValidationReport

    def dimension(self, dimension: QualityDimension) -> QualityDimensionScore:
        return next(item for item in self.dimensions if item.dimension is dimension)


def _normalized(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore")
    return re.sub(r"[^a-z0-9]+", "_", ascii_value.decode().casefold()).strip("_")


def _tokens(value: str) -> set[str]:
    return {token for token in _normalized(value).split("_") if token}


def _owners(model: MCDModel) -> list[Entity | Association]:
    return [*model.entities.values(), *model.associations.values()]


def _suggested_type(attribute: Attribute) -> tuple[MLDDataType, str] | None:
    name = _normalized(attribute.name)
    tokens = _tokens(attribute.name)
    if attribute.identifier or not name:
        return None
    if name.endswith("_at") or tokens.intersection(
        {"horodatage", "timestamp", "datetime"}
    ):
        return MLDDataType(MLDDataTypeName.TIMESTAMP), "un horodatage"
    if "date" in tokens or tokens.intersection({"naissance", "echeance", "expiration"}):
        return MLDDataType(MLDDataTypeName.DATE), "une date"
    if name.startswith(("est_", "is_", "has_")) or tokens.intersection(
        {"actif", "active", "archive", "disponible", "valide", "supprime"}
    ):
        return MLDDataType(MLDDataTypeName.BOOLEAN), "un indicateur vrai/faux"
    if tokens.intersection(
        {"prix", "montant", "cout", "tarif", "solde", "salaire", "total"}
    ):
        return (
            MLDDataType(MLDDataTypeName.DECIMAL, precision=10, scale=2),
            "une valeur monétaire ou décimale",
        )
    if tokens.intersection({"description", "commentaire", "contenu", "biographie"}):
        return MLDDataType(MLDDataTypeName.TEXT), "un texte potentiellement long"
    if tokens.intersection({"age", "quantite", "stock", "nombre", "rang", "position"}):
        return MLDDataType(MLDDataTypeName.INTEGER), "une valeur entière"
    return None


def _type_findings(model: MCDModel) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    for owner in _owners(model):
        for attribute in owner.attributes:
            suggestion = _suggested_type(attribute)
            if suggestion is None:
                continue
            expected, meaning = suggestion
            if attribute.data_type == expected:
                continue
            current = (
                "AUTO → VARCHAR(100)"
                if attribute.data_type is None
                else attribute.data_type.label
            )
            confidence = (
                QualityConfidence.HIGH
                if expected.name
                in {
                    MLDDataTypeName.DATE,
                    MLDDataTypeName.BOOLEAN,
                    MLDDataTypeName.DECIMAL,
                }
                else QualityConfidence.MEDIUM
            )
            findings.append(
                QualityFinding(
                    code="quality.attribute.type_suggestion",
                    category=QualityCategory.TYPE_SUGGESTION,
                    message=(
                        f"{owner.name}.{attribute.name} utilise {current} ; "
                        f"{expected.label} semble plus approprié."
                    ),
                    rationale=f"Le nom de l'attribut évoque {meaning}.",
                    confidence=confidence,
                    element_ids=(owner.id, attribute.id),
                    suggested_value=expected.label,
                    penalty=8 if confidence is QualityConfidence.HIGH else 5,
                )
            )
    return findings


def _uniqueness_findings(model: MCDModel) -> list[QualityFinding]:
    strong_tokens = {"email", "courriel", "uuid", "siret", "siren", "isbn"}
    medium_tokens = {"login", "username", "identifiant", "reference", "slug"}
    findings: list[QualityFinding] = []
    for owner in _owners(model):
        for attribute in owner.attributes:
            if attribute.identifier or attribute.unique:
                continue
            tokens = _tokens(attribute.name)
            confidence: QualityConfidence | None = None
            if tokens.intersection(strong_tokens):
                confidence = QualityConfidence.HIGH
            elif tokens.intersection(medium_tokens):
                confidence = QualityConfidence.MEDIUM
            if confidence is None:
                continue
            findings.append(
                QualityFinding(
                    code="quality.attribute.uniqueness_suggestion",
                    category=QualityCategory.UNIQUENESS,
                    message=(
                        f"{owner.name}.{attribute.name} semble devoir être unique "
                        "pour chaque occurrence."
                    ),
                    rationale=(
                        "Le nom correspond à une donnée généralement utilisée comme "
                        "référence ou moyen d'identification."
                    ),
                    confidence=confidence,
                    element_ids=(owner.id, attribute.id),
                    suggested_value="UNIQUE",
                    penalty=4 if confidence is QualityConfidence.HIGH else 2,
                )
            )
    return findings


_SYNONYM_GROUPS = (
    frozenset({"client", "acheteur", "customer"}),
    frozenset({"utilisateur", "usager", "user"}),
    frozenset({"produit", "article", "item"}),
    frozenset({"employe", "salarie", "collaborateur"}),
    frozenset({"fournisseur", "prestataire"}),
)


def _are_known_synonyms(first: str, second: str) -> bool:
    return any(first in group and second in group for group in _SYNONYM_GROUPS)


def _inheritance_pairs(model: MCDModel) -> set[frozenset[str]]:
    return {
        frozenset((inheritance.parent_entity_id, child_id))
        for inheritance in model.inheritances.values()
        for child_id in inheritance.child_entity_ids
    }


def _similar_entity_findings(model: MCDModel) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    inheritance_pairs = _inheritance_pairs(model)
    entities = sorted(model.entities.values(), key=lambda item: item.id)
    for first, second in combinations(entities, 2):
        if frozenset((first.id, second.id)) in inheritance_pairs:
            continue
        first_name = _normalized(first.name)
        second_name = _normalized(second.name)
        if not first_name or not second_name or first_name == second_name:
            continue
        name_similarity = SequenceMatcher(None, first_name, second_name).ratio()
        first_attributes = {
            _normalized(attribute.name)
            for attribute in first.attributes
            if not attribute.identifier and _normalized(attribute.name)
        }
        second_attributes = {
            _normalized(attribute.name)
            for attribute in second.attributes
            if not attribute.identifier and _normalized(attribute.name)
        }
        union = first_attributes | second_attributes
        shared = first_attributes & second_attributes
        attribute_similarity = len(shared) / len(union) if union else 0.0
        synonyms = _are_known_synonyms(first_name, second_name)
        similar_attributes = len(shared) >= 3 and attribute_similarity >= 0.75
        if not synonyms and name_similarity < 0.82 and not similar_attributes:
            continue
        reasons: list[str] = []
        if synonyms:
            reasons.append("leurs noms sont des synonymes fréquents")
        elif name_similarity >= 0.82:
            reasons.append(
                f"leurs noms sont proches ({round(name_similarity * 100)} %)"
            )
        if similar_attributes:
            reasons.append(f"elles partagent {len(shared)} attributs sur {len(union)}")
        confidence = (
            QualityConfidence.HIGH
            if synonyms and similar_attributes
            else QualityConfidence.MEDIUM
        )
        findings.append(
            QualityFinding(
                code="quality.entity.similar_concept",
                category=QualityCategory.SIMILAR_ENTITY,
                message=(
                    f"Les entités {first.name} et {second.name} pourraient "
                    "représenter le même concept."
                ),
                rationale=" ; ".join(reasons).capitalize() + ".",
                confidence=confidence,
                element_ids=(first.id, second.id),
                penalty=10 if confidence is QualityConfidence.HIGH else 6,
            )
        )
    return findings


def _naming_style(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    if re.fullmatch(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*", normalized):
        return "MAJUSCULES_AVEC_UNDERSCORE"
    if re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", normalized):
        return "snake_case"
    if re.fullmatch(r"[A-Z][A-Za-z0-9]*", normalized):
        return "PascalCase"
    if re.fullmatch(r"[a-z][A-Za-z0-9]*", normalized):
        return "camelCase"
    return "mixte"


def _dominant_style(items: list[tuple[str, str]]) -> str | None:
    if len(items) < 3:
        return None
    counts = Counter(_naming_style(name) for _, name in items)
    style, count = counts.most_common(1)[0]
    if style == "mixte" or count / len(items) < 0.6:
        return None
    return style


def _naming_findings(model: MCDModel) -> list[QualityFinding]:
    groups: tuple[tuple[str, list[tuple[str, str]]], ...] = (
        ("entités", [(item.id, item.name) for item in model.entities.values()]),
        (
            "associations",
            [(item.id, item.name) for item in model.associations.values()],
        ),
        (
            "attributs",
            [
                (attribute.id, attribute.name)
                for owner in _owners(model)
                for attribute in owner.attributes
            ],
        ),
    )
    findings: list[QualityFinding] = []
    for label, items in groups:
        dominant = _dominant_style(items)
        if dominant is None:
            continue
        for item_id, name in items:
            style = _naming_style(name)
            if style == dominant:
                continue
            findings.append(
                QualityFinding(
                    code="quality.naming.inconsistent_style",
                    category=QualityCategory.NAMING,
                    message=(
                        f"Le nom « {name} » ne suit pas la convention {dominant} "
                        f"majoritaire pour les {label}."
                    ),
                    rationale=(
                        "Une convention uniforme rend le modèle et les exports "
                        "plus faciles à lire."
                    ),
                    confidence=QualityConfidence.HIGH,
                    element_ids=(item_id,),
                    suggested_value=dominant,
                    penalty=3,
                )
            )
    return findings


def _normalization_findings(model: MCDModel) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    entity_names = {
        _normalized(entity.name): entity for entity in model.entities.values()
    }
    multi_value_names = {"tags", "telephones", "emails", "adresses"}
    compound_names = {"nom_prenom", "adresse_complete", "contact_complet"}
    for owner in _owners(model):
        numbered: dict[str, list[Attribute]] = defaultdict(list)
        for attribute in owner.attributes:
            name = _normalized(attribute.name)
            numbered_match = re.fullmatch(r"(.+?)(?:_?\d+)", name)
            if numbered_match:
                numbered[numbered_match.group(1)].append(attribute)
            if (
                name in multi_value_names
                or name.startswith("liste_")
                or name.endswith(("_csv", "_json"))
            ):
                findings.append(
                    QualityFinding(
                        code="quality.normalization.multivalued_attribute",
                        category=QualityCategory.NORMALIZATION,
                        message=(
                            f"{owner.name}.{attribute.name} semble contenir plusieurs "
                            "valeurs dans un seul attribut."
                        ),
                        rationale=(
                            "Une collection répétable est généralement représentée "
                            "par une entité et une association dédiées."
                        ),
                        confidence=QualityConfidence.MEDIUM,
                        element_ids=(owner.id, attribute.id),
                        penalty=7,
                    )
                )
            if name in compound_names:
                findings.append(
                    QualityFinding(
                        code="quality.normalization.compound_attribute",
                        category=QualityCategory.NORMALIZATION,
                        message=(
                            f"{owner.name}.{attribute.name} semble regrouper plusieurs "
                            "informations élémentaires."
                        ),
                        rationale=(
                            "Un attribut atomique est plus facile à valider, rechercher "
                            "et transformer."
                        ),
                        confidence=QualityConfidence.MEDIUM,
                        element_ids=(owner.id, attribute.id),
                        penalty=6,
                    )
                )
            if (
                isinstance(owner, Entity)
                and not attribute.identifier
                and name.startswith("id_")
                and name[3:] in entity_names
                and entity_names[name[3:]].id != owner.id
            ):
                referenced = entity_names[name[3:]]
                findings.append(
                    QualityFinding(
                        code="quality.normalization.foreign_id_in_mcd",
                        category=QualityCategory.NORMALIZATION,
                        message=(
                            f"{owner.name}.{attribute.name} ressemble à une clé étrangère "
                            f"technique vers {referenced.name}."
                        ),
                        rationale=(
                            "Dans un MCD, le lien conceptuel devrait normalement être "
                            "porté par une association."
                        ),
                        confidence=QualityConfidence.HIGH,
                        element_ids=(owner.id, attribute.id, referenced.id),
                        penalty=9,
                    )
                )
        for base, attributes in numbered.items():
            if len(attributes) < 2:
                continue
            findings.append(
                QualityFinding(
                    code="quality.normalization.repeating_group",
                    category=QualityCategory.NORMALIZATION,
                    message=(
                        f"{owner.name} répète le groupe « {base} » dans "
                        f"{len(attributes)} attributs numérotés."
                    ),
                    rationale=(
                        "Des attributs numérotés signalent souvent une valeur répétable "
                        "qui mérite une entité séparée."
                    ),
                    confidence=QualityConfidence.HIGH,
                    element_ids=(owner.id, *(item.id for item in attributes)),
                    penalty=10,
                )
            )
        if len(owner.attributes) > 15:
            findings.append(
                QualityFinding(
                    code="quality.normalization.large_owner",
                    category=QualityCategory.NORMALIZATION,
                    message=(
                        f"{owner.name} contient {len(owner.attributes)} attributs ; "
                        "plusieurs sous-concepts sont peut-être mélangés."
                    ),
                    rationale=(
                        "Un objet très large mérite une vérification de ses dépendances "
                        "fonctionnelles."
                    ),
                    confidence=QualityConfidence.LOW,
                    element_ids=(owner.id,),
                    penalty=4,
                )
            )
    return findings


def _validation_dimension(issue: ValidationIssue) -> QualityDimension:
    if "identifier" in issue.code:
        return QualityDimension.IDENTIFIERS
    if issue.code.startswith("relation.") or issue.code in {
        "association.too_few_entities",
        "association.force_fk_many_to_many",
        "association.force_fk_nary",
        "association.historized_force_fk",
    }:
        return QualityDimension.CARDINALITIES
    return QualityDimension.STRUCTURE


def analyze_model_quality(
    model: MCDModel,
    validation_report: ValidationReport | None = None,
) -> ModelQualityReport:
    """Produit des suggestions et un score sans modifier le modèle."""

    validation = validation_report or validate_mcd(model)
    findings = sorted(
        (
            *_type_findings(model),
            *_uniqueness_findings(model),
            *_similar_entity_findings(model),
            *_naming_findings(model),
            *_normalization_findings(model),
        ),
        key=lambda item: (
            list(QualityCategory).index(item.category),
            item.message.casefold(),
            item.element_ids,
        ),
    )
    deductions: dict[QualityDimension, list[tuple[int, str]]] = {
        dimension: [] for dimension in QualityDimension
    }
    if not model.entities:
        deductions[QualityDimension.STRUCTURE].append(
            (100, "Le modèle ne contient aucune entité.")
        )
    for issue in validation.issues:
        penalty = 20 if issue.severity is ValidationSeverity.ERROR else 7
        deductions[_validation_dimension(issue)].append((penalty, issue.message))
    for finding in findings:
        deductions[finding.dimension].append((finding.penalty, finding.message))

    dimension_scores = tuple(
        QualityDimensionScore(
            dimension=dimension,
            label=DIMENSION_LABELS[dimension],
            weight=DIMENSION_WEIGHTS[dimension],
            score=max(0, 100 - sum(item[0] for item in deductions[dimension])),
            deductions=tuple(item[1] for item in deductions[dimension]),
        )
        for dimension in QualityDimension
    )
    overall = round(sum(item.score * item.weight for item in dimension_scores) / 100)
    return ModelQualityReport(
        overall_score=overall,
        dimensions=dimension_scores,
        findings=tuple(findings),
        validation_report=validation,
    )
