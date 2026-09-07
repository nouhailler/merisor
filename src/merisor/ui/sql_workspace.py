"""Espace SQL intégré : dialecte, validation, recherche, copie et export."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from merisor.application import SQLGenerationError, SQLGenerator, SQLTarget
from merisor.domain import MLDModel
from merisor.ui.theme import DARK_COLORS, LIGHT_COLORS


class SQLSyntaxHighlighter(QSyntaxHighlighter):
    """Coloration légère sans dépendance externe."""

    KEYWORDS = (
        "CREATE|TABLE|PRIMARY|KEY|FOREIGN|REFERENCES|UNIQUE|CHECK|INDEX|"
        "NOT|NULL|DEFAULT|CONSTRAINT|ALTER|ADD|ON|DELETE|UPDATE|CASCADE|"
        "RESTRICT|SET|INSERT|INTO|VALUES|GENERATED|IDENTITY|AUTO_INCREMENT"
    )

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self.set_dark_theme(False)

    def set_dark_theme(self, enabled: bool) -> None:
        colors = DARK_COLORS if enabled else LIGHT_COLORS
        keyword = QTextCharFormat()
        keyword.setForeground(QColor(colors.primary))
        keyword.setFontWeight(QFont.Weight.DemiBold)
        comment = QTextCharFormat()
        comment.setForeground(QColor(colors.success))
        string = QTextCharFormat()
        string.setForeground(QColor(colors.warning))
        self._rules = (
            (
                QRegularExpression(
                    rf"\b(?:{self.KEYWORDS})\b",
                    QRegularExpression.PatternOption.CaseInsensitiveOption,
                ),
                keyword,
            ),
            (QRegularExpression(r"--[^\n]*"), comment),
            (QRegularExpression(r"'(?:''|[^'])*'"), string),
        )
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        for pattern, text_format in self._rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(
                    match.capturedStart(), match.capturedLength(), text_format
                )


class SQLCodeEditor(QWidget):
    """Éditeur SQL en lecture seule avec gouttière de numéros de lignes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.line_numbers = QPlainTextEdit()
        self.line_numbers.setObjectName("sqlLineNumbers")
        self.line_numbers.setReadOnly(True)
        self.line_numbers.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.line_numbers.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.line_numbers.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.line_numbers.setMaximumWidth(58)
        self.editor = QPlainTextEdit()
        self.editor.setObjectName("sqlEditor")
        self.editor.setReadOnly(True)
        font = QFont("monospace")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.line_numbers.setFont(font)
        self.editor.setFont(font)
        self.highlighter = SQLSyntaxHighlighter(self.editor.document())
        layout.addWidget(self.line_numbers)
        layout.addWidget(self.editor, 1)
        self.editor.blockCountChanged.connect(self._refresh_numbers)
        self.editor.verticalScrollBar().valueChanged.connect(
            self.line_numbers.verticalScrollBar().setValue
        )

    def setPlainText(self, text: str) -> None:
        self.editor.setPlainText(text)
        self._refresh_numbers()

    def toPlainText(self) -> str:
        return self.editor.toPlainText()

    def _refresh_numbers(self, _count: int = 0) -> None:
        count = max(1, self.editor.blockCount())
        self.line_numbers.setPlainText(
            "\n".join(str(value) for value in range(1, count + 1))
        )
        self.line_numbers.verticalScrollBar().setValue(
            self.editor.verticalScrollBar().value()
        )

    def set_dark_theme(self, enabled: bool) -> None:
        self.highlighter.set_dark_theme(enabled)


class SQLWorkspace(QWidget):
    """Vue de production SQL, exclusivement alimentée par le MLD courant."""

    def __init__(
        self,
        parent: QWidget | None = None,
        generator: SQLGenerator | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("sqlWorkspace")
        self.model: MLDModel | None = None
        self.project_name = "Sans titre"
        self.generator = generator or SQLGenerator()

        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel("SQL")
        title.setProperty("role", "pageTitle")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(QLabel("SGBD cible"))
        self.target_combo = QComboBox()
        for target in SQLTarget:
            self.target_combo.addItem(target.display_name, target.value)
        header.addWidget(self.target_combo)
        self.copy_button = QPushButton("Copier")
        self.copy_button.setProperty("role", "primary")
        self.export_button = QPushButton("Exporter…")
        header.addWidget(self.copy_button)
        header.addWidget(self.export_button)
        layout.addLayout(header)

        summary = QFrame()
        summary.setProperty("role", "card")
        summary_layout = QHBoxLayout(summary)
        self.status_label = QLabel("Aucun MLD à produire")
        self.status_label.setProperty("role", "secondary")
        self.stats_label = QLabel("0 table · 0 contrainte")
        self.stats_label.setProperty("role", "secondary")
        summary_layout.addWidget(self.status_label)
        summary_layout.addStretch(1)
        summary_layout.addWidget(self.stats_label)
        layout.addWidget(summary)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Rechercher"))
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Table, colonne, contrainte…")
        self.search_field.setClearButtonEnabled(True)
        search_row.addWidget(self.search_field, 1)
        self.result_label = QLabel()
        self.result_label.setProperty("role", "secondary")
        search_row.addWidget(self.result_label)
        layout.addLayout(search_row)

        self.code_editor = SQLCodeEditor()
        layout.addWidget(self.code_editor, 1)
        self.copy_button.setEnabled(False)
        self.export_button.setEnabled(False)

        self.target_combo.currentIndexChanged.connect(self.generate_preview)
        self.copy_button.clicked.connect(self.copy_sql)
        self.export_button.clicked.connect(self._choose_export_path)
        self.search_field.textChanged.connect(self._search)

    @property
    def target(self) -> SQLTarget:
        return SQLTarget(self.target_combo.currentData())

    @property
    def script(self) -> str:
        return self.code_editor.toPlainText()

    def set_model(self, model: MLDModel, project_name: str) -> bool:
        self.model = model
        self.project_name = project_name
        constraints = 0
        for table in model.tables:
            constraints += int(bool(table.primary_key))
            constraints += len(table.foreign_keys)
            constraints += len(table.unique_constraints)
            constraints += len(table.check_constraints)
        self.stats_label.setText(
            f"{len(model.tables)} table(s) · {constraints} contrainte(s)"
        )
        return self.generate_preview()

    def clear_model(self) -> None:
        self.model = None
        self.code_editor.setPlainText("")
        self.status_label.setText("Aucun MLD à produire")
        self._set_status_role("secondary")
        self.stats_label.setText("0 table · 0 contrainte")
        self.copy_button.setEnabled(False)
        self.export_button.setEnabled(False)

    def set_dark_theme(self, enabled: bool) -> None:
        self.code_editor.set_dark_theme(enabled)

    def generate_preview(self, _index: int = -1) -> bool:
        if self.model is None:
            self.clear_model()
            return False
        report = self.generator.validate(self.model, self.target)
        if report.errors:
            messages = "\n".join(f"• {issue.message}" for issue in report.errors)
            self.code_editor.setPlainText(
                "Impossible de générer le SQL.\n\n"
                f"{len(report.errors)} erreur(s) dans le MLD :\n{messages}"
            )
            self.status_label.setText(
                f"{len(report.errors)} erreur(s) bloquent la génération"
            )
            self._set_status_role("error")
            self.copy_button.setEnabled(False)
            self.export_button.setEnabled(False)
            return False
        try:
            script = self.generator.generate(
                self.model, self.target, project_name=self.project_name
            )
        except SQLGenerationError as error:
            self.code_editor.setPlainText(str(error))
            self.status_label.setText("Génération impossible")
            self._set_status_role("error")
            self.copy_button.setEnabled(False)
            self.export_button.setEnabled(False)
            return False
        self.code_editor.setPlainText(script)
        if report.warnings:
            self.status_label.setText(
                f"SQL généré · {len(report.warnings)} avertissement(s)"
            )
            self._set_status_role("warning")
        else:
            self.status_label.setText(f"✓ SQL {self.target.display_name} généré")
            self._set_status_role("success")
        self.copy_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self._search(self.search_field.text())
        return True

    def copy_sql(self) -> None:
        if self.copy_button.isEnabled():
            QApplication.clipboard().setText(self.script)

    def export_to(self, path: str | Path) -> Path:
        if not self.export_button.isEnabled():
            raise ValueError("Aucun script SQL valide n'est disponible.")
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(".sql")
        target.write_text(self.script, encoding="utf-8")
        return target

    def _search(self, query: str) -> None:
        query = query.strip()
        if not query:
            self.result_label.clear()
            return
        document = self.code_editor.editor.document()
        cursor = document.find(query, self.code_editor.editor.textCursor())
        if cursor.isNull():
            cursor = document.find(query)
        if cursor.isNull():
            self.result_label.setText("Aucun résultat")
            return
        self.code_editor.editor.setTextCursor(cursor)
        self.code_editor.editor.ensureCursorVisible()
        count = self.script.casefold().count(query.casefold())
        self.result_label.setText(f"{count} occurrence(s)")

    def _set_status_role(self, role: str) -> None:
        self.status_label.setProperty("role", role)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _choose_export_path(self) -> None:
        project = (
            re.sub(r"[^0-9A-Za-z_-]+", "_", self.project_name.strip()).strip("_")
            or "modele"
        )
        filename, _filter = QFileDialog.getSaveFileName(
            self,
            "Enregistrer le script SQL",
            f"{project}_{self.target.value}.sql",
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
