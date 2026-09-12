"""Dialogue « Et si… ? » de simulation avant suppression."""

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
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.application import (
    ImpactCertainty,
    ImpactLayer,
    WhatIfAnalyzer,
    WhatIfReport,
)
from merisor.domain import MCDModel


class WhatIfImpactDialog(QDialog):
    """Expose les conséquences calculables et attend une confirmation explicite."""

    def __init__(
        self,
        model: MCDModel,
        selected_id: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.model = model
        self.analyzer = WhatIfAnalyzer()
        self.current_report: WhatIfReport | None = None
        self.setWindowTitle("Et si… ? — Analyse d'impact")
        self.resize(1060, 720)

        intro = QLabel(
            "<h2>⚠ Et si… ?</h2>"
            "<p>Simulez une suppression avant de toucher au MCD. Les dépendances "
            "certaines sont séparées des livrables à régénérer ou usages que "
            "MERISOR ne peut pas compter.</p>"
        )
        intro.setWordWrap(True)
        self.target_combo = QComboBox()
        self.target_combo.setEditable(True)
        self.target_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for target in self.analyzer.targets(model):
            self.target_combo.addItem(f"{target.label} — {target.kind}", target.id)
        self.operation_combo = QComboBox()
        self.operation_combo.addItem("Supprimer l'élément", "delete")

        selectors = QHBoxLayout()
        selectors.addWidget(QLabel("Élément :"))
        selectors.addWidget(self.target_combo, 1)
        selectors.addWidget(QLabel("Hypothèse :"))
        selectors.addWidget(self.operation_combo)

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(
            "background: #fff4ce; color: #5c4400; border: 1px solid #d6b656; "
            "border-radius: 4px; padding: 8px;"
        )
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Couche / impact", "Certitude", "Pourquoi ?"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 360)
        self.tree.setColumnWidth(1, 120)
        self.tree.header().setStretchLastSection(True)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.tree)
        splitter.addWidget(self.details)
        splitter.setSizes([650, 410])

        self.copy_button = QPushButton("Copier le rapport")
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.continue_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.continue_button.setText("Continuer et supprimer")
        self.continue_button.setStyleSheet("font-weight: bold; color: #b42318;")
        self.cancel_button = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        self.cancel_button.setText("Annuler")
        footer = QHBoxLayout()
        footer.addWidget(self.copy_button)
        footer.addStretch(1)
        footer.addWidget(self.buttons)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addLayout(selectors)
        layout.addWidget(self.summary_label)
        layout.addWidget(splitter, 1)
        layout.addLayout(footer)

        self.target_combo.currentIndexChanged.connect(self._analyze_current)
        self.tree.currentItemChanged.connect(self._show_item)
        self.copy_button.clicked.connect(self._copy_report)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        if selected_id is not None:
            index = self.target_combo.findData(selected_id)
            if index >= 0:
                self.target_combo.setCurrentIndex(index)
        self._analyze_current()

    @property
    def target_id(self) -> str | None:
        return self.current_report.target.id if self.current_report else None

    def _analyze_current(self, _index: int = -1) -> None:
        target_id = self.target_combo.currentData()
        if not isinstance(target_id, str):
            self.current_report = None
            self.tree.clear()
            self.details.setPlainText("Le MCD ne contient aucun élément analysable.")
            self.continue_button.setEnabled(False)
            return
        report = self.analyzer.analyze_delete(self.model, target_id)
        self.current_report = report
        self.continue_button.setEnabled(True)
        validation = (
            f" · ❌ {len(report.new_validation_errors)} nouvelle(s) erreur(s) MCD"
            if report.new_validation_errors
            else " · aucune nouvelle erreur structurelle"
        )
        self.summary_label.setText(
            f"Suppression simulée : <b>{report.target.label}</b> — "
            f"{len(report.certain)} impact(s) certain(s), "
            f"{len(report.potential)} élément(s) à régénérer ou confirmer"
            f"{validation}. Aucune modification n'est encore appliquée."
        )
        self._populate_tree(report)
        self.details.setPlainText(report.render())

    def _populate_tree(self, report: WhatIfReport) -> None:
        self.tree.clear()
        for layer in ImpactLayer:
            impacts = report.for_layer(layer)
            root = QTreeWidgetItem([f"{layer.label} ({len(impacts)})", "", ""])
            font = root.font(0)
            font.setBold(True)
            root.setFont(0, font)
            self.tree.addTopLevelItem(root)
            for impact in impacts:
                certain = impact.certainty is ImpactCertainty.CERTAIN
                item = QTreeWidgetItem(
                    [
                        impact.label,
                        "Certain" if certain else "À confirmer",
                        impact.reason,
                    ]
                )
                item.setForeground(0, QColor("#b42318" if certain else "#9a6700"))
                item.setData(0, Qt.ItemDataRole.UserRole, impact.reason)
                root.addChild(item)
            root.setExpanded(True)
        if report.new_validation_errors:
            root = QTreeWidgetItem(
                [
                    f"Erreurs créées ({len(report.new_validation_errors)})",
                    "Certain",
                    "Résultat du validateur sur la copie simulée",
                ]
            )
            root.setForeground(0, QColor("#b42318"))
            self.tree.addTopLevelItem(root)
            for message in report.new_validation_errors:
                root.addChild(QTreeWidgetItem([message, "Certain", "Validation MCD"]))
            root.setExpanded(True)

    def _show_item(
        self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        if current is None:
            return
        reason = current.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(reason, str):
            self.details.setPlainText(
                f"{current.text(0)}\n\nCertitude : {current.text(1)}\n\n{reason}"
            )

    def _copy_report(self, _checked: bool = False) -> None:
        if self.current_report is not None:
            QApplication.clipboard().setText(self.current_report.render())
