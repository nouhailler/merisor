"""Simulation explicable d'un changement avant son application au MCD."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from enum import Enum

from merisor.application.impact_analysis import (
    ImpactCertainty,
    ImpactReference,
    ImpactTarget,
    ModelImpactAnalyzer,
)
from merisor.domain import Association, Attribute, Entity, MCDModel, validate_mcd


class WhatIfOperation(str, Enum):
    DELETE = "delete"

    @property
    def label(self) -> str:
        return {WhatIfOperation.DELETE: "Suppression"}[self]


class ImpactLayer(str, Enum):
    MCD = "mcd"
    MLD = "mld"
    SQL = "sql"
    DOCUMENTATION = "documentation"
    TEST_DATA = "test_data"
    QUERIES = "queries"

    @property
    def label(self) -> str:
        return {
            ImpactLayer.MCD: "Impact MCD",
            ImpactLayer.MLD: "Impact MLD",
            ImpactLayer.SQL: "Impact SQL",
            ImpactLayer.DOCUMENTATION: "Impact documentation",
            ImpactLayer.TEST_DATA: "Impact données de test",
            ImpactLayer.QUERIES: "Impact requêtes",
        }[self]


@dataclass(frozen=True, slots=True)
class WhatIfImpact:
    layer: ImpactLayer
    label: str
    reason: str
    certainty: ImpactCertainty = ImpactCertainty.CERTAIN


@dataclass(frozen=True, slots=True)
class WhatIfReport:
    target: ImpactTarget
    operation: WhatIfOperation
    impacts: tuple[WhatIfImpact, ...]
    new_validation_errors: tuple[str, ...]
    mld_available: bool

    def for_layer(self, layer: ImpactLayer) -> tuple[WhatIfImpact, ...]:
        return tuple(item for item in self.impacts if item.layer is layer)

    @property
    def certain(self) -> tuple[WhatIfImpact, ...]:
        return tuple(
            item for item in self.impacts if item.certainty is ImpactCertainty.CERTAIN
        )

    @property
    def potential(self) -> tuple[WhatIfImpact, ...]:
        return tuple(
            item for item in self.impacts if item.certainty is ImpactCertainty.POTENTIAL
        )

    def render(self) -> str:
        lines = [
            "ANALYSE D'IMPACT — ET SI… ?",
            "=" * 56,
            f"{self.operation.label} de {self.target.label}",
        ]
        for layer in ImpactLayer:
            lines.extend(("", layer.label))
            impacts = self.for_layer(layer)
            if not impacts:
                lines.append("  Aucun impact calculable.")
                continue
            for impact in impacts:
                marker = "✓" if impact.certainty is ImpactCertainty.CERTAIN else "⚠"
                lines.append(f"  {marker} {impact.label}")
                lines.append(f"    {impact.reason}")
        if self.new_validation_errors:
            lines.extend(("", "ERREURS CRÉÉES PAR LA SIMULATION"))
            lines.extend(f"  ❌ {message}" for message in self.new_validation_errors)
        lines.extend(
            (
                "",
                "Les livrables non persistés sont signalés comme à régénérer ; ",
                "MERISOR n'invente jamais un nombre d'usages qu'il ne peut pas tracer.",
            )
        )
        return "\n".join(lines)


class WhatIfAnalyzer:
    """Projette les conséquences d'une suppression, sans muter le modèle source."""

    def __init__(self, impact_analyzer: ModelImpactAnalyzer | None = None) -> None:
        self.impact_analyzer = impact_analyzer or ModelImpactAnalyzer()

    def targets(self, model: MCDModel) -> tuple[ImpactTarget, ...]:
        return self.impact_analyzer.targets(model)

    def analyze_delete(self, model: MCDModel, target_id: str) -> WhatIfReport:
        base = self.impact_analyzer.analyze(model, target_id)
        owner, attribute = self._owner_and_attribute(model, base.target)
        impacts = [
            WhatIfImpact(
                ImpactLayer.MCD,
                base.target.label,
                "élément directement supprimé du modèle conceptuel",
            )
        ]
        for reference in base.references:
            impacts.extend(self._map_reference(reference))

        impacts.append(
            WhatIfImpact(
                ImpactLayer.DOCUMENTATION,
                "Documentation générée",
                "les vues MCD, inventaires et descriptions doivent être régénérés",
                ImpactCertainty.POTENTIAL,
            )
        )
        if base.mld_available:
            impacts.extend(
                (
                    WhatIfImpact(
                        ImpactLayer.TEST_DATA,
                        "Scripts de données de test",
                        "générés à la demande et non enregistrés : régénération requise",
                        ImpactCertainty.POTENTIAL,
                    ),
                    WhatIfImpact(
                        ImpactLayer.QUERIES,
                        "Requêtes SQL générées",
                        "non persistées par MERISOR : leurs usages exacts ne peuvent "
                        "pas être comptés",
                        ImpactCertainty.POTENTIAL,
                    ),
                )
            )

        simulated = copy.deepcopy(model)
        self._delete(simulated, owner.id, attribute)
        before_errors = {
            (issue.code, issue.element_id, issue.message)
            for issue in validate_mcd(model).errors
        }
        new_errors = tuple(
            issue.message
            for issue in validate_mcd(simulated).errors
            if (issue.code, issue.element_id, issue.message) not in before_errors
        )
        unique = {
            (item.layer, item.label, item.reason, item.certainty): item
            for item in impacts
        }
        ordered = tuple(
            sorted(
                unique.values(),
                key=lambda item: (
                    list(ImpactLayer).index(item.layer),
                    item.certainty is ImpactCertainty.POTENTIAL,
                    item.label.casefold(),
                ),
            )
        )
        return WhatIfReport(
            base.target,
            WhatIfOperation.DELETE,
            ordered,
            new_errors,
            base.mld_available,
        )

    @staticmethod
    def _owner_and_attribute(
        model: MCDModel, target: ImpactTarget
    ) -> tuple[Entity | Association, Attribute | None]:
        owner = model.node(target.owner_id)
        attribute = next(
            (item for item in owner.attributes if item.id == target.id), None
        )
        return owner, attribute

    @staticmethod
    def _delete(
        model: MCDModel,
        owner_id: str,
        attribute: Attribute | None,
    ) -> None:
        if attribute is not None:
            model.remove_attribute(owner_id, attribute.id)
        elif owner_id in model.entities:
            model.remove_entity(owner_id)
        else:
            model.remove_association(owner_id)

    @staticmethod
    def _map_reference(reference: ImpactReference) -> tuple[WhatIfImpact, ...]:
        certain = reference.certainty
        if reference.category in {"Relation MCD", "Contrainte fonctionnelle"}:
            return (
                WhatIfImpact(
                    ImpactLayer.MCD, reference.label, reference.reason, certain
                ),
            )
        if reference.category == "Correspondance de nom":
            return (
                WhatIfImpact(
                    ImpactLayer.MCD, reference.label, reference.reason, certain
                ),
            )
        if reference.category == "Colonne MLD":
            return (
                WhatIfImpact(
                    ImpactLayer.MLD, reference.label, reference.reason, certain
                ),
                WhatIfImpact(
                    ImpactLayer.SQL,
                    f"Colonne {reference.label}",
                    "la colonne SQL dérivée disparaîtra au prochain export",
                    certain,
                ),
            )
        if reference.category == "Index SQL":
            return (
                WhatIfImpact(
                    ImpactLayer.SQL, reference.label, reference.reason, certain
                ),
            )
        if reference.category.startswith("Contrainte"):
            return (
                WhatIfImpact(
                    ImpactLayer.MLD, reference.label, reference.reason, certain
                ),
                WhatIfImpact(
                    ImpactLayer.SQL,
                    f"{reference.category.removeprefix('Contrainte ')}({reference.label})",
                    "contrainte SQL dérivée à supprimer ou régénérer",
                    certain,
                ),
            )
        return ()
