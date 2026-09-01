"""Configuration, aperçu et export des INSERT de données de test."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.application import (
    SQLTarget,
    TestDataGenerationError,
    TestDataGenerationResult,
    TestDataGenerator,
)
from merisor.domain import MLDModel


class TestDataDialog(QDialog):
    """Le dialogue ne reçoit qu'un MLD et n'exécute jamais son résultat."""

    MAX_INTERACTIVE_ROWS = 10_000

    def __init__(
        self,
        model: MLDModel,
        project_name: str,
        parent: QWidget | None = None,
        generator: TestDataGenerator | None = None,
    ) -> None:
        super().__init__(parent)
        self.model = model
        self.project_name = project_name
        self.generator = generator or TestDataGenerator()
        self.generation_result: TestDataGenerationResult | None = None
        self._count_editors: dict[str, QSpinBox] = {}
        self.setWindowTitle("Générer des données de test")
        self.resize(980, 760)

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Définissez le nombre de lignes par table. MERISOR génère uniquement "
            "un script INSERT : aucune base n'est contactée et rien n'est exécuté."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        self.target_combo = QComboBox()
        for target in SQLTarget:
            self.target_combo.addItem(target.display_name, target.value)
        form.addRow("Dialecte", self.target_combo)
        layout.addLayout(form)

        self.count_table = QTableWidget(len(model.tables), 2)
        self.count_table.setHorizontalHeaderLabels(("Table", "Nombre de lignes"))
        self.count_table.verticalHeader().setVisible(False)
        header = self.count_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        for row, table in enumerate(
            sorted(model.tables, key=lambda item: (item.name.casefold(), item.id))
        ):
            name = QTableWidgetItem(table.name)
            name.setFlags(name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.count_table.setItem(row, 0, name)
            count = QSpinBox()
            count.setRange(0, self.MAX_INTERACTIVE_ROWS)
            count.setValue(TestDataGenerator.DEFAULT_ROWS)
            count.setSuffix(" ligne(s)")
            self.count_table.setCellWidget(row, 1, count)
            self._count_editors[table.id] = count
        layout.addWidget(self.count_table, 2)

        generate_row = QHBoxLayout()
        self.generate_button = QPushButton("Générer")
        generate_row.addWidget(self.generate_button)
        generate_row.addStretch(1)
        layout.addLayout(generate_row)

        self.report_label = QLabel()
        self.report_label.setWordWrap(True)
        layout.addWidget(self.report_label)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        font = QFont("monospace")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.preview.setFont(font)
        layout.addWidget(self.preview, 5)

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
        self.target_combo.currentIndexChanged.connect(self._invalidate_preview)
        for editor in self._count_editors.values():
            editor.valueChanged.connect(self._invalidate_preview)
        self.copy_button.clicked.connect(self.copy_script)
        self.save_button.clicked.connect(self._choose_export_path)
        self._set_export_enabled(False)

    @property
    def target(self) -> SQLTarget:
        return SQLTarget(self.target_combo.currentData())

    @property
    def row_counts(self) -> dict[str, int]:
        return {
            table_id: editor.value() for table_id, editor in self._count_editors.items()
        }

    @property
    def script(self) -> str:
        return self.preview.toPlainText()

    def generate_preview(self, _checked: bool = False) -> bool:
        self.generation_result = None
        try:
            self.generation_result = self.generator.generate(
                self.model,
                self.target,
                self.row_counts,
                project_name=self.project_name,
            )
        except TestDataGenerationError as error:
            messages = "\n".join(f"• {item.message}" for item in error.problems)
            self.preview.setPlainText(
                "Impossible de générer les données de test.\n\n" + messages
            )
            self.report_label.setText(
                f"❌ {len(error.problems)} problème(s) bloquent la génération."
            )
            self.report_label.setStyleSheet("color: #b42318; font-weight: bold;")
            self._set_export_enabled(False)
            return False

        self.preview.setPlainText(self.generation_result.script)
        if self.generation_result.warnings:
            self.report_label.setText(
                "\n".join(
                    f"⚠ {item.message}" for item in self.generation_result.warnings
                )
            )
            self.report_label.setStyleSheet("color: #8a5a00;")
        else:
            total = sum(self.generation_result.generated_rows.values())
            self.report_label.setText(
                f"✓ {total} ligne(s) générée(s) pour {self.target.display_name}."
            )
            self.report_label.setStyleSheet("color: #18794e; font-weight: bold;")
        self._set_export_enabled(True)
        return True

    def copy_script(self) -> None:
        if self.copy_button.isEnabled():
            QApplication.clipboard().setText(self.script)

    def export_to(self, path: str | Path) -> Path:
        if not self.save_button.isEnabled() or self.generation_result is None:
            raise ValueError("Aucun script de données valide n'est disponible.")
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(".sql")
        target.write_text(self.generation_result.script, encoding="utf-8")
        return target

    def _choose_export_path(self) -> None:
        project = (
            re.sub(r"[^0-9A-Za-z_-]+", "_", self.project_name.strip()).strip("_")
            or "modele"
        )
        filename, _filter = QFileDialog.getSaveFileName(
            self,
            "Enregistrer les données de test",
            f"{project}_donnees_test_{self.target.value}.sql",
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
                f"Impossible d'enregistrer le script : {error}",
            )

    def _invalidate_preview(self, _value: int = -1) -> None:
        self.generation_result = None
        self.report_label.setText("Paramètres modifiés : cliquez sur Générer.")
        self.report_label.setStyleSheet("color: #5b6472;")
        self._set_export_enabled(False)

    def _set_export_enabled(self, enabled: bool) -> None:
        self.copy_button.setEnabled(enabled)
        self.save_button.setEnabled(enabled)
