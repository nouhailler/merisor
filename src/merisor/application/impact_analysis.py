"""Analyse de dépendances et d'impact d'un élément du MCD."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from merisor.application.mld_transformer import (
    McdToMldTransformer,
    MLDTransformationError,
)
from merisor.domain import Association, Attribute, Entity, MCDModel, MLDModel


class ImpactCertainty(str, Enum):
    CERTAIN = "certain"
    POTENTIAL = "potential"


@dataclass(frozen=True, slots=True)
class ImpactTarget:
    id: str
    owner_id: str
    label: str
    kind: str


@dataclass(frozen=True, slots=True)
class ImpactReference:
    category: str
    label: str
    reason: str
    certainty: ImpactCertainty = ImpactCertainty.CERTAIN


@dataclass(frozen=True, slots=True)
class ImpactReport:
    target: ImpactTarget
    references: tuple[ImpactReference, ...]
    mld_available: bool

    @property
    def certain(self) -> tuple[ImpactReference, ...]:
        return tuple(
            item
            for item in self.references
            if item.certainty is ImpactCertainty.CERTAIN
        )

    @property
    def potential(self) -> tuple[ImpactReference, ...]:
        return tuple(
            item
            for item in self.references
            if item.certainty is ImpactCertainty.POTENTIAL
        )

    @property
    def relation_count(self) -> int:
        return sum(item.category == "Relation MCD" for item in self.certain)

    @property
    def constraint_count(self) -> int:
        return sum("Contrainte" in item.category for item in self.certain)

    @property
    def risk_level(self) -> str:
        if (
            self.relation_count >= 3
            or self.constraint_count >= 3
            or len(self.certain) >= 6
        ):
            return "Élevé"
        if self.certain or self.potential:
            return "Modéré"
        return "Faible"

    def render(self) -> str:
        lines = [
            f"ANALYSE D'IMPACT — {self.target.label}",
            "=" * 48,
            f"Risque estimé : {self.risk_level}",
            f"Dépendances certaines : {len(self.certain)}",
            f"Relations : {self.relation_count}",
            f"Contraintes : {self.constraint_count}",
        ]
        for title, references in (
            ("IMPACTS CERTAINS", self.certain),
            ("CORRESPONDANCES À CONFIRMER", self.potential),
        ):
            lines.extend(("", title))
            if not references:
                lines.append("  Aucun.")
            else:
                lines.extend(f"  • {item.label} — {item.reason}" for item in references)
        if not self.mld_available:
            lines.extend(
                (
                    "",
                    "Note : le MCD actuel ne permet pas de reconstruire un MLD valide. ",
                    "Les dépendances MLD/SQL ne sont donc pas incluses.",
                )
            )
        return "\n".join(lines)


class ModelImpactAnalyzer:
    """Suit les provenances formelles et isole les heuristiques de nommage."""

    def targets(self, model: MCDModel) -> tuple[ImpactTarget, ...]:
        targets: list[ImpactTarget] = []
        nodes: list[Entity | Association] = list(model.entities.values())
        nodes.extend(model.associations.values())
        for node in nodes:
            kind = "Entité" if isinstance(node, Entity) else "Association"
            targets.append(ImpactTarget(node.id, node.id, node.name, kind))
            targets.extend(
                ImpactTarget(
                    attribute.id,
                    node.id,
                    f"{node.name}.{attribute.name}",
                    "Attribut",
                )
                for attribute in node.attributes
            )
        return tuple(sorted(targets, key=lambda item: (item.label.casefold(), item.id)))

    def analyze(self, model: MCDModel, target_id: str) -> ImpactReport:
        target = self._target(model, target_id)
        owner = model.node(target.owner_id)
        attribute = self._attribute(owner, target_id)
        references: list[ImpactReference] = []

        if attribute is None or attribute.identifier:
            self._add_mcd_relations(model, owner, references)
        self._add_functional_dependencies(model, target_id, references)
        if attribute is not None:
            self._add_attribute_constraints(attribute, references)
            self._add_name_matches(model, owner.id, attribute, references)

        mld = self._safe_mld(model)
        if mld is not None:
            self._add_mld_references(model, mld, owner, attribute, references)

        unique = {
            (item.category, item.label, item.reason, item.certainty): item
            for item in references
        }
        ordered = tuple(
            sorted(
                unique.values(),
                key=lambda item: (
                    item.certainty is ImpactCertainty.POTENTIAL,
                    item.category.casefold(),
                    item.label.casefold(),
                ),
            )
        )
        return ImpactReport(target, ordered, mld is not None)

    def _target(self, model: MCDModel, target_id: str) -> ImpactTarget:
        for target in self.targets(model):
            if target.id == target_id:
                return target
        raise ValueError(f"Élément inconnu pour l'analyse d'impact : {target_id}")

    @staticmethod
    def _attribute(owner: Entity | Association, target_id: str) -> Attribute | None:
        return next(
            (attribute for attribute in owner.attributes if attribute.id == target_id),
            None,
        )

    @staticmethod
    def _safe_mld(model: MCDModel) -> MLDModel | None:
        try:
            return McdToMldTransformer().transform(model)
        except (MLDTransformationError, ValueError, KeyError):
            return None

    @staticmethod
    def _add_mcd_relations(
        model: MCDModel,
        owner: Entity | Association,
        references: list[ImpactReference],
    ) -> None:
        for relation in model.relations.values():
            if isinstance(owner, Entity) and relation.entity_id != owner.id:
                continue
            if isinstance(owner, Association) and relation.association_id != owner.id:
                continue
            entity = model.entities.get(relation.entity_id)
            association = model.associations.get(relation.association_id)
            cardinality = relation.cardinality.label if relation.cardinality else "?"
            references.append(
                ImpactReference(
                    "Relation MCD",
                    f"{entity.name if entity else '?'} ↔ {association.name if association else '?'}",
                    f"cardinalité {cardinality}"
                    + (f", rôle {relation.role}" if relation.role else ""),
                )
            )

    @staticmethod
    def _add_functional_dependencies(
        model: MCDModel,
        target_id: str,
        references: list[ImpactReference],
    ) -> None:
        for dependency in model.functional_dependencies.values():
            ids = (
                *dependency.determinant_attribute_ids,
                *dependency.dependent_attribute_ids,
            )
            if target_id not in ids:
                continue
            owner = model.node(dependency.owner_id)
            by_id = {attribute.id: attribute.name for attribute in owner.attributes}
            left = ", ".join(
                by_id.get(item, "?") for item in dependency.determinant_attribute_ids
            )
            right = ", ".join(
                by_id.get(item, "?") for item in dependency.dependent_attribute_ids
            )
            references.append(
                ImpactReference(
                    "Contrainte fonctionnelle",
                    f"{owner.name} : {left} → {right}",
                    "dépendance fonctionnelle déclarée",
                )
            )

    @staticmethod
    def _add_attribute_constraints(
        attribute: Attribute, references: list[ImpactReference]
    ) -> None:
        for expression in attribute.constraints:
            references.append(
                ImpactReference(
                    "Contrainte CHECK",
                    expression,
                    "expression portée par l'attribut",
                )
            )
        if attribute.unique:
            references.append(
                ImpactReference(
                    "Contrainte UNIQUE",
                    attribute.name,
                    "unicité explicitement demandée",
                )
            )
        if attribute.identifier:
            references.append(
                ImpactReference(
                    "Contrainte PK",
                    attribute.name,
                    "membre de l'identifiant conceptuel",
                )
            )

    @staticmethod
    def _normalized_name(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.casefold())

    def _add_name_matches(
        self,
        model: MCDModel,
        owner_id: str,
        target: Attribute,
        references: list[ImpactReference],
    ) -> None:
        normalized = self._normalized_name(target.name)
        if not normalized:
            return
        nodes: list[Entity | Association] = list(model.entities.values())
        nodes.extend(model.associations.values())
        for node in nodes:
            if node.id == owner_id:
                continue
            for attribute in node.attributes:
                if self._normalized_name(attribute.name) == normalized:
                    references.append(
                        ImpactReference(
                            "Correspondance de nom",
                            f"{node.name}.{attribute.name}",
                            "même nom ; usage métier à confirmer",
                            ImpactCertainty.POTENTIAL,
                        )
                    )

    @staticmethod
    def _add_mld_references(
        model: MCDModel,
        mld: MLDModel,
        owner: Entity | Association,
        attribute: Attribute | None,
        references: list[ImpactReference],
    ) -> None:
        attribute_ids = (
            {attribute.id}
            if attribute is not None
            else {item.id for item in owner.attributes}
        )
        owner_table_ids = {
            table.id for table in mld.tables if table.source_element_id == owner.id
        }
        touched: dict[str, set[str]] = {}
        for table in mld.tables:
            for column in table.columns:
                if column.source_attribute_id in attribute_ids:
                    touched.setdefault(table.id, set()).add(column.id)
                    if table.id not in owner_table_ids:
                        references.append(
                            ImpactReference(
                                "Colonne MLD",
                                f"{table.name}.{column.name}",
                                "colonne dérivée de l'attribut source",
                            )
                        )

        for table in mld.tables:
            local_ids = touched.get(table.id, set())
            for foreign_key in table.foreign_keys:
                target_ids = touched.get(foreign_key.referenced_table_id, set())
                if local_ids.intersection(
                    foreign_key.column_ids
                ) or target_ids.intersection(foreign_key.referenced_column_ids):
                    references.append(
                        ImpactReference(
                            "Contrainte FK",
                            f"{table.name}.{foreign_key.name or foreign_key.id}",
                            "clé étrangère dérivée ou référençant l'attribut",
                        )
                    )
            for unique_constraint in table.unique_constraints:
                if attribute is None and local_ids.intersection(
                    unique_constraint.column_ids
                ):
                    references.append(
                        ImpactReference(
                            "Contrainte UNIQUE",
                            f"{table.name}.{unique_constraint.name or unique_constraint.id}",
                            "contrainte logique sur la colonne dérivée",
                        )
                    )
            for check_constraint in table.check_constraints:
                if (
                    attribute is None
                    and check_constraint.source_element_id in attribute_ids
                ):
                    references.append(
                        ImpactReference(
                            "Contrainte CHECK",
                            f"{table.name}.{check_constraint.name or check_constraint.id}",
                            check_constraint.expression,
                        )
                    )
            for index in table.indexes:
                if local_ids.intersection(index.column_ids):
                    references.append(
                        ImpactReference(
                            "Index SQL",
                            f"{table.name}.{index.name}",
                            "index explicite sur la colonne dérivée",
                        )
                    )
