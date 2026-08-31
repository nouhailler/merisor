"""Contrôleur principal : commandes, modèle, vue et document courant."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, Signal, Slot
from PySide6.QtGui import QUndoStack

from merisor.application.commands import (
    AddAttributeCommand,
    AddInheritanceCommand,
    AddNodeCommand,
    AddRelationCommand,
    DeleteItemsCommand,
    DeletionSnapshot,
    MoveNodeCommand,
    RemoveAttributeCommand,
    RenameAttributeCommand,
    RenameNodeCommand,
    SetAssociationHistorizedCommand,
    SetAssociationMaterializationStrategyCommand,
    SetAttributeDataTypeCommand,
    SetCardinalityCommand,
    SetIdentifierCommand,
    SetRelationRoleCommand,
)
from merisor.application.mld_transformer import (
    McdToMldTransformer,
    mcd_logical_fingerprint,
)
from merisor.application.mcd_layout import McdAutoLayout
from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    DEFAULT_CARDINALITY,
    DiagramError,
    Entity,
    Inheritance,
    InheritanceStrategy,
    MCDModel,
    MLDModel,
    MLDDataType,
    MaterializationStrategy,
    Position,
    Relation,
    ValidationReport,
    validate_mcd,
)
from merisor.persistence import JsonDiagramRepository
from merisor.ui.canvas import DiagramScene
from merisor.ui.items import (
    AssociationGraphicsItem,
    EntityGraphicsItem,
    InheritanceGraphicsItem,
    NodeGraphicsItem,
    RelationGraphicsItem,
)


class MLDGenerationBlocked(ValueError):
    """La validation métier interdit de lancer le transformateur."""

    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        super().__init__(
            f"Impossible de générer le MLD : {len(report.errors)} erreur(s)."
        )


class DiagramController(QObject):
    """Façade applicative et unique synchronisateur modèle–scène."""

    model_changed = Signal()
    selection_changed = Signal(object)
    dirty_changed = Signal(bool)
    document_path_changed = Signal(object)
    message = Signal(str)
    mld_changed = Signal(object)
    mld_stale_changed = Signal(bool)

    def __init__(self, scene: DiagramScene, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.scene = scene
        self.model = MCDModel()
        self.repository = JsonDiagramRepository()
        self.mld_transformer = McdToMldTransformer()
        self.mcd_layout = McdAutoLayout()
        self.mld_model: MLDModel | None = None
        self.undo_stack = QUndoStack(self)
        self.document_path: Path | None = None
        self._node_items: dict[str, NodeGraphicsItem] = {}
        self._relation_items: dict[str, RelationGraphicsItem] = {}
        self._inheritance_items: dict[str, InheritanceGraphicsItem] = {}

        self.undo_stack.cleanChanged.connect(self._undo_clean_changed)
        self.scene.selectionChanged.connect(self._emit_selection)
        self.scene.relation_creation_requested.connect(self.create_relation)

    @Slot(bool)
    def _undo_clean_changed(self, clean: bool) -> None:
        self.dirty_changed.emit(not clean)

    @property
    def is_dirty(self) -> bool:
        return not self.undo_stack.isClean()

    def create_entity(self, name: str | None, point: QPointF) -> Entity:
        clean_name = name.strip() if isinstance(name, str) else ""
        if not clean_name:
            clean_name = self._next_name(
                "Entité", (item.name for item in self.model.entities.values())
            )
        entity = Entity(clean_name, Position(point.x(), point.y()))
        self.undo_stack.push(AddNodeCommand(self, entity))
        return entity

    def create_association(self, name: str | None, point: QPointF) -> Association:
        clean_name = name.strip() if isinstance(name, str) else ""
        if not clean_name:
            clean_name = self._next_name(
                "Association",
                (item.name for item in self.model.associations.values()),
            )
        association = Association(clean_name, Position(point.x(), point.y()))
        self.undo_stack.push(AddNodeCommand(self, association))
        return association

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
        self.undo_stack.push(AddInheritanceCommand(self, inheritance))
        self.message.emit("Spécialisation ISA ajoutée au MCD.")
        return inheritance

    @staticmethod
    def _next_name(prefix: str, names: Iterable[str]) -> str:
        existing = set(names)
        index = 1
        while f"{prefix}_{index}" in existing:
            index += 1
        return f"{prefix}_{index}"

    def rename_node(self, node_id: str, name: str) -> None:
        node = self.model.node(node_id)
        if node.name != name:
            self.undo_stack.push(RenameNodeCommand(self, node_id, node.name, name))

    def add_attribute(
        self, owner_id: str, name: str, identifier: bool = False
    ) -> Attribute:
        owner = self.model.node(owner_id)
        attribute = Attribute(name=name, identifier=identifier)
        self.undo_stack.push(
            AddAttributeCommand(
                self, owner_id, attribute, index=len(owner.attributes)
            )
        )
        return attribute

    def remove_attribute(self, owner_id: str, attribute_id: str) -> None:
        owner = self.model.node(owner_id)
        for index, attribute in enumerate(owner.attributes):
            if attribute.id == attribute_id:
                self.undo_stack.push(
                    RemoveAttributeCommand(
                        self, owner_id, attribute, index
                    )
                )
                return
        raise DiagramError(f"Attribut inconnu : {attribute_id}")

    def rename_attribute(
        self, owner_id: str, attribute_id: str, name: str
    ) -> None:
        attribute = self.model.attribute(owner_id, attribute_id)
        if attribute.name != name:
            self.undo_stack.push(
                RenameAttributeCommand(
                    self, owner_id, attribute_id, attribute.name, name
                )
            )

    def set_attribute_identifier(
        self, owner_id: str, attribute_id: str, identifier: bool
    ) -> None:
        attribute = self.model.attribute(owner_id, attribute_id)
        if attribute.identifier != identifier:
            self.undo_stack.push(
                SetIdentifierCommand(
                    self,
                    owner_id,
                    attribute_id,
                    attribute.identifier,
                    identifier,
                )
            )

    def set_attribute_data_type(
        self,
        owner_id: str,
        attribute_id: str,
        data_type: MLDDataType | None,
    ) -> None:
        attribute = self.model.attribute(owner_id, attribute_id)
        if attribute.data_type != data_type:
            self.undo_stack.push(
                SetAttributeDataTypeCommand(
                    self,
                    owner_id,
                    attribute_id,
                    attribute.data_type,
                    data_type,
                )
            )

    def create_relation(
        self, first_id: str, second_id: str, role: str = ""
    ) -> bool:
        if first_id in self.model.entities and second_id in self.model.associations:
            entity_id, association_id = first_id, second_id
        elif second_id in self.model.entities and first_id in self.model.associations:
            entity_id, association_id = second_id, first_id
        else:
            self.message.emit("Une relation doit relier une entité et une association.")
            return False
        parallel_relations = [
            relation
            for relation in self.model.relations.values()
            if relation.entity_id == entity_id
            and relation.association_id == association_id
        ]
        clean_role = role.strip()
        if clean_role and any(
            relation.entity_id == entity_id
            and relation.association_id == association_id
            and relation.role.casefold() == clean_role.casefold()
            for relation in self.model.relations.values()
        ):
            self.message.emit(
                f'Le rôle « {clean_role} » existe déjà entre ces deux objets.'
            )
            return False

        used_roles = {
            relation.role.casefold()
            for relation in parallel_relations
            if relation.role
        }

        def next_role() -> str:
            index = 1
            while f"rôle_{index}".casefold() in used_roles:
                index += 1
            value = f"rôle_{index}"
            used_roles.add(value.casefold())
            return value

        changes: list[tuple[Relation, str]] = []
        if parallel_relations:
            for existing in sorted(parallel_relations, key=lambda item: item.id):
                if not existing.role:
                    changes.append((existing, next_role()))
            if not clean_role:
                clean_role = next_role()
        relation = Relation(
            entity_id=entity_id,
            association_id=association_id,
            cardinality=DEFAULT_CARDINALITY,
            role=clean_role,
        )
        if changes:
            self.undo_stack.beginMacro("Créer une relation réflexive")
            try:
                for existing, generated_role in changes:
                    self.undo_stack.push(
                        SetRelationRoleCommand(
                            self,
                            existing.id,
                            existing.role,
                            generated_role,
                        )
                    )
                self.undo_stack.push(AddRelationCommand(self, relation))
            finally:
                self.undo_stack.endMacro()
        else:
            self.undo_stack.push(AddRelationCommand(self, relation))
        if parallel_relations:
            self.message.emit(
                "Relation réflexive créée ; les rôles sont modifiables dans "
                "le panneau de propriétés."
            )
        else:
            self.message.emit("Relation créée avec la cardinalité (0,N).")
        return True

    def set_relation_cardinality(
        self,
        relation_id: str,
        cardinality: Cardinality | None,
    ) -> None:
        relation = self.model.relations[relation_id]
        if relation.cardinality != cardinality:
            self.undo_stack.push(
                SetCardinalityCommand(
                    self, relation_id, relation.cardinality, cardinality
                )
            )

    def set_relation_role(self, relation_id: str, role: str) -> None:
        relation = self.model.relations[relation_id]
        clean_role = role.strip()
        if relation.role != clean_role:
            self.undo_stack.push(
                SetRelationRoleCommand(
                    self, relation_id, relation.role, clean_role
                )
            )

    def set_association_historized(
        self, association_id: str, is_historized: bool
    ) -> None:
        association = self.model.associations[association_id]
        if association.is_historized != is_historized:
            self.undo_stack.push(
                SetAssociationHistorizedCommand(
                    self,
                    association_id,
                    association.is_historized,
                    is_historized,
                )
            )

    def set_association_materialization_strategy(
        self,
        association_id: str,
        strategy: MaterializationStrategy | str,
    ) -> None:
        normalized = MaterializationStrategy(strategy)
        association = self.model.associations[association_id]
        if association.materialization_strategy is not normalized:
            self.undo_stack.push(
                SetAssociationMaterializationStrategyCommand(
                    self,
                    association_id,
                    association.materialization_strategy,
                    normalized,
                )
            )

    def validate(self) -> ValidationReport:
        return validate_mcd(self.model)

    @property
    def mld_is_stale(self) -> bool:
        return (
            self.mld_model is not None
            and self.mld_model.generated_from_fingerprint
            != mcd_logical_fingerprint(self.model)
        )

    def generate_mld(self) -> MLDModel:
        report = self.validate()
        if report.errors:
            raise MLDGenerationBlocked(report)
        self.mld_model = self.mld_transformer.transform(self.model)
        self.mld_changed.emit(self.mld_model)
        self.mld_stale_changed.emit(False)
        self.message.emit("MLD généré à partir du MCD courant.")
        return self.mld_model

    def delete_selected(self) -> None:
        element_ids = {
            item.element_id
            for item in self.scene.selectedItems()
            if hasattr(item, "element_id")
        }
        snapshot = self._snapshot_for_deletion(element_ids)
        if not snapshot.empty:
            self.undo_stack.push(DeleteItemsCommand(self, snapshot))

    def _snapshot_for_deletion(self, element_ids: set[str]) -> DeletionSnapshot:
        entities = tuple(
            self.model.entities[element_id]
            for element_id in element_ids
            if element_id in self.model.entities
        )
        associations = tuple(
            self.model.associations[element_id]
            for element_id in element_ids
            if element_id in self.model.associations
        )
        relation_ids = {
            element_id for element_id in element_ids if element_id in self.model.relations
        }
        for node in (*entities, *associations):
            relation_ids.update(
                relation.id for relation in self.model.connected_relations(node.id)
            )
        relations = tuple(self.model.relations[item_id] for item_id in relation_ids)
        selected_entity_ids = {entity.id for entity in entities}
        inheritances = tuple(
            inheritance
            for inheritance in self.model.inheritances.values()
            if inheritance.parent_entity_id in selected_entity_ids
            or bool(selected_entity_ids.intersection(inheritance.child_entity_ids))
        )
        return DeletionSnapshot(entities, associations, relations, inheritances)

    def new_document(self) -> None:
        self._replace_model(MCDModel(), None)
        self.message.emit("Nouveau diagramme.")

    def load(self, path: str | Path) -> None:
        source = Path(path)
        model = self.repository.load(source)
        self._replace_model(model, source)
        self.message.emit(f"Diagramme chargé : {source.name}")

    def import_generated_model(self, model: MCDModel) -> None:
        """Remplace le document par un candidat validé et le marque à enregistrer."""

        self._replace_model(model, None)
        self.undo_stack.resetClean()
        self.message.emit("MCD généré par l'IA importé ; enregistrez le document.")

    def import_reverse_engineered_model(
        self, model: MCDModel, mld_model: MLDModel
    ) -> None:
        """Installe un couple MCD/MLD confirmé issu d'un DDL."""

        self._replace_model(model, None)
        mld_model.generated_from_fingerprint = mcd_logical_fingerprint(model)
        self.mld_model = mld_model
        self.mld_changed.emit(mld_model)
        self.mld_stale_changed.emit(False)
        self.undo_stack.resetClean()
        self.message.emit(
            "DDL importé : vérifiez le MCD reconstruit puis enregistrez le projet."
        )

    def auto_layout(self) -> None:
        positions = self.mcd_layout.calculate(self.model)
        changes = [
            (node_id, self.model.node(node_id).position, position)
            for node_id, position in positions.items()
            if self.model.node(node_id).position != position
        ]
        if not changes:
            self.message.emit("Le MCD est déjà organisé.")
            return
        self.undo_stack.beginMacro("Réorganiser automatiquement le MCD")
        try:
            for node_id, old_position, new_position in changes:
                self.undo_stack.push(
                    MoveNodeCommand(self, node_id, old_position, new_position)
                )
        finally:
            self.undo_stack.endMacro()
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-100, -100, 100, 100))
        self.message.emit("Disposition automatique du MCD appliquée.")

    def save(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path is not None else self.document_path
        if target is None:
            raise ValueError("Aucun chemin d'enregistrement n'a été choisi.")
        self.repository.save(self.model, target)
        self.document_path = target
        self.undo_stack.setClean()
        self.document_path_changed.emit(target)
        self.message.emit(f"Diagramme enregistré : {target.name}")
        return target

    def _replace_model(self, model: MCDModel, path: Path | None) -> None:
        self.scene.reset_interaction()
        self.scene.clear()
        self._node_items.clear()
        self._relation_items.clear()
        self._inheritance_items.clear()
        self.model = model
        self.mld_model = None
        for entity in self.model.entities.values():
            self._add_node_item(entity)
        for association in self.model.associations.values():
            self._add_node_item(association)
        for inheritance in self.model.inheritances.values():
            self._add_inheritance_item(inheritance)
        for relation in self.model.relations.values():
            self._add_relation_item(relation)
        self._refresh_all_parallel_relations()
        self.document_path = path
        self.undo_stack.clear()
        self.undo_stack.setClean()
        self.document_path_changed.emit(path)
        self.model_changed.emit()
        self.mld_changed.emit(None)
        self.mld_stale_changed.emit(False)
        self._emit_selection()

    def selected_elements(self) -> list[Entity | Association | Relation]:
        result: list[Entity | Association | Relation] = []
        try:
            selected_items = self.scene.selectedItems()
        except RuntimeError:
            # La scène Qt peut être détruite avant le contrôleur à la fermeture.
            return result
        for item in selected_items:
            element_id = getattr(item, "element_id", None)
            if isinstance(element_id, str):
                try:
                    result.append(self.model.element(element_id))
                except DiagramError:
                    pass
        return result

    def _emit_selection(self) -> None:
        self.selection_changed.emit(self.selected_elements())

    def _model_did_change(self) -> None:
        self.model_changed.emit()
        self.mld_stale_changed.emit(self.mld_is_stale)
        self._emit_selection()

    @staticmethod
    def _attribute_display(node: Entity | Association) -> list[tuple[str, bool]]:
        return [
            (attribute.name, attribute.identifier) for attribute in node.attributes
        ]

    def _add_node_item(self, node: Entity | Association) -> None:
        attributes = self._attribute_display(node)
        if isinstance(node, Entity):
            item: NodeGraphicsItem = EntityGraphicsItem(
                node.id, node.name, attributes
            )
        else:
            item = AssociationGraphicsItem(node.id, node.name, attributes)
        item.setPos(node.position.x, node.position.y)
        item.position_changed.connect(self._update_relations_for_node)
        item.move_finished.connect(self._node_move_finished)
        self.scene.addItem(item)
        self._node_items[node.id] = item

    @staticmethod
    def _cardinality_text(relation: Relation) -> str:
        return relation.cardinality.label if relation.cardinality is not None else "?,?"

    def _add_relation_item(self, relation: Relation) -> None:
        entity_item = self._node_items[relation.entity_id]
        association_item = self._node_items[relation.association_id]
        if not isinstance(entity_item, EntityGraphicsItem) or not isinstance(
            association_item, AssociationGraphicsItem
        ):
            raise DiagramError("Types graphiques incompatibles pour la relation.")
        item = RelationGraphicsItem(
            relation.id,
            entity_item,
            association_item,
            self._cardinality_text(relation),
            relation.role,
        )
        self.scene.addItem(item)
        self._relation_items[relation.id] = item

    def _add_inheritance_item(self, inheritance: Inheritance) -> None:
        parent_item = self._node_items[inheritance.parent_entity_id]
        child_items = [
            self._node_items[child_id] for child_id in inheritance.child_entity_ids
        ]
        if not isinstance(parent_item, EntityGraphicsItem) or not all(
            isinstance(item, EntityGraphicsItem) for item in child_items
        ):
            raise DiagramError("Un héritage ISA ne peut relier que des entités.")
        item = InheritanceGraphicsItem(
            inheritance.id,
            parent_item,
            [child for child in child_items if isinstance(child, EntityGraphicsItem)],
        )
        self.scene.addItem(item)
        self._inheritance_items[inheritance.id] = item

    def _refresh_node_item(self, node_id: str) -> None:
        node = self.model.node(node_id)
        item = self._node_items[node_id]
        item.set_content(node.name, self._attribute_display(node))
        self._update_relations_for_node(node_id)

    def _update_relations_for_node(self, node_id: str) -> None:
        if node_id not in self.model.entities and node_id not in self.model.associations:
            return
        for relation in self.model.connected_relations(node_id):
            item = self._relation_items.get(relation.id)
            if item is not None:
                item.update_geometry()
        for inheritance in self.model.inheritances.values():
            if (
                inheritance.parent_entity_id == node_id
                or node_id in inheritance.child_entity_ids
            ):
                item = self._inheritance_items.get(inheritance.id)
                if item is not None:
                    item.update_geometry()

    def _node_move_finished(
        self, node_id: str, old_point: QPointF, new_point: QPointF
    ) -> None:
        old_position = Position(old_point.x(), old_point.y())
        new_position = Position(new_point.x(), new_point.y())
        if old_position != new_position:
            self.undo_stack.push(
                MoveNodeCommand(self, node_id, old_position, new_position)
            )

    def command_insert_node(self, node: Entity | Association) -> None:
        if isinstance(node, Entity):
            self.model.add_entity(node)
        else:
            self.model.add_association(node)
        self._add_node_item(node)
        self._model_did_change()

    def command_remove_node(self, node_id: str) -> None:
        for relation in list(self.model.connected_relations(node_id)):
            item = self._relation_items.pop(relation.id, None)
            if item is not None:
                self.scene.removeItem(item)
        if node_id in self.model.entities:
            self.model.remove_entity(node_id)
        elif node_id in self.model.associations:
            self.model.remove_association(node_id)
        item = self._node_items.pop(node_id, None)
        if item is not None:
            self.scene.removeItem(item)
        self._model_did_change()

    def command_insert_relation(self, relation: Relation) -> None:
        self.model.add_relation(relation)
        self._add_relation_item(relation)
        self._refresh_parallel_relations(
            relation.entity_id, relation.association_id
        )
        self._model_did_change()

    def command_remove_relation(self, relation_id: str) -> None:
        relation = self.model.relations[relation_id]
        self.model.remove_relation(relation_id)
        item = self._relation_items.pop(relation_id, None)
        if item is not None:
            self.scene.removeItem(item)
        self._refresh_parallel_relations(
            relation.entity_id, relation.association_id
        )
        self._model_did_change()

    def command_insert_inheritance(self, inheritance: Inheritance) -> None:
        self.model.add_inheritance(inheritance)
        self._add_inheritance_item(inheritance)
        self._model_did_change()

    def command_remove_inheritance(self, inheritance_id: str) -> None:
        try:
            del self.model.inheritances[inheritance_id]
        except KeyError as error:
            raise DiagramError(f"Héritage inconnu : {inheritance_id}") from error
        item = self._inheritance_items.pop(inheritance_id, None)
        if item is not None:
            self.scene.removeItem(item)
        self._model_did_change()

    def command_move_node(self, node_id: str, position: Position) -> None:
        self.model.move_node(node_id, position)
        item = self._node_items[node_id]
        item.setPos(position.x, position.y)
        self._update_relations_for_node(node_id)
        self._model_did_change()

    def command_rename_node(self, node_id: str, name: str) -> None:
        self.model.rename_node(node_id, name)
        self._refresh_node_item(node_id)
        self._model_did_change()

    def command_insert_attribute(
        self, owner_id: str, attribute: Attribute, index: int
    ) -> None:
        self.model.add_attribute(owner_id, attribute, index)
        self._refresh_node_item(owner_id)
        self._model_did_change()

    def command_remove_attribute(self, owner_id: str, attribute_id: str) -> None:
        self.model.remove_attribute(owner_id, attribute_id)
        self._refresh_node_item(owner_id)
        self._model_did_change()

    def command_rename_attribute(
        self, owner_id: str, attribute_id: str, name: str
    ) -> None:
        self.model.rename_attribute(owner_id, attribute_id, name)
        self._refresh_node_item(owner_id)
        self._model_did_change()

    def command_set_identifier(
        self, owner_id: str, attribute_id: str, identifier: bool
    ) -> None:
        self.model.set_attribute_identifier(owner_id, attribute_id, identifier)
        self._refresh_node_item(owner_id)
        self._model_did_change()

    def command_set_attribute_data_type(
        self,
        owner_id: str,
        attribute_id: str,
        data_type: MLDDataType | None,
    ) -> None:
        self.model.set_attribute_data_type(owner_id, attribute_id, data_type)
        self._model_did_change()

    def command_set_cardinality(
        self, relation_id: str, cardinality: Cardinality | None
    ) -> None:
        self.model.set_relation_cardinality(relation_id, cardinality)
        self._relation_items[relation_id].set_cardinality(
            self._cardinality_text(self.model.relations[relation_id])
        )
        self._model_did_change()

    def command_set_relation_role(self, relation_id: str, role: str) -> None:
        relation = self.model.relations[relation_id]
        self.model.set_relation_role(relation_id, role)
        item = self._relation_items.get(relation_id)
        if item is not None:
            item.set_role(self.model.relations[relation_id].role)
        self._refresh_parallel_relations(
            relation.entity_id, relation.association_id
        )
        self._model_did_change()

    def command_set_association_historized(
        self, association_id: str, is_historized: bool
    ) -> None:
        self.model.set_association_historized(association_id, is_historized)
        self._model_did_change()

    def command_set_association_materialization_strategy(
        self, association_id: str, strategy: MaterializationStrategy
    ) -> None:
        self.model.set_association_materialization_strategy(
            association_id, strategy
        )
        self._model_did_change()

    def command_remove_snapshot(self, snapshot: DeletionSnapshot) -> None:
        for inheritance in snapshot.inheritances:
            self.model.inheritances.pop(inheritance.id, None)
            item = self._inheritance_items.pop(inheritance.id, None)
            if item is not None:
                self.scene.removeItem(item)
        for relation in snapshot.relations:
            if relation.id in self.model.relations:
                self.model.remove_relation(relation.id)
                item = self._relation_items.pop(relation.id, None)
                if item is not None:
                    self.scene.removeItem(item)
        for node in (*snapshot.entities, *snapshot.associations):
            if node.id in self._node_items:
                if isinstance(node, Entity):
                    self.model.remove_entity(node.id)
                else:
                    self.model.remove_association(node.id)
                item = self._node_items.pop(node.id)
                self.scene.removeItem(item)
        self._refresh_all_parallel_relations()
        self._model_did_change()

    def command_restore_snapshot(self, snapshot: DeletionSnapshot) -> None:
        for node in (*snapshot.entities, *snapshot.associations):
            if isinstance(node, Entity):
                self.model.add_entity(node)
            else:
                self.model.add_association(node)
            self._add_node_item(node)
        for relation in snapshot.relations:
            self.model.add_relation(relation)
            self._add_relation_item(relation)
        for inheritance in snapshot.inheritances:
            self.model.add_inheritance(inheritance)
            self._add_inheritance_item(inheritance)
        self._refresh_all_parallel_relations()
        self._model_did_change()

    def _refresh_parallel_relations(
        self, entity_id: str, association_id: str
    ) -> None:
        relations = sorted(
            (
                relation
                for relation in self.model.relations.values()
                if relation.entity_id == entity_id
                and relation.association_id == association_id
            ),
            key=lambda item: (item.role.casefold(), item.id),
        )
        for index, relation in enumerate(relations):
            item = self._relation_items.get(relation.id)
            if item is not None:
                item.set_role(relation.role)
                item.set_parallel(index, len(relations))

    def _refresh_all_parallel_relations(self) -> None:
        pairs = {
            (relation.entity_id, relation.association_id)
            for relation in self.model.relations.values()
        }
        for entity_id, association_id in pairs:
            self._refresh_parallel_relations(entity_id, association_id)
