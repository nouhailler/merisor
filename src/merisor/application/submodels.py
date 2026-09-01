"""Résolution déterministe des domaines et vues enregistrées d'un MCD."""

from __future__ import annotations

from dataclasses import dataclass

from merisor.domain import MCDModel, SubmodelViewKind

GLOBAL_SCOPE_ID = "global"


@dataclass(frozen=True, slots=True)
class SubmodelScope:
    id: str
    label: str
    category: str
    node_ids: frozenset[str]


class SubmodelResolver:
    """Expose une vue globale, chaque domaine et chaque vue personnalisée."""

    def scopes(self, model: MCDModel) -> tuple[SubmodelScope, ...]:
        all_nodes = frozenset((*model.entities, *model.associations))
        result = [SubmodelScope(GLOBAL_SCOPE_ID, "Vue globale", "GLOBAL", all_nodes)]
        for domain in sorted(
            model.domains.values(), key=lambda item: (item.name.casefold(), item.id)
        ):
            result.append(
                SubmodelScope(
                    f"domain:{domain.id}",
                    domain.name,
                    "DOMAIN",
                    frozenset(domain.node_ids),
                )
            )
        for view in sorted(
            model.submodel_views.values(),
            key=lambda item: (item.kind.value, item.name.casefold(), item.id),
        ):
            node_ids = set(view.node_ids)
            for domain_id in view.domain_ids:
                if domain_id in model.domains:
                    node_ids.update(model.domains[domain_id].node_ids)
            category = (
                "BUSINESS" if view.kind is SubmodelViewKind.BUSINESS else "TECHNICAL"
            )
            result.append(
                SubmodelScope(
                    f"view:{view.id}", view.name, category, frozenset(node_ids)
                )
            )
        return tuple(result)

    def resolve(self, model: MCDModel, scope_id: str) -> SubmodelScope:
        available = self.scopes(model)
        return next(
            (scope for scope in available if scope.id == scope_id),
            available[0],
        )
