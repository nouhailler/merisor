"""Modèle métier reconstructible d'un MCD MERISE.

Le domaine ne dépend pas de Qt. Il accepte certains états incomplets (nom vide
ou cardinalité absente) afin qu'un diagramme en cours de construction puisse
être sauvegardé puis analysé par le validateur.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Iterable
from uuid import uuid4


class DiagramError(ValueError):
    """Erreur structurelle empêchant de maintenir un modèle cohérent."""


def _new_id() -> str:
    return str(uuid4())


def _validate_internal_id(element_id: str, kind: str) -> None:
    if not isinstance(element_id, str) or not element_id.strip():
        raise DiagramError(f"L'identifiant interne de {kind} est obligatoire.")


def _validate_name_type(name: str, kind: str) -> None:
    if not isinstance(name, str):
        raise DiagramError(f"Le nom de {kind} doit être une chaîne.")


@dataclass(frozen=True, slots=True)
class Position:
    """Position d'un nœud dans les coordonnées de la scène."""

    x: float = 0.0
    y: float = 0.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.x) or not math.isfinite(self.y):
            raise DiagramError("Une position doit contenir des nombres finis.")


class CardinalityMinimum(str, Enum):
    ZERO = "0"
    ONE = "1"


class CardinalityMaximum(str, Enum):
    ONE = "1"
    MANY = "N"


class MaterializationStrategy(str, Enum):
    """Directive explicite pour la future transformation d'une association."""

    AUTO = "AUTO"
    FORCE_TABLE = "FORCE_TABLE"
    FORCE_FK = "FORCE_FK"


@dataclass(frozen=True, slots=True)
class Cardinality:
    """Cardinalité MERISE portée par l'extrémité entité d'une relation."""

    minimum: CardinalityMinimum | str
    maximum: CardinalityMaximum | str

    def __post_init__(self) -> None:
        try:
            minimum = CardinalityMinimum(self.minimum)
            maximum = CardinalityMaximum(self.maximum)
        except (TypeError, ValueError) as error:
            raise DiagramError(
                "Cardinalité invalide : minimum attendu 0 ou 1, maximum attendu 1 ou N."
            ) from error
        object.__setattr__(self, "minimum", minimum)
        object.__setattr__(self, "maximum", maximum)

    @property
    def label(self) -> str:
        return f"{self.minimum.value},{self.maximum.value}"

    def __str__(self) -> str:
        return f"({self.label})"


DEFAULT_CARDINALITY = Cardinality(CardinalityMinimum.ZERO, CardinalityMaximum.MANY)


@dataclass(slots=True)
class Attribute:
    """Attribut d'entité ou d'association."""

    name: str
    identifier: bool = False
    id: str = field(default_factory=_new_id)

    def __post_init__(self) -> None:
        _validate_internal_id(self.id, "l'attribut")
        _validate_name_type(self.name, "l'attribut")
        if not isinstance(self.identifier, bool):
            raise DiagramError("Le statut d'identifiant doit être booléen.")


@dataclass(slots=True)
class Entity:
    """Entité MERISE et ses attributs, identifiant composé compris."""

    name: str
    position: Position = field(default_factory=Position)
    id: str = field(default_factory=_new_id)
    attributes: list[Attribute] = field(default_factory=list)

    def __post_init__(self) -> None:
        _validate_internal_id(self.id, "l'entité")
        _validate_name_type(self.name, "l'entité")
        if not isinstance(self.attributes, list) or not all(
            isinstance(attribute, Attribute) for attribute in self.attributes
        ):
            raise DiagramError("Les attributs d'une entité doivent être des Attribute.")

    @property
    def identifier_attributes(self) -> list[Attribute]:
        return [attribute for attribute in self.attributes if attribute.identifier]


@dataclass(slots=True)
class Association:
    """Association MERISE, éventuellement porteuse d'attributs."""

    name: str
    position: Position = field(default_factory=Position)
    id: str = field(default_factory=_new_id)
    attributes: list[Attribute] = field(default_factory=list)
    is_historized: bool = False
    materialization_strategy: MaterializationStrategy | str = (
        MaterializationStrategy.AUTO
    )

    def __post_init__(self) -> None:
        _validate_internal_id(self.id, "l'association")
        _validate_name_type(self.name, "l'association")
        if not isinstance(self.attributes, list) or not all(
            isinstance(attribute, Attribute) for attribute in self.attributes
        ):
            raise DiagramError(
                "Les attributs d'une association doivent être des Attribute."
            )
        if not isinstance(self.is_historized, bool):
            raise DiagramError("Le statut d'historisation doit être booléen.")
        try:
            self.materialization_strategy = MaterializationStrategy(
                self.materialization_strategy
            )
        except (TypeError, ValueError) as error:
            raise DiagramError(
                "Stratégie de matérialisation invalide : "
                "AUTO, FORCE_TABLE ou FORCE_FK attendu."
            ) from error

    @property
    def identifier_attributes(self) -> list[Attribute]:
        """Identifiant conceptuel optionnel d'une association matérialisée."""

        return [attribute for attribute in self.attributes if attribute.identifier]


@dataclass(slots=True)
class Relation:
    """Lien métier entre une entité, une association et sa cardinalité."""

    entity_id: str
    association_id: str
    id: str = field(default_factory=_new_id)
    cardinality: Cardinality | None = field(
        default_factory=lambda: DEFAULT_CARDINALITY
    )

    def __post_init__(self) -> None:
        _validate_internal_id(self.id, "la relation")
        _validate_internal_id(self.entity_id, "l'entité référencée")
        _validate_internal_id(self.association_id, "l'association référencée")
        if self.cardinality is not None and not isinstance(
            self.cardinality, Cardinality
        ):
            raise DiagramError("La cardinalité d'une relation est invalide.")


Node = Entity | Association


class MCDModel:
    """Agrégat racine garantissant les références internes du MCD."""

    def __init__(self) -> None:
        self.entities: dict[str, Entity] = {}
        self.associations: dict[str, Association] = {}
        self.relations: dict[str, Relation] = {}

    def _all_ids(self) -> set[str]:
        attribute_ids = {
            attribute.id
            for node in (*self.entities.values(), *self.associations.values())
            for attribute in node.attributes
        }
        return (
            set(self.entities)
            | set(self.associations)
            | set(self.relations)
            | attribute_ids
        )

    def _ensure_available_ids(self, ids: Iterable[str]) -> None:
        candidate_ids = list(ids)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise DiagramError("Un objet contient des identifiants internes dupliqués.")
        existing = self._all_ids()
        conflict = next((item_id for item_id in candidate_ids if item_id in existing), None)
        if conflict is not None:
            raise DiagramError(f"Identifiant déjà utilisé : {conflict}")

    @staticmethod
    def _automatic_name(prefix: str, existing_names: Iterable[str]) -> str:
        names = set(existing_names)
        index = 1
        while f"{prefix}_{index}" in names:
            index += 1
        return f"{prefix}_{index}"

    def create_entity(self, name: str | None, position: Position) -> Entity:
        clean_name = name.strip() if isinstance(name, str) else ""
        if not clean_name:
            clean_name = self._automatic_name(
                "Entité", (entity.name for entity in self.entities.values())
            )
        entity = Entity(name=clean_name, position=position)
        self.add_entity(entity)
        return entity

    def create_association(self, name: str | None, position: Position) -> Association:
        clean_name = name.strip() if isinstance(name, str) else ""
        if not clean_name:
            clean_name = self._automatic_name(
                "Association",
                (association.name for association in self.associations.values()),
            )
        association = Association(name=clean_name, position=position)
        self.add_association(association)
        return association

    def create_relation(
        self,
        entity_id: str,
        association_id: str,
        cardinality: Cardinality | None = DEFAULT_CARDINALITY,
    ) -> Relation:
        relation = Relation(
            entity_id=entity_id,
            association_id=association_id,
            cardinality=cardinality,
        )
        self.add_relation(relation)
        return relation

    def create_attribute(
        self, owner_id: str, name: str, identifier: bool = False
    ) -> Attribute:
        attribute = Attribute(name=name, identifier=identifier)
        self.add_attribute(owner_id, attribute)
        return attribute

    def add_entity(self, entity: Entity) -> None:
        self._ensure_available_ids(
            [entity.id, *(attribute.id for attribute in entity.attributes)]
        )
        self.entities[entity.id] = entity

    def add_association(self, association: Association) -> None:
        self._ensure_available_ids(
            [association.id, *(attribute.id for attribute in association.attributes)]
        )
        self.associations[association.id] = association

    def add_relation(self, relation: Relation) -> None:
        self._ensure_available_ids([relation.id])
        if relation.entity_id not in self.entities:
            raise DiagramError(f"Entité inconnue : {relation.entity_id}")
        if relation.association_id not in self.associations:
            raise DiagramError(f"Association inconnue : {relation.association_id}")
        if any(
            existing.entity_id == relation.entity_id
            and existing.association_id == relation.association_id
            for existing in self.relations.values()
        ):
            raise DiagramError("Cette entité et cette association sont déjà reliées.")
        self.relations[relation.id] = relation

    def add_attribute(
        self, owner_id: str, attribute: Attribute, index: int | None = None
    ) -> None:
        self._ensure_available_ids([attribute.id])
        owner = self.node(owner_id)
        if index is None:
            owner.attributes.append(attribute)
        else:
            owner.attributes.insert(index, attribute)

    def remove_attribute(self, owner_id: str, attribute_id: str) -> tuple[Attribute, int]:
        owner = self.node(owner_id)
        for index, attribute in enumerate(owner.attributes):
            if attribute.id == attribute_id:
                return owner.attributes.pop(index), index
        raise DiagramError(f"Attribut inconnu : {attribute_id}")

    def attribute(self, owner_id: str, attribute_id: str) -> Attribute:
        owner = self.node(owner_id)
        for attribute in owner.attributes:
            if attribute.id == attribute_id:
                return attribute
        raise DiagramError(f"Attribut inconnu : {attribute_id}")

    def rename_node(self, element_id: str, name: str) -> None:
        _validate_name_type(name, "l'objet")
        self.node(element_id).name = name

    def rename_attribute(self, owner_id: str, attribute_id: str, name: str) -> None:
        _validate_name_type(name, "l'attribut")
        self.attribute(owner_id, attribute_id).name = name

    def set_attribute_identifier(
        self, owner_id: str, attribute_id: str, identifier: bool
    ) -> None:
        if not isinstance(identifier, bool):
            raise DiagramError("Le statut d'identifiant doit être booléen.")
        self.attribute(owner_id, attribute_id).identifier = identifier

    def set_association_historized(
        self, association_id: str, is_historized: bool
    ) -> None:
        if not isinstance(is_historized, bool):
            raise DiagramError("Le statut d'historisation doit être booléen.")
        try:
            self.associations[association_id].is_historized = is_historized
        except KeyError as error:
            raise DiagramError(f"Association inconnue : {association_id}") from error

    def set_association_materialization_strategy(
        self,
        association_id: str,
        strategy: MaterializationStrategy | str,
    ) -> None:
        try:
            normalized = MaterializationStrategy(strategy)
        except (TypeError, ValueError) as error:
            raise DiagramError(
                "Stratégie de matérialisation invalide : "
                "AUTO, FORCE_TABLE ou FORCE_FK attendu."
            ) from error
        try:
            self.associations[association_id].materialization_strategy = normalized
        except KeyError as error:
            raise DiagramError(f"Association inconnue : {association_id}") from error

    def set_relation_cardinality(
        self, relation_id: str, cardinality: Cardinality | None
    ) -> None:
        if cardinality is not None and not isinstance(cardinality, Cardinality):
            raise DiagramError("La cardinalité d'une relation est invalide.")
        try:
            self.relations[relation_id].cardinality = cardinality
        except KeyError as error:
            raise DiagramError(f"Relation inconnue : {relation_id}") from error

    def move_node(self, element_id: str, position: Position) -> None:
        self.node(element_id).position = position

    def connected_relations(self, node_id: str) -> list[Relation]:
        return [
            relation
            for relation in self.relations.values()
            if relation.entity_id == node_id or relation.association_id == node_id
        ]

    def remove_relation(self, relation_id: str) -> Relation:
        try:
            return self.relations.pop(relation_id)
        except KeyError as error:
            raise DiagramError(f"Relation inconnue : {relation_id}") from error

    def remove_entity(self, entity_id: str) -> tuple[Entity, list[Relation]]:
        if entity_id not in self.entities:
            raise DiagramError(f"Entité inconnue : {entity_id}")
        relations = self.connected_relations(entity_id)
        for relation in relations:
            del self.relations[relation.id]
        return self.entities.pop(entity_id), relations

    def remove_association(
        self, association_id: str
    ) -> tuple[Association, list[Relation]]:
        if association_id not in self.associations:
            raise DiagramError(f"Association inconnue : {association_id}")
        relations = self.connected_relations(association_id)
        for relation in relations:
            del self.relations[relation.id]
        return self.associations.pop(association_id), relations

    def node(self, element_id: str) -> Node:
        if element_id in self.entities:
            return self.entities[element_id]
        if element_id in self.associations:
            return self.associations[element_id]
        raise DiagramError(f"Nœud inconnu : {element_id}")

    def element(self, element_id: str) -> Node | Relation:
        if element_id in self.entities:
            return self.entities[element_id]
        if element_id in self.associations:
            return self.associations[element_id]
        if element_id in self.relations:
            return self.relations[element_id]
        raise DiagramError(f"Élément inconnu : {element_id}")


# Nom historique conservé pour les extensions et fichiers clients de la V0.1.
DiagramModel = MCDModel
