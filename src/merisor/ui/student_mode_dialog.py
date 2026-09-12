"""Interface du mode étudiant et de son barème pédagogique."""

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
    QProgressBar,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.application import (
    STUDENT_EXERCISES,
    StudentCriterionStatus,
    StudentExercise,
    StudentExerciseEvaluator,
    StudentExerciseReport,
)
from merisor.domain import MCDModel


class StudentModeDialog(QDialog):
    """Évalue le MCD courant sans le modifier et explique le barème."""

    def __init__(self, model: MCDModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.model = model
        self.evaluator = StudentExerciseEvaluator()
        self.current_report: StudentExerciseReport | None = None
        self.setWindowTitle("Mode étudiant — exercices MERISE")
        self.resize(1120, 760)

        title = QLabel(
            "<h2>🎓 Mode étudiant</h2>"
            "<p>Construisez le MCD correspondant à l'énoncé, puis demandez une "
            "évaluation. Chaque critère indique ce qui est acquis, ce qui reste à "
            "revoir et surtout <b>pourquoi</b>.</p>"
        )
        title.setWordWrap(True)

        self.exercise_combo = QComboBox()
        for exercise in STUDENT_EXERCISES:
            self.exercise_combo.addItem(exercise.title, exercise.id)
        self.statement = QPlainTextEdit()
        self.statement.setReadOnly(True)
        self.statement.setMaximumHeight(130)
        self.assumptions = QLabel()
        self.assumptions.setWordWrap(True)
        self.assumptions.setStyleSheet(
            "background: #eef5ff; border: 1px solid #9bbce0; "
            "border-radius: 4px; padding: 8px;"
        )

        self.evaluate_button = QPushButton("Évaluer mon MCD")
        self.evaluate_button.setProperty("role", "primary")
        self.score = QProgressBar()
        self.score.setRange(0, 100)
        self.score.setFormat("Pas encore évalué")
        header = QHBoxLayout()
        header.addWidget(QLabel("Exercice :"))
        header.addWidget(self.exercise_combo, 1)
        header.addWidget(self.evaluate_button)
        header.addWidget(self.score)

        self.criteria = QTreeWidget()
        self.criteria.setHeaderLabels(["Résultat", "Critère", "Constat"])
        self.criteria.setAlternatingRowColors(True)
        self.criteria.setColumnWidth(0, 110)
        self.criteria.setColumnWidth(1, 300)
        self.criteria.header().setStretchLastSection(True)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText(
            "Sélectionnez un critère pour afficher l'explication « Pourquoi ? »."
        )
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.criteria)
        splitter.addWidget(self.details)
        splitter.setSizes([680, 440])

        self.copy_button = QPushButton("Copier le résultat")
        self.copy_button.setEnabled(False)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        footer = QHBoxLayout()
        footer.addWidget(self.copy_button)
        footer.addStretch(1)
        footer.addWidget(buttons)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addLayout(header)
        layout.addWidget(self.statement)
        layout.addWidget(self.assumptions)
        layout.addWidget(splitter, 1)
        layout.addLayout(footer)

        self.exercise_combo.currentIndexChanged.connect(self._show_exercise)
        self.evaluate_button.clicked.connect(self.evaluate)
        self.criteria.currentItemChanged.connect(self._show_why)
        self.copy_button.clicked.connect(self.copy_report)
        buttons.rejected.connect(self.reject)
        self._show_exercise()

    def _exercise(self) -> StudentExercise:
        exercise_id = self.exercise_combo.currentData()
        return next(
            exercise for exercise in STUDENT_EXERCISES if exercise.id == exercise_id
        )

    def _show_exercise(self, _index: int = -1) -> None:
        exercise = self._exercise()
        self.statement.setPlainText(exercise.statement)
        assumptions = "<br>".join(f"• {item}" for item in exercise.assumptions)
        self.assumptions.setText(
            "<b>Hypothèses explicites du barème</b><br>" + assumptions
        )
        self.criteria.clear()
        self.details.clear()
        self.score.setValue(0)
        self.score.setFormat("Pas encore évalué")
        self.copy_button.setEnabled(False)
        self.current_report = None

    def evaluate(self, _checked: bool = False) -> None:
        report = self.evaluator.evaluate(self.model, self._exercise())
        self.current_report = report
        self.criteria.clear()
        for criterion in report.criteria:
            passed = criterion.status is StudentCriterionStatus.PASSED
            item = QTreeWidgetItem(
                [
                    "✓ Acquis" if passed else "⚠ À revoir",
                    criterion.label,
                    criterion.explanation,
                ]
            )
            item.setForeground(0, QColor("#137333" if passed else "#9a6700"))
            item.setData(0, Qt.ItemDataRole.UserRole, criterion.why)
            self.criteria.addTopLevelItem(item)
        self.score.setValue(report.score)
        self.score.setFormat(
            f"{report.score} % — {report.passed_count}/{len(report.criteria)}"
        )
        self.copy_button.setEnabled(True)
        self.details.setPlainText(report.render())

    def _show_why(
        self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        if current is None:
            return
        why = current.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(why, str):
            self.details.setPlainText(
                f"{current.text(1)}\n\n{current.text(2)}\n\nPourquoi ?\n{why}"
            )

    def copy_report(self, _checked: bool = False) -> None:
        if self.current_report is not None:
            QApplication.clipboard().setText(self.current_report.render())
