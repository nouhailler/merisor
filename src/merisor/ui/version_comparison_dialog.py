"""Dialogue de consultation des différences entre deux versions du MCD."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.application import ChangeKind, VersionComparison


class VersionComparisonDialog(QDialog):
    """Rapport filtrable ; aucune action ne modifie le document courant."""

    def __init__(
        self,
        comparison: VersionComparison,
        reference_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.comparison = comparison
        self.setWindowTitle("Comparer avec une version")
        self.resize(1050, 680)

        title = QLabel(
            f"<h2>Comparaison de versions</h2>"
            f"<p><b>Référence :</b> {reference_name}<br>"
            "<b>Cible :</b> modèle actuellement ouvert</p>"
        )
        self.summary_label = QLabel()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Rechercher un objet ou une propriété…")
        self.kind_combo = QComboBox()
        self.kind_combo.addItem("Tous les changements", None)
        self.kind_combo.addItem("Ajouts", ChangeKind.ADDED)
        self.kind_combo.addItem("Modifications", ChangeKind.MODIFIED)
        self.kind_combo.addItem("Suppressions", ChangeKind.REMOVED)

        filters = QHBoxLayout()
        filters.addWidget(self.search_edit, 1)
        filters.addWidget(self.kind_combo)

        self.change_tree = QTreeWidget()
        self.change_tree.setHeaderLabels(["Changement", "Objet", "Détail"])
        self.change_tree.setRootIsDecorated(False)
        self.change_tree.setAlternatingRowColors(True)
        self.change_tree.setColumnWidth(0, 130)
        self.change_tree.setColumnWidth(1, 300)

        self.impact_view = QPlainTextEdit()
        self.impact_view.setReadOnly(True)
        self.impact_view.setPlaceholderText(
            "Sélectionnez un changement pour afficher ses impacts."
        )
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.change_tree)
        splitter.addWidget(self.impact_view)
        splitter.setSizes([650, 400])

        copy_button = QPushButton("Copier le rapport")
        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_buttons.rejected.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addWidget(copy_button)
        buttons.addStretch(1)
        buttons.addWidget(close_buttons)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(self.summary_label)
        layout.addLayout(filters)
        layout.addWidget(splitter, 1)
        layout.addLayout(buttons)

        self.search_edit.textChanged.connect(self._refresh)
        self.kind_combo.currentIndexChanged.connect(self._refresh)
        self.change_tree.currentItemChanged.connect(self._selection_changed)
        copy_button.clicked.connect(self._copy_report)
        self._refresh_summary()
        self._refresh()

    def _refresh_summary(self) -> None:
        comparison = self.comparison
        if comparison.identical:
            self.summary_label.setText("✓ Aucune différence logique détectée.")
            self.summary_label.setStyleSheet("color: #157347; font-weight: 600;")
            return
        self.summary_label.setText(
            f"<b>{len(comparison.changes)} changement(s)</b> — "
            f"<span style='color:#157347'>+ {comparison.count(ChangeKind.ADDED)}</span> · "
            f"<span style='color:#9a6700'>~ {comparison.count(ChangeKind.MODIFIED)}</span> · "
            f"<span style='color:#b42318'>- {comparison.count(ChangeKind.REMOVED)}</span>"
        )

    def _refresh(self, _value: object = None) -> None:
        query = self.search_edit.text().strip().casefold()
        selected_kind = self.kind_combo.currentData()
        self.change_tree.clear()
        colors = {
            ChangeKind.ADDED: QColor("#157347"),
            ChangeKind.MODIFIED: QColor("#9a6700"),
            ChangeKind.REMOVED: QColor("#b42318"),
        }
        labels = {
            ChangeKind.ADDED: "+ Ajout",
            ChangeKind.MODIFIED: "~ Modification",
            ChangeKind.REMOVED: "- Suppression",
        }
        for index, change in enumerate(self.comparison.changes):
            if selected_kind is not None and change.kind is not selected_kind:
                continue
            searchable = f"{change.category} {change.path} {change.detail}".casefold()
            if query and query not in searchable:
                continue
            item = QTreeWidgetItem(
                [
                    labels[change.kind],
                    change.path,
                    f"{change.category} : {change.detail}",
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, index)
            item.setForeground(0, colors[change.kind])
            item.setToolTip(1, change.render())
            self.change_tree.addTopLevelItem(item)
        self.change_tree.resizeColumnToContents(0)
        if self.change_tree.topLevelItemCount():
            first_item = self.change_tree.topLevelItem(0)
            if first_item is not None:
                self.change_tree.setCurrentItem(first_item)
        else:
            self.impact_view.clear()

    def _selection_changed(
        self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        if current is None:
            self.impact_view.clear()
            return
        index = current.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(index, int):
            change = self.comparison.changes[index]
            self.impact_view.setPlainText(
                f"{change.render()}\n\n{change.impact.render()}"
            )

    def _copy_report(self) -> None:
        QApplication.clipboard().setText(self.comparison.render_detailed())
