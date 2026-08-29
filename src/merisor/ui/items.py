"""Représentations Qt du modèle métier, sans règles de validation MERISE."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsObject,
    QGraphicsSimpleTextItem,
    QStyleOptionGraphicsItem,
    QWidget,
)


DEFAULT_BORDER = QColor("#283548")
SELECTED_BORDER = QColor("#1976d2")
ENTITY_FILL = QColor("#ffffff")
ASSOCIATION_FILL = QColor("#fff8e1")
RELATION_COLOR = QColor("#526477")
IDENTIFIER_COLOR = QColor("#0d5c3d")

AttributeDisplay = tuple[str, bool]


class NodeGraphicsItem(QGraphicsObject):
    """Base commune déplaçable ; l'origine locale est le centre du nœud."""

    position_changed = Signal(str)
    move_finished = Signal(str, QPointF, QPointF)

    def __init__(
        self,
        element_id: str,
        name: str,
        attributes: Iterable[AttributeDisplay] = (),
    ) -> None:
        super().__init__()
        self.element_id = element_id
        self.name = name
        self.attributes = list(attributes)
        self._drag_origin: QPointF | None = None
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setZValue(10)

    def set_content(
        self, name: str, attributes: Iterable[AttributeDisplay]
    ) -> None:
        self.prepareGeometryChange()
        self.name = name
        self.attributes = list(attributes)
        self.update()

    def itemChange(
        self, change: QGraphicsItem.GraphicsItemChange, value: object
    ) -> object:
        result = super().itemChange(change, value)
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.position_changed.emit(self.element_id)
        return result

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = QPointF(self.pos())
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().mouseReleaseEvent(event)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if self._drag_origin is not None:
            old_position = self._drag_origin
            new_position = QPointF(self.pos())
            self._drag_origin = None
            if old_position != new_position:
                self.move_finished.emit(self.element_id, old_position, new_position)

    def connection_point_towards(self, target: QPointF) -> QPointF:
        raise NotImplementedError

    @staticmethod
    def _border_pen(selected: bool) -> QPen:
        return QPen(
            SELECTED_BORDER if selected else DEFAULT_BORDER,
            3.0 if selected else 2.0,
        )

    @staticmethod
    def _display_name(name: str) -> str:
        return name if name.strip() else "(sans nom)"


class EntityGraphicsItem(NodeGraphicsItem):
    WIDTH = 210.0
    MIN_HEIGHT = 92.0
    HEADER_HEIGHT = 38.0
    ROW_HEIGHT = 23.0
    BODY_PADDING = 10.0

    @property
    def height(self) -> float:
        content_height = (
            self.HEADER_HEIGHT
            + 2 * self.BODY_PADDING
            + len(self.attributes) * self.ROW_HEIGHT
        )
        return max(self.MIN_HEIGHT, content_height)

    def _rectangle(self) -> QRectF:
        return QRectF(-self.WIDTH / 2, -self.height / 2, self.WIDTH, self.height)

    def boundingRect(self) -> QRectF:
        return self._rectangle().adjusted(-3, -3, 3, 3)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(self._rectangle(), 4, 4)
        return path

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        del option, widget
        rectangle = self._rectangle()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(self._border_pen(self.isSelected()))
        painter.setBrush(QBrush(ENTITY_FILL))
        painter.drawRoundedRect(rectangle, 4, 4)
        header_y = rectangle.top() + self.HEADER_HEIGHT
        painter.drawLine(
            QPointF(rectangle.left(), header_y), QPointF(rectangle.right(), header_y)
        )

        font = QFont(painter.font())
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(DEFAULT_BORDER)
        text_rect = QRectF(
            rectangle.left() + 8,
            rectangle.top(),
            rectangle.width() - 16,
            self.HEADER_HEIGHT,
        )
        elided = painter.fontMetrics().elidedText(
            self._display_name(self.name),
            Qt.TextElideMode.ElideRight,
            int(text_rect.width()),
        )
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, elided)

        font.setBold(False)
        painter.setFont(font)
        row_y = header_y + self.BODY_PADDING
        for attribute_name, identifier in self.attributes:
            prefix = "# " if identifier else "  "
            painter.setPen(IDENTIFIER_COLOR if identifier else DEFAULT_BORDER)
            attribute_rect = QRectF(
                rectangle.left() + 12,
                row_y,
                rectangle.width() - 24,
                self.ROW_HEIGHT,
            )
            attribute_text = prefix + (attribute_name or "(sans nom)")
            elided_attribute = painter.fontMetrics().elidedText(
                attribute_text,
                Qt.TextElideMode.ElideRight,
                int(attribute_rect.width()),
            )
            painter.drawText(
                attribute_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                elided_attribute,
            )
            row_y += self.ROW_HEIGHT

    def connection_point_towards(self, target: QPointF) -> QPointF:
        center = self.scenePos()
        direction = target - center
        dx, dy = direction.x(), direction.y()
        if dx == 0 and dy == 0:
            return center
        scale_x = (self.WIDTH / 2) / abs(dx) if dx else float("inf")
        scale_y = (self.height / 2) / abs(dy) if dy else float("inf")
        return center + direction * min(scale_x, scale_y)


class AssociationGraphicsItem(NodeGraphicsItem):
    HALF_WIDTH = 105.0
    HALF_HEIGHT = 58.0
    PANEL_WIDTH = 190.0
    ROW_HEIGHT = 22.0
    PANEL_GAP = 5.0
    PANEL_PADDING = 8.0

    def _polygon(self) -> QPolygonF:
        return QPolygonF(
            [
                QPointF(0, -self.HALF_HEIGHT),
                QPointF(self.HALF_WIDTH, 0),
                QPointF(0, self.HALF_HEIGHT),
                QPointF(-self.HALF_WIDTH, 0),
            ]
        )

    def _attribute_panel(self) -> QRectF | None:
        if not self.attributes:
            return None
        height = 2 * self.PANEL_PADDING + len(self.attributes) * self.ROW_HEIGHT
        return QRectF(
            -self.PANEL_WIDTH / 2,
            self.HALF_HEIGHT + self.PANEL_GAP,
            self.PANEL_WIDTH,
            height,
        )

    def boundingRect(self) -> QRectF:
        diamond = QRectF(
            -self.HALF_WIDTH,
            -self.HALF_HEIGHT,
            2 * self.HALF_WIDTH,
            2 * self.HALF_HEIGHT,
        )
        panel = self._attribute_panel()
        bounds = diamond.united(panel) if panel is not None else diamond
        return bounds.adjusted(-3, -3, 3, 3)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addPolygon(self._polygon())
        path.closeSubpath()
        panel = self._attribute_panel()
        if panel is not None:
            path.addRoundedRect(panel, 3, 3)
        return path

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        del option, widget
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(self._border_pen(self.isSelected()))
        painter.setBrush(QBrush(ASSOCIATION_FILL))
        painter.drawPolygon(self._polygon())
        font = QFont(painter.font())
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(DEFAULT_BORDER)
        text_rect = QRectF(
            -self.HALF_WIDTH * 0.70,
            -self.HALF_HEIGHT * 0.38,
            self.HALF_WIDTH * 1.40,
            self.HALF_HEIGHT * 0.76,
        )
        elided = painter.fontMetrics().elidedText(
            self._display_name(self.name),
            Qt.TextElideMode.ElideRight,
            int(text_rect.width()),
        )
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, elided)

        panel = self._attribute_panel()
        if panel is None:
            return
        painter.setPen(self._border_pen(self.isSelected()))
        painter.setBrush(QBrush(ENTITY_FILL))
        painter.drawLine(
            QPointF(0, self.HALF_HEIGHT), QPointF(0, panel.top())
        )
        painter.drawRoundedRect(panel, 3, 3)
        font.setBold(False)
        painter.setFont(font)
        row_y = panel.top() + self.PANEL_PADDING
        for attribute_name, identifier in self.attributes:
            prefix = "# " if identifier else ""
            painter.setPen(IDENTIFIER_COLOR if identifier else DEFAULT_BORDER)
            attribute_rect = QRectF(
                panel.left() + 10,
                row_y,
                panel.width() - 20,
                self.ROW_HEIGHT,
            )
            text = prefix + (attribute_name or "(sans nom)")
            painter.drawText(
                attribute_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                painter.fontMetrics().elidedText(
                    text, Qt.TextElideMode.ElideRight, int(attribute_rect.width())
                ),
            )
            row_y += self.ROW_HEIGHT

    def connection_point_towards(self, target: QPointF) -> QPointF:
        center = self.scenePos()
        direction = target - center
        dx, dy = direction.x(), direction.y()
        if dx == 0 and dy == 0:
            return center
        denominator = abs(dx) / self.HALF_WIDTH + abs(dy) / self.HALF_HEIGHT
        return center + direction * (1.0 / denominator)


class CardinalityLabelItem(QGraphicsSimpleTextItem):
    """Texte de cardinalité lisible sur le fond du canvas."""

    def __init__(self, parent: QGraphicsItem) -> None:
        super().__init__(parent)
        font = QFont(self.font())
        font.setBold(True)
        self.setFont(font)
        self.setBrush(QBrush(DEFAULT_BORDER))
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setZValue(2)

    def boundingRect(self) -> QRectF:
        return super().boundingRect().adjusted(-4, -2, 4, 2)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 225)))
        painter.drawRoundedRect(self.boundingRect(), 3, 3)
        super().paint(painter, option, widget)


class RelationGraphicsItem(QGraphicsLineItem):
    """Ligne attachée à deux objets et portant une cardinalité graphique."""

    def __init__(
        self,
        element_id: str,
        entity_item: EntityGraphicsItem,
        association_item: AssociationGraphicsItem,
        cardinality_text: str,
    ) -> None:
        super().__init__()
        self.element_id = element_id
        self.entity_item = entity_item
        self.association_item = association_item
        self.cardinality_label = CardinalityLabelItem(self)
        self.cardinality_label.setText(cardinality_text)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(0)
        self.update_geometry()

    @property
    def cardinality_text(self) -> str:
        return self.cardinality_label.text()

    def set_cardinality(self, text: str) -> None:
        self.cardinality_label.setText(text)
        self._position_cardinality()

    def update_geometry(self) -> None:
        entity_center = self.entity_item.scenePos()
        association_center = self.association_item.scenePos()
        start = self.entity_item.connection_point_towards(association_center)
        end = self.association_item.connection_point_towards(entity_center)
        self.setLine(QLineF(start, end))
        self._position_cardinality()

    def _position_cardinality(self) -> None:
        line = self.line()
        length = line.length()
        if length <= 0:
            return
        distance = min(44.0, length * 0.38)
        ux = line.dx() / length
        uy = line.dy() / length
        anchor = line.p1() + QPointF(ux * distance, uy * distance)
        perpendicular = QPointF(-uy * 14.0, ux * 14.0)
        label_rect = self.cardinality_label.boundingRect()
        self.cardinality_label.setPos(anchor + perpendicular - label_rect.center())

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.moveTo(self.line().p1())
        path.lineTo(self.line().p2())
        stroker = QPainterPathStroker()
        stroker.setWidth(14.0)
        return stroker.createStroke(path)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        del option, widget
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = SELECTED_BORDER if self.isSelected() else RELATION_COLOR
        width = 3.5 if self.isSelected() else 2.0
        painter.setPen(
            QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        )
        painter.drawLine(self.line())

