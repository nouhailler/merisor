"""Panneau en lecture seule des propriétés d'une table MLD."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHeaderView,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.domain import MLDTable


class MLDPropertiesPanel(QWidget):
    """Affiche la structure de la table MLD sélectionnée dans le graphe."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        title = QLabel("PROPRIÉTÉS MLD")
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        form = QFormLayout()
        self.table_name = QLabel("—")
        self.table_name.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.table_source = QLabel("—")
        self.table_source.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.table_identifier = QLabel("—")
        self.table_identifier.setWordWrap(True)
        self.table_identifier.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        form.addRow("Table", self.table_name)
        form.addRow("Source", self.table_source)
        form.addRow("ID interne", self.table_identifier)
        layout.addLayout(form)

        self.columns = QTreeWidget()
        self.columns.setHeaderLabels(["Rôle", "Colonne", "Type", "Null"])
        self.columns.setRootIsDecorated(False)
        self.columns.setAlternatingRowColors(True)
        self.columns.header().setStretchLastSection(False)
        self.columns.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.columns, 1)

        self.foreign_keys = QLabel("—")
        self.foreign_keys.setWordWrap(True)
        self.foreign_keys.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(QLabel("Clés étrangères"))
        layout.addWidget(self.foreign_keys)
        self.clear()

    def clear(self) -> None:
        self.table_name.setText("—")
        self.table_source.setText("—")
        self.table_identifier.setText("—")
        self.columns.clear()
        self.foreign_keys.setText("—")

    def display(self, table: MLDTable | None) -> None:
        if table is None:
            self.clear()
            return
        self.table_name.setText(table.name)
        self.table_source.setText(table.source.value)
        self.table_identifier.setText(table.id)
        self.columns.clear()
        for column in table.columns:
            roles: list[str] = []
            if table.is_primary_key(column.id):
                roles.append("PK")
            if table.is_foreign_key(column.id):
                roles.append("FK")
            if table.is_unique(column.id):
                roles.append("UQ")
            if column.auto_increment:
                roles.append("AI")
            item = QTreeWidgetItem(
                [
                    "/".join(roles),
                    column.name,
                    column.data_type.label,
                    "NULL"
                    if column.nullable is True
                    else "NOT NULL"
                    if column.nullable is False
                    else "—",
                ]
            )
            self.columns.addTopLevelItem(item)
        fk_lines = []
        for foreign_key in table.foreign_keys:
            local = ", ".join(
                table.column_by_id(cid).name for cid in foreign_key.column_ids
            )
            fk_lines.append(f"{local} → {foreign_key.referenced_table_id}")
        self.foreign_keys.setText("\n".join(fk_lines) if fk_lines else "Aucune")
