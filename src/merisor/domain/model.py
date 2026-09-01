"""Modèle métier reconstructible d'un MCD MERISE.

Le domaine ne dépend pas de Qt. Il accepte certains états incomplets (nom vide
ou cardinalité absente) afin qu'un diagramme en cours de construction puisse
être sauvegardé puis analysé par le validateur.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

from merisor.domain.mld import MLDDataType


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


_ORIGIN = Position()


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


class InheritanceStrategy(str, Enum):
    """Stratégie de projection d'une spécialisation ISA dans le MLD."""

    PARENT_ONLY = "PARENT_ONLY"
    CHILDREN_ONLY = "CHILDREN_ONLY"
    JOINED = "JOINED"


class FunctionalDependencyOrigin(str, Enum):
    """Origine d'une dépendance, afin de distinguer faits et suggestions."""

    USER = "USER"
    AI = "AI"


class SubmodelViewKind(str, Enum):
    """Intention d'une vue enregistrée du MCD."""

    BUSINESS = "BUSINESS"
    TECHNICAL = "TECHNICAL"


@dataclass(frozen=True, slots=True, init=False)
class Cardinality:
    """Cardinalité MERISE portée par l'extrémité entité d'une relation."""

    minimum: CardinalityMinimum
    maximum: CardinalityMaximum

    def __init__(
        self,
        minimum: CardinalityMinimum | str,
        maximum: CardinalityMaximum | str,
    ) -> None:
        try:
            normalized_minimum = CardinalityMinimum(minimum)
            normalized_maximum = CardinalityMaximum(maximum)
        except (TypeError, ValueError) as error:
            raise DiagramError(
                "Cardinalité invalide : minimum attendu 0 ou 1, maximum attendu 1 ou N."
            ) from error
        object.__setattr__(self, "minimum", normalized_minimum)
        object.__setattr__(self, "maximum", normalized_maximum)

    def __post_init__(self) -> None:
        """Compatibilité avec les outils appelant explicitement ce hook."""

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
    data_type: MLDDataType | None = None
    nullable: bool | None = None
    default: str | None = None
    unique: bool = False
    comment: str = ""
    auto_increment: bool = False
    constraints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_internal_id(self.id, "l'attribut")
        _validate_name_type(self.name, "l'attribut")
        if not isinstance(self.identifier, bool):
            raise DiagramError("Le statut d'identifiant doit être booléen.")
        if self.data_type is not None and not isinstance(self.data_type, MLDDataType):
            raise DiagramError(
                "Le type explicite d'un attribut doit être un type logique MLD."
            )
        if self.nullable is not None and not isinstance(self.nullable, bool):
            raise DiagramError(
                "La nullabilité d'un attribut doit être booléenne ou automatique."
            )
        if self.default is not None and not isinstance(self.default, str):
            raise DiagramError("La valeur par défaut doit être textuelle.")
        if not isinstance(self.unique, bool):
            raise DiagramError("Le statut UNIQUE doit être booléen.")
        if not isinstance(self.comment, str):
            raise DiagramError("Le commentaire d'un attribut doit être textuel.")
        if not isinstance(self.auto_increment, bool):
            raise DiagramError("Le statut d'auto-incrémentation doit être booléen.")
        if not isinstance(self.constraints, tuple):
            self.constraints = tuple(self.constraints)
        if not all(isinstance(expression, str) for expression in self.constraints):
            raise DiagramError("Les contraintes d'un attribut doivent être textuelles.")
        self.default = (
            self.default.strip() or None if self.default is not None else None
        )
        self.comment = self.comment.strip()
        self.constraints = tuple(
            expression.strip() for expression in self.constraints if expression.strip()
        )


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


@dataclass(slots=True, init=False)
class Association:
    """Association MERISE, éventuellement porteuse d'attributs."""

    name: str
    position: Position = field(default_factory=Position)
    id: str = field(default_factory=_new_id)
    attributes: list[Attribute] = field(default_factory=list)
    is_historized: bool = False
    materialization_strategy: MaterializationStrategy = MaterializationStrategy.AUTO

    def __init__(
        self,
        name: str,
        position: Position = _ORIGIN,
        id: str | None = None,
        attributes: list[Attribute] | None = None,
        is_historized: bool = False,
        materialization_strategy: MaterializationStrategy | str = (
            MaterializationStrategy.AUTO
        ),
    ) -> None:
        self.name = name
        self.position = position
        self.id = _new_id() if id is None else id
        self.attributes = [] if attributes is None else attributes
        self.is_historized = is_historized
        try:
            self.materialization_strategy = MaterializationStrategy(
                materialization_strategy
            )
        except (TypeError, ValueError) as error:
            raise DiagramError(
                "Stratégie de matérialisation invalide : "
                "AUTO, FORCE_TABLE ou FORCE_FK attendu."
            ) from error
        self.__post_init__()

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
    cardinality: Cardinality | None = field(default_factory=lambda: DEFAULT_CARDINALITY)
    role: str = ""

    def __post_init__(self) -> None:
        _validate_internal_id(self.id, "la relation")
        _validate_internal_id(self.entity_id, "l'entité référencée")
        _validate_internal_id(self.association_id, "l'association référencée")
        if self.cardinality is not None and not isinstance(
            self.cardinality, Cardinality
        ):
            raise DiagramError("La cardinalité d'une relation est invalide.")
        if not isinstance(self.role, str):
            raise DiagramError("Le rôle d'une relation doit être une chaîne.")
        self.role = self.role.strip()


@dataclass(slots=True, init=False)
class Inheritance:
    """Spécialisation ISA d'une entité mère vers une ou plusieurs filles."""

    parent_entity_id: str
    child_entity_ids: tuple[str, ...]
    strategy: InheritanceStrategy = InheritanceStrategy.JOINED
    id: str = field(default_factory=_new_id)

    def __init__(
        self,
        parent_entity_id: str,
        child_entity_ids: tuple[str, ...],
        strategy: InheritanceStrategy | str = InheritanceStrategy.JOINED,
        id: str | None = None,
    ) -> None:
        self.parent_entity_id = parent_entity_id
        self.child_entity_ids = tuple(child_entity_ids)
        try:
            self.strategy = InheritanceStrategy(strategy)
        except (TypeError, ValueError) as error:
            raise DiagramError(
                "Stratégie d'héritage invalide : PARENT_ONLY, CHILDREN_ONLY "
                "ou JOINED attendu."
            ) from error
        self.id = _new_id() if id is None else id
        self.__post_init__()

    def __post_init__(self) -> None:
        _validate_internal_id(self.id, "l'héritage")
        _validate_internal_id(self.parent_entity_id, "l'entité mère")
        if not isinstance(self.child_entity_ids, tuple):
            self.child_entity_ids = tuple(self.child_entity_ids)
        if not self.child_entity_ids:
            raise DiagramError("Un héritage doit posséder au moins une entité fille.")
        for child_id in self.child_entity_ids:
            _validate_internal_id(child_id, "l'entité fille")


@dataclass(frozen=True, slots=True, init=False)
class FunctionalDependency:
    """Dépendance fonctionnelle X → Y déclarée sur un même objet métier."""

    owner_id: str
    determinant_attribute_ids: tuple[str, ...]
    dependent_attribute_ids: tuple[str, ...]
    origin: FunctionalDependencyOrigin
    id: str

    def __init__(
        self,
        owner_id: str,
        determinant_attribute_ids: Iterable[str],
        dependent_attribute_ids: Iterable[str],
        origin: FunctionalDependencyOrigin | str = FunctionalDependencyOrigin.USER,
        id: str | None = None,
    ) -> None:
        determinants = tuple(determinant_attribute_ids)
        dependents = tuple(dependent_attribute_ids)
        _validate_internal_id(owner_id, "l'objet porteur")
        dependency_id = _new_id() if id is None else id
        _validate_internal_id(dependency_id, "la dépendance fonctionnelle")
        if not determinants or not dependents:
            raise DiagramError(
                "Une dépendance fonctionnelle doit avoir un déterminant et une cible."
            )
        if len(determinants) != len(set(determinants)) or len(dependents) != len(
            set(dependents)
        ):
            raise DiagramError(
                "Une dépendance fonctionnelle contient un attribut dupliqué."
            )
        for attribute_id in (*determinants, *dependents):
            _validate_internal_id(attribute_id, "l'attribut référencé")
        if set(determinants) & set(dependents):
            raise DiagramError(
                "Le déterminant et la cible d'une dépendance doivent être disjoints."
            )
        try:
            normalized_origin = FunctionalDependencyOrigin(origin)
        except (TypeError, ValueError) as error:
            raise DiagramError(
                "Origine de dépendance invalide : USER ou AI attendu."
            ) from error
        object.__setattr__(self, "owner_id", owner_id)
        object.__setattr__(self, "determinant_attribute_ids", determinants)
        object.__setattr__(self, "dependent_attribute_ids", dependents)
        object.__setattr__(self, "origin", normalized_origin)
        object.__setattr__(self, "id", dependency_id)


@dataclass(slots=True)
class ModelDomain:
    """Regroupement thématique réutilisable dans plusieurs vues."""

    name: str
    node_ids: tuple[str, ...] = ()
    id: str = field(default_factory=_new_id)
    description: str = ""

    def __post_init__(self) -> None:
        _validate_internal_id(self.id, "ce domaine")
        _validate_name_type(self.name, "ce domaine")
        self.name = self.name.strip()
        if not self.name:
            raise DiagramError("Le nom d'un domaine est obligatoire.")
        if not isinstance(self.node_ids, tuple):
            self.node_ids = tuple(self.node_ids)
        if len(self.node_ids) != len(set(self.node_ids)):
            raise DiagramError("Un domaine contient un objet dupliqué.")
        for node_id in self.node_ids:
            _validate_internal_id(node_id, "l'objet du domaine")
        if not isinstance(self.description, str):
            raise DiagramError("La description d'un domaine doit être textuelle.")
        self.description = self.description.strip()


@dataclass(slots=True, init=False)
class SubmodelView:
    """Vue métier ou technique composée de domaines et d'objets explicites."""

    name: str
    kind: SubmodelViewKind
    domain_ids: tuple[str, ...]
    node_ids: tuple[str, ...]
    id: str

    def __init__(
        self,
        name: str,
        kind: SubmodelViewKind | str,
        domain_ids: Iterable[str] = (),
        node_ids: Iterable[str] = (),
        id: str | None = None,
    ) -> None:
        self.name = name
        try:
            self.kind = SubmodelViewKind(kind)
        except (TypeError, ValueError) as error:
            raise DiagramError(
                "Le type de vue doit valoir BUSINESS ou TECHNICAL."
            ) from error
        self.domain_ids = tuple(domain_ids)
        self.node_ids = tuple(node_ids)
        self.id = _new_id() if id is None else id
        self.__post_init__()

    def __post_init__(self) -> None:
        _validate_internal_id(self.id, "cette vue")
        _validate_name_type(self.name, "cette vue")
        self.name = self.name.strip()
        if not self.name:
            raise DiagramError("Le nom d'une vue est obligatoire.")
        if len(self.domain_ids) != len(set(self.domain_ids)):
            raise DiagramError("Une vue contient un domaine dupliqué.")
        if len(self.node_ids) != len(set(self.node_ids)):
            raise DiagramError("Une vue contient un objet dupliqué.")
        for domain_id in self.domain_ids:
            _validate_internal_id(domain_id, "ce domaine référencé")
        for node_id in self.node_ids:
            _validate_internal_id(node_id, "l'objet de la vue")


Node = Entity | Association


class MCDModel:
    """Agrégat racine garantissant les références internes du MCD."""

    def __init__(self) -> None:
        self.entities: dict[str, Entity] = {}
        self.associations: dict[str, Association] = {}
        self.relations: dict[str, Relation] = {}
        self.inheritances: dict[str, Inheritance] = {}
        self.functional_dependencies: dict[str, FunctionalDependency] = {}
        self.domains: dict[str, ModelDomain] = {}
        self.submodel_views: dict[str, SubmodelView] = {}

    def _all_ids(self) -> set[str]:
        attribute_ids = {
            attribute.id
            for entity in self.entities.values()
            for attribute in entity.attributes
        } | {
            attribute.id
            for association in self.associations.values()
            for attribute in association.attributes
        }
        return (
            set(self.entities)
            | set(self.associations)
            | set(self.relations)
            | set(self.inheritances)
            | set(self.functional_dependencies)
            | set(self.domains)
            | set(self.submodel_views)
            | attribute_ids
        )

    def _ensure_available_ids(self, ids: Iterable[str]) -> None:
        candidate_ids = list(ids)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise DiagramError("Un objet contient des identifiants internes dupliqués.")
        existing = self._all_ids()
        conflict = next(
            (item_id for item_id in candidate_ids if item_id in existing), None
        )
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
        role: str = "",
    ) -> Relation:
        relation = Relation(
            entity_id=entity_id,
            association_id=association_id,
            cardinality=cardinality,
            role=role,
        )
        self.add_relation(relation)
        return relation

    def create_attribute(
        self,
        owner_id: str,
        name: str,
        identifier: bool = False,
        data_type: MLDDataType | None = None,
        nullable: bool | None = None,
        default: str | None = None,
        unique: bool = False,
        comment: str = "",
        auto_increment: bool = False,
        constraints: Iterable[str] = (),
    ) -> Attribute:
        attribute = Attribute(
            name=name,
            identifier=identifier,
            data_type=data_type,
            nullable=nullable,
            default=default,
            unique=unique,
            comment=comment,
            auto_increment=auto_increment,
            constraints=tuple(constraints),
        )
        self.add_attribute(owner_id, attribute)
        return attribute

    def create_inheritance(
        self,
        parent_entity_id: str,
        child_entity_ids: Iterable[str],
        strategy: InheritanceStrategy | str = InheritanceStrategy.JOINED,
    ) -> Inheritance:
        inheritance = Inheritance(
            parent_entity_id,
            tuple(child_entity_ids),
            strategy,
        )
        self.add_inheritance(inheritance)
        return inheritance

    def create_functional_dependency(
        self,
        owner_id: str,
        determinant_attribute_ids: Iterable[str],
        dependent_attribute_ids: Iterable[str],
        origin: FunctionalDependencyOrigin | str = FunctionalDependencyOrigin.USER,
    ) -> FunctionalDependency:
        dependency = FunctionalDependency(
            owner_id,
            determinant_attribute_ids,
            dependent_attribute_ids,
            origin,
        )
        self.add_functional_dependency(dependency)
        return dependency

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
        self.relations[relation.id] = relation

    def add_inheritance(self, inheritance: Inheritance) -> None:
        self._ensure_available_ids([inheritance.id])
        if inheritance.parent_entity_id not in self.entities:
            raise DiagramError(f"Entité mère inconnue : {inheritance.parent_entity_id}")
        if inheritance.parent_entity_id in inheritance.child_entity_ids:
            raise DiagramError("Une entité ne peut pas hériter d'elle-même.")
        if len(set(inheritance.child_entity_ids)) != len(inheritance.child_entity_ids):
            raise DiagramError("Un héritage contient une entité fille dupliquée.")
        unknown = next(
            (
                child_id
                for child_id in inheritance.child_entity_ids
                if child_id not in self.entities
            ),
            None,
        )
        if unknown is not None:
            raise DiagramError(f"Entité fille inconnue : {unknown}")
        self.inheritances[inheritance.id] = inheritance

    def add_functional_dependency(self, dependency: FunctionalDependency) -> None:
        self._ensure_available_ids([dependency.id])
        owner = self.node(dependency.owner_id)
        owner_attribute_ids = {attribute.id for attribute in owner.attributes}
        referenced_ids = set(dependency.determinant_attribute_ids) | set(
            dependency.dependent_attribute_ids
        )
        unknown = referenced_ids - owner_attribute_ids
        if unknown:
            raise DiagramError(
                "Une dépendance fonctionnelle référence un attribut inconnu : "
                f"{sorted(unknown)[0]}"
            )
        signature = (
            frozenset(dependency.determinant_attribute_ids),
            frozenset(dependency.dependent_attribute_ids),
        )
        if any(
            item.owner_id == dependency.owner_id
            and (
                frozenset(item.determinant_attribute_ids),
                frozenset(item.dependent_attribute_ids),
            )
            == signature
            for item in self.functional_dependencies.values()
        ):
            raise DiagramError("Cette dépendance fonctionnelle existe déjà.")
        self.functional_dependencies[dependency.id] = dependency

    def add_domain(self, domain: ModelDomain) -> None:
        self._ensure_available_ids([domain.id])
        if any(
            item.name.casefold() == domain.name.casefold()
            for item in self.domains.values()
        ):
            raise DiagramError(f"Domaine déjà présent : {domain.name}")
        unknown = set(domain.node_ids) - (set(self.entities) | set(self.associations))
        if unknown:
            raise DiagramError(
                f"Le domaine référence un objet inconnu : {sorted(unknown)[0]}"
            )
        self.domains[domain.id] = domain

    def add_submodel_view(self, view: SubmodelView) -> None:
        self._ensure_available_ids([view.id])
        if any(
            item.name.casefold() == view.name.casefold()
            for item in self.submodel_views.values()
        ):
            raise DiagramError(f"Vue déjà présente : {view.name}")
        unknown_domains = set(view.domain_ids) - set(self.domains)
        if unknown_domains:
            raise DiagramError(
                f"La vue référence un domaine inconnu : {sorted(unknown_domains)[0]}"
            )
        unknown_nodes = set(view.node_ids) - (
            set(self.entities) | set(self.associations)
        )
        if unknown_nodes:
            raise DiagramError(
                f"La vue référence un objet inconnu : {sorted(unknown_nodes)[0]}"
            )
        self.submodel_views[view.id] = view

    def replace_submodels(
        self,
        domains: Iterable[ModelDomain],
        views: Iterable[SubmodelView],
    ) -> None:
        domain_values = list(domains)
        view_values = list(views)
        domain_names = [domain.name.casefold() for domain in domain_values]
        view_names = [view.name.casefold() for view in view_values]
        if len(domain_names) != len(set(domain_names)):
            raise DiagramError("Deux domaines ne peuvent pas porter le même nom.")
        if len(view_names) != len(set(view_names)):
            raise DiagramError("Deux vues ne peuvent pas porter le même nom.")
        previous_domains = self.domains
        previous_views = self.submodel_views
        self.domains = {}
        self.submodel_views = {}
        try:
            for domain in domain_values:
                self.add_domain(domain)
            for view in view_values:
                self.add_submodel_view(view)
        except DiagramError:
            self.domains = previous_domains
            self.submodel_views = previous_views
            raise

    def replace_functional_dependency(
        self, dependency_id: str, replacement: FunctionalDependency
    ) -> None:
        if dependency_id not in self.functional_dependencies:
            raise DiagramError(f"Dépendance fonctionnelle inconnue : {dependency_id}")
        if replacement.id != dependency_id:
            raise DiagramError(
                "L'identifiant d'une dépendance ne peut pas être modifié."
            )
        previous = self.functional_dependencies.pop(dependency_id)
        try:
            self.add_functional_dependency(replacement)
        except DiagramError:
            self.functional_dependencies[dependency_id] = previous
            raise

    def add_attribute(
        self, owner_id: str, attribute: Attribute, index: int | None = None
    ) -> None:
        self._ensure_available_ids([attribute.id])
        owner = self.node(owner_id)
        if index is None:
            owner.attributes.append(attribute)
        else:
            owner.attributes.insert(index, attribute)

    def remove_attribute(
        self, owner_id: str, attribute_id: str
    ) -> tuple[Attribute, int]:
        owner = self.node(owner_id)
        for index, attribute in enumerate(owner.attributes):
            if attribute.id == attribute_id:
                removed = owner.attributes.pop(index)
                for dependency_id, dependency in list(
                    self.functional_dependencies.items()
                ):
                    if attribute_id in (
                        *dependency.determinant_attribute_ids,
                        *dependency.dependent_attribute_ids,
                    ):
                        del self.functional_dependencies[dependency_id]
                return removed, index
        raise DiagramError(f"Attribut inconnu : {attribute_id}")

    def attribute(self, owner_id: str, attribute_id: str) -> Attribute:
        owner = self.node(owner_id)
        for attribute in owner.attributes:
            if attribute.id == attribute_id:
                return attribute
        raise DiagramError(f"Attribut inconnu : {attribute_id}")

    def replace_attribute(self, owner_id: str, replacement: Attribute) -> None:
        current = self.attribute(owner_id, replacement.id)
        replacement.__post_init__()
        current.name = replacement.name
        current.identifier = replacement.identifier
        current.data_type = replacement.data_type
        current.nullable = replacement.nullable
        current.default = replacement.default
        current.unique = replacement.unique
        current.comment = replacement.comment
        current.auto_increment = replacement.auto_increment
        current.constraints = replacement.constraints

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

    def set_attribute_data_type(
        self,
        owner_id: str,
        attribute_id: str,
        data_type: MLDDataType | None,
    ) -> None:
        if data_type is not None and not isinstance(data_type, MLDDataType):
            raise DiagramError(
                "Le type explicite d'un attribut doit être un type logique MLD."
            )
        self.attribute(owner_id, attribute_id).data_type = data_type

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

    def set_relation_role(self, relation_id: str, role: str) -> None:
        if not isinstance(role, str):
            raise DiagramError("Le rôle d'une relation doit être une chaîne.")
        try:
            self.relations[relation_id].role = role.strip()
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

    def functional_dependencies_for(self, owner_id: str) -> list[FunctionalDependency]:
        self.node(owner_id)
        return sorted(
            (
                dependency
                for dependency in self.functional_dependencies.values()
                if dependency.owner_id == owner_id
            ),
            key=lambda dependency: dependency.id,
        )

    def remove_functional_dependency(self, dependency_id: str) -> FunctionalDependency:
        try:
            return self.functional_dependencies.pop(dependency_id)
        except KeyError as error:
            raise DiagramError(
                f"Dépendance fonctionnelle inconnue : {dependency_id}"
            ) from error

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
        for inheritance_id, inheritance in list(self.inheritances.items()):
            if (
                inheritance.parent_entity_id == entity_id
                or entity_id in inheritance.child_entity_ids
            ):
                del self.inheritances[inheritance_id]
        self._remove_owner_dependencies(entity_id)
        self._remove_node_from_submodels(entity_id)
        return self.entities.pop(entity_id), relations

    def remove_association(
        self, association_id: str
    ) -> tuple[Association, list[Relation]]:
        if association_id not in self.associations:
            raise DiagramError(f"Association inconnue : {association_id}")
        relations = self.connected_relations(association_id)
        for relation in relations:
            del self.relations[relation.id]
        self._remove_owner_dependencies(association_id)
        self._remove_node_from_submodels(association_id)
        return self.associations.pop(association_id), relations

    def _remove_owner_dependencies(self, owner_id: str) -> None:
        for dependency_id, dependency in list(self.functional_dependencies.items()):
            if dependency.owner_id == owner_id:
                del self.functional_dependencies[dependency_id]

    def _remove_node_from_submodels(self, node_id: str) -> None:
        for domain in self.domains.values():
            domain.node_ids = tuple(
                item_id for item_id in domain.node_ids if item_id != node_id
            )
        for view in self.submodel_views.values():
            view.node_ids = tuple(
                item_id for item_id in view.node_ids if item_id != node_id
            )

    def node(self, element_id: str) -> Node:
        if element_id in self.entities:
            return self.entities[element_id]
        if element_id in self.associations:
            return self.associations[element_id]
        raise DiagramError(f"Nœud inconnu : {element_id}")

    def element(self, element_id: str) -> Node | Relation | Inheritance:
        if element_id in self.entities:
            return self.entities[element_id]
        if element_id in self.associations:
            return self.associations[element_id]
        if element_id in self.relations:
            return self.relations[element_id]
        if element_id in self.inheritances:
            return self.inheritances[element_id]
        raise DiagramError(f"Élément inconnu : {element_id}")


# Nom historique conservé pour les extensions et fichiers clients de la V0.1.
DiagramModel = MCDModel
