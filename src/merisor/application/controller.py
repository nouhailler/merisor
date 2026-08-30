"""Contrôleur principal : commandes, modèle, vue et document courant."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, Signal, Slot
from PySide6.QtGui import QUndoStack

from merisor.application.commands import (
    AddAttributeCommand,
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
    SetCardinalityCommand,
    SetIdentifierCommand,
)
from merisor.application.mld_transformer import (
    McdToMldTransformer,
    mcd_logical_fingerprint,
)
from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    DEFAULT_CARDINALITY,
    DiagramError,
    Entity,
    MCDModel,
    MLDModel,
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
        self.mld_model: MLDModel | None = None
        self.undo_stack = QUndoStack(self)
        self.document_path: Path | None = None
        self._node_items: dict[str, NodeGraphicsItem] = {}
        self._relation_items: dict[str, RelationGraphicsItem] = {}

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

    def create_relation(self, first_id: str, second_id: str) -> bool:
        if first_id in self.model.entities and second_id in self.model.associations:
            entity_id, association_id = first_id, second_id
        elif second_id in self.model.entities and first_id in self.model.associations:
            entity_id, association_id = second_id, first_id
        else:
            self.message.emit("Une relation doit relier une entité et une association.")
            return False
        if any(
            relation.entity_id == entity_id
            and relation.association_id == association_id
            for relation in self.model.relations.values()
        ):
            self.message.emit("Ces deux objets sont déjà reliés.")
            return False
        relation = Relation(
            entity_id=entity_id,
            association_id=association_id,
            cardinality=DEFAULT_CARDINALITY,
        )
        self.undo_stack.push(AddRelationCommand(self, relation))
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
        return DeletionSnapshot(entities, associations, relations)

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
        self.model = model
        self.mld_model = None
        for entity in self.model.entities.values():
            self._add_node_item(entity)
        for association in self.model.associations.values():
            self._add_node_item(association)
        for relation in self.model.relations.values():
            self._add_relation_item(relation)
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
        )
        self.scene.addItem(item)
        self._relation_items[relation.id] = item

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
        self._model_did_change()

    def command_remove_relation(self, relation_id: str) -> None:
        self.model.remove_relation(relation_id)
        item = self._relation_items.pop(relation_id, None)
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

    def command_set_cardinality(
        self, relation_id: str, cardinality: Cardinality | None
    ) -> None:
        self.model.set_relation_cardinality(relation_id, cardinality)
        self._relation_items[relation_id].set_cardinality(
            self._cardinality_text(self.model.relations[relation_id])
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
        self._model_did_change()
