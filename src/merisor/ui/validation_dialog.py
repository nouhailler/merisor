"""Présentation Qt d'un rapport de validation métier."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.domain import ValidationReport, ValidationSeverity


class ValidationDialog(QDialog):
    def __init__(self, report: ValidationReport, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Validation du MCD")
        self.resize(680, 430)
        layout = QVBoxLayout(self)
        title = QLabel("VALIDATION DU MCD")
        font = title.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 2)
        title.setFont(font)
        layout.addWidget(title)

        if not report.issues:
            summary = QLabel("✓ MCD valide — aucune erreur détectée.")
            summary.setStyleSheet("color: #18794e; font-weight: bold;")
        else:
            summary = QLabel(
                f"{len(report.errors)} erreur(s), {len(report.warnings)} avertissement(s)."
            )
            summary.setStyleSheet(
                "color: #b42318; font-weight: bold;"
                if report.errors
                else "color: #8a5a00; font-weight: bold;"
            )
        layout.addWidget(summary)

        tree = QTreeWidget()
        tree.setHeaderLabels(["Niveau", "Problème détecté"])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        tree.header().setStretchLastSection(True)
        tree.setColumnWidth(0, 125)
        for issue in report.issues:
            is_error = issue.severity is ValidationSeverity.ERROR
            item = QTreeWidgetItem(
                ["❌ Erreur" if is_error else "⚠ Avertissement", issue.message]
            )
            item.setToolTip(1, issue.code)
            tree.addTopLevelItem(item)
        layout.addWidget(tree, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
