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

from merisor.domain import ModelQualityReport, QualityFinding, QualityFindingKind


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
        self.overall_progress.setFormat("Indicateur de qualité : %v / 100")
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

        self.disclaimer_label = QLabel(
            "⚠ Indicateur heuristique, pas une certification. Le score aide à orienter "
            "la relecture ; il ne prouve ni la justesse métier ni la normalisation du "
            "modèle."
        )
        self.disclaimer_label.setWordWrap(True)
        self.disclaimer_label.setStyleSheet(
            "background: #fff4ce; color: #5c4400; border: 1px solid #d6b656; "
            "border-radius: 4px; padding: 8px; font-weight: bold;"
        )
        self.disclaimer_label.setToolTip(report.score_explanation)
        layout.addWidget(self.disclaimer_label)

        self.summary_label = QLabel(
            f"❌ {len(report.errors)} erreur(s) structurelle(s)   ·   "
            f"⚠ {len(report.risks)} risque(s)   ·   "
            f"💡 {len(report.suggestions)} suggestion(s)"
        )
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        tabs = QTabWidget()
        self.score_tree = self._score_tree(report)
        self.findings_tree = self._findings_tree(report)
        tabs.addTab(self.score_tree, "Scores détaillés")
        tabs.addTab(
            self.findings_tree,
            f"Constats ({len(report.all_findings)})",
        )
        layout.addWidget(tabs, 1)

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
        tree.setHeaderLabels(["Nature / catégorie", "Confiance", "Constat", "Action"])
        tree.setAlternatingRowColors(True)
        tree.setRootIsDecorated(True)
        tree.setColumnWidth(0, 210)
        tree.setColumnWidth(1, 100)
        tree.setColumnWidth(2, 360)
        tree.header().setStretchLastSection(True)
        groups = (
            (
                QualityFindingKind.ERROR,
                "❌ Erreurs structurelles",
                report.errors,
                "À corriger avant les transformations bloquantes",
            ),
            (
                QualityFindingKind.RISK,
                "⚠ Risques à examiner",
                report.risks,
                "À confirmer selon le contexte métier",
            ),
            (
                QualityFindingKind.SUGGESTION,
                "💡 Suggestions possibles",
                report.suggestions,
                "Améliorations facultatives à valider humainement",
            ),
        )
        for kind, label, findings, explanation in groups:
            root = QTreeWidgetItem([f"{label} ({len(findings)})", "", explanation, ""])
            root.setData(0, Qt.ItemDataRole.UserRole, kind.value)
            tree.addTopLevelItem(root)
            for finding in findings:
                root.addChild(QualityReportDialog._finding_item(finding))
        tree.expandAll()
        return tree

    @staticmethod
    def _finding_item(finding: QualityFinding) -> QTreeWidgetItem:
        suggested = finding.suggested_value or (
            "Corriger dans le MCD"
            if finding.kind is QualityFindingKind.ERROR
            else "À vérifier"
        )
        item = QTreeWidgetItem(
            [
                finding.category.label,
                finding.confidence.label,
                finding.message,
                suggested,
            ]
        )
        item.setToolTip(
            2,
            f"{finding.rationale}\nCode : {finding.code}\n"
            f"Nature : {finding.kind.label}",
        )
        item.setData(0, Qt.ItemDataRole.UserRole, finding.element_ids)
        return item
