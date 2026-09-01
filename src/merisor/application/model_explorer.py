"""Projection non destructive d'un MCD pour la navigation et le focus."""

from __future__ import annotations

import copy
from collections import deque
from dataclasses import dataclass

from merisor.domain import Association, Entity, Inheritance, MCDModel


@dataclass(frozen=True, slots=True)
class ExplorationOptions:
    """Filtres appliqués à une vue temporaire du modèle."""

    show_entities: bool = True
    show_associations: bool = True
    show_links: bool = True
    focus_id: str | None = None
    depth: int | None = None
    query: str = ""
    restrict_to_query: bool = False
    hidden_ids: frozenset[str] = frozenset()
    scope_ids: frozenset[str] | None = None


@dataclass(frozen=True, slots=True)
class ExplorationResult:
    model: MCDModel
    visible_ids: frozenset[str]
    hidden_ids: frozenset[str]


@dataclass(frozen=True, slots=True)
class ExplorationSearchResult:
    element_id: str
    name: str
    kind: str
    matched_attributes: tuple[str, ...] = ()


class ModelExplorer:
    """Calcule recherches, voisinages et dépendances sans toucher au MCD source."""

    def search(
        self, model: MCDModel, query: str
    ) -> tuple[ExplorationSearchResult, ...]:
        needle = query.strip().casefold()
        results: list[ExplorationSearchResult] = []
        for node in self._ordered_nodes(model):
            matching_attributes = tuple(
                attribute.name
                for attribute in node.attributes
                if needle and needle in attribute.name.casefold()
            )
            if not needle or needle in node.name.casefold() or matching_attributes:
                results.append(
                    ExplorationSearchResult(
                        node.id,
                        node.name,
                        "Entité" if isinstance(node, Entity) else "Association",
                        matching_attributes,
                    )
                )
        return tuple(results)

    def project(
        self, model: MCDModel, options: ExplorationOptions
    ) -> ExplorationResult:
        all_node_ids = set(model.entities) | set(model.associations)
        visible = all_node_ids - set(options.hidden_ids)

        if options.scope_ids is not None:
            visible &= set(options.scope_ids)

        if not options.show_entities:
            visible -= set(model.entities)
        if not options.show_associations:
            visible -= set(model.associations)

        if options.focus_id in all_node_ids:
            visible &= self._neighborhood(model, options.focus_id, options.depth)

        if options.restrict_to_query and options.query.strip():
            matches = {
                result.element_id for result in self.search(model, options.query)
            }
            expanded_matches = set(matches)
            for match in matches:
                expanded_matches.update(self._neighborhood(model, match, 1))
            visible &= expanded_matches

        projected = MCDModel()
        for entity in model.entities.values():
            if entity.id in visible:
                projected.add_entity(copy.deepcopy(entity))
        for association in model.associations.values():
            if association.id in visible:
                projected.add_association(copy.deepcopy(association))

        if options.show_links:
            for relation in model.relations.values():
                if relation.entity_id in visible and relation.association_id in visible:
                    projected.add_relation(copy.deepcopy(relation))
            for inheritance in model.inheritances.values():
                children = tuple(
                    child_id
                    for child_id in inheritance.child_entity_ids
                    if child_id in visible
                )
                if inheritance.parent_entity_id in visible and children:
                    projected.add_inheritance(
                        Inheritance(
                            inheritance.parent_entity_id,
                            children,
                            inheritance.strategy,
                            id=inheritance.id,
                        )
                    )

        for dependency in model.functional_dependencies.values():
            if dependency.owner_id in visible:
                projected.add_functional_dependency(copy.deepcopy(dependency))

        return ExplorationResult(
            projected,
            frozenset(visible),
            frozenset(options.hidden_ids & all_node_ids),
        )

    def dependency_text(self, model: MCDModel, element_id: str) -> str:
        node = model.node(element_id)
        lines = [node.name, "=" * max(8, len(node.name))]

        relationships = model.connected_relations(element_id)
        if relationships:
            lines.append("\nRelations métier")
        for relation in relationships:
            target: Entity | Association
            if isinstance(node, Entity):
                target = model.associations[relation.association_id]
            else:
                target = model.entities[relation.entity_id]
            cardinality = str(relation.cardinality) if relation.cardinality else "(?)"
            role = f" — rôle : {relation.role}" if relation.role else ""
            lines.append(f"• {target.name} {cardinality}{role}")

        inheritances = [
            inheritance
            for inheritance in model.inheritances.values()
            if element_id == inheritance.parent_entity_id
            or element_id in inheritance.child_entity_ids
        ]
        if inheritances:
            lines.append("\nHéritages ISA")
        for inheritance in inheritances:
            parent = model.entities[inheritance.parent_entity_id].name
            children = ", ".join(
                model.entities[child_id].name
                for child_id in inheritance.child_entity_ids
            )
            lines.append(f"• {parent} → {children} ({inheritance.strategy.value})")

        dependencies = model.functional_dependencies_for(element_id)
        if dependencies:
            attributes = {attribute.id: attribute.name for attribute in node.attributes}
            lines.append("\nDépendances fonctionnelles")
            for dependency in dependencies:
                determinants = ", ".join(
                    attributes[item_id]
                    for item_id in dependency.determinant_attribute_ids
                )
                dependents = ", ".join(
                    attributes[item_id]
                    for item_id in dependency.dependent_attribute_ids
                )
                lines.append(
                    f"• {determinants} → {dependents} [{dependency.origin.value}]"
                )

        if len(lines) == 2:
            lines.append("\nAucune dépendance déclarée.")
        return "\n".join(lines)

    def _neighborhood(
        self, model: MCDModel, start_id: str, depth: int | None
    ) -> set[str]:
        if depth is None:
            return set(model.entities) | set(model.associations)
        adjacency = self._adjacency(model)
        visited = {start_id}
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])
        while queue:
            current, current_depth = queue.popleft()
            if current_depth >= max(0, depth):
                continue
            for neighbor in adjacency.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, current_depth + 1))
        return visited

    @staticmethod
    def _adjacency(model: MCDModel) -> dict[str, set[str]]:
        adjacency: dict[str, set[str]] = {
            node_id: set() for node_id in (*model.entities, *model.associations)
        }
        for relation in model.relations.values():
            adjacency[relation.entity_id].add(relation.association_id)
            adjacency[relation.association_id].add(relation.entity_id)
        for inheritance in model.inheritances.values():
            for child_id in inheritance.child_entity_ids:
                adjacency[inheritance.parent_entity_id].add(child_id)
                adjacency[child_id].add(inheritance.parent_entity_id)
        return adjacency

    @staticmethod
    def _ordered_nodes(model: MCDModel) -> list[Entity | Association]:
        return sorted(
            (*model.entities.values(), *model.associations.values()),
            key=lambda node: (
                node.name.casefold(),
                0 if isinstance(node, Entity) else 1,
                node.id,
            ),
        )
