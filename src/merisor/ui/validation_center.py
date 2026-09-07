"""Centre de validation intégré, exploitable et pédagogique."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
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

from merisor.domain import (
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)
from merisor.ui.theme import Spacing


class ValidationCenter(QWidget):
    """Présente le rapport existant sans implémenter de règle métier."""

    locate_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("validationCenter")
        self._report = ValidationReport(())
        root = QVBoxLayout(self)
        root.setContentsMargins(Spacing.XL, Spacing.LG, Spacing.XL, Spacing.LG)
        root.setSpacing(Spacing.MD)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Qualité du modèle", self)
        title.setProperty("role", "pageTitle")
        subtitle = QLabel(
            "Corrigez les problèmes bloquants avant de transformer le MCD.", self
        )
        subtitle.setProperty("role", "secondary")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        self.filter_combo = QComboBox(self)
        self.filter_combo.addItem("Tous les problèmes", "all")
        self.filter_combo.addItem("Erreurs", ValidationSeverity.ERROR.value)
        self.filter_combo.addItem("Avertissements", ValidationSeverity.WARNING.value)
        header.addWidget(self.filter_combo)
        root.addLayout(header)

        cards = QHBoxLayout()
        self.error_count = self._summary_card(cards, "Erreurs", "0", "error")
        self.warning_count = self._summary_card(cards, "Avertissements", "0", "warning")
        self.success_count = self._summary_card(
            cards, "Contrôles réussis", "18", "success"
        )
        root.addLayout(cards)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.issue_tree = QTreeWidget(splitter)
        self.issue_tree.setHeaderLabels(["Niveau", "Problème"])
        self.issue_tree.setRootIsDecorated(False)
        self.issue_tree.setAlternatingRowColors(True)
        self.issue_tree.setColumnWidth(0, 135)
        self.issue_tree.header().setStretchLastSection(True)
        details_panel = QWidget(splitter)
        details_layout = QVBoxLayout(details_panel)
        details_title = QLabel("Détails du problème", details_panel)
        details_title.setProperty("role", "sectionTitle")
        details_layout.addWidget(details_title)
        self.details = QPlainTextEdit(details_panel)
        self.details.setReadOnly(True)
        self.details.setPlaceholderText(
            "Sélectionnez un problème pour comprendre sa cause et l'action attendue."
        )
        details_layout.addWidget(self.details, 1)
        actions = QHBoxLayout()
        self.locate_button = QPushButton("Localiser", details_panel)
        self.correct_button = QPushButton("Corriger dans les propriétés", details_panel)
        self.correct_button.setProperty("role", "primary")
        self.why_button = QPushButton("ⓘ Pourquoi ?", details_panel)
        actions.addWidget(self.locate_button)
        actions.addWidget(self.correct_button)
        actions.addWidget(self.why_button)
        details_layout.addLayout(actions)
        splitter.addWidget(self.issue_tree)
        splitter.addWidget(details_panel)
        splitter.setSizes([620, 420])
        root.addWidget(splitter, 1)

        self.filter_combo.currentIndexChanged.connect(self._populate)
        self.issue_tree.currentItemChanged.connect(self._selection_changed)
        self.locate_button.clicked.connect(self._locate_current)
        self.correct_button.clicked.connect(self._locate_current)
        self.why_button.clicked.connect(self._show_why)
        self._set_action_state(False)

    def set_report(self, report: ValidationReport) -> None:
        self._report = report
        self.error_count.setText(str(len(report.errors)))
        self.warning_count.setText(str(len(report.warnings)))
        self.success_count.setText(str(max(0, 18 - len(report.issues))))
        self._populate()

    @staticmethod
    def _summary_card(layout: QHBoxLayout, title: str, value: str, role: str) -> QLabel:
        card = QFrame()
        card.setProperty("role", "card")
        card_layout = QVBoxLayout(card)
        value_label = QLabel(value)
        value_label.setProperty("role", role)
        font = value_label.font()
        font.setPointSize(font.pointSize() + 7)
        font.setBold(True)
        value_label.setFont(font)
        caption = QLabel(title)
        caption.setProperty("role", "secondary")
        card_layout.addWidget(value_label)
        card_layout.addWidget(caption)
        layout.addWidget(card)
        return value_label

    def _populate(self, _index: int = -1) -> None:
        self.issue_tree.clear()
        selected_filter = self.filter_combo.currentData()
        for issue in self._report.issues:
            if selected_filter != "all" and issue.severity.value != selected_filter:
                continue
            item = QTreeWidgetItem(
                [
                    "✕ Erreur"
                    if issue.severity is ValidationSeverity.ERROR
                    else "⚠ Avertissement",
                    issue.message,
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, issue)
            item.setToolTip(1, issue.code)
            self.issue_tree.addTopLevelItem(item)
        if self.issue_tree.topLevelItemCount():
            first = self.issue_tree.topLevelItem(0)
            if first is not None:
                self.issue_tree.setCurrentItem(first)
        else:
            self.details.setPlainText(
                "✓ Aucun problème dans cette catégorie.\n\n"
                "Le MCD peut poursuivre le workflow de transformation."
            )
            self._set_action_state(False)

    def _current_issue(self) -> ValidationIssue | None:
        item = self.issue_tree.currentItem()
        if item is None:
            return None
        issue = item.data(0, Qt.ItemDataRole.UserRole)
        return issue if isinstance(issue, ValidationIssue) else None

    def _selection_changed(
        self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        issue = self._current_issue() if current is not None else None
        if issue is None:
            self.details.clear()
            self._set_action_state(False)
            return
        consequence = (
            "Cette erreur bloque la génération d'un MLD cohérent."
            if issue.severity is ValidationSeverity.ERROR
            else "Cet avertissement n'empêche pas la génération, mais mérite une vérification."
        )
        self.details.setPlainText(
            f"{issue.message}\n\nCode du contrôle : {issue.code}\n\n{consequence}"
        )
        self._set_action_state(issue.element_id is not None)

    def _locate_current(self) -> None:
        issue = self._current_issue()
        if issue is not None and issue.element_id is not None:
            self.locate_requested.emit(issue.element_id)

    def _show_why(self) -> None:
        issue = self._current_issue()
        if issue is None:
            return
        self.details.appendPlainText(
            "\n\nPourquoi ?\n"
            + self._explanation(issue.code)
            + "\n\nCette explication décrit le contrôle réellement exécuté par MERISOR."
        )

    def _set_action_state(self, enabled: bool) -> None:
        self.locate_button.setEnabled(enabled)
        self.correct_button.setEnabled(enabled)
        self.why_button.setEnabled(self._current_issue() is not None)

    @staticmethod
    def _explanation(code: str) -> str:
        prefix = code.split(".", 1)[0]
        explanations = {
            "entity": "Une entité doit être nommée et posséder au moins un identifiant pour devenir une table exploitable.",
            "association": "Une association décrit un fait entre au moins deux participations et doit pouvoir être distinguée sans ambiguïté.",
            "relation": "Chaque branche relie une entité à une association et porte une cardinalité valide.",
            "attribute": "Les attributs d'un même objet doivent être nommés sans doublon et respecter leurs contraintes.",
            "inheritance": "Une spécialisation doit conserver une hiérarchie transformable de façon déterministe.",
            "functional_dependency": "Une dépendance fonctionnelle doit référencer des attributs présents et séparer déterminant et dépendants.",
        }
        return explanations.get(
            prefix,
            "Ce contrôle protège la cohérence structurelle du modèle avant sa transformation.",
        )
