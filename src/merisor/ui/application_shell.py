"""Composants de structure du shell applicatif MERISOR 2.0."""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from merisor.ui.theme import Spacing


class WorkflowStep(str, Enum):
    DESIGN = "design"
    VERIFY = "verify"
    TRANSFORM = "transform"
    PRODUCE = "produce"
    AI = "ai"


class WorkflowState(str, Enum):
    READY = "ready"
    WARNING = "warning"
    ERROR = "error"
    STALE = "stale"
    PENDING = "pending"


class WorkflowNavigation(QWidget):
    """Navigation principale alignée sur le parcours métier MERISE."""

    step_requested = Signal(str)

    LABELS = (
        (WorkflowStep.DESIGN, "①  CONCEVOIR"),
        (WorkflowStep.VERIFY, "②  VÉRIFIER"),
        (WorkflowStep.TRANSFORM, "③  TRANSFORMER"),
        (WorkflowStep.PRODUCE, "④  PRODUIRE"),
        (WorkflowStep.AI, "✨  IA"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("workflowNavigation")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.XS, Spacing.SM, Spacing.XS)
        layout.setSpacing(Spacing.XS)
        self.buttons: dict[WorkflowStep, QPushButton] = {}
        self._base_labels = dict(self.LABELS)
        for step, label in self.LABELS:
            button = QPushButton(label, self)
            button.setProperty("workflowStep", True)
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setToolTip(self._tooltip(step))
            button.setAccessibleName(label.replace("  ", " "))
            button.clicked.connect(
                lambda _checked=False, value=step: self.step_requested.emit(value.value)
            )
            layout.addWidget(button)
            self.buttons[step] = button
        layout.addStretch(1)
        self.set_current(WorkflowStep.DESIGN)

    def set_current(self, step: WorkflowStep) -> None:
        self.buttons[step].setChecked(True)

    def set_state(
        self, step: WorkflowStep, state: WorkflowState, detail: str = ""
    ) -> None:
        button = self.buttons[step]
        button.setProperty("workflowState", state.value)
        symbols = {
            WorkflowState.READY: "✓",
            WorkflowState.WARNING: "⚠",
            WorkflowState.ERROR: "✕",
            WorkflowState.STALE: "↻",
            WorkflowState.PENDING: "",
        }
        suffix = symbols[state]
        button.setText(
            f"{self._base_labels[step]}  {suffix}"
            if suffix
            else self._base_labels[step]
        )
        button.setToolTip(detail or self._tooltip(step))
        button.style().unpolish(button)
        button.style().polish(button)

    @staticmethod
    def _tooltip(step: WorkflowStep) -> str:
        return {
            WorkflowStep.DESIGN: "Construire et modifier le modèle conceptuel",
            WorkflowStep.VERIFY: "Valider, analyser et normaliser le modèle",
            WorkflowStep.TRANSFORM: "Générer et expliquer le modèle logique",
            WorkflowStep.PRODUCE: "Produire SQL, documentation et exports",
            WorkflowStep.AI: "Concevoir ou améliorer le MCD avec l'assistant IA",
        }[step]


class ToolPalette(QWidget):
    """Palette verticale des outils agissant directement sur le canvas."""

    def __init__(
        self,
        drawing_actions: Iterable[QAction],
        utility_actions: Iterable[QAction],
        search: QLineEdit,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("toolPalette")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.XS)

        title = QLabel("OUTILS", self)
        title.setProperty("role", "sectionTitle")
        layout.addWidget(title)
        for action in drawing_actions:
            layout.addWidget(self._button(action))

        separator = QFrame(self)
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)
        for action in utility_actions:
            layout.addWidget(self._button(action))

        search_label = QLabel("RECHERCHE", self)
        search_label.setProperty("role", "sectionTitle")
        layout.addWidget(search_label)
        search.setMaximumWidth(16777215)
        layout.addWidget(search)
        layout.addStretch(1)

    @staticmethod
    def _button(action: QAction) -> QToolButton:
        button = QToolButton()
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return button


class ModelStatusStrip(QWidget):
    """Résumé permanent et lisible de l'état de la chaîne MCD → MLD."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("modelStatusStrip")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, 0, Spacing.SM, 0)
        layout.setSpacing(Spacing.LG)
        self.validation_label = QLabel("MCD non vérifié", self)
        self.document_label = QLabel("Nouveau modèle", self)
        self.mld_label = QLabel("MLD non généré", self)
        self.sql_label = QLabel("SQL non généré", self)
        for label in (
            self.validation_label,
            self.document_label,
            self.mld_label,
            self.sql_label,
        ):
            label.setProperty("role", "secondary")
            layout.addWidget(label)

    def set_validation(self, errors: int, warnings: int) -> None:
        if errors:
            self.validation_label.setText(f"✕ {errors} erreur(s) MCD")
            self._set_role(self.validation_label, "error")
        elif warnings:
            self.validation_label.setText(f"⚠ {warnings} avertissement(s)")
            self._set_role(self.validation_label, "warning")
        else:
            self.validation_label.setText("✓ MCD valide")
            self._set_role(self.validation_label, "success")

    def set_document(self, *, dirty: bool, named: bool) -> None:
        name = "Projet ouvert" if named else "Nouveau modèle"
        self.document_label.setText(f"● {name} modifié" if dirty else name)
        self._set_role(self.document_label, "warning" if dirty else "secondary")

    def set_mld(self, *, exists: bool, stale: bool) -> None:
        if not exists:
            self.mld_label.setText("MLD non généré")
            role = "secondary"
        elif stale:
            self.mld_label.setText("⚠ MLD obsolète")
            role = "warning"
        else:
            self.mld_label.setText("✓ MLD à jour")
            role = "success"
        self._set_role(self.mld_label, role)

    def set_sql(self, *, exists: bool, stale: bool) -> None:
        if not exists:
            self.sql_label.setText("SQL non généré")
            role = "secondary"
        elif stale:
            self.sql_label.setText("⚠ SQL à régénérer")
            role = "warning"
        else:
            self.sql_label.setText("✓ SQL à jour")
            role = "success"
        self._set_role(self.sql_label, role)

    @staticmethod
    def _set_role(label: QLabel, role: str) -> None:
        label.setProperty("role", role)
        label.style().unpolish(label)
        label.style().polish(label)
