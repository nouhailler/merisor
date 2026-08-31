"""Assistant graphique de normalisation pédagogique et non destructif."""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.application.ai_normalization_service import (
    AiDependencySuggestion,
    AiNormalizationError,
    AiNormalizationService,
)
from merisor.application.controller import DiagramController
from merisor.application.openrouter_client import OpenRouterClient, OpenRouterError
from merisor.application.openrouter_settings import OpenRouterKeyStore
from merisor.domain import (
    Association,
    Attribute,
    Entity,
    FunctionalDependency,
    FunctionalDependencyOrigin,
    NormalFormAssessment,
    NormalFormStatus,
    NormalizationProposal,
    OwnerNormalizationReport,
    apply_normalization_proposal,
)


class FunctionalDependencyDialog(QDialog):
    def __init__(
        self,
        owner: Entity | Association,
        dependency: FunctionalDependency | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Dépendance fonctionnelle")
        self.resize(660, 440)
        layout = QVBoxLayout(self)
        help_label = QLabel(
            "Sélectionnez X et Y pour exprimer X → Y. Les deux ensembles doivent "
            "être non vides et disjoints."
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        lists = QHBoxLayout()
        self.determinants = self._attribute_list(
            "Déterminant (X)", owner.attributes, lists
        )
        self.dependents = self._attribute_list("Dépendant (Y)", owner.attributes, lists)
        layout.addLayout(lists, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        if dependency is not None:
            self._check_ids(self.determinants, dependency.determinant_attribute_ids)
            self._check_ids(self.dependents, dependency.dependent_attribute_ids)

    @staticmethod
    def _attribute_list(
        title: str, attributes: list[Attribute], parent_layout: QHBoxLayout
    ) -> QListWidget:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        widget = QListWidget()
        for attribute in attributes:
            item = QListWidgetItem(attribute.name or "(sans nom)")
            item.setData(Qt.ItemDataRole.UserRole, attribute.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            widget.addItem(item)
        layout.addWidget(widget)
        parent_layout.addWidget(group)
        return widget

    @staticmethod
    def _check_ids(widget: QListWidget, ids: tuple[str, ...]) -> None:
        selected = set(ids)
        for index in range(widget.count()):
            item = widget.item(index)
            if item.data(Qt.ItemDataRole.UserRole) in selected:
                item.setCheckState(Qt.CheckState.Checked)

    @staticmethod
    def _selected_ids(widget: QListWidget) -> tuple[str, ...]:
        return tuple(
            str(widget.item(index).data(Qt.ItemDataRole.UserRole))
            for index in range(widget.count())
            if widget.item(index).checkState() is Qt.CheckState.Checked
        )

    @property
    def values(self) -> tuple[tuple[str, ...], tuple[str, ...]]:
        return self._selected_ids(self.determinants), self._selected_ids(
            self.dependents
        )

    def _validate_and_accept(self) -> None:
        determinants, dependents = self.values
        if not determinants or not dependents:
            QMessageBox.warning(self, "Dépendance incomplète", "Sélectionnez X et Y.")
            return
        if set(determinants) & set(dependents):
            QMessageBox.warning(
                self,
                "Dépendance triviale",
                "Un même attribut ne peut pas apparaître dans X et Y.",
            )
            return
        self.accept()


class DecompositionPreviewDialog(QDialog):
    def __init__(
        self,
        controller: DiagramController,
        proposal: NormalizationProposal,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Aperçu de la décomposition")
        self.resize(760, 540)
        self.controller = controller
        self.proposal = proposal
        layout = QVBoxLayout(self)
        explanation = QLabel(proposal.explanation)
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        preview = QPlainTextEdit()
        preview.setReadOnly(True)
        try:
            transformed = apply_normalization_proposal(controller.model, proposal)
            preview.setPlainText(self._model_summary(transformed))
        except ValueError:
            preview.setPlainText(self._manual_preview())
        layout.addWidget(preview, 1)
        if proposal.limitation:
            limitation = QLabel(f"⚠ {proposal.limitation}")
            limitation.setWordWrap(True)
            limitation.setStyleSheet("color: #8a5a00;")
            layout.addWidget(limitation)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.apply_button = buttons.addButton(
            "Appliquer la décomposition", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.apply_button.setEnabled(proposal.can_apply)
        self.apply_button.clicked.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _manual_preview(self) -> str:
        owner = self.controller.model.node(self.proposal.owner_id)
        names = {attribute.id: attribute.name for attribute in owner.attributes}
        determinants = ", ".join(
            names[item] for item in self.proposal.determinant_attribute_ids
        )
        dependents = ", ".join(
            names[item] for item in self.proposal.dependent_attribute_ids
        )
        return (
            "Aucun changement n'a été appliqué.\n\n"
            f"Structure suggérée : {self.proposal.suggested_entity_name}\n"
            f"Identifiant : {determinants}\n"
            f"Attributs déplacés : {dependents}\n"
        )

    @staticmethod
    def _model_summary(model) -> str:  # type: ignore[no-untyped-def]
        lines = ["MCD projeté — aucun changement appliqué", ""]
        for entity in sorted(
            model.entities.values(), key=lambda item: item.name.casefold()
        ):
            lines.append(entity.name)
            lines.append("-" * max(3, len(entity.name)))
            for attribute in entity.attributes:
                lines.append(
                    f"{'# ' if attribute.identifier else '  '}{attribute.name}"
                )
            lines.append("")
        lines.append(
            f"{len(model.associations)} association(s), {len(model.relations)} relation(s)."
        )
        return "\n".join(lines)

    def _apply(self) -> None:
        response = QMessageBox.question(
            self,
            "Confirmer la décomposition",
            "Appliquer cette décomposition au MCD ? L'opération restera annulable.",
        )
        if response is QMessageBox.StandardButton.Yes:
            self.controller.apply_normalization(self.proposal)
            self.accept()


class _AiDependencyWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        api_key: str,
        model_id: str,
        owner: Entity | Association,
    ) -> None:
        super().__init__()
        self.api_key = api_key
        self.model_id = model_id
        self.owner = owner

    @Slot()
    def run(self) -> None:
        try:
            suggestions = AiNormalizationService().suggest(
                OpenRouterClient(self.api_key, timeout=60), self.model_id, self.owner
            )
        except (OpenRouterError, AiNormalizationError) as error:
            self.failed.emit(str(error))
        except Exception as error:
            self.failed.emit(f"Erreur inattendue pendant l'analyse IA : {error}")
        else:
            self.succeeded.emit(suggestions)


class NormalizationAssistantDialog(QDialog):
    def __init__(
        self, controller: DiagramController, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.store = OpenRouterKeyStore()
        self._report: OwnerNormalizationReport | None = None
        self._thread: QThread | None = None
        self._worker: _AiDependencyWorker | None = None
        self.setWindowTitle("Assistant de normalisation")
        self.resize(1040, 720)
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("Objet analysé :"))
        self.owner_combo = QComboBox()
        header.addWidget(self.owner_combo, 1)
        self.refresh_button = QPushButton("Recalculer")
        header.addWidget(self.refresh_button)
        layout.addLayout(header)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._dependencies_tab(), "Dépendances fonctionnelles")
        self.tabs.addTab(self._report_tab(), "Rapport pédagogique")
        layout.addWidget(self.tabs, 1)
        close_button = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_button.rejected.connect(self.reject)
        layout.addWidget(close_button)
        self.owner_combo.currentIndexChanged.connect(self.refresh)
        self.refresh_button.clicked.connect(self.refresh)
        self._load_owners()
        self.refresh()

    def _dependencies_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        intro = QLabel(
            "Une dépendance X → Y signifie qu'une valeur de X détermine une seule "
            "valeur de Y. Elle constitue la base des contrôles formels 2NF et 3NF."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.dependency_tree = QTreeWidget()
        self.dependency_tree.setHeaderLabels(
            ["Déterminant X", "Dépendant Y", "Origine"]
        )
        self.dependency_tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.dependency_tree, 1)
        buttons = QHBoxLayout()
        self.add_button = QPushButton("Ajouter")
        self.edit_button = QPushButton("Modifier")
        self.remove_button = QPushButton("Supprimer")
        self.ai_button = QPushButton("Suggérer avec l'IA…")
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.edit_button)
        buttons.addWidget(self.remove_button)
        buttons.addStretch(1)
        buttons.addWidget(self.ai_button)
        layout.addLayout(buttons)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        self.add_button.clicked.connect(self._add_dependency)
        self.edit_button.clicked.connect(self._edit_dependency)
        self.remove_button.clicked.connect(self._remove_dependency)
        self.ai_button.clicked.connect(self._suggest_with_ai)
        return tab

    def _report_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.report_text = QPlainTextEdit()
        self.report_text.setReadOnly(True)
        splitter.addWidget(self.report_text)
        proposal_widget = QWidget()
        proposal_layout = QVBoxLayout(proposal_widget)
        proposal_layout.setContentsMargins(0, 0, 0, 0)
        proposal_layout.addWidget(QLabel("Décompositions proposées"))
        self.proposal_tree = QTreeWidget()
        self.proposal_tree.setHeaderLabels(["Proposition", "Application"])
        proposal_layout.addWidget(self.proposal_tree)
        self.preview_button = QPushButton("Prévisualiser…")
        proposal_layout.addWidget(self.preview_button)
        splitter.addWidget(proposal_widget)
        layout.addWidget(splitter)
        self.preview_button.clicked.connect(self._preview_proposal)
        return tab

    def _load_owners(self) -> None:
        current = self.owner_combo.currentData()
        self.owner_combo.blockSignals(True)
        self.owner_combo.clear()
        owner_values: tuple[Entity | Association, ...] = (
            *self.controller.model.entities.values(),
            *self.controller.model.associations.values(),
        )
        owners = sorted(
            owner_values,
            key=lambda item: (item.name.casefold(), item.id),
        )
        for owner in owners:
            kind = "Entité" if isinstance(owner, Entity) else "Association"
            self.owner_combo.addItem(f"{kind} — {owner.name}", owner.id)
        if current is not None:
            index = self.owner_combo.findData(current)
            if index >= 0:
                self.owner_combo.setCurrentIndex(index)
        self.owner_combo.blockSignals(False)

    def _owner(self) -> Entity | Association | None:
        owner_id = self.owner_combo.currentData()
        if not isinstance(owner_id, str):
            return None
        try:
            return self.controller.model.node(owner_id)
        except Exception:
            return None

    def refresh(self, _index: int = -1) -> None:
        owner = self._owner()
        self.dependency_tree.clear()
        self.proposal_tree.clear()
        enabled = owner is not None and bool(owner.attributes)
        for button in (self.add_button, self.edit_button, self.remove_button):
            button.setEnabled(enabled)
        self.ai_button.setEnabled(
            enabled
            and self.store.is_enabled()
            and bool(self.store.get())
            and bool(self.store.get_model())
        )
        if owner is None:
            self.report_text.setPlainText(
                "Ajoutez une entité ou une association à analyser."
            )
            return
        names = {attribute.id: attribute.name for attribute in owner.attributes}
        for dependency in self.controller.model.functional_dependencies_for(owner.id):
            item = QTreeWidgetItem(
                [
                    ", ".join(
                        names[item] for item in dependency.determinant_attribute_ids
                    ),
                    ", ".join(
                        names[item] for item in dependency.dependent_attribute_ids
                    ),
                    "IA (confirmée)"
                    if dependency.origin is FunctionalDependencyOrigin.AI
                    else "Utilisateur",
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, dependency.id)
            self.dependency_tree.addTopLevelItem(item)
        report = next(
            item
            for item in self.controller.analyze_normalization().owners
            if item.owner_id == owner.id
        )
        self._report = report
        self.report_text.setPlainText(self._render_report(report, names))
        for index, proposal in enumerate(report.proposals):
            item = QTreeWidgetItem(
                [
                    proposal.title,
                    "Automatique et annulable"
                    if proposal.can_apply
                    else "Aperçu seulement",
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, index)
            self.proposal_tree.addTopLevelItem(item)

    @staticmethod
    def _render_report(report: OwnerNormalizationReport, names: dict[str, str]) -> str:
        lines = [f"NORMALISATION — {report.owner_name}", "=" * 50, ""]
        keys = [
            " + ".join(names[item] for item in key) for key in report.candidate_keys
        ]
        lines.append("Clés candidates : " + (" ; ".join(keys) or "non déterminées"))
        for assessment in (
            report.first_normal_form,
            report.second_normal_form,
            report.third_normal_form,
        ):
            lines.extend(
                NormalizationAssistantDialog._assessment_lines(assessment, names)
            )
        lines.extend(
            [
                "",
                "Important : les contrôles 2NF/3NF ne valent que pour les dépendances ",
                "déclarées. La 1NF est une aide heuristique à confirmer avec le métier.",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _assessment_lines(
        assessment: NormalFormAssessment, names: dict[str, str]
    ) -> list[str]:
        icon = {
            NormalFormStatus.COMPLIANT: "✓",
            NormalFormStatus.VIOLATION: "⚠",
            NormalFormStatus.UNDETERMINED: "?",
        }[assessment.status]
        lines = [
            "",
            f"{icon} {assessment.normal_form} — {assessment.summary}",
            assessment.explanation,
        ]
        for violation in assessment.violations:
            determinant = ", ".join(
                names.get(item, item) for item in violation.determinant_attribute_ids
            )
            dependent = ", ".join(
                names.get(item, item) for item in violation.dependent_attribute_ids
            )
            arrow = f" [{determinant} → {dependent}]" if determinant else ""
            lines.append(f"  • {violation.message}{arrow}")
            lines.append(f"    Pourquoi ? {violation.explanation}")
        return lines

    def _selected_dependency(self) -> FunctionalDependency | None:
        item = self.dependency_tree.currentItem()
        if item is None:
            return None
        dependency_id = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(dependency_id, str):
            return self.controller.model.functional_dependencies.get(dependency_id)
        return None

    def _add_dependency(self) -> None:
        owner = self._owner()
        if owner is None:
            return
        dialog = FunctionalDependencyDialog(owner, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.controller.add_functional_dependency(owner.id, *dialog.values)
            except ValueError as error:
                QMessageBox.warning(self, "Dépendance refusée", str(error))
            self.refresh()

    def _edit_dependency(self) -> None:
        owner = self._owner()
        dependency = self._selected_dependency()
        if owner is None or dependency is None:
            return
        dialog = FunctionalDependencyDialog(owner, dependency, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.controller.update_functional_dependency(
                    dependency.id, *dialog.values
                )
            except ValueError as error:
                QMessageBox.warning(self, "Dépendance refusée", str(error))
            self.refresh()

    def _remove_dependency(self) -> None:
        dependency = self._selected_dependency()
        if dependency is not None:
            self.controller.remove_functional_dependency(dependency.id)
            self.refresh()

    def _preview_proposal(self) -> None:
        if self._report is None:
            return
        item = self.proposal_tree.currentItem()
        if item is None:
            QMessageBox.information(self, "Aperçu", "Sélectionnez une proposition.")
            return
        index = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(index, int):
            return
        dialog = DecompositionPreviewDialog(
            self.controller, self._report.proposals[index], self
        )
        dialog.exec()
        self._load_owners()
        self.refresh()

    def _suggest_with_ai(self) -> None:
        owner = self._owner()
        if owner is None or self._thread is not None:
            return
        self.progress.setVisible(True)
        self.ai_button.setEnabled(False)
        thread = QThread(self)
        worker = _AiDependencyWorker(self.store.get(), self.store.get_model(), owner)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._ai_succeeded)
        worker.failed.connect(self._ai_failed)
        worker.succeeded.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.succeeded.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(self._ai_finished)
        self._thread = thread
        self._worker = worker
        thread.start()

    @Slot(object)
    def _ai_succeeded(self, raw_suggestions: object) -> None:
        suggestions = (
            tuple(raw_suggestions) if isinstance(raw_suggestions, tuple) else ()
        )
        if not suggestions:
            QMessageBox.information(
                self, "Suggestions IA", "Aucune dépendance suggérée."
            )
            return
        owner = self._owner()
        if owner is None:
            return
        names = {attribute.id: attribute.name for attribute in owner.attributes}
        details = "\n\n".join(
            f"{', '.join(names[item] for item in suggestion.determinant_attribute_ids)} "
            f"→ {', '.join(names[item] for item in suggestion.dependent_attribute_ids)}\n"
            f"{suggestion.explanation or 'Aucune justification fournie.'}"
            for suggestion in suggestions
            if isinstance(suggestion, AiDependencySuggestion)
        )
        response = QMessageBox.question(
            self,
            "Confirmer les suggestions IA",
            "L'IA peut se tromper. Vérifiez ces dépendances avant de les ajouter :\n\n"
            + details,
        )
        if response is not QMessageBox.StandardButton.Yes:
            return
        for suggestion in suggestions:
            if not isinstance(suggestion, AiDependencySuggestion):
                continue
            try:
                self.controller.add_functional_dependency(
                    owner.id,
                    suggestion.determinant_attribute_ids,
                    suggestion.dependent_attribute_ids,
                    FunctionalDependencyOrigin.AI,
                )
            except ValueError:
                continue
        self.refresh()

    @Slot(str)
    def _ai_failed(self, message: str) -> None:
        QMessageBox.warning(self, "Analyse IA impossible", message)

    @Slot()
    def _ai_finished(self) -> None:
        thread = self._thread
        self._thread = None
        self._worker = None
        self.progress.setVisible(False)
        self.ai_button.setEnabled(True)
        if thread is not None:
            thread.deleteLater()

    def reject(self) -> None:
        if self._thread is not None:
            QMessageBox.information(
                self,
                "Analyse en cours",
                "Attendez la fin de la suggestion OpenRouter avant de fermer.",
            )
            return
        super().reject()
