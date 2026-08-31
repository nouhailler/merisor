"""Choix du dialecte, aperçu, copie et export d'un script SQL généré."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from merisor.application import SQLGenerationError, SQLGenerator, SQLTarget
from merisor.domain import MLDModel


class SQLPreviewDialog(QDialog):
    """Le dialogue ne reçoit qu'un MLD ; il ne connaît jamais le MCD."""

    def __init__(
        self,
        model: MLDModel,
        project_name: str,
        parent: QWidget | None = None,
        generator: SQLGenerator | None = None,
    ) -> None:
        super().__init__(parent)
        self.model = model
        self.project_name = project_name
        self.generator = generator or SQLGenerator()
        self.setWindowTitle("Générer SQL")
        self.resize(900, 680)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.target_combo = QComboBox()
        for target in SQLTarget:
            self.target_combo.addItem(target.display_name, target.value)
        form.addRow("SGBD cible", self.target_combo)
        layout.addLayout(form)

        self.report_label = QLabel()
        self.report_label.setWordWrap(True)
        layout.addWidget(self.report_label)

        self.sql_preview = QPlainTextEdit()
        self.sql_preview.setReadOnly(True)
        font = QFont("monospace")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.sql_preview.setFont(font)
        layout.addWidget(self.sql_preview, 1)

        actions = QHBoxLayout()
        self.copy_button = QPushButton("Copier")
        self.save_button = QPushButton("Enregistrer sous…")
        actions.addWidget(self.copy_button)
        actions.addWidget(self.save_button)
        actions.addStretch(1)
        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_buttons.rejected.connect(self.reject)
        actions.addWidget(close_buttons)
        layout.addLayout(actions)

        self.target_combo.currentIndexChanged.connect(self.generate_preview)
        self.copy_button.clicked.connect(self.copy_sql)
        self.save_button.clicked.connect(self._choose_export_path)
        self.generate_preview()

    @property
    def target(self) -> SQLTarget:
        return SQLTarget(self.target_combo.currentData())

    @property
    def script(self) -> str:
        return self.sql_preview.toPlainText()

    def generate_preview(self, _index: int = -1) -> bool:
        report = self.generator.validate(self.model, self.target)
        if report.errors:
            messages = "\n".join(f"• {issue.message}" for issue in report.errors)
            self.sql_preview.setPlainText(
                "Impossible de générer le SQL.\n\n"
                f"{len(report.errors)} erreur(s) dans le MLD :\n{messages}"
            )
            self.report_label.setText(
                f"❌ {len(report.errors)} erreur(s) bloquent la génération."
            )
            self.report_label.setStyleSheet("color: #b42318; font-weight: bold;")
            self.copy_button.setEnabled(False)
            self.save_button.setEnabled(False)
            return False
        try:
            script = self.generator.generate(
                self.model,
                self.target,
                project_name=self.project_name,
            )
        except SQLGenerationError as error:
            self.sql_preview.setPlainText(str(error))
            self.copy_button.setEnabled(False)
            self.save_button.setEnabled(False)
            return False
        self.sql_preview.setPlainText(script)
        if report.warnings:
            messages = "\n".join(f"⚠ {issue.message}" for issue in report.warnings)
            self.report_label.setText(messages)
            self.report_label.setStyleSheet("color: #8a5a00;")
        else:
            self.report_label.setText(
                f"✓ Script {self.target.display_name} généré depuis le MLD."
            )
            self.report_label.setStyleSheet("color: #18794e; font-weight: bold;")
        self.copy_button.setEnabled(True)
        self.save_button.setEnabled(True)
        return True

    def copy_sql(self) -> None:
        if self.copy_button.isEnabled():
            QApplication.clipboard().setText(self.script)

    def export_to(self, path: str | Path) -> Path:
        if not self.save_button.isEnabled():
            raise ValueError("Aucun script SQL valide n'est disponible.")
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(".sql")
        target.write_text(self.script, encoding="utf-8")
        return target

    def _choose_export_path(self) -> None:
        project = (
            re.sub(r"[^0-9A-Za-z_-]+", "_", self.project_name.strip()).strip("_")
            or "modele"
        )
        suggested = f"{project}_{self.target.value}.sql"
        filename, _filter = QFileDialog.getSaveFileName(
            self,
            "Enregistrer le script SQL",
            suggested,
            "Scripts SQL (*.sql);;Tous les fichiers (*)",
        )
        if not filename:
            return
        try:
            self.export_to(filename)
        except (OSError, ValueError) as error:
            QMessageBox.critical(
                self,
                "Export impossible",
                f"Impossible d'enregistrer le script SQL : {error}",
            )
