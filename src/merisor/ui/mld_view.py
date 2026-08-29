"""Consultation graphique et textuelle d'un MLD généré."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
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
    QVBoxLayout,
    QWidget,
)

from merisor.application.mld_text import render_mld_text
from merisor.domain import MLDModel, MLDTable


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
        self.setZValue(5)

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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#283548"), 2))
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawRoundedRect(rectangle, 4, 4)
        painter.fillRect(
            QRectF(1, 1, self.WIDTH - 2, self.header_height - 1),
            QBrush(QColor("#e8f1fb")),
        )
        painter.drawLine(
            QPointF(0, self.header_height),
            QPointF(self.WIDTH, self.header_height),
        )
        font = QFont(painter.font())
        original_point_size = font.pointSize()
        font.setBold(True)
        painter.setFont(font)
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
            painter.setPen(QColor("#52677d"))
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
            painter.setPen(QColor("#0d5c3d") if roles else QColor("#283548"))
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
            painter.setPen(QColor("#637083"))
            painter.drawText(
                QRectF(self.WIDTH - 92, y, 82, self.ROW_HEIGHT),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                nullability,
            )
            y += self.ROW_HEIGHT

        painter.setPen(QColor("#637083"))
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
    def __init__(self, parent: QWidget | None = None) -> None:
        self.mld_scene = QGraphicsScene(parent)
        super().__init__(self.mld_scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor("#f5f7fa")))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def set_model(self, model: MLDModel) -> None:
        self.mld_scene.clear()
        items: dict[str, MLDTableGraphicsItem] = {}
        columns_per_row = 3
        horizontal_spacing = 455.0
        vertical_spacing = 320.0
        for index, table in enumerate(model.tables):
            item = MLDTableGraphicsItem(model, table)
            row, column = divmod(index, columns_per_row)
            item.setPos(column * horizontal_spacing, row * vertical_spacing)
            self.mld_scene.addItem(item)
            items[table.id] = item

        for table in model.tables:
            source_item = items[table.id]
            for foreign_key in table.foreign_keys:
                target_item = items[foreign_key.referenced_table_id]
                start = source_item.sceneBoundingRect().center()
                end = target_item.sceneBoundingRect().center()
                line = QGraphicsLineItem(start.x(), start.y(), end.x(), end.y())
                line.setPen(QPen(QColor("#60758a"), 1.7))
                line.setZValue(0)
                self.mld_scene.addItem(line)
                label = QGraphicsSimpleTextItem("FK")
                label.setBrush(QBrush(QColor("#36536e")))
                label.setPos((start + end) / 2 + QPointF(4, -16))
                label.setZValue(1)
                self.mld_scene.addItem(label)

        self.mld_scene.setSceneRect(
            self.mld_scene.itemsBoundingRect().adjusted(-40, -40, 40, 40)
        )
        if model.tables:
            self.fitInView(
                self.mld_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
            )


class MLDView(QWidget):
    """Vue du dernier MLD ; le contrôleur reste propriétaire de son état."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.model: MLDModel | None = None
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        self.status_label = QLabel("MLD non généré")
        font = self.status_label.font()
        font.setBold(True)
        self.status_label.setFont(font)
        header.addWidget(self.status_label)
        header.addStretch(1)
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
        layout.addWidget(self.tabs, 1)

        self.copy_button.clicked.connect(self.copy_text)
        self.export_button.clicked.connect(self._choose_export_path)

    @property
    def text(self) -> str:
        return self.text_view.toPlainText()

    def set_model(self, model: MLDModel) -> None:
        self.model = model
        self.text_view.setPlainText(render_mld_text(model))
        self.graphics_view.set_model(model)
        self.copy_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.set_stale(False)

    def clear_model(self) -> None:
        self.model = None
        self.text_view.clear()
        self.graphics_view.mld_scene.clear()
        self.status_label.setText("MLD non généré")
        self.status_label.setStyleSheet("color: #637083;")
        self.copy_button.setEnabled(False)
        self.export_button.setEnabled(False)

    def set_stale(self, stale: bool) -> None:
        if self.model is None:
            self.status_label.setText("MLD non généré")
            self.status_label.setStyleSheet("color: #637083;")
        elif stale:
            self.status_label.setText(
                "⚠ MLD obsolète — le MCD doit être régénéré"
            )
            self.status_label.setStyleSheet("color: #9a6700;")
        else:
            self.status_label.setText("✓ MLD à jour")
            self.status_label.setStyleSheet("color: #18794e;")

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
