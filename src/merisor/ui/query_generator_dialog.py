"""Description, aperçu et export d'une requête SELECT dérivée du MLD."""

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

from merisor.application import (
    QueryGenerationError,
    QueryGenerationResult,
    QueryTarget,
    SQLQueryGenerator,
)
from merisor.domain import MLDModel


class QueryGeneratorDialog(QDialog):
    """Génère un SELECT depuis un MLD sans jamais l'exécuter."""

    def __init__(
        self,
        model: MLDModel,
        project_name: str,
        parent: QWidget | None = None,
        generator: SQLQueryGenerator | None = None,
    ) -> None:
        super().__init__(parent)
        self.model = model
        self.project_name = project_name
        self.generator = generator or SQLQueryGenerator()
        self.generation_result: QueryGenerationResult | None = None
        self.setWindowTitle("Générer une requête SQL")
        self.resize(940, 740)

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Décrivez les données à consulter. Les jointures sont déduites "
            "uniquement des clés étrangères du MLD. La requête est générée, "
            "mais jamais exécutée."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        example = QLabel(
            "Exemple : « Afficher les 10 meilleurs clients selon le montant "
            "total de leurs commandes. »"
        )
        example.setWordWrap(True)
        example.setStyleSheet("color: #5b6472; font-style: italic;")
        layout.addWidget(example)

        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText(
            "Décrivez le résultat attendu en citant les concepts du modèle…"
        )
        self.description_edit.setMaximumHeight(130)
        layout.addWidget(self.description_edit)

        form = QFormLayout()
        self.target_combo = QComboBox()
        for target in QueryTarget:
            self.target_combo.addItem(target.display_name, target.value)
        form.addRow("Dialecte", self.target_combo)
        layout.addLayout(form)

        generate_row = QHBoxLayout()
        self.generate_button = QPushButton("Générer la requête")
        generate_row.addWidget(self.generate_button)
        generate_row.addStretch(1)
        layout.addLayout(generate_row)

        self.tables_label = QLabel("Tables utilisées : —")
        self.tables_label.setWordWrap(True)
        self.tables_label.setStyleSheet("font-weight: bold; color: #26364f;")
        layout.addWidget(self.tables_label)
        self.report_label = QLabel()
        self.report_label.setWordWrap(True)
        layout.addWidget(self.report_label)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        font = QFont("monospace")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.preview.setFont(font)
        layout.addWidget(self.preview, 1)

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

        self.generate_button.clicked.connect(self.generate_preview)
        self.description_edit.textChanged.connect(self._invalidate_preview)
        self.target_combo.currentIndexChanged.connect(self._invalidate_preview)
        self.copy_button.clicked.connect(self.copy_query)
        self.save_button.clicked.connect(self._choose_export_path)
        self._set_export_enabled(False)

    @property
    def target(self) -> QueryTarget:
        return QueryTarget(self.target_combo.currentData())

    @property
    def query(self) -> str:
        return self.preview.toPlainText()

    def generate_preview(self, _checked: bool = False) -> bool:
        self.generation_result = None
        try:
            self.generation_result = self.generator.generate(
                self.model,
                self.description_edit.toPlainText(),
                self.target,
            )
        except QueryGenerationError as error:
            self.preview.setPlainText(
                "Impossible de générer la requête.\n\n"
                + "\n".join(f"• {problem}" for problem in error.problems)
            )
            self.tables_label.setText("Tables utilisées : —")
            self.report_label.setText(
                f"❌ {len(error.problems)} problème(s) bloquent la génération."
            )
            self.report_label.setStyleSheet("color: #b42318; font-weight: bold;")
            self._set_export_enabled(False)
            return False

        result = self.generation_result
        self.preview.setPlainText(result.sql)
        self.tables_label.setText(
            "Cette requête utilise les tables : " + ", ".join(result.used_tables) + "."
        )
        messages = [f"✓ {item}" for item in result.explanation]
        messages.extend(f"⚠ {item}" for item in result.warnings)
        self.report_label.setText("\n".join(messages))
        self.report_label.setStyleSheet(
            "color: #8a5a00;" if result.warnings else "color: #18794e;"
        )
        self._set_export_enabled(True)
        return True

    def copy_query(self) -> None:
        if self.copy_button.isEnabled():
            QApplication.clipboard().setText(self.query)

    def export_to(self, path: str | Path) -> Path:
        if not self.save_button.isEnabled() or self.generation_result is None:
            raise ValueError("Aucune requête valide n'est disponible.")
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(".sql")
        target.write_text(self.generation_result.sql, encoding="utf-8")
        return target

    def _choose_export_path(self) -> None:
        project = (
            re.sub(r"[^0-9A-Za-z_-]+", "_", self.project_name.strip()).strip("_")
            or "modele"
        )
        filename, _filter = QFileDialog.getSaveFileName(
            self,
            "Enregistrer la requête SQL",
            f"{project}_requete_{self.target.value}.sql",
            "Requêtes SQL (*.sql);;Tous les fichiers (*)",
        )
        if not filename:
            return
        try:
            self.export_to(filename)
        except (OSError, ValueError) as error:
            QMessageBox.critical(
                self,
                "Export impossible",
                f"Impossible d'enregistrer la requête : {error}",
            )

    def _invalidate_preview(self, _value: int = -1) -> None:
        self.generation_result = None
        self.tables_label.setText("Tables utilisées : —")
        self.report_label.setText("Description modifiée : cliquez sur Générer.")
        self.report_label.setStyleSheet("color: #5b6472;")
        self._set_export_enabled(False)

    def _set_export_enabled(self, enabled: bool) -> None:
        self.copy_button.setEnabled(enabled)
        self.save_button.setEnabled(enabled)
