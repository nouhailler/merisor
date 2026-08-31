"""Rapport Qt de l'analyse déterministe de qualité du MCD."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QProgressBar,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.domain import ModelQualityReport


class QualityReportDialog(QDialog):
    """Affiche scores, déductions et suggestions sans modifier le MCD."""

    def __init__(
        self,
        report: ModelQualityReport,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.report = report
        self.setWindowTitle("Qualité du modèle")
        self.resize(900, 620)

        layout = QVBoxLayout(self)
        title = QLabel("QUALITÉ DU MODÈLE")
        font = title.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 2)
        title.setFont(font)
        layout.addWidget(title)

        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setValue(report.overall_score)
        self.overall_progress.setFormat("Score global : %v %")
        self.overall_progress.setMinimumHeight(28)
        color = (
            "#18794e"
            if report.overall_score >= 80
            else "#8a5a00"
            if report.overall_score >= 60
            else "#b42318"
        )
        self.overall_progress.setStyleSheet(
            "QProgressBar { text-align: center; font-weight: bold; } "
            f"QProgressBar::chunk {{ background-color: {color}; }}"
        )
        layout.addWidget(self.overall_progress)

        explanation = QLabel(
            "Analyse locale déterministe : les suggestions sont des indices, pas des "
            "erreurs MERISE. Chaque déduction est explicitée et aucune modification "
            "n'est appliquée automatiquement."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        tabs = QTabWidget()
        self.score_tree = self._score_tree(report)
        self.findings_tree = self._findings_tree(report)
        tabs.addTab(self.score_tree, "Scores détaillés")
        tabs.addTab(
            self.findings_tree,
            f"Suggestions ({len(report.findings)})",
        )
        layout.addWidget(tabs, 1)

        if report.validation_report.errors:
            validation_note = QLabel(
                f"❌ {len(report.validation_report.errors)} erreur(s) structurelle(s) "
                "réduisent également le score. Utilisez « Valider le MCD » pour les "
                "examiner."
            )
            validation_note.setWordWrap(True)
            validation_note.setStyleSheet("color: #b42318; font-weight: bold;")
            layout.addWidget(validation_note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    @staticmethod
    def _score_tree(report: ModelQualityReport) -> QTreeWidget:
        tree = QTreeWidget()
        tree.setHeaderLabels(["Dimension", "Score", "Poids", "Explication"])
        tree.setAlternatingRowColors(True)
        tree.setColumnWidth(0, 220)
        tree.setColumnWidth(1, 90)
        tree.setColumnWidth(2, 80)
        tree.header().setStretchLastSection(True)
        for dimension in report.dimensions:
            item = QTreeWidgetItem(
                [
                    dimension.label,
                    f"{dimension.score} %",
                    f"{dimension.weight} %",
                    (
                        f"{len(dimension.deductions)} déduction(s)"
                        if dimension.deductions
                        else "Aucune déduction"
                    ),
                ]
            )
            if dimension.score >= 90:
                item.setText(0, f"✓ {dimension.label}")
            elif dimension.score >= 70:
                item.setText(0, f"⚠ {dimension.label}")
            else:
                item.setText(0, f"❌ {dimension.label}")
            tree.addTopLevelItem(item)
            for deduction in dimension.deductions:
                detail = QTreeWidgetItem(["", "", "", f"- {deduction}"])
                detail.setToolTip(3, deduction)
                item.addChild(detail)
        tree.expandAll()
        return tree

    @staticmethod
    def _findings_tree(report: ModelQualityReport) -> QTreeWidget:
        tree = QTreeWidget()
        tree.setHeaderLabels(["Catégorie", "Confiance", "Observation", "Suggestion"])
        tree.setAlternatingRowColors(True)
        tree.setRootIsDecorated(False)
        tree.setColumnWidth(0, 175)
        tree.setColumnWidth(1, 100)
        tree.setColumnWidth(2, 390)
        tree.header().setStretchLastSection(True)
        for finding in report.findings:
            suggested = finding.suggested_value or "À vérifier"
            item = QTreeWidgetItem(
                [
                    finding.category.label,
                    finding.confidence.label,
                    finding.message,
                    suggested,
                ]
            )
            item.setToolTip(2, f"{finding.rationale}\nCode : {finding.code}")
            item.setData(0, Qt.ItemDataRole.UserRole, finding.element_ids)
            tree.addTopLevelItem(item)
        return tree
