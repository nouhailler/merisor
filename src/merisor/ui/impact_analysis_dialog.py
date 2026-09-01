"""Dialogue interactif d'analyse d'impact du modèle courant."""

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

from merisor.application import ImpactCertainty, ImpactReport, ModelImpactAnalyzer
from merisor.domain import MCDModel


class ImpactAnalysisDialog(QDialog):
    def __init__(
        self,
        model: MCDModel,
        selected_id: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.model = model
        self.analyzer = ModelImpactAnalyzer()
        self.current_report: ImpactReport | None = None
        self.setWindowTitle("Analyse d'impact")
        self.resize(1000, 680)

        intro = QLabel(
            "<h2>Analyse d'impact</h2>"
            "<p>Identifiez ce qui devra être vérifié avant de renommer, modifier "
            "ou supprimer un objet. Les dépendances formelles sont séparées des "
            "correspondances heuristiques.</p>"
        )
        intro.setWordWrap(True)
        self.target_combo = QComboBox()
        self.target_combo.setEditable(True)
        self.target_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for target in self.analyzer.targets(model):
            self.target_combo.addItem(f"{target.label} — {target.kind}", target.id)

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Dépendance", "Catégorie", "Pourquoi ?"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 300)
        self.tree.setColumnWidth(1, 180)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.tree)
        splitter.addWidget(self.details)
        splitter.setSizes([640, 360])

        copy_button = QPushButton("Copier le rapport")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        footer = QHBoxLayout()
        footer.addWidget(copy_button)
        footer.addStretch(1)
        footer.addWidget(buttons)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(QLabel("Élément à analyser :"))
        layout.addWidget(self.target_combo)
        layout.addWidget(self.summary)
        layout.addWidget(splitter, 1)
        layout.addLayout(footer)

        self.target_combo.currentIndexChanged.connect(self._analyze_current)
        self.tree.currentItemChanged.connect(self._show_reference)
        copy_button.clicked.connect(self._copy_report)
        if selected_id is not None:
            selected_index = self.target_combo.findData(selected_id)
            if selected_index >= 0:
                self.target_combo.setCurrentIndex(selected_index)
        self._analyze_current()

    def _analyze_current(self, _index: int = -1) -> None:
        target_id = self.target_combo.currentData()
        if not isinstance(target_id, str):
            self.tree.clear()
            self.summary.setText("Aucun élément disponible.")
            return
        report = self.analyzer.analyze(self.model, target_id)
        self.current_report = report
        self.summary.setText(
            f"<b>Risque {report.risk_level}</b> — "
            f"{len(report.certain)} dépendance(s) certaine(s), "
            f"{report.relation_count} relation(s), "
            f"{report.constraint_count} contrainte(s) et "
            f"{len(report.potential)} correspondance(s) à confirmer."
        )
        colors = {
            ImpactCertainty.CERTAIN: QColor("#b42318"),
            ImpactCertainty.POTENTIAL: QColor("#9a6700"),
        }
        self.tree.clear()
        groups = (
            ("Impacts certains", report.certain),
            ("À confirmer", report.potential),
        )
        for group_label, references in groups:
            root = QTreeWidgetItem([group_label, "", ""])
            root.setExpanded(True)
            font = root.font(0)
            font.setBold(True)
            root.setFont(0, font)
            self.tree.addTopLevelItem(root)
            for reference in references:
                item = QTreeWidgetItem(
                    [reference.label, reference.category, reference.reason]
                )
                item.setData(0, Qt.ItemDataRole.UserRole, reference.reason)
                item.setForeground(0, colors[reference.certainty])
                root.addChild(item)
        self.tree.expandAll()
        self.details.setPlainText(report.render())

    def _show_reference(
        self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        if current is None:
            return
        reason = current.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(reason, str):
            self.details.setPlainText(
                f"{current.text(0)}\n\nCatégorie : {current.text(1)}\n\n{reason}"
            )

    def _copy_report(self) -> None:
        if self.current_report is not None:
            QApplication.clipboard().setText(self.current_report.render())
