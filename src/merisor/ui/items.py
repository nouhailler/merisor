"""Représentations Qt du modèle métier, sans règles de validation MERISE."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, cast

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

from merisor.ui.theme import DARK_COLORS, LIGHT_COLORS, Radii

DEFAULT_BORDER = QColor("#283548")
SELECTED_BORDER = QColor("#1976d2")
ENTITY_FILL = QColor("#ffffff")
ASSOCIATION_FILL = QColor("#fff8e1")
RELATION_COLOR = QColor("#526477")
IDENTIFIER_COLOR = QColor("#0d5c3d")

AttributeDisplay = tuple[str, bool]


class PositionConstraintScene(Protocol):
    def constrain_position(
        self, item: NodeGraphicsItem, position: QPointF
    ) -> QPointF: ...

    def clear_guides(self) -> None: ...


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
        self._attributes_visible = True
        self._fill_color: QColor | None = None
        self._dark_theme = False
        self._search_match: bool | None = None
        self._hovered = False
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setAcceptHoverEvents(True)
        self.setZValue(10)

    def set_content(self, name: str, attributes: Iterable[AttributeDisplay]) -> None:
        self.prepareGeometryChange()
        self.name = name
        self.attributes = list(attributes)
        self.update()

    @property
    def attributes_visible(self) -> bool:
        return self._attributes_visible

    def set_attributes_visible(self, visible: bool) -> None:
        if self._attributes_visible == visible:
            return
        self.prepareGeometryChange()
        self._attributes_visible = visible
        self.update()
        self.position_changed.emit(self.element_id)

    def set_visual_style(self, *, fill: QColor | None, dark: bool) -> None:
        self._fill_color = QColor(fill) if fill is not None else None
        self._dark_theme = dark
        self.update()

    def set_search_match(self, match: bool | None) -> None:
        self._search_match = match
        self.setOpacity(0.24 if match is False else 1.0)
        self.update()

    def itemChange(
        self, change: QGraphicsItem.GraphicsItemChange, value: object
    ) -> object:
        result = super().itemChange(change, value)
        if (
            change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
            and isinstance(value, QPointF)
            and self._drag_origin is not None
        ):
            scene = self.scene()
            if scene is not None and hasattr(scene, "constrain_position"):
                constraint_scene = cast(PositionConstraintScene, scene)
                return constraint_scene.constrain_position(self, value)
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
        scene = self.scene()
        if scene is not None and hasattr(scene, "clear_guides"):
            cast(PositionConstraintScene, scene).clear_guides()

    def connection_point_towards(self, target: QPointF) -> QPointF:
        raise NotImplementedError

    def _border_pen(self, selected: bool) -> QPen:
        colors = DARK_COLORS if self._dark_theme else LIGHT_COLORS
        color = QColor(colors.border_strong)
        if self._hovered:
            color = QColor(colors.primary_hover)
        if self._search_match:
            color = QColor(colors.warning)
        return QPen(
            QColor(colors.primary) if selected else color,
            3.0 if selected or self._search_match else 1.6,
        )

    def _text_color(self) -> QColor:
        colors = DARK_COLORS if self._dark_theme else LIGHT_COLORS
        return QColor(colors.text)

    def _identifier_color(self) -> QColor:
        colors = DARK_COLORS if self._dark_theme else LIGHT_COLORS
        return QColor(colors.success)

    def _body_fill(self, fallback: QColor) -> QColor:
        if self._fill_color is not None:
            return self._fill_color
        del fallback
        colors = DARK_COLORS if self._dark_theme else LIGHT_COLORS
        return QColor(colors.surface)

    def hoverEnterEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def _draw_selection_handles(self, painter: QPainter, rectangle: QRectF) -> None:
        if not self.isSelected():
            return
        colors = DARK_COLORS if self._dark_theme else LIGHT_COLORS
        painter.setPen(QPen(QColor(colors.surface), 1.0))
        painter.setBrush(QBrush(QColor(colors.primary)))
        size = 7.0
        for point in (
            rectangle.topLeft(),
            rectangle.topRight(),
            rectangle.bottomLeft(),
            rectangle.bottomRight(),
        ):
            painter.drawEllipse(
                QRectF(point.x() - size / 2, point.y() - size / 2, size, size)
            )

    @staticmethod
    def _attribute_parts(value: str) -> tuple[str, str]:
        name, separator, details = value.partition(" : ")
        return name, details if separator else ""

    @staticmethod
    def _display_name(name: str) -> str:
        return name if name.strip() else "(sans nom)"


class EntityGraphicsItem(NodeGraphicsItem):
    WIDTH = 340.0
    MIN_HEIGHT = 98.0
    HEADER_HEIGHT = 44.0
    ROW_HEIGHT = 27.0
    BODY_PADDING = 10.0

    @property
    def height(self) -> float:
        content_height = (
            self.HEADER_HEIGHT
            + 2 * self.BODY_PADDING
            + (len(self.attributes) * self.ROW_HEIGHT if self.attributes_visible else 0)
        )
        minimum = (
            self.HEADER_HEIGHT + 8 if not self.attributes_visible else self.MIN_HEIGHT
        )
        return max(minimum, content_height)

    def _rectangle(self) -> QRectF:
        return QRectF(-self.WIDTH / 2, -self.height / 2, self.WIDTH, self.height)

    def boundingRect(self) -> QRectF:
        return self._rectangle().adjusted(-5, -5, 5, 8)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(self._rectangle(), Radii.LARGE, Radii.LARGE)
        return path

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        del option, widget
        rectangle = self._rectangle()
        colors = DARK_COLORS if self._dark_theme else LIGHT_COLORS
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(9, 18, 34, 38)))
        painter.drawRoundedRect(rectangle.translated(0, 4), Radii.LARGE, Radii.LARGE)
        painter.setPen(self._border_pen(self.isSelected()))
        painter.setBrush(QBrush(self._body_fill(ENTITY_FILL)))
        painter.drawRoundedRect(rectangle, Radii.LARGE, Radii.LARGE)

        header_y = rectangle.top() + self.HEADER_HEIGHT
        painter.fillRect(
            QRectF(
                rectangle.left() + 1,
                rectangle.top() + 1,
                rectangle.width() - 2,
                self.HEADER_HEIGHT - 1,
            ),
            QBrush(QColor(colors.surface_muted)),
        )
        painter.fillRect(
            QRectF(
                rectangle.left() + 1,
                rectangle.top() + 1,
                5,
                self.HEADER_HEIGHT - 1,
            ),
            QBrush(QColor(colors.primary)),
        )
        painter.setPen(self._border_pen(self.isSelected()))
        painter.drawLine(
            QPointF(rectangle.left(), header_y), QPointF(rectangle.right(), header_y)
        )

        font = QFont(painter.font())
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(self._text_color())
        text_rect = QRectF(
            rectangle.left() + 18,
            rectangle.top(),
            rectangle.width() - 30,
            self.HEADER_HEIGHT,
        )
        elided = painter.fontMetrics().elidedText(
            self._display_name(self.name),
            Qt.TextElideMode.ElideRight,
            int(text_rect.width()),
        )
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided,
        )

        font.setBold(False)
        painter.setFont(font)
        if not self.attributes_visible:
            self._draw_selection_handles(painter, rectangle)
            return
        row_y = header_y + self.BODY_PADDING
        for attribute_name, identifier in self.attributes:
            name, details = self._attribute_parts(attribute_name)
            badge_rect = QRectF(rectangle.left() + 12, row_y + 4, 30, 19)
            if identifier:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(colors.selection)))
                painter.drawRoundedRect(badge_rect, 5, 5)
                painter.setPen(QColor(colors.primary))
                badge_font = QFont(font)
                badge_font.setBold(True)
                badge_font.setPointSize(max(7, badge_font.pointSize() - 1))
                painter.setFont(badge_font)
                painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "PK")
            painter.setFont(font)
            painter.setPen(
                self._identifier_color() if identifier else self._text_color()
            )
            name_rect = QRectF(
                rectangle.left() + 50,
                row_y,
                132,
                self.ROW_HEIGHT,
            )
            painter.drawText(
                name_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                painter.fontMetrics().elidedText(
                    name or "(sans nom)",
                    Qt.TextElideMode.ElideRight,
                    int(name_rect.width()),
                ),
            )
            painter.setPen(QColor(colors.text_secondary))
            detail_rect = QRectF(
                rectangle.left() + 188,
                row_y,
                rectangle.width() - 200,
                self.ROW_HEIGHT,
            )
            painter.drawText(
                detail_rect,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                painter.fontMetrics().elidedText(
                    details,
                    Qt.TextElideMode.ElideRight,
                    int(detail_rect.width()),
                ),
            )
            row_y += self.ROW_HEIGHT
        self._draw_selection_handles(painter, rectangle)

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
    HALF_WIDTH = 118.0
    HALF_HEIGHT = 62.0
    PANEL_WIDTH = 320.0
    ROW_HEIGHT = 26.0
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
        if not self.attributes or not self.attributes_visible:
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
        colors = DARK_COLORS if self._dark_theme else LIGHT_COLORS
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(9, 18, 34, 34)))
        painter.drawPolygon(self._polygon().translated(0, 4))
        painter.setPen(self._border_pen(self.isSelected()))
        painter.setBrush(QBrush(self._body_fill(ASSOCIATION_FILL)))
        painter.drawPolygon(self._polygon())
        font = QFont(painter.font())
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(self._text_color())
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
        if self.isSelected():
            self._draw_selection_handles(
                painter,
                QRectF(
                    -self.HALF_WIDTH,
                    -self.HALF_HEIGHT,
                    self.HALF_WIDTH * 2,
                    self.HALF_HEIGHT * 2,
                ),
            )

        panel = self._attribute_panel()
        if panel is None:
            return
        painter.setPen(self._border_pen(self.isSelected()))
        painter.setBrush(QBrush(self._body_fill(ENTITY_FILL)))
        painter.drawLine(QPointF(0, self.HALF_HEIGHT), QPointF(0, panel.top()))
        painter.drawRoundedRect(panel, 3, 3)
        font.setBold(False)
        painter.setFont(font)
        row_y = panel.top() + self.PANEL_PADDING
        for attribute_name, identifier in self.attributes:
            name, details = self._attribute_parts(attribute_name)
            painter.setPen(
                self._identifier_color() if identifier else self._text_color()
            )
            name_rect = QRectF(
                panel.left() + 10,
                row_y,
                135,
                self.ROW_HEIGHT,
            )
            painter.drawText(
                name_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                painter.fontMetrics().elidedText(
                    ("PK  " if identifier else "") + (name or "(sans nom)"),
                    Qt.TextElideMode.ElideRight,
                    int(name_rect.width()),
                ),
            )
            painter.setPen(QColor(colors.text_secondary))
            detail_rect = QRectF(
                panel.left() + 150,
                row_y,
                panel.width() - 160,
                self.ROW_HEIGHT,
            )
            painter.drawText(
                detail_rect,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                painter.fontMetrics().elidedText(
                    details, Qt.TextElideMode.ElideRight, int(detail_rect.width())
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
        self._dark_theme = False

    def set_dark_theme(self, enabled: bool) -> None:
        self._dark_theme = enabled
        colors = DARK_COLORS if enabled else LIGHT_COLORS
        self.setBrush(QBrush(QColor(colors.text)))
        self.update()

    def boundingRect(self) -> QRectF:
        return super().boundingRect().adjusted(-4, -2, 4, 2)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        colors = DARK_COLORS if self._dark_theme else LIGHT_COLORS
        painter.setBrush(QBrush(QColor(colors.surface_raised)))
        painter.drawRoundedRect(self.boundingRect(), Radii.SMALL, Radii.SMALL)
        super().paint(painter, option, cast(QWidget, widget))


class RelationRoleLabelItem(CardinalityLabelItem):
    """Rôle sémantique d'une branche, notamment pour une réflexive."""

    def __init__(self, parent: QGraphicsItem) -> None:
        super().__init__(parent)
        font = QFont(self.font())
        font.setBold(False)
        font.setItalic(True)
        self.setFont(font)
        self.setBrush(QBrush(RELATION_COLOR))


class RelationGraphicsItem(QGraphicsLineItem):
    """Ligne attachée à deux objets et portant une cardinalité graphique."""

    def __init__(
        self,
        element_id: str,
        entity_item: EntityGraphicsItem,
        association_item: AssociationGraphicsItem,
        cardinality_text: str,
        role_text: str = "",
    ) -> None:
        super().__init__()
        self.element_id = element_id
        self.entity_item = entity_item
        self.association_item = association_item
        self.cardinality_label = CardinalityLabelItem(self)
        self.cardinality_label.setText(cardinality_text)
        self.role_label = RelationRoleLabelItem(self)
        self.role_label.setText(role_text)
        self.role_label.setVisible(bool(role_text))
        self._parallel_index = 0
        self._parallel_count = 1
        self._dark_theme = False
        self._hovered = False
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(0)
        self.update_geometry()

    def set_dark_theme(self, enabled: bool) -> None:
        self._dark_theme = enabled
        self.cardinality_label.set_dark_theme(enabled)
        self.role_label.set_dark_theme(enabled)
        self.update()

    def hoverEnterEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def set_search_match(self, match: bool | None) -> None:
        self.setOpacity(0.18 if match is False else 1.0)
        self.update()

    @property
    def cardinality_text(self) -> str:
        return self.cardinality_label.text()

    def set_cardinality(self, text: str) -> None:
        self.cardinality_label.setText(text)
        self._position_labels()

    @property
    def role_text(self) -> str:
        return self.role_label.text()

    def set_role(self, text: str) -> None:
        self.role_label.setText(text)
        self.role_label.setVisible(bool(text))
        self._position_labels()

    def set_parallel(self, index: int, count: int) -> None:
        self._parallel_index = max(0, index)
        self._parallel_count = max(1, count)
        self.update_geometry()

    def update_geometry(self) -> None:
        entity_center = self.entity_item.scenePos()
        association_center = self.association_item.scenePos()
        start = self.entity_item.connection_point_towards(association_center)
        end = self.association_item.connection_point_towards(entity_center)
        base_line = QLineF(start, end)
        length = base_line.length()
        if length > 0 and self._parallel_count > 1:
            offset = (self._parallel_index - (self._parallel_count - 1) / 2) * 22.0
            normal = QPointF(
                -base_line.dy() / length,
                base_line.dx() / length,
            )
            displacement = normal * offset
            start += displacement
            end += displacement
        self.setLine(QLineF(start, end))
        self._position_labels()

    def _position_labels(self) -> None:
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
        role_distance = min(48.0, length * 0.34)
        role_anchor = line.p2() - QPointF(ux * role_distance, uy * role_distance)
        role_perpendicular = QPointF(uy * 14.0, -ux * 14.0)
        role_rect = self.role_label.boundingRect()
        self.role_label.setPos(role_anchor + role_perpendicular - role_rect.center())

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
        colors = DARK_COLORS if self._dark_theme else LIGHT_COLORS
        normal_color = QColor(colors.border_strong)
        color = (
            QColor(colors.primary)
            if self.isSelected() or self._hovered
            else normal_color
        )
        width = 3.5 if self.isSelected() else 2.7 if self._hovered else 2.0
        painter.setPen(
            QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        )
        painter.drawLine(self.line())


class InheritanceGraphicsItem(QGraphicsItem):
    """Connecteur ISA non métier reliant une mère à ses spécialisations."""

    def __init__(
        self,
        element_id: str,
        parent_item: EntityGraphicsItem,
        child_items: list[EntityGraphicsItem],
    ) -> None:
        super().__init__()
        self.element_id = element_id
        self.parent_item = parent_item
        self.child_items = child_items
        self._path = QPainterPath()
        self._label_position = QPointF()
        self._dark_theme = False
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setZValue(-1)
        self.update_geometry()

    def set_dark_theme(self, enabled: bool) -> None:
        self._dark_theme = enabled
        self.update()

    def update_geometry(self) -> None:
        self.prepareGeometryChange()
        parent_center = self.parent_item.scenePos()
        child_centers = [item.scenePos() for item in self.child_items]
        if not child_centers:
            self._path = QPainterPath()
            return
        junction = QPointF(
            sum(point.x() for point in child_centers) / len(child_centers),
            sum(point.y() for point in child_centers) / len(child_centers),
        )
        junction = (parent_center + junction) / 2
        path = QPainterPath()
        parent_point = self.parent_item.connection_point_towards(junction)
        path.moveTo(parent_point)
        path.lineTo(junction)
        for child_item, _child_center in zip(
            self.child_items, child_centers, strict=True
        ):
            child_point = child_item.connection_point_towards(junction)
            path.moveTo(junction)
            path.lineTo(child_point)
        self._path = path
        self._label_position = junction
        self.update()

    def boundingRect(self) -> QRectF:
        return self._path.boundingRect().adjusted(-28, -20, 28, 20)

    def shape(self) -> QPainterPath:
        stroker = QPainterPathStroker()
        stroker.setWidth(12)
        return stroker.createStroke(self._path)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        del option, widget
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = DARK_COLORS if self._dark_theme else LIGHT_COLORS
        painter.setPen(QPen(QColor(colors.border_strong), 2.0))
        painter.drawPath(self._path)
        triangle = QPolygonF(
            [
                self._label_position + QPointF(0, -13),
                self._label_position + QPointF(15, 12),
                self._label_position + QPointF(-15, 12),
            ]
        )
        painter.setBrush(QBrush(QColor(colors.surface_muted)))
        painter.drawPolygon(triangle)
        painter.setPen(QColor(colors.text))
        painter.drawText(
            QRectF(
                self._label_position.x() - 18,
                self._label_position.y() - 9,
                36,
                18,
            ),
            Qt.AlignmentFlag.AlignCenter,
            "ISA",
        )
