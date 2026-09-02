"""Scène interactive et vue zoomable du diagramme."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QTransform
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
        self.grid_size = 25.0
        self.grid_visible = False
        self.snap_enabled = False
        self.guides_enabled = True
        self._guide_x: float | None = None
        self._guide_y: float | None = None
        self._dark_theme = False

    def configure_canvas(
        self,
        *,
        grid_visible: bool | None = None,
        snap_enabled: bool | None = None,
        guides_enabled: bool | None = None,
    ) -> None:
        if grid_visible is not None:
            self.grid_visible = grid_visible
        if snap_enabled is not None:
            self.snap_enabled = snap_enabled
        if guides_enabled is not None:
            self.guides_enabled = guides_enabled
        self.update()

    def set_dark_theme(self, enabled: bool) -> None:
        self._dark_theme = enabled
        self.setBackgroundBrush(QBrush(QColor("#1d222b" if enabled else "#f5f7fa")))
        self.update()

    def constrain_position(self, item: NodeGraphicsItem, position: QPointF) -> QPointF:
        """Applique grille et guides sans déformer une sélection multiple."""

        if (
            len(
                [
                    value
                    for value in self.selectedItems()
                    if isinstance(value, NodeGraphicsItem)
                ]
            )
            > 1
        ):
            self.clear_guides()
            return position
        x, y = position.x(), position.y()
        if self.snap_enabled:
            x = round(x / self.grid_size) * self.grid_size
            y = round(y / self.grid_size) * self.grid_size
        self._guide_x = None
        self._guide_y = None
        if self.guides_enabled:
            tolerance = 8.0
            peers = [
                value
                for value in self.items()
                if isinstance(value, NodeGraphicsItem) and value is not item
            ]
            x_match = next(
                (
                    peer.pos().x()
                    for peer in peers
                    if abs(peer.pos().x() - x) <= tolerance
                ),
                None,
            )
            y_match = next(
                (
                    peer.pos().y()
                    for peer in peers
                    if abs(peer.pos().y() - y) <= tolerance
                ),
                None,
            )
            if x_match is not None:
                x = x_match
                self._guide_x = x_match
            if y_match is not None:
                y = y_match
                self._guide_y = y_match
        self.update()
        return QPointF(x, y)

    def clear_guides(self) -> None:
        if self._guide_x is not None or self._guide_y is not None:
            self._guide_x = None
            self._guide_y = None
            self.update()

    def drawBackground(self, painter: QPainter, rect: QRectF | QRect) -> None:
        super().drawBackground(painter, rect)
        rect = QRectF(rect)
        if not self.grid_visible:
            return
        color = QColor("#3b4555" if self._dark_theme else "#d7dde6")
        pen = QPen(color, 0.0)
        painter.setPen(pen)
        left = int(rect.left() // self.grid_size) * self.grid_size
        top = int(rect.top() // self.grid_size) * self.grid_size
        x = left
        while x <= rect.right():
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += self.grid_size
        y = top
        while y <= rect.bottom():
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += self.grid_size

    def drawForeground(self, painter: QPainter, rect: QRectF | QRect) -> None:
        super().drawForeground(painter, rect)
        rect = QRectF(rect)
        painter.setPen(QPen(QColor("#e91e63"), 1.2, Qt.PenStyle.DashLine))
        if self._guide_x is not None:
            painter.drawLine(
                QPointF(self._guide_x, rect.top()),
                QPointF(self._guide_x, rect.bottom()),
            )
        if self._guide_y is not None:
            painter.drawLine(
                QPointF(rect.left(), self._guide_y),
                QPointF(rect.right(), self._guide_y),
            )

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
        for item in self.items(
            position,
            Qt.ItemSelectionMode.IntersectsItemShape,
            Qt.SortOrder.DescendingOrder,
            QTransform(),
        ):
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
            self.interaction_message.emit(
                "Choisissez un autre objet comme seconde extrémité."
            )
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
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate
        )
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

    def fit_scene(self) -> None:
        rectangle = self.scene().itemsBoundingRect().adjusted(-80, -80, 80, 80)
        if rectangle.isEmpty():
            self.reset_zoom()
            return
        self.resetTransform()
        self.fitInView(rectangle, Qt.AspectRatioMode.KeepAspectRatio)
        factor = self.transform().m11()
        if factor < self.MIN_ZOOM or factor > self.MAX_ZOOM:
            self.resetTransform()
            bounded = max(self.MIN_ZOOM, min(self.MAX_ZOOM, factor))
            self.scale(bounded, bounded)
            factor = bounded
        self._zoom = factor
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
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
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


class MiniMapView(QGraphicsView):
    """Vue d'ensemble cliquable partageant la scène du MCD principal."""

    def __init__(self, main_view: DiagramView, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(main_view.scene(), parent)
        self.main_view = main_view
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setInteractive(False)
        self.setMinimumSize(220, 140)
        self.setMaximumHeight(190)
        self.scene().changed.connect(self.refresh_overview)

    def refresh_overview(self, _regions: object = None) -> None:
        bounds = self.scene().itemsBoundingRect().adjusted(-80, -80, 80, 80)
        if not bounds.isEmpty():
            self.fitInView(bounds, Qt.AspectRatioMode.KeepAspectRatio)
        self.viewport().update()

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        self.refresh_overview()

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton:
            self.main_view.centerOn(self.mapToScene(event.position().toPoint()))
            self.viewport().update()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().paintEvent(event)
        visible = self.main_view.mapToScene(
            self.main_view.viewport().rect()
        ).boundingRect()
        mapped = self.mapFromScene(visible).boundingRect()
        painter = QPainter(self.viewport())
        painter.setPen(QPen(QColor("#e91e63"), 2.0))
        painter.setBrush(QColor(233, 30, 99, 24))
        painter.drawRect(mapped)
