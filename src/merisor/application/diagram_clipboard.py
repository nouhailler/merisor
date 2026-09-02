"""Copie structurée d'une sélection MCD, indépendante du presse-papiers texte."""

from __future__ import annotations

import copy
from dataclasses import replace
from uuid import uuid4

from merisor.domain import (
    Association,
    Attribute,
    Entity,
    FunctionalDependency,
    Inheritance,
    MCDModel,
    Position,
    Relation,
)


def paste_selection(
    source: MCDModel,
    source_node_ids: set[str],
    target: MCDModel,
    *,
    offset: float = 45.0,
) -> tuple[MCDModel, tuple[str, ...]]:
    """Ajoute une copie cohérente des nœuds et liens internes à la sélection."""

    result = copy.deepcopy(target)
    node_mapping: dict[str, str] = {}
    attribute_mapping: dict[str, str] = {}
    created_ids: list[str] = []
    entity_names = {item.name.casefold() for item in result.entities.values()}
    association_names = {item.name.casefold() for item in result.associations.values()}

    for node_id in sorted(source_node_ids):
        if node_id not in source.entities and node_id not in source.associations:
            continue
        original = source.node(node_id)
        copied_attributes = [
            _copy_attribute(attribute, attribute_mapping)
            for attribute in original.attributes
        ]
        new_id = str(uuid4())
        node_mapping[node_id] = new_id
        created_ids.append(new_id)
        position = Position(original.position.x + offset, original.position.y + offset)
        if isinstance(original, Entity):
            name = _copy_name(original.name, entity_names)
            result.add_entity(Entity(name, position, new_id, copied_attributes))
        else:
            name = _copy_name(original.name, association_names)
            result.add_association(
                Association(
                    name,
                    position,
                    new_id,
                    copied_attributes,
                    original.is_historized,
                    original.materialization_strategy,
                )
            )

    for relation in source.relations.values():
        if (
            relation.entity_id in node_mapping
            and relation.association_id in node_mapping
        ):
            result.add_relation(
                Relation(
                    node_mapping[relation.entity_id],
                    node_mapping[relation.association_id],
                    id=str(uuid4()),
                    cardinality=copy.deepcopy(relation.cardinality),
                    role=relation.role,
                )
            )
    for inheritance in source.inheritances.values():
        involved = {
            inheritance.parent_entity_id,
            *inheritance.child_entity_ids,
        }
        if involved <= node_mapping.keys():
            result.add_inheritance(
                Inheritance(
                    node_mapping[inheritance.parent_entity_id],
                    tuple(node_mapping[item] for item in inheritance.child_entity_ids),
                    inheritance.strategy,
                )
            )
    for dependency in source.functional_dependencies.values():
        if dependency.owner_id not in node_mapping:
            continue
        referenced = {
            *dependency.determinant_attribute_ids,
            *dependency.dependent_attribute_ids,
        }
        if referenced <= attribute_mapping.keys():
            result.add_functional_dependency(
                FunctionalDependency(
                    node_mapping[dependency.owner_id],
                    tuple(
                        attribute_mapping[item]
                        for item in dependency.determinant_attribute_ids
                    ),
                    tuple(
                        attribute_mapping[item]
                        for item in dependency.dependent_attribute_ids
                    ),
                    dependency.origin,
                )
            )

    for domain in result.domains.values():
        additions = [
            node_mapping[item]
            for item in source_node_ids
            if item in node_mapping
            and item in source.domains.get(domain.id, domain).node_ids
        ]
        domain.node_ids = (*domain.node_ids, *additions)
    for view in result.submodel_views.values():
        source_view = source.submodel_views.get(view.id)
        if source_view is None:
            continue
        additions = [
            node_mapping[item]
            for item in source_node_ids
            if item in node_mapping and item in source_view.node_ids
        ]
        view.node_ids = (*view.node_ids, *additions)
    return result, tuple(created_ids)


def _copy_attribute(attribute: Attribute, mapping: dict[str, str]) -> Attribute:
    new_id = str(uuid4())
    mapping[attribute.id] = new_id
    return replace(copy.deepcopy(attribute), id=new_id)


def _copy_name(name: str, used: set[str]) -> str:
    base = f"{name}_copie"
    candidate = base
    index = 2
    while candidate.casefold() in used:
        candidate = f"{base}_{index}"
        index += 1
    used.add(candidate.casefold())
    return candidate
