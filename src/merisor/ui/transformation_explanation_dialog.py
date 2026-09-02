"""Fenêtre pédagogique expliquant les décisions MCD → MLD."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
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

from merisor.application import TransformationExplanationReport


class TransformationExplanationDialog(QDialog):
    """Présente chaque règle et sa provenance, sans recalcul ni IA."""

    def __init__(
        self,
        report: TransformationExplanationReport,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.report = report
        self.setWindowTitle(f"Pourquoi ? — {report.table_name}")
        self.resize(920, 620)

        root = QVBoxLayout(self)
        title = QLabel(f"ⓘ Pourquoi ce MLD ? — {report.table_name}")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        root.addWidget(title)
        headline = QLabel(report.headline)
        headline.setWordWrap(True)
        root.addWidget(headline)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.decisions = QTreeWidget()
        self.decisions.setHeaderLabels(["Transformation expliquée"])
        self.decisions.setRootIsDecorated(False)
        for index, explanation in enumerate(report.explanations):
            item = QTreeWidgetItem([explanation.title])
            item.setData(0, Qt.ItemDataRole.UserRole, index)
            item.setToolTip(0, explanation.result)
            self.decisions.addTopLevelItem(item)
        splitter.addWidget(self.decisions)

        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        splitter.addWidget(self.details)
        splitter.setSizes([320, 580])
        root.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        self.copy_button = QPushButton("Copier l'explication")
        close_button = QPushButton("Fermer")
        buttons.addWidget(self.copy_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)
        root.addLayout(buttons)

        self.decisions.currentItemChanged.connect(self._selection_changed)
        self.copy_button.clicked.connect(self._copy)
        close_button.clicked.connect(self.accept)
        first = self.decisions.topLevelItem(0)
        if first is not None:
            self.decisions.setCurrentItem(first)

    def _selection_changed(
        self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        if current is None:
            self.details.clear()
            return
        index = current.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(index, int) or not 0 <= index < len(self.report.explanations):
            self.details.clear()
            return
        explanation = self.report.explanations[index]
        self.details.setPlainText(
            f"{explanation.title}\n\n{explanation.text}\n\n"
            f"Référence interne : {explanation.code}"
        )

    def _copy(self) -> None:
        QApplication.clipboard().setText(self.report.render_text())
