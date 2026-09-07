"""Consultation graphique et textuelle d'un MLD généré."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.application.mld_text import render_mld_text
from merisor.domain import MLDModel, MLDTable
from merisor.ui.theme import DARK_COLORS, LIGHT_COLORS, Radii


class MLDTableGraphicsItem(QGraphicsItem):
    # La colonne centrale doit laisser cohabiter les noms/types et la
    # nullabilité sans chevauchement, y compris pour les FK techniques.
    WIDTH = 390.0
    HEADER_HEIGHT = 38.0
    ROW_HEIGHT = 24.0
    PADDING = 10.0

    def __init__(self, model: MLDModel, table: MLDTable) -> None:
        super().__init__()
        self.model = model
        self.table = table
        self._dark_theme = False
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(5)

    def set_dark_theme(self, enabled: bool) -> None:
        self._dark_theme = enabled
        self.update()

    @property
    def header_height(self) -> float:
        return 56.0 if self.table.is_historized else self.HEADER_HEIGHT

    @property
    def height(self) -> float:
        constraint_rows = len(self.table.foreign_keys) + len(
            self.table.unique_constraints
        )
        return (
            self.header_height
            + 2 * self.PADDING
            + len(self.table.columns) * self.ROW_HEIGHT
            + constraint_rows * 18.0
        )

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.WIDTH, self.height)

    def paint(self, painter: QPainter, option, widget=None) -> None:  # type: ignore[no-untyped-def]
        del option, widget
        rectangle = self.boundingRect()
        colors = DARK_COLORS if self._dark_theme else LIGHT_COLORS
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        border_color = colors.primary if self.isSelected() else colors.border_strong
        painter.setPen(QPen(QColor(border_color), 2.5 if self.isSelected() else 1.6))
        painter.setBrush(QBrush(QColor(colors.surface)))
        painter.drawRoundedRect(rectangle, Radii.LARGE, Radii.LARGE)
        painter.fillRect(
            QRectF(1, 1, self.WIDTH - 2, self.header_height - 1),
            QBrush(QColor(colors.surface_muted)),
        )
        painter.drawLine(
            QPointF(0, self.header_height),
            QPointF(self.WIDTH, self.header_height),
        )
        font = QFont(painter.font())
        original_point_size = font.pointSize()
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(colors.text))
        painter.drawText(
            QRectF(
                8,
                0,
                self.WIDTH - 16,
                34 if self.table.is_historized else self.header_height,
            ),
            Qt.AlignmentFlag.AlignCenter,
            self.table.name,
        )

        if self.table.is_historized:
            font.setBold(False)
            font.setPointSize(max(8, font.pointSize() - 1))
            painter.setFont(font)
            painter.setPen(QColor(colors.text_secondary))
            painter.drawText(
                QRectF(8, 30, self.WIDTH - 16, 22),
                Qt.AlignmentFlag.AlignCenter,
                "Association historisée",
            )

        font.setBold(False)
        font.setPointSize(original_point_size)
        painter.setFont(font)
        y = self.header_height + self.PADDING
        for column in self.table.columns:
            roles: list[str] = []
            if self.table.is_primary_key(column.id):
                roles.append("PK")
            if self.table.is_foreign_key(column.id):
                roles.append("FK")
            if self.table.is_unique(column.id):
                roles.append("UQ")
            if column.auto_increment:
                roles.append("AI")
            role_text = "/".join(roles)
            painter.setPen(QColor(colors.success) if roles else QColor(colors.text))
            painter.drawText(
                QRectF(10, y, 58, self.ROW_HEIGHT),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                role_text,
            )
            nullability = (
                "NULL"
                if column.nullable is True
                else "NOT NULL"
                if column.nullable is False
                else ""
            )
            value_rect = QRectF(78, y, self.WIDTH - 180, self.ROW_HEIGHT)
            value_text = painter.fontMetrics().elidedText(
                f"{column.name} : {column.data_type.label}",
                Qt.TextElideMode.ElideRight,
                int(value_rect.width()),
            )
            painter.drawText(
                value_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                value_text,
            )
            painter.setPen(QColor(colors.text_secondary))
            painter.drawText(
                QRectF(self.WIDTH - 92, y, 82, self.ROW_HEIGHT),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                nullability,
            )
            y += self.ROW_HEIGHT

        painter.setPen(QColor(colors.text_secondary))
        for foreign_key in self.table.foreign_keys:
            target = self.model.table_by_id(foreign_key.referenced_table_id)
            painter.drawText(
                QRectF(10, y, self.WIDTH - 20, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"FK → {target.name}",
            )
            y += 18
        for constraint in self.table.unique_constraints:
            names = ", ".join(
                self.table.column_by_id(column_id).name
                for column_id in constraint.column_ids
            )
            painter.drawText(
                QRectF(10, y, self.WIDTH - 20, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"UNIQUE ({names})",
            )
            y += 18


class MLDGraphicsView(QGraphicsView):
    ZOOM_FACTOR = 1.25
    table_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mld_scene = QGraphicsScene(self)
        self._table_items: dict[str, MLDTableGraphicsItem] = {}
        self._dark_theme = False
        self.setScene(self.mld_scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor(LIGHT_COLORS.canvas)))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.mld_scene.selectionChanged.connect(self._selection_changed)

    def set_dark_theme(self, enabled: bool) -> None:
        self._dark_theme = enabled
        colors = DARK_COLORS if enabled else LIGHT_COLORS
        self.setBackgroundBrush(QBrush(QColor(colors.canvas)))
        for item in self.mld_scene.items():
            if isinstance(item, MLDTableGraphicsItem):
                item.set_dark_theme(enabled)

    def _selection_changed(self) -> None:
        try:
            selected = [
                item
                for item in self.mld_scene.selectedItems()
                if isinstance(item, MLDTableGraphicsItem)
            ]
        except RuntimeError:
            return
        self.table_selected.emit(selected[0].table if len(selected) == 1 else None)

    def zoom_in(self) -> None:
        self.scale(self.ZOOM_FACTOR, self.ZOOM_FACTOR)

    def zoom_out(self) -> None:
        self.scale(1 / self.ZOOM_FACTOR, 1 / self.ZOOM_FACTOR)

    def reset_zoom(self) -> None:
        if self.mld_scene.items():
            self.fitInView(
                self.mld_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
            )

    def wheelEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            elif event.angleDelta().y() < 0:
                self.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    def set_model(self, model: MLDModel) -> None:
        self.mld_scene.clear()
        self._table_items.clear()
        items: dict[str, MLDTableGraphicsItem] = {}
        columns_per_row = 3
        horizontal_spacing = 455.0
        rows = [
            model.tables[index : index + columns_per_row]
            for index in range(0, len(model.tables), columns_per_row)
        ]
        row_y: list[float] = []
        current_y = 0.0
        for table_row in rows:
            row_y.append(current_y)
            current_y += (
                max(MLDTableGraphicsItem(model, table).height for table in table_row)
                + 90.0
            )
        for index, table in enumerate(model.tables):
            item = MLDTableGraphicsItem(model, table)
            item.set_dark_theme(self._dark_theme)
            row, column = divmod(index, columns_per_row)
            item.setPos(column * horizontal_spacing, row_y[row])
            self.mld_scene.addItem(item)
            items[table.id] = item
            self._table_items[table.id] = item

        for table in model.tables:
            source_item = items[table.id]
            for foreign_key in table.foreign_keys:
                target_item = items[foreign_key.referenced_table_id]
                start = source_item.sceneBoundingRect().center()
                end = target_item.sceneBoundingRect().center()
                line = QGraphicsLineItem(start.x(), start.y(), end.x(), end.y())
                colors = DARK_COLORS if self._dark_theme else LIGHT_COLORS
                line.setPen(QPen(QColor(colors.border_strong), 1.7))
                line.setZValue(0)
                self.mld_scene.addItem(line)
                label = QGraphicsSimpleTextItem("FK")
                label.setBrush(QBrush(QColor(colors.info)))
                label.setPos((start + end) / 2 + QPointF(4, -16))
                label.setZValue(1)
                self.mld_scene.addItem(label)

        self.mld_scene.setSceneRect(
            self.mld_scene.itemsBoundingRect().adjusted(-40, -40, 40, 40)
        )
        if model.tables:
            self.reset_zoom()

    def select_table(self, table_id: str) -> bool:
        item = self._table_items.get(table_id)
        if item is None:
            return False
        self.mld_scene.clearSelection()
        item.setSelected(True)
        self.centerOn(item)
        return True


class MLDView(QWidget):
    """Vue du dernier MLD ; le contrôleur reste propriétaire de son état."""

    source_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.model: MLDModel | None = None
        self._dark_theme = False
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        self.status_label = QLabel("MLD non généré")
        font = self.status_label.font()
        font.setBold(True)
        self.status_label.setFont(font)
        header.addWidget(self.status_label)
        header.addStretch(1)
        self.zoom_out_button = QPushButton("-")
        self.zoom_out_button.setToolTip("Réduire le graphe")
        self.zoom_out_button.setAccessibleName("Zoom arrière MLD")
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setToolTip("Agrandir le graphe")
        self.zoom_in_button.setAccessibleName("Zoom avant MLD")
        self.reset_zoom_button = QPushButton("Adapter")
        self.reset_zoom_button.setToolTip("Recentrer le graphe")
        self.reset_zoom_button.setAccessibleName("Réinitialiser le zoom MLD")
        header.addWidget(self.zoom_out_button)
        header.addWidget(self.zoom_in_button)
        header.addWidget(self.reset_zoom_button)
        self.copy_button = QPushButton("Copier le texte")
        self.export_button = QPushButton("Exporter…")
        self.copy_button.setEnabled(False)
        self.export_button.setEnabled(False)
        header.addWidget(self.copy_button)
        header.addWidget(self.export_button)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        self.graphics_view = MLDGraphicsView()
        self.text_view = QPlainTextEdit()
        self.text_view.setReadOnly(True)
        font = QFont("monospace")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.text_view.setFont(font)
        self.tabs.addTab(self.graphics_view, "Vue graphique")
        self.tabs.addTab(self.text_view, "Vue textuelle")
        self.provenance_tree = QTreeWidget()
        self.provenance_tree.setHeaderLabels(["Élément MLD", "Origine MCD"])
        self.provenance_tree.setAlternatingRowColors(True)
        self.provenance_tree.header().setStretchLastSection(True)
        self.tabs.addTab(self.provenance_tree, "Provenance")
        self.show_source_button = QPushButton("Voir dans le MCD")
        self.show_source_button.setEnabled(False)
        self.show_source_button.setToolTip(
            "Sélectionner et centrer l'objet conceptuel à l'origine de cet élément"
        )
        layout.addWidget(self.show_source_button)
        layout.addWidget(self.tabs, 1)

        self.copy_button.clicked.connect(self.copy_text)
        self.export_button.clicked.connect(self._choose_export_path)
        self.zoom_in_button.clicked.connect(self.graphics_view.zoom_in)
        self.zoom_out_button.clicked.connect(self.graphics_view.zoom_out)
        self.reset_zoom_button.clicked.connect(self.graphics_view.reset_zoom)
        self.provenance_tree.currentItemChanged.connect(
            self._provenance_selection_changed
        )
        self.show_source_button.clicked.connect(self._request_selected_source)

    @property
    def text(self) -> str:
        return self.text_view.toPlainText()

    def set_model(self, model: MLDModel) -> None:
        self.model = model
        self.text_view.setPlainText(render_mld_text(model))
        self.graphics_view.set_model(model)
        self._populate_provenance(model)
        self.copy_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.set_stale(False)

    def clear_model(self) -> None:
        self.model = None
        self.text_view.clear()
        self.graphics_view.mld_scene.clear()
        self.provenance_tree.clear()
        self.status_label.setText("MLD non généré")
        self._set_status_role("secondary")
        self.copy_button.setEnabled(False)
        self.export_button.setEnabled(False)

    def set_stale(self, stale: bool) -> None:
        if self.model is None:
            self.status_label.setText("MLD non généré")
            self._set_status_role("secondary")
        elif stale:
            self.status_label.setText("⚠ MLD obsolète — le MCD doit être régénéré")
            self._set_status_role("warning")
        else:
            self.status_label.setText("✓ MLD à jour")
            self._set_status_role("success")

    def set_dark_theme(self, enabled: bool) -> None:
        self._dark_theme = enabled
        self.graphics_view.set_dark_theme(enabled)

    def _populate_provenance(self, model: MLDModel) -> None:
        self.provenance_tree.clear()
        for table in model.tables:
            table_item = QTreeWidgetItem(
                [table.name, f"{table.source.value} · {table.source_element_id}"]
            )
            table_item.setToolTip(1, table.source_element_id)
            table_item.setData(0, Qt.ItemDataRole.UserRole, table.source_element_id)
            self.provenance_tree.addTopLevelItem(table_item)
            for column in table.columns:
                sources = [
                    value
                    for value in (
                        column.source_element_id,
                        column.source_attribute_id,
                        column.source_relation_id,
                    )
                    if value
                ]
                origin = " → ".join(sources) if sources else "Générée par MERISOR"
                column_item = QTreeWidgetItem(table_item, [column.name, origin])
                source_id = column.source_element_id or column.source_relation_id
                column_item.setData(0, Qt.ItemDataRole.UserRole, source_id)
        self.provenance_tree.expandAll()

    def _provenance_selection_changed(
        self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        source_id = (
            current.data(0, Qt.ItemDataRole.UserRole) if current is not None else None
        )
        self.show_source_button.setEnabled(
            isinstance(source_id, str) and bool(source_id)
        )

    def _request_selected_source(self) -> None:
        current = self.provenance_tree.currentItem()
        if current is None:
            return
        source_id = current.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(source_id, str) and source_id:
            self.source_requested.emit(source_id)

    def _set_status_role(self, role: str) -> None:
        self.status_label.setProperty("role", role)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def copy_text(self) -> None:
        if self.model is not None:
            QApplication.clipboard().setText(self.text)

    def export_to(self, path: str | Path) -> None:
        if self.model is None:
            raise ValueError("Aucun MLD n'a été généré.")
        Path(path).write_text(self.text, encoding="utf-8")

    def _choose_export_path(self) -> None:
        filename, _filter = QFileDialog.getSaveFileName(
            self,
            "Exporter le MLD textuel",
            "mld.txt",
            "Fichiers texte (*.txt);;Tous les fichiers (*)",
        )
        if filename:
            path = Path(filename)
            if not path.suffix:
                path = path.with_suffix(".txt")
            try:
                self.export_to(path)
            except (OSError, ValueError) as error:
                QMessageBox.critical(
                    self, "Export impossible", f"Impossible d'exporter le MLD : {error}"
                )
