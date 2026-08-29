"""Lecture, migration et écriture du format JSON versionné de MERISOR."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    DiagramError,
    MCDModel,
    MaterializationStrategy,
    Entity,
    Position,
    Relation,
)


FORMAT_VERSION = 2
LEGACY_FORMAT_VERSION = 1


class PersistenceError(ValueError):
    """Fichier absent, illisible ou non conforme au format MERISOR."""


class JsonDiagramRepository:
    """Dépôt JSON sans dépendance à l'interface graphique."""

    def to_dict(self, model: MCDModel) -> dict[str, Any]:
        def attribute_data(attribute: Attribute) -> dict[str, Any]:
            return {
                "id": attribute.id,
                "name": attribute.name,
                "identifier": attribute.identifier,
            }

        def node_data(node: Entity | Association) -> dict[str, Any]:
            return {
                "id": node.id,
                "name": node.name,
                "position": {"x": node.position.x, "y": node.position.y},
                "attributes": [
                    attribute_data(attribute) for attribute in node.attributes
                ],
            }

        def association_data(association: Association) -> dict[str, Any]:
            data = node_data(association)
            data.update(
                {
                    "is_historized": association.is_historized,
                    "materialization_strategy": (
                        association.materialization_strategy.value
                    ),
                }
            )
            return data

        def cardinality_data(cardinality: Cardinality | None) -> dict[str, str] | None:
            if cardinality is None:
                return None
            return {
                "minimum": cardinality.minimum.value,
                "maximum": cardinality.maximum.value,
            }

        return {
            "format_version": FORMAT_VERSION,
            "entities": [
                node_data(entity)
                for entity in sorted(model.entities.values(), key=lambda item: item.id)
            ],
            "associations": [
                association_data(association)
                for association in sorted(
                    model.associations.values(), key=lambda item: item.id
                )
            ],
            "relations": [
                {
                    "id": relation.id,
                    "entity_id": relation.entity_id,
                    "association_id": relation.association_id,
                    "cardinality": cardinality_data(relation.cardinality),
                }
                for relation in sorted(
                    model.relations.values(), key=lambda item: item.id
                )
            ],
        }

    def from_dict(self, data: Any) -> MCDModel:
        if not isinstance(data, dict):
            raise PersistenceError("La racine du fichier doit être un objet JSON.")
        version = data.get("format_version")
        if version == LEGACY_FORMAT_VERSION:
            return self._from_v1(data)
        if version == FORMAT_VERSION:
            return self._from_v2(data)
        raise PersistenceError(
            f"Version de format non prise en charge : {version!r} "
            f"(versions acceptées : {LEGACY_FORMAT_VERSION} et {FORMAT_VERSION})."
        )

    def _from_v1(self, data: dict[str, Any]) -> MCDModel:
        """Migre sans perte la V0.1 ; aucune cardinalité n'est inventée."""

        model = MCDModel()
        try:
            for raw in self._required_list(data, "entities"):
                item = self._required_object(raw, "entité")
                model.add_entity(
                    Entity(
                        id=self._required_id(item, "id"),
                        name=self._required_text(item, "name"),
                        position=self._position(item),
                    )
                )
            for raw in self._required_list(data, "associations"):
                item = self._required_object(raw, "association")
                model.add_association(
                    Association(
                        id=self._required_id(item, "id"),
                        name=self._required_text(item, "name"),
                        position=self._position(item),
                    )
                )
            for raw in self._required_list(data, "relations"):
                item = self._required_object(raw, "relation")
                model.add_relation(
                    Relation(
                        id=self._required_id(item, "id"),
                        entity_id=self._required_id(item, "entity_id"),
                        association_id=self._required_id(item, "association_id"),
                        cardinality=None,
                    )
                )
        except DiagramError as error:
            raise PersistenceError(f"Diagramme V0.1 incohérent : {error}") from error
        return model

    def _from_v2(self, data: dict[str, Any]) -> MCDModel:
        model = MCDModel()
        try:
            for raw in self._required_list(data, "entities"):
                item = self._required_object(raw, "entité")
                model.add_entity(
                    Entity(
                        id=self._required_id(item, "id"),
                        name=self._required_text(item, "name"),
                        position=self._position(item),
                        attributes=self._attributes(item),
                    )
                )
            for raw in self._required_list(data, "associations"):
                item = self._required_object(raw, "association")
                model.add_association(
                    Association(
                        id=self._required_id(item, "id"),
                        name=self._required_text(item, "name"),
                        position=self._position(item),
                        attributes=self._attributes(item),
                        is_historized=self._is_historized(item),
                        materialization_strategy=self._materialization_strategy(item),
                    )
                )
            for raw in self._required_list(data, "relations"):
                item = self._required_object(raw, "relation")
                model.add_relation(
                    Relation(
                        id=self._required_id(item, "id"),
                        entity_id=self._required_id(item, "entity_id"),
                        association_id=self._required_id(item, "association_id"),
                        cardinality=self._cardinality(item),
                    )
                )
        except DiagramError as error:
            raise PersistenceError(f"Diagramme V0.2 incohérent : {error}") from error
        return model

    def save(self, model: MCDModel, path: str | Path) -> None:
        target = Path(path)
        if not target.parent.exists():
            raise PersistenceError(f"Le dossier n'existe pas : {target.parent}")
        temporary_name: str | None = None
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_name = temporary.name
                json.dump(
                    self.to_dict(model),
                    temporary,
                    ensure_ascii=False,
                    indent=2,
                )
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, target)
        except (OSError, TypeError, ValueError) as error:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)
            raise PersistenceError(f"Impossible d'enregistrer {target} : {error}") from error

    def load(self, path: str | Path) -> MCDModel:
        source = Path(path)
        try:
            with source.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
        except (OSError, json.JSONDecodeError) as error:
            raise PersistenceError(f"Impossible d'ouvrir {source} : {error}") from error
        return self.from_dict(data)

    def _attributes(self, data: dict[str, Any]) -> list[Attribute]:
        raw_attributes = data.get("attributes", [])
        if not isinstance(raw_attributes, list):
            raise PersistenceError("Le champ 'attributes' doit être une liste.")
        attributes: list[Attribute] = []
        for raw in raw_attributes:
            item = self._required_object(raw, "attribut")
            identifier = item.get("identifier", False)
            if not isinstance(identifier, bool):
                raise PersistenceError(
                    "Le champ 'identifier' d'un attribut doit être booléen."
                )
            attributes.append(
                Attribute(
                    id=self._required_id(item, "id"),
                    name=self._required_text(item, "name"),
                    identifier=identifier,
                )
            )
        return attributes

    def _cardinality(self, data: dict[str, Any]) -> Cardinality | None:
        raw = data.get("cardinality")
        if raw is None:
            return None
        item = self._required_object(raw, "cardinalité")
        minimum = self._required_text(item, "minimum")
        maximum = self._required_text(item, "maximum")
        return Cardinality(minimum, maximum)

    @staticmethod
    def _is_historized(data: dict[str, Any]) -> bool:
        value = data.get("is_historized", False)
        if not isinstance(value, bool):
            raise PersistenceError("Le champ 'is_historized' doit être booléen.")
        return value

    @staticmethod
    def _materialization_strategy(
        data: dict[str, Any],
    ) -> MaterializationStrategy:
        value = data.get(
            "materialization_strategy", MaterializationStrategy.AUTO.value
        )
        try:
            return MaterializationStrategy(value)
        except (TypeError, ValueError) as error:
            raise PersistenceError(
                "Le champ 'materialization_strategy' doit valoir "
                "AUTO, FORCE_TABLE ou FORCE_FK."
            ) from error

    @staticmethod
    def _required_list(data: dict[str, Any], key: str) -> list[Any]:
        value = data.get(key)
        if not isinstance(value, list):
            raise PersistenceError(f"Le champ '{key}' doit être une liste.")
        return value

    @staticmethod
    def _required_object(value: Any, kind: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise PersistenceError(f"Chaque {kind} doit être un objet JSON.")
        return value

    @staticmethod
    def _required_id(data: dict[str, Any], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise PersistenceError(f"Le champ '{key}' doit être une chaîne non vide.")
        return value

    @staticmethod
    def _required_text(data: dict[str, Any], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str):
            raise PersistenceError(f"Le champ '{key}' doit être une chaîne.")
        return value

    @staticmethod
    def _position(data: dict[str, Any]) -> Position:
        value = data.get("position")
        if not isinstance(value, dict):
            raise PersistenceError("Le champ 'position' doit être un objet.")
        x = value.get("x")
        y = value.get("y")
        if (
            not isinstance(x, (int, float))
            or isinstance(x, bool)
            or not isinstance(y, (int, float))
            or isinstance(y, bool)
        ):
            raise PersistenceError("Les coordonnées x et y doivent être numériques.")
        try:
            return Position(float(x), float(y))
        except DiagramError as error:
            raise PersistenceError(str(error)) from error
