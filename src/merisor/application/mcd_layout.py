"""Placement automatique déterministe d'un graphe MCD biparti."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, hypot, pi, sin

from merisor.domain import Association, Entity, MCDModel, Position


@dataclass(frozen=True, slots=True)
class _NodeSize:
    width: float
    height: float


class McdAutoLayout:
    """Algorithme force-directed complété par une résolution des collisions."""

    ITERATIONS = 220
    EDGE_LENGTH = 330.0
    REPULSION = 115_000.0
    MARGIN = 65.0

    def calculate(self, model: MCDModel) -> dict[str, Position]:
        nodes = self._ordered_nodes(model)
        if not nodes:
            return {}
        if len(nodes) == 1:
            return {nodes[0].id: Position(180.0, 150.0)}

        radius = max(300.0, len(nodes) * 58.0)
        coordinates = {
            node.id: [
                radius * cos(2 * pi * index / len(nodes)),
                radius * sin(2 * pi * index / len(nodes)),
            ]
            for index, node in enumerate(nodes)
        }
        edges = [
            (relation.entity_id, relation.association_id)
            for relation in model.relations.values()
            if relation.entity_id in coordinates
            and relation.association_id in coordinates
        ]
        edges.extend(
            (inheritance.parent_entity_id, child_id)
            for inheritance in model.inheritances.values()
            for child_id in inheritance.child_entity_ids
            if inheritance.parent_entity_id in coordinates and child_id in coordinates
        )

        for iteration in range(self.ITERATIONS):
            forces = {node.id: [0.0, 0.0] for node in nodes}
            for index, first in enumerate(nodes):
                for second in nodes[index + 1 :]:
                    self._repel(
                        coordinates[first.id],
                        coordinates[second.id],
                        forces[first.id],
                        forces[second.id],
                    )
            for first_id, second_id in edges:
                self._attract(
                    coordinates[first_id],
                    coordinates[second_id],
                    forces[first_id],
                    forces[second_id],
                )
            temperature = max(1.0, 22.0 * (1.0 - iteration / self.ITERATIONS))
            for node in nodes:
                x, y = coordinates[node.id]
                force_x, force_y = forces[node.id]
                # Une faible gravité garde les composantes proches du centre.
                force_x -= x * 0.006
                force_y -= y * 0.006
                magnitude = hypot(force_x, force_y)
                if magnitude:
                    scale = min(temperature, magnitude) / magnitude
                    coordinates[node.id][0] += force_x * scale
                    coordinates[node.id][1] += force_y * scale

        sizes = {node.id: self._node_size(node) for node in nodes}
        self._resolve_collisions(nodes, coordinates, sizes)
        self._normalize(nodes, coordinates, sizes)
        return {
            node.id: Position(
                round(coordinates[node.id][0], 1), round(coordinates[node.id][1], 1)
            )
            for node in nodes
        }

    @staticmethod
    def _ordered_nodes(model: MCDModel) -> list[Entity | Association]:
        entities = sorted(
            model.entities.values(), key=lambda node: (node.name.casefold(), node.id)
        )
        associations = sorted(
            model.associations.values(),
            key=lambda node: (node.name.casefold(), node.id),
        )
        result: list[Entity | Association] = []
        for index in range(max(len(entities), len(associations))):
            if index < len(entities):
                result.append(entities[index])
            if index < len(associations):
                result.append(associations[index])
        return result

    def _repel(
        self,
        first: list[float],
        second: list[float],
        first_force: list[float],
        second_force: list[float],
    ) -> None:
        dx = first[0] - second[0]
        dy = first[1] - second[1]
        distance = max(1.0, hypot(dx, dy))
        force = min(45.0, self.REPULSION / (distance * distance))
        force_x = dx / distance * force
        force_y = dy / distance * force
        first_force[0] += force_x
        first_force[1] += force_y
        second_force[0] -= force_x
        second_force[1] -= force_y

    def _attract(
        self,
        first: list[float],
        second: list[float],
        first_force: list[float],
        second_force: list[float],
    ) -> None:
        dx = second[0] - first[0]
        dy = second[1] - first[1]
        distance = max(1.0, hypot(dx, dy))
        force = (distance - self.EDGE_LENGTH) * 0.045
        force_x = dx / distance * force
        force_y = dy / distance * force
        first_force[0] += force_x
        first_force[1] += force_y
        second_force[0] -= force_x
        second_force[1] -= force_y

    def _resolve_collisions(
        self,
        nodes: list[Entity | Association],
        coordinates: dict[str, list[float]],
        sizes: dict[str, _NodeSize],
    ) -> None:
        for _pass in range(45):
            moved = False
            for index, first in enumerate(nodes):
                for second in nodes[index + 1 :]:
                    first_position = coordinates[first.id]
                    second_position = coordinates[second.id]
                    dx = second_position[0] - first_position[0]
                    dy = second_position[1] - first_position[1]
                    required_x = (
                        sizes[first.id].width + sizes[second.id].width
                    ) / 2 + self.MARGIN
                    required_y = (
                        sizes[first.id].height + sizes[second.id].height
                    ) / 2 + self.MARGIN
                    overlap_x = required_x - abs(dx)
                    overlap_y = required_y - abs(dy)
                    if overlap_x <= 0 or overlap_y <= 0:
                        continue
                    moved = True
                    if overlap_x < overlap_y:
                        shift = overlap_x / 2 + 1
                        direction = 1 if dx >= 0 else -1
                        first_position[0] -= shift * direction
                        second_position[0] += shift * direction
                    else:
                        shift = overlap_y / 2 + 1
                        direction = 1 if dy >= 0 else -1
                        first_position[1] -= shift * direction
                        second_position[1] += shift * direction
            if not moved:
                break

    @staticmethod
    def _node_size(node: Entity | Association) -> _NodeSize:
        if isinstance(node, Entity):
            return _NodeSize(220.0, max(100.0, 62.0 + len(node.attributes) * 23.0))
        attribute_panel = (
            0.0 if not node.attributes else 21.0 + len(node.attributes) * 22.0
        )
        return _NodeSize(220.0, 122.0 + attribute_panel)

    @staticmethod
    def _normalize(
        nodes: list[Entity | Association],
        coordinates: dict[str, list[float]],
        sizes: dict[str, _NodeSize],
    ) -> None:
        minimum_x = min(
            coordinates[node.id][0] - sizes[node.id].width / 2 for node in nodes
        )
        minimum_y = min(
            coordinates[node.id][1] - sizes[node.id].height / 2 for node in nodes
        )
        shift_x = 100.0 - minimum_x
        shift_y = 100.0 - minimum_y
        for node in nodes:
            coordinates[node.id][0] += shift_x
            coordinates[node.id][1] += shift_y
