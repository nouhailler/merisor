"""Scène interactive et vue zoomable du diagramme."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QTransform
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from merisor.ui.items import NodeGraphicsItem


class ToolMode(Enum):
    SELECT = "select"
    ENTITY = "entity"
    ASSOCIATION = "association"
    RELATION = "relation"


class DiagramScene(QGraphicsScene):
    entity_creation_requested = Signal(QPointF)
    association_creation_requested = Signal(QPointF)
    relation_creation_requested = Signal(str, str)
    interaction_message = Signal(str)

    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setSceneRect(QRectF(-5000, -5000, 10000, 10000))
        self.setBackgroundBrush(QBrush(QColor("#f5f7fa")))
        self.mode = ToolMode.SELECT
        self._relation_start: NodeGraphicsItem | None = None

    def set_mode(self, mode: ToolMode) -> None:
        if self._relation_start is not None:
            self._relation_start.setSelected(False)
        self._relation_start = None
        self.mode = mode
        messages = {
            ToolMode.SELECT: "Sélection : cliquez ou déplacez les objets ; bouton central pour parcourir.",
            ToolMode.ENTITY: "Entité : cliquez dans une zone vide du canvas.",
            ToolMode.ASSOCIATION: "Association : cliquez dans une zone vide du canvas.",
            ToolMode.RELATION: "Relation : cliquez sur une entité puis une association (ou inversement).",
        }
        self.interaction_message.emit(messages[mode])

    def reset_interaction(self) -> None:
        self.set_mode(ToolMode.SELECT)

    def _node_at(self, position: QPointF) -> NodeGraphicsItem | None:
        for item in self.items(position, Qt.ItemSelectionMode.IntersectsItemShape, Qt.SortOrder.DescendingOrder, QTransform()):
            current = item
            while current is not None:
                if isinstance(current, NodeGraphicsItem):
                    return current
                current = current.parentItem()
        return None

    def _has_item_at(self, position: QPointF) -> bool:
        return bool(
            self.items(
                position,
                Qt.ItemSelectionMode.IntersectsItemShape,
                Qt.SortOrder.DescendingOrder,
                QTransform(),
            )
        )

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        position = event.scenePos()
        if self.mode == ToolMode.ENTITY and not self._has_item_at(position):
            self.clearSelection()
            self.entity_creation_requested.emit(position)
            event.accept()
            return
        if self.mode == ToolMode.ASSOCIATION and not self._has_item_at(position):
            self.clearSelection()
            self.association_creation_requested.emit(position)
            event.accept()
            return
        if self.mode == ToolMode.RELATION:
            node = self._node_at(position)
            if node is not None:
                self._handle_relation_click(node)
                event.accept()
                return
        super().mousePressEvent(event)

    def _handle_relation_click(self, node: NodeGraphicsItem) -> None:
        if self._relation_start is None:
            self.clearSelection()
            self._relation_start = node
            node.setSelected(True)
            self.interaction_message.emit(
                "Première extrémité choisie ; sélectionnez un objet de l'autre type."
            )
            return
        if self._relation_start is node:
            self.interaction_message.emit("Choisissez un autre objet comme seconde extrémité.")
            return
        start = self._relation_start
        start.setSelected(False)
        self._relation_start = None
        self.relation_creation_requested.emit(start.element_id, node.element_id)


class DiagramView(QGraphicsView):
    MIN_ZOOM = 0.2
    MAX_ZOOM = 4.0
    zoom_changed = Signal(float)

    def __init__(self, scene: DiagramScene, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self._zoom = 1.0
        self._panning = False
        self._pan_origin = QPoint()

    @property
    def zoom_factor(self) -> float:
        return self._zoom

    def set_zoom(self, factor: float) -> None:
        bounded = max(self.MIN_ZOOM, min(self.MAX_ZOOM, factor))
        ratio = bounded / self._zoom
        self.scale(ratio, ratio)
        self._zoom = bounded
        self.zoom_changed.emit(self._zoom)

    def zoom_in(self) -> None:
        self.set_zoom(self._zoom * 1.2)

    def zoom_out(self) -> None:
        self.set_zoom(self._zoom / 1.2)

    def reset_zoom(self) -> None:
        self.resetTransform()
        self._zoom = 1.0
        self.zoom_changed.emit(self._zoom)

    def wheelEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.angleDelta().y() > 0:
            self.zoom_in()
        elif event.angleDelta().y() < 0:
            self.zoom_out()
        event.accept()

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_origin = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self._panning:
            current = event.position().toPoint()
            delta = current - self._pan_origin
            self._pan_origin = current
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.MiddleButton and self._panning:
            self._panning = False
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

