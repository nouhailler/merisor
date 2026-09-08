"""Interface de test fonctionnel d'un MCD par scénarios métier."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.application import (
    BusinessScenarioAnalyzer,
    BusinessScenarioReport,
    ScenarioCheckStatus,
    parse_scenario,
)
from merisor.domain import MCDModel


class BusinessScenarioDialog(QDialog):
    """Saisit des attentes métier et montre ce que le MCD permet de vérifier."""

    def __init__(self, model: MCDModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.model = model
        self.analyzer = BusinessScenarioAnalyzer()
        self.current_report: BusinessScenarioReport | None = None
        self.setWindowTitle("Scénarios métier — test fonctionnel du MCD")
        self.resize(1060, 720)

        intro = QLabel(
            "<h2>Scénarios métier</h2>"
            "<p>Décrivez un usage réel puis formulez une attente par ligne. "
            "MERISOR vérifie le chemin, les cardinalités et les attributs visibles "
            "dans le MCD, sans modifier le modèle.</p>"
        )
        intro.setWordWrap(True)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Ex. Emprunter un livre")
        self.expectations_edit = QPlainTextEdit()
        self.expectations_edit.setPlaceholderText(
            "Un lecteur peut effectuer plusieurs emprunts\n"
            "Un emprunt possède une date de début\n"
            "Un emprunt possède une date de retour\n"
            "Déterminer si un exemplaire est disponible à une date donnée"
        )
        self.expectations_edit.setMinimumHeight(145)
        form = QFormLayout()
        form.addRow("Nom du scénario :", self.title_edit)
        form.addRow("Attentes métier :", self.expectations_edit)

        self.analyze_button = QPushButton("Analyser le scénario")
        self.analyze_button.setDefault(True)
        self.summary_label = QLabel("Saisissez un scénario pour commencer.")
        self.summary_label.setWordWrap(True)
        action_row = QHBoxLayout()
        action_row.addWidget(self.analyze_button)
        action_row.addWidget(self.summary_label, 1)

        self.path_view = QPlainTextEdit()
        self.path_view.setReadOnly(True)
        self.path_view.setPlaceholderText("Le chemin métier apparaîtra ici.")
        self.checks_tree = QTreeWidget()
        self.checks_tree.setHeaderLabels(["État", "Attente métier", "Explication"])
        self.checks_tree.setAlternatingRowColors(True)
        self.checks_tree.setColumnWidth(0, 130)
        self.checks_tree.setColumnWidth(1, 330)
        self.checks_tree.header().setStretchLastSection(True)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.path_view)
        splitter.addWidget(self.checks_tree)
        splitter.setSizes([300, 700])

        self.copy_button = QPushButton("Copier le rapport")
        self.copy_button.setEnabled(False)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        footer = QHBoxLayout()
        footer.addWidget(self.copy_button)
        footer.addStretch(1)
        footer.addWidget(buttons)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addLayout(form)
        layout.addLayout(action_row)
        layout.addWidget(splitter, 1)
        layout.addLayout(footer)

        self.analyze_button.clicked.connect(self.analyze)
        self.copy_button.clicked.connect(self.copy_report)

    def analyze(self, _checked: bool = False) -> None:
        try:
            scenario = parse_scenario(
                self.title_edit.text(), self.expectations_edit.toPlainText()
            )
        except ValueError as error:
            QMessageBox.warning(self, "Scénario incomplet", str(error))
            return
        report = self.analyzer.analyze(self.model, scenario)
        self.current_report = report
        self.copy_button.setEnabled(True)
        self._display_path(report)
        self._display_checks(report)
        self.summary_label.setText(
            f"✓ {len(report.satisfied)} satisfaite(s) · "
            f"⚠ {len(report.risks)} risque(s) · "
            f"? {len(report.unverifiable)} non vérifiable(s)"
        )

    def _display_path(self, report: BusinessScenarioReport) -> None:
        if not report.path:
            self.path_view.setPlainText(
                "Aucun concept reconnu.\n\nUtilisez dans les attentes les noms "
                "des entités ou associations du MCD."
            )
            return
        lines: list[str] = []
        for index, element in enumerate(report.path):
            if index:
                lines.append("        │\n        ▼")
            lines.append(f"[{element.kind}]\n{element.label}")
        self.path_view.setPlainText("\n".join(lines))

    def _display_checks(self, report: BusinessScenarioReport) -> None:
        self.checks_tree.clear()
        metadata = {
            ScenarioCheckStatus.SATISFIED: ("✓ Satisfait", QColor("#18794e")),
            ScenarioCheckStatus.RISK: ("⚠ Risque", QColor("#9a6700")),
            ScenarioCheckStatus.UNVERIFIABLE: (
                "? Non vérifiable",
                QColor("#57606a"),
            ),
        }
        for check in report.checks:
            label, color = metadata[check.status]
            item = QTreeWidgetItem([label, check.expectation, check.explanation])
            item.setForeground(0, color)
            item.setToolTip(2, check.explanation)
            item.setData(0, Qt.ItemDataRole.UserRole, check.element_ids)
            self.checks_tree.addTopLevelItem(item)

    def copy_report(self, _checked: bool = False) -> None:
        if self.current_report is not None:
            QApplication.clipboard().setText(self.current_report.render())
