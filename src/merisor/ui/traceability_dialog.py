"""Vue navigable de traçabilité MCD → MLD → SQL."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.application import ModelTraceabilityService, SQLTarget, TraceabilityReport
from merisor.domain import MCDModel, MLDModel, MLDTable


class TraceabilityDialog(QDialog):
    """Explique et relie un élément logique à ses sources et à son SQL."""

    def __init__(
        self,
        mcd: MCDModel,
        mld: MLDModel,
        table: MLDTable,
        column_id: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._mcd = mcd
        self._mld = mld
        self._table = table
        self._column_id = column_id
        self._service = ModelTraceabilityService()
        self.report: TraceabilityReport | None = None
        self.setWindowTitle("Traçabilité MCD → MLD → SQL")
        self.resize(1040, 680)

        root = QVBoxLayout(self)
        title = QLabel("ⓘ Pourquoi ? — Traçabilité complète")
        title.setProperty("role", "pageTitle")
        root.addWidget(title)
        subtitle = QLabel(
            "Sélectionnez une étape pour suivre l'origine conceptuelle, la règle "
            "MCD → MLD et sa traduction SQL. Cette analyse est déterministe et "
            "n'utilise aucune IA."
        )
        subtitle.setWordWrap(True)
        subtitle.setProperty("role", "secondary")
        root.addWidget(subtitle)

        options = QFormLayout()
        self.target_combo = QComboBox()
        for target in SQLTarget:
            self.target_combo.addItem(target.display_name, target.value)
        options.addRow("Dialecte SQL", self.target_combo)
        root.addLayout(options)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.navigation = QTreeWidget()
        self.navigation.setHeaderLabels(["Chaîne de transformation"])
        self.navigation.itemSelectionChanged.connect(self._selection_changed)
        splitter.addWidget(self.navigation)

        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        splitter.addWidget(self.details)
        splitter.setSizes([360, 680])
        root.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        self.copy_button = QPushButton("Copier la traçabilité")
        close_button = QPushButton("Fermer")
        buttons.addWidget(self.copy_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)
        root.addLayout(buttons)

        self.copy_button.clicked.connect(self._copy)
        close_button.clicked.connect(self.accept)
        self.target_combo.currentIndexChanged.connect(self._refresh)
        self._refresh()

    def _refresh(self) -> None:
        try:
            target = SQLTarget(self.target_combo.currentData())
        except (TypeError, ValueError):
            target = SQLTarget.POSTGRESQL
        self.report = self._service.trace(
            self._mcd,
            self._mld,
            self._table,
            self._column_id,
            target,
        )
        self.navigation.clear()
        mcd_root = self._root("MCD — Source de vérité", "origin")
        self._append_path(mcd_root, self.report.mcd_path, "origin")
        mld_root = self._root("MLD — Transformation", "transformation")
        self._append_path(mld_root, self.report.mld_path, "transformation")
        sql_root = self._root(
            f"SQL — {self.report.sql_target.display_name}",
            "sql",
        )
        sql_statement = QTreeWidgetItem(
            sql_root, [f"CREATE TABLE {self._table.name} (…)"]
        )
        sql_statement.setData(0, Qt.ItemDataRole.UserRole, "sql")
        self.navigation.expandAll()
        selected = mld_root.child(mld_root.childCount() - 1)
        self.navigation.setCurrentItem(selected or mld_root)

    def _root(self, label: str, section: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem([label])
        item.setData(0, Qt.ItemDataRole.UserRole, section)
        self.navigation.addTopLevelItem(item)
        return item

    @staticmethod
    def _append_path(
        parent: QTreeWidgetItem, path: tuple[str, ...], section: str
    ) -> None:
        current = parent
        for label in path:
            child = QTreeWidgetItem(current, [label])
            child.setData(0, Qt.ItemDataRole.UserRole, section)
            current = child

    def _selection_changed(self) -> None:
        report = self.report
        selected = self.navigation.selectedItems()
        if report is None or not selected:
            self.details.clear()
            return
        section = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if section == "origin":
            text = f"ORIGINE\n\n{report.origin}"
        elif section == "sql":
            text = f"SQL — {report.sql_target.display_name}\n\n{report.sql}"
        else:
            text = (
                f"TRANSFORMATION\n\n{report.transformation}\n\n"
                f"CONSÉQUENCE\n\n{report.consequence}"
            )
        self.details.setPlainText(text)

    def _copy(self) -> None:
        if self.report is not None:
            QApplication.clipboard().setText(self.report.render_text())
