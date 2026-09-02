"""Analyse et réparation IA d'un MCD existant, toujours sous confirmation."""

from __future__ import annotations

import copy
import json

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
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
    AiRepairError,
    AiRepairProposal,
    AiRepairReport,
    AiRepairService,
    OpenRouterClient,
    OpenRouterError,
    OpenRouterKeyStore,
)
from merisor.domain import MCDModel
from merisor.persistence import JsonDiagramRepository
from merisor.ui.conversational_design_dialog import DesignDraftPreviewDialog


class _RepairWorker(QObject):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        service: AiRepairService,
        api_key: str,
        model_id: str,
        model: MCDModel,
    ) -> None:
        super().__init__()
        self._service = service
        self._api_key = api_key
        self._model_id = model_id
        self._model = copy.deepcopy(model)

    @Slot()
    def run(self) -> None:
        try:
            raw = self._service.analyze(
                OpenRouterClient(self._api_key, timeout=60),
                self._model_id,
                self._model,
            )
        except (OpenRouterError, AiRepairError) as error:
            self.failed.emit(str(error))
        except Exception as error:  # filet de sécurité du thread réseau
            self.failed.emit(f"Erreur inattendue pendant l'analyse : {error}")
        else:
            self.succeeded.emit(raw)


class AiRepairDialog(QDialog):
    """Sélectionne des patchs validés puis présente leur résultat combiné."""

    def __init__(self, current_model: MCDModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Analyser et améliorer le MCD avec l'IA")
        self.resize(1080, 720)
        self.original_model = copy.deepcopy(current_model)
        self.repaired_model: MCDModel | None = None
        self.store = OpenRouterKeyStore()
        self.service = AiRepairService()
        self.report: AiRepairReport | None = None
        self._thread: QThread | None = None
        self._worker: _RepairWorker | None = None
        self._raw: str | None = None
        self._error: str | None = None

        root = QVBoxLayout(self)
        model_id = self.store.get_model()
        notice = QLabel(
            f"Modèle OpenRouter : {model_id or '(aucun)'}\n"
            "Le MCD courant et les observations locales seront transmis à "
            "OpenRouter. Aucune proposition ne sera appliquée sans aperçu et "
            "confirmation explicite."
        )
        notice.setWordWrap(True)
        root.addWidget(notice)
        self.summary_label = QLabel("Lancez l'analyse pour obtenir des propositions.")
        self.summary_label.setStyleSheet("font-weight: bold;")
        self.summary_label.setWordWrap(True)
        root.addWidget(self.summary_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.proposals = QTreeWidget()
        self.proposals.setHeaderLabels(
            ["Appliquer", "Confiance", "Amélioration", "État"]
        )
        self.proposals.setColumnWidth(0, 75)
        self.proposals.setColumnWidth(1, 90)
        self.proposals.setColumnWidth(2, 410)
        self.proposals.currentItemChanged.connect(self._selection_changed)
        self.proposals.itemChanged.connect(
            lambda _item, _column: self._refresh_buttons()
        )
        splitter.addWidget(self.proposals)

        details_panel = QWidget()
        details_layout = QVBoxLayout(details_panel)
        details_layout.addWidget(QLabel("Détails de la proposition"))
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        details_layout.addWidget(self.details, 1)
        splitter.addWidget(details_panel)
        splitter.setSizes([650, 400])
        root.addWidget(splitter, 1)

        self.progress_label = QLabel("OpenRouter analyse le MCD…")
        self.progress_label.setStyleSheet("color: #315d8a; font-weight: bold;")
        self.progress_label.hide()
        root.addWidget(self.progress_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        root.addWidget(self.progress)

        buttons = QHBoxLayout()
        self.analyze_button = QPushButton("✨ Analyser avec l'IA")
        self.view_button = QPushButton("Voir")
        self.ignore_button = QPushButton("Ignorer")
        self.apply_button = QPushButton("Appliquer la sélection…")
        close_button = QPushButton("Fermer")
        self.analyze_button.clicked.connect(self.start_analysis)
        self.view_button.clicked.connect(self.view_selected)
        self.ignore_button.clicked.connect(self.ignore_selected)
        self.apply_button.clicked.connect(self.apply_selected)
        close_button.clicked.connect(self.reject)
        buttons.addWidget(self.analyze_button)
        buttons.addWidget(self.view_button)
        buttons.addWidget(self.ignore_button)
        buttons.addStretch(1)
        buttons.addWidget(self.apply_button)
        buttons.addWidget(close_button)
        root.addLayout(buttons)

        enabled = bool(
            self.store.is_enabled() and self.store.get() and self.store.get_model()
        )
        self.analyze_button.setEnabled(enabled)
        self._refresh_buttons()
        if not enabled:
            self.details.setPlainText(
                "Activez OpenRouter, renseignez votre clé et choisissez un modèle "
                "dans Paramètres → Paramètres OpenRouter."
            )

    def start_analysis(self) -> None:
        if self._thread is not None:
            return
        self._raw = None
        self._error = None
        self._set_busy(True)
        thread = QThread(self)
        worker = _RepairWorker(
            self.service,
            self.store.get(),
            self.store.get_model(),
            self.original_model,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._succeeded)
        worker.failed.connect(self._failed)
        worker.succeeded.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.succeeded.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(self._finished)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()

    @Slot(str)
    def _succeeded(self, raw: str) -> None:
        self._raw = raw

    @Slot(str)
    def _failed(self, message: str) -> None:
        self._error = message

    @Slot()
    def _finished(self) -> None:
        raw, error = self._raw, self._error
        self._thread = None
        self._worker = None
        self._set_busy(False)
        if error:
            QMessageBox.critical(self, "Analyse impossible", error)
            return
        if raw is None:
            QMessageBox.critical(
                self, "Analyse impossible", "OpenRouter n'a renvoyé aucun résultat."
            )
            return
        try:
            self.display_report(self.service.interpret(self.original_model, raw))
        except AiRepairError as parse_error:
            QMessageBox.critical(self, "Réponse IA invalide", str(parse_error))

    def display_report(self, report: AiRepairReport) -> None:
        self.report = report
        count = len(report.proposals)
        default_summary = (
            f"{count} amélioration(s) proposée(s)"
            if count
            else "Aucune amélioration proposée."
        )
        self.summary_label.setText(report.summary or default_summary)
        self.proposals.clear()
        for proposal in report.proposals:
            state = (
                f"{len(proposal.validation.errors)} erreur(s)"
                if proposal.validation.errors
                else "Validée"
            )
            item = QTreeWidgetItem(
                ["", proposal.confidence.label, proposal.title, state]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, proposal.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                0,
                Qt.CheckState.Unchecked
                if proposal.validation.errors
                else Qt.CheckState.Checked,
            )
            if proposal.validation.errors:
                item.setDisabled(True)
            self.proposals.addTopLevelItem(item)
        if self.proposals.topLevelItemCount():
            first = self.proposals.topLevelItem(0)
            if first is not None:
                self.proposals.setCurrentItem(first)
        else:
            self.details.setPlainText(
                report.summary or "Aucune amélioration n'a été proposée."
            )
        self._refresh_buttons()

    def _proposal_id(self) -> str | None:
        item = self.proposals.currentItem()
        if item is None:
            return None
        value = item.data(0, Qt.ItemDataRole.UserRole)
        return value if isinstance(value, str) else None

    def _proposal(self) -> AiRepairProposal | None:
        proposal_id = self._proposal_id()
        if self.report is None or proposal_id is None:
            return None
        return next(
            (item for item in self.report.proposals if item.id == proposal_id), None
        )

    def _selection_changed(
        self, _current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        proposal = self._proposal()
        if proposal is None:
            self.details.clear()
        else:
            validation = (
                "\n".join(f"- {issue.message}" for issue in proposal.validation.issues)
                or "Aucune erreur structurelle."
            )
            self.details.setPlainText(
                f"{proposal.description}\n\nPourquoi ?\n{proposal.rationale}\n\n"
                f"Confiance : {proposal.confidence.label}\n\n"
                f"Patch contrôlé\n{proposal.patch_summary}\n\nValidation\n{validation}"
            )
        self._refresh_buttons()

    def view_selected(self) -> None:
        proposal = self._proposal()
        if proposal is None:
            return
        json_text = json.dumps(
            JsonDiagramRepository().to_dict(proposal.candidate),
            ensure_ascii=False,
            indent=2,
        )
        DesignDraftPreviewDialog(
            self.original_model,
            proposal.candidate,
            json_text,
            proposal.validation,
            self,
            title=f"Voir — {proposal.title}",
            allow_import=False,
        ).exec()

    def ignore_selected(self) -> None:
        item = self.proposals.currentItem()
        if item is not None and not item.isDisabled():
            item.setCheckState(0, Qt.CheckState.Unchecked)
            item.setText(3, "Ignorée")
        self._refresh_buttons()

    def _checked_ids(self) -> set[str]:
        result: set[str] = set()
        for index in range(self.proposals.topLevelItemCount()):
            item = self.proposals.topLevelItem(index)
            if item is not None and item.checkState(0) == Qt.CheckState.Checked:
                value = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(value, str):
                    result.add(value)
        return result

    def apply_selected(self) -> None:
        if self.report is None:
            return
        try:
            candidate, validation, _summary = self.service.combine(
                self.original_model, self.report, self._checked_ids()
            )
        except AiRepairError as error:
            QMessageBox.warning(self, "Réparations incompatibles", str(error))
            return
        json_text = json.dumps(
            JsonDiagramRepository().to_dict(candidate), ensure_ascii=False, indent=2
        )
        preview = DesignDraftPreviewDialog(
            self.original_model,
            candidate,
            json_text,
            validation,
            self,
            title="Aperçu des réparations sélectionnées",
            confirm_label="Confirmer les modifications",
        )
        if preview.exec() == QDialog.DialogCode.Accepted and preview.import_confirmed:
            self.repaired_model = copy.deepcopy(candidate)
            self.accept()

    def _set_busy(self, busy: bool) -> None:
        self.progress_label.setVisible(busy)
        self.progress.setVisible(busy)
        self.analyze_button.setEnabled(not busy)
        self.proposals.setEnabled(not busy)
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        selected = self._proposal() is not None
        busy = self._thread is not None
        self.view_button.setEnabled(selected and not busy)
        self.ignore_button.setEnabled(selected and not busy)
        self.apply_button.setEnabled(bool(self._checked_ids()) and not busy)

    def reject(self) -> None:
        if self._thread is not None:
            self.progress_label.setText(
                "La requête OpenRouter est encore en cours ; attendez sa fin."
            )
            return
        super().reject()
