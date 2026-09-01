"""Commandes annulables de l'éditeur MCD."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Protocol

from PySide6.QtGui import QUndoCommand

from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    Entity,
    FunctionalDependency,
    Inheritance,
    MaterializationStrategy,
    MCDModel,
    MLDDataType,
    ModelDomain,
    Position,
    Relation,
    SubmodelView,
)


@dataclass(frozen=True, slots=True)
class DeletionSnapshot:
    """Éléments nécessaires pour annuler une suppression en cascade."""

    entities: tuple[Entity, ...]
    associations: tuple[Association, ...]
    relations: tuple[Relation, ...]
    inheritances: tuple[Inheritance, ...] = ()
    functional_dependencies: tuple[FunctionalDependency, ...] = ()
    domains: tuple[ModelDomain, ...] = ()
    submodel_views: tuple[SubmodelView, ...] = ()

    @property
    def empty(self) -> bool:
        return not (
            self.entities
            or self.associations
            or self.relations
            or self.inheritances
            or self.functional_dependencies
        )


class CommandTarget(Protocol):
    def command_insert_node(self, node: Entity | Association) -> None: ...

    def command_remove_node(self, node_id: str) -> None: ...

    def command_insert_relation(self, relation: Relation) -> None: ...

    def command_remove_relation(self, relation_id: str) -> None: ...

    def command_insert_inheritance(self, inheritance: Inheritance) -> None: ...

    def command_remove_inheritance(self, inheritance_id: str) -> None: ...

    def command_insert_functional_dependency(
        self, dependency: FunctionalDependency
    ) -> None: ...

    def command_remove_functional_dependency(self, dependency_id: str) -> None: ...

    def command_replace_functional_dependency(
        self, dependency_id: str, replacement: FunctionalDependency
    ) -> None: ...

    def command_replace_model_state(self, model: MCDModel) -> None: ...

    def command_replace_submodels(
        self,
        domains: tuple[ModelDomain, ...],
        views: tuple[SubmodelView, ...],
    ) -> None: ...

    def command_move_node(self, node_id: str, position: Position) -> None: ...

    def command_remove_snapshot(self, snapshot: DeletionSnapshot) -> None: ...

    def command_restore_snapshot(self, snapshot: DeletionSnapshot) -> None: ...

    def command_rename_node(self, node_id: str, name: str) -> None: ...

    def command_insert_attribute(
        self, owner_id: str, attribute: Attribute, index: int
    ) -> None: ...

    def command_remove_attribute(self, owner_id: str, attribute_id: str) -> None: ...

    def command_replace_attribute(
        self, owner_id: str, replacement: Attribute
    ) -> None: ...

    def command_rename_attribute(
        self, owner_id: str, attribute_id: str, name: str
    ) -> None: ...

    def command_set_identifier(
        self, owner_id: str, attribute_id: str, identifier: bool
    ) -> None: ...

    def command_set_attribute_data_type(
        self,
        owner_id: str,
        attribute_id: str,
        data_type: MLDDataType | None,
    ) -> None: ...

    def command_set_cardinality(
        self, relation_id: str, cardinality: Cardinality | None
    ) -> None: ...

    def command_set_relation_role(self, relation_id: str, role: str) -> None: ...

    def command_set_association_historized(
        self, association_id: str, is_historized: bool
    ) -> None: ...

    def command_set_association_materialization_strategy(
        self, association_id: str, strategy: MaterializationStrategy
    ) -> None: ...


class AddNodeCommand(QUndoCommand):
    def __init__(self, target: CommandTarget, node: Entity | Association) -> None:
        label = (
            "Ajouter une entité"
            if isinstance(node, Entity)
            else "Ajouter une association"
        )
        super().__init__(label)
        self._target = target
        self._node = node

    def redo(self) -> None:
        self._target.command_insert_node(self._node)

    def undo(self) -> None:
        self._target.command_remove_node(self._node.id)


class AddRelationCommand(QUndoCommand):
    def __init__(self, target: CommandTarget, relation: Relation) -> None:
        super().__init__("Créer une relation")
        self._target = target
        self._relation = relation

    def redo(self) -> None:
        self._target.command_insert_relation(self._relation)

    def undo(self) -> None:
        self._target.command_remove_relation(self._relation.id)


class AddInheritanceCommand(QUndoCommand):
    def __init__(self, target: CommandTarget, inheritance: Inheritance) -> None:
        super().__init__("Ajouter une spécialisation ISA")
        self._target = target
        self._inheritance = inheritance

    def redo(self) -> None:
        self._target.command_insert_inheritance(self._inheritance)

    def undo(self) -> None:
        self._target.command_remove_inheritance(self._inheritance.id)


class AddFunctionalDependencyCommand(QUndoCommand):
    def __init__(self, target: CommandTarget, dependency: FunctionalDependency) -> None:
        super().__init__("Ajouter une dépendance fonctionnelle")
        self._target = target
        self._dependency = dependency

    def redo(self) -> None:
        self._target.command_insert_functional_dependency(self._dependency)

    def undo(self) -> None:
        self._target.command_remove_functional_dependency(self._dependency.id)


class RemoveFunctionalDependencyCommand(QUndoCommand):
    def __init__(self, target: CommandTarget, dependency: FunctionalDependency) -> None:
        super().__init__("Supprimer une dépendance fonctionnelle")
        self._target = target
        self._dependency = dependency

    def redo(self) -> None:
        self._target.command_remove_functional_dependency(self._dependency.id)

    def undo(self) -> None:
        self._target.command_insert_functional_dependency(self._dependency)


class ReplaceFunctionalDependencyCommand(QUndoCommand):
    def __init__(
        self,
        target: CommandTarget,
        old_value: FunctionalDependency,
        new_value: FunctionalDependency,
    ) -> None:
        super().__init__("Modifier une dépendance fonctionnelle")
        self._target = target
        self._old_value = old_value
        self._new_value = new_value

    def redo(self) -> None:
        self._target.command_replace_functional_dependency(
            self._old_value.id, self._new_value
        )

    def undo(self) -> None:
        self._target.command_replace_functional_dependency(
            self._new_value.id, self._old_value
        )


class ReplaceModelStateCommand(QUndoCommand):
    """Applique une décomposition complète comme une seule opération annulable."""

    def __init__(
        self,
        target: CommandTarget,
        old_model: MCDModel,
        new_model: MCDModel,
        label: str = "Appliquer la décomposition normalisée",
    ) -> None:
        super().__init__(label)
        self._target = target
        self._old_model = copy.deepcopy(old_model)
        self._new_model = copy.deepcopy(new_model)

    def redo(self) -> None:
        self._target.command_replace_model_state(copy.deepcopy(self._new_model))

    def undo(self) -> None:
        self._target.command_replace_model_state(copy.deepcopy(self._old_model))


class ReplaceSubmodelsCommand(QUndoCommand):
    """Remplace uniquement les métadonnées de vues, sans invalider le MLD."""

    def __init__(
        self,
        target: CommandTarget,
        old_domains: tuple[ModelDomain, ...],
        old_views: tuple[SubmodelView, ...],
        new_domains: tuple[ModelDomain, ...],
        new_views: tuple[SubmodelView, ...],
    ) -> None:
        super().__init__("Modifier les domaines et sous-modèles")
        self._target = target
        self._old_domains = copy.deepcopy(old_domains)
        self._old_views = copy.deepcopy(old_views)
        self._new_domains = copy.deepcopy(new_domains)
        self._new_views = copy.deepcopy(new_views)

    def redo(self) -> None:
        self._target.command_replace_submodels(
            copy.deepcopy(self._new_domains), copy.deepcopy(self._new_views)
        )

    def undo(self) -> None:
        self._target.command_replace_submodels(
            copy.deepcopy(self._old_domains), copy.deepcopy(self._old_views)
        )


class MoveNodeCommand(QUndoCommand):
    def __init__(
        self,
        target: CommandTarget,
        node_id: str,
        old_position: Position,
        new_position: Position,
    ) -> None:
        super().__init__("Déplacer un objet")
        self._target = target
        self._node_id = node_id
        self._old_position = old_position
        self._new_position = new_position

    def redo(self) -> None:
        self._target.command_move_node(self._node_id, self._new_position)

    def undo(self) -> None:
        self._target.command_move_node(self._node_id, self._old_position)


class DeleteItemsCommand(QUndoCommand):
    def __init__(self, target: CommandTarget, snapshot: DeletionSnapshot) -> None:
        super().__init__("Supprimer la sélection")
        self._target = target
        self._snapshot = snapshot

    def redo(self) -> None:
        self._target.command_remove_snapshot(self._snapshot)

    def undo(self) -> None:
        self._target.command_restore_snapshot(self._snapshot)


class RenameNodeCommand(QUndoCommand):
    def __init__(
        self, target: CommandTarget, node_id: str, old_name: str, new_name: str
    ) -> None:
        super().__init__("Renommer un objet")
        self._target = target
        self._node_id = node_id
        self._old_name = old_name
        self._new_name = new_name

    def redo(self) -> None:
        self._target.command_rename_node(self._node_id, self._new_name)

    def undo(self) -> None:
        self._target.command_rename_node(self._node_id, self._old_name)


class AddAttributeCommand(QUndoCommand):
    def __init__(
        self,
        target: CommandTarget,
        owner_id: str,
        attribute: Attribute,
        index: int,
    ) -> None:
        super().__init__("Ajouter un attribut")
        self._target = target
        self._owner_id = owner_id
        self._attribute = attribute
        self._index = index

    def redo(self) -> None:
        self._target.command_insert_attribute(
            self._owner_id, self._attribute, self._index
        )

    def undo(self) -> None:
        self._target.command_remove_attribute(self._owner_id, self._attribute.id)


class RemoveAttributeCommand(QUndoCommand):
    def __init__(
        self,
        target: CommandTarget,
        owner_id: str,
        attribute: Attribute,
        index: int,
        dependencies: tuple[FunctionalDependency, ...] = (),
    ) -> None:
        super().__init__("Supprimer un attribut")
        self._target = target
        self._owner_id = owner_id
        self._attribute = attribute
        self._index = index
        self._dependencies = dependencies

    def redo(self) -> None:
        self._target.command_remove_attribute(self._owner_id, self._attribute.id)

    def undo(self) -> None:
        self._target.command_insert_attribute(
            self._owner_id, self._attribute, self._index
        )
        for dependency in self._dependencies:
            self._target.command_insert_functional_dependency(dependency)


class RenameAttributeCommand(QUndoCommand):
    def __init__(
        self,
        target: CommandTarget,
        owner_id: str,
        attribute_id: str,
        old_name: str,
        new_name: str,
    ) -> None:
        super().__init__("Renommer un attribut")
        self._target = target
        self._owner_id = owner_id
        self._attribute_id = attribute_id
        self._old_name = old_name
        self._new_name = new_name

    def redo(self) -> None:
        self._target.command_rename_attribute(
            self._owner_id, self._attribute_id, self._new_name
        )

    def undo(self) -> None:
        self._target.command_rename_attribute(
            self._owner_id, self._attribute_id, self._old_name
        )


class ReplaceAttributeCommand(QUndoCommand):
    """Remplace toutes les propriétés d'un attribut en une opération."""

    def __init__(
        self,
        target: CommandTarget,
        owner_id: str,
        old_value: Attribute,
        new_value: Attribute,
    ) -> None:
        super().__init__("Modifier les propriétés d'un attribut")
        self._target = target
        self._owner_id = owner_id
        self._old_value = old_value
        self._new_value = new_value

    def redo(self) -> None:
        self._target.command_replace_attribute(self._owner_id, self._new_value)

    def undo(self) -> None:
        self._target.command_replace_attribute(self._owner_id, self._old_value)


class SetIdentifierCommand(QUndoCommand):
    def __init__(
        self,
        target: CommandTarget,
        owner_id: str,
        attribute_id: str,
        old_value: bool,
        new_value: bool,
    ) -> None:
        super().__init__("Modifier l'identifiant")
        self._target = target
        self._owner_id = owner_id
        self._attribute_id = attribute_id
        self._old_value = old_value
        self._new_value = new_value

    def redo(self) -> None:
        self._target.command_set_identifier(
            self._owner_id, self._attribute_id, self._new_value
        )

    def undo(self) -> None:
        self._target.command_set_identifier(
            self._owner_id, self._attribute_id, self._old_value
        )


class SetAttributeDataTypeCommand(QUndoCommand):
    def __init__(
        self,
        target: CommandTarget,
        owner_id: str,
        attribute_id: str,
        old_value: MLDDataType | None,
        new_value: MLDDataType | None,
    ) -> None:
        super().__init__("Modifier le type d'un attribut")
        self._target = target
        self._owner_id = owner_id
        self._attribute_id = attribute_id
        self._old_value = old_value
        self._new_value = new_value

    def redo(self) -> None:
        self._target.command_set_attribute_data_type(
            self._owner_id, self._attribute_id, self._new_value
        )

    def undo(self) -> None:
        self._target.command_set_attribute_data_type(
            self._owner_id, self._attribute_id, self._old_value
        )


class SetCardinalityCommand(QUndoCommand):
    def __init__(
        self,
        target: CommandTarget,
        relation_id: str,
        old_value: Cardinality | None,
        new_value: Cardinality | None,
    ) -> None:
        super().__init__("Modifier une cardinalité")
        self._target = target
        self._relation_id = relation_id
        self._old_value = old_value
        self._new_value = new_value

    def redo(self) -> None:
        self._target.command_set_cardinality(self._relation_id, self._new_value)

    def undo(self) -> None:
        self._target.command_set_cardinality(self._relation_id, self._old_value)


class SetRelationRoleCommand(QUndoCommand):
    def __init__(
        self,
        target: CommandTarget,
        relation_id: str,
        old_value: str,
        new_value: str,
    ) -> None:
        super().__init__("Modifier le rôle d'une relation")
        self._target = target
        self._relation_id = relation_id
        self._old_value = old_value
        self._new_value = new_value

    def redo(self) -> None:
        self._target.command_set_relation_role(self._relation_id, self._new_value)

    def undo(self) -> None:
        self._target.command_set_relation_role(self._relation_id, self._old_value)


class SetAssociationHistorizedCommand(QUndoCommand):
    def __init__(
        self,
        target: CommandTarget,
        association_id: str,
        old_value: bool,
        new_value: bool,
    ) -> None:
        super().__init__("Modifier l'historisation")
        self._target = target
        self._association_id = association_id
        self._old_value = old_value
        self._new_value = new_value

    def redo(self) -> None:
        self._target.command_set_association_historized(
            self._association_id, self._new_value
        )

    def undo(self) -> None:
        self._target.command_set_association_historized(
            self._association_id, self._old_value
        )


class SetAssociationMaterializationStrategyCommand(QUndoCommand):
    def __init__(
        self,
        target: CommandTarget,
        association_id: str,
        old_value: MaterializationStrategy,
        new_value: MaterializationStrategy,
    ) -> None:
        super().__init__("Modifier la matérialisation")
        self._target = target
        self._association_id = association_id
        self._old_value = old_value
        self._new_value = new_value

    def redo(self) -> None:
        self._target.command_set_association_materialization_strategy(
            self._association_id, self._new_value
        )

    def undo(self) -> None:
        self._target.command_set_association_materialization_strategy(
            self._association_id, self._old_value
        )
