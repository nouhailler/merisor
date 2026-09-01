"""Assistant MERISE conversationnel, brouillon versionné et import explicite."""

from __future__ import annotations

import copy

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
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

from merisor.application import (
    ConversationalDesignService,
    DesignSession,
    DesignSessionError,
    DesignStep,
    DiagramController,
    McdAutoLayout,
    OpenRouterClient,
    OpenRouterError,
    OpenRouterKeyStore,
    compare_models,
)
from merisor.domain import MCDModel, ValidationReport
from merisor.ui.canvas import DiagramScene, DiagramView


class _ConversationWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        service: ConversationalDesignService,
        api_key: str,
        model_id: str,
        session: DesignSession,
        message: str,
    ) -> None:
        super().__init__()
        self._service = service
        self._api_key = api_key
        self._model_id = model_id
        self._session = session
        self._message = message

    @Slot()
    def run(self) -> None:
        try:
            client = OpenRouterClient(self._api_key, timeout=60)
            step = self._service.generate_step(
                client, self._model_id, self._session, self._message
            )
        except (OpenRouterError, DesignSessionError) as error:
            self.failed.emit(str(error))
        except Exception as error:  # filet de sécurité du thread réseau
            self.failed.emit(f"Erreur inattendue pendant l'analyse : {error}")
        else:
            self.succeeded.emit(step)


class DesignDraftPreviewDialog(QDialog):
    """Aperçu graphique et différentiel d'une copie du MCD."""

    def __init__(
        self,
        current_model: MCDModel,
        draft_model: MCDModel,
        json_text: str,
        report: ValidationReport,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Aperçu du brouillon conversationnel")
        self.resize(1050, 760)
        self.import_confirmed = False

        layout = QVBoxLayout(self)
        status = QLabel()
        status.setWordWrap(True)
        if report.errors:
            status.setText(
                f"❌ Brouillon non importable — {len(report.errors)} erreur(s)."
            )
            status.setStyleSheet("color: #b3261e; font-weight: bold;")
        else:
            status.setText(
                "✓ Brouillon importable. Le MCD courant ne sera remplacé "
                "qu'après confirmation."
            )
            status.setStyleSheet("color: #18794e; font-weight: bold;")
        layout.addWidget(status)

        tabs = QTabWidget()
        preview_model = copy.deepcopy(draft_model)
        for node_id, position in McdAutoLayout().calculate(preview_model).items():
            preview_model.move_node(node_id, position)
        scene = DiagramScene(self)
        self.graph_view = DiagramView(scene, self)
        self.preview_controller = DiagramController(scene, self)
        self.preview_controller.load_transient_model(preview_model)
        self.graph_view.fit_scene()
        tabs.addTab(self.graph_view, "Graphe")

        differences = QPlainTextEdit(
            compare_models(current_model, draft_model).render()
        )
        differences.setReadOnly(True)
        tabs.addTab(differences, "Différences")

        json_view = QPlainTextEdit(json_text)
        json_view.setReadOnly(True)
        json_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        tabs.addTab(json_view, "JSON")
        layout.addWidget(tabs, 1)

        validation = QPlainTextEdit()
        validation.setReadOnly(True)
        validation.setMaximumHeight(130)
        validation.setPlainText(
            "\n".join(
                f"{'ERREUR' if issue in report.errors else 'AVERTISSEMENT'} — "
                f"{issue.message}"
                for issue in report.issues
            )
            or "Aucun problème détecté."
        )
        layout.addWidget(validation)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        import_button = QPushButton("Confirmer l'import")
        import_button.setEnabled(not report.errors)
        cancel_button = QPushButton("Revenir à la conversation")
        import_button.clicked.connect(self._confirm)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(cancel_button)
        buttons.addWidget(import_button)
        layout.addLayout(buttons)

    def _confirm(self) -> None:
        answer = QMessageBox.question(
            self,
            "Importer le brouillon",
            "Remplacer le MCD courant par ce brouillon ?\n\n"
            "Cette opération pourra être annulée avec Édition → Annuler.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.import_confirmed = True
            self.accept()


class ConversationalDesignDialog(QDialog):
    """Dialogue itératif : analyse, questions, révisions, puis aperçu."""

    def __init__(
        self,
        current_model: MCDModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Assistant MERISE conversationnel")
        self.resize(1180, 760)
        self.store = OpenRouterKeyStore()
        self.service = ConversationalDesignService()
        self.original_model = copy.deepcopy(current_model)
        self.session = DesignSession(current_draft=current_model)
        self.imported_model: MCDModel | None = None
        self._thread: QThread | None = None
        self._worker: _ConversationWorker | None = None
        self._pending_message = ""
        self._step: DesignStep | None = None
        self._error: str | None = None

        root = QVBoxLayout(self)
        header = QLabel(
            f"Modèle OpenRouter : {self.store.get_model() or '(aucun)'} — "
            "les propositions restent dans un brouillon isolé. À chaque envoi, "
            "le brouillon et le contexte affiché sont transmis à OpenRouter."
        )
        header.setWordWrap(True)
        root.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._conversation_panel())
        splitter.addWidget(self._analysis_panel())
        splitter.setSizes([650, 500])
        root.addWidget(splitter, 1)

        self.progress_label = QLabel("OpenRouter analyse votre modèle…")
        self.progress_label.setStyleSheet("color: #315d8a; font-weight: bold;")
        self.progress_label.hide()
        root.addWidget(self.progress_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        root.addWidget(self.progress)

        footer = QHBoxLayout()
        self.rewind_button = QPushButton("Révision précédente")
        self.preview_button = QPushButton("Aperçu et import…")
        close_button = QPushButton("Fermer")
        self.rewind_button.clicked.connect(self._rewind)
        self.preview_button.clicked.connect(self._preview)
        close_button.clicked.connect(self.reject)
        footer.addWidget(self.rewind_button)
        footer.addStretch(1)
        footer.addWidget(self.preview_button)
        footer.addWidget(close_button)
        root.addLayout(footer)
        self._refresh()

    def _conversation_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("Conversation"))
        self.conversation = QPlainTextEdit()
        self.conversation.setReadOnly(True)
        self.conversation.setPlaceholderText(
            "Décrivez votre besoin. L'assistant identifiera les concepts puis "
            "posera uniquement les questions qui influencent le modèle."
        )
        layout.addWidget(self.conversation, 1)
        self.message_edit = QPlainTextEdit()
        self.message_edit.setMaximumHeight(115)
        self.message_edit.setPlaceholderText(
            "Exemple : je veux gérer une bibliothèque avec des livres, des "
            "auteurs, des lecteurs et l'historique des emprunts."
        )
        layout.addWidget(self.message_edit)
        self.send_button = QPushButton("Analyser et proposer")
        self.send_button.clicked.connect(self._send_free_message)
        layout.addWidget(self.send_button)
        return panel

    def _analysis_panel(self) -> QWidget:
        tabs = QTabWidget()
        questions = QWidget()
        questions_layout = QVBoxLayout(questions)
        self.questions_tree = QTreeWidget()
        self.questions_tree.setHeaderLabels(["Question", "Impact"])
        self.questions_tree.currentItemChanged.connect(self._question_selected)
        questions_layout.addWidget(self.questions_tree, 1)
        self.answer_choice = QComboBox()
        self.answer_choice.setEditable(True)
        questions_layout.addWidget(self.answer_choice)
        self.answer_button = QPushButton("Enregistrer cette réponse")
        self.answer_button.clicked.connect(self._record_answer)
        questions_layout.addWidget(self.answer_button)
        self.continue_button = QPushButton("Continuer avec les réponses")
        self.continue_button.clicked.connect(self._continue_with_answers)
        questions_layout.addWidget(self.continue_button)
        tabs.addTab(questions, "Questions")

        concepts = QWidget()
        concepts_layout = QVBoxLayout(concepts)
        self.concepts_tree = QTreeWidget()
        self.concepts_tree.setHeaderLabels(["Concept", "Type", "Confiance"])
        concepts_layout.addWidget(self.concepts_tree)
        tabs.addTab(concepts, "Concepts")

        assumptions = QWidget()
        assumptions_layout = QVBoxLayout(assumptions)
        self.assumptions_list = QListWidget()
        assumptions_layout.addWidget(self.assumptions_list)
        tabs.addTab(assumptions, "Hypothèses")

        draft = QWidget()
        draft_layout = QVBoxLayout(draft)
        self.revision_label = QLabel()
        draft_layout.addWidget(self.revision_label)
        self.draft_tree = QTreeWidget()
        self.draft_tree.setHeaderLabels(["Brouillon", "Détails"])
        draft_layout.addWidget(self.draft_tree, 1)
        self.validation_text = QPlainTextEdit()
        self.validation_text.setReadOnly(True)
        self.validation_text.setMaximumHeight(160)
        draft_layout.addWidget(self.validation_text)
        tabs.addTab(draft, "Brouillon")
        return tabs

    def _send_free_message(self) -> None:
        self._start_request(self.message_edit.toPlainText())

    def _continue_with_answers(self) -> None:
        if not self.session.all_pending_questions_answered:
            QMessageBox.warning(
                self,
                "Réponses incomplètes",
                "Répondez à toutes les questions structurantes avant de continuer.",
            )
            return
        self._start_request(self.session.formatted_answers())

    def _start_request(self, message: str) -> None:
        if self._thread is not None:
            return
        clean_message = message.strip()
        if not clean_message:
            QMessageBox.warning(self, "Description requise", "Écrivez un message.")
            return
        if not (
            self.store.is_enabled() and self.store.get() and self.store.get_model()
        ):
            QMessageBox.warning(
                self,
                "OpenRouter non configuré",
                "Activez l'IA, renseignez une clé et sélectionnez un modèle gratuit "
                "dans Paramètres → Paramètres OpenRouter.",
            )
            return
        self._pending_message = clean_message
        self._step = None
        self._error = None
        self._set_busy(True)
        thread = QThread(self)
        worker = _ConversationWorker(
            self.service,
            self.store.get(),
            self.store.get_model(),
            self.session,
            clean_message,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._request_succeeded)
        worker.failed.connect(self._request_failed)
        worker.succeeded.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.succeeded.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(self._request_finished)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()

    @Slot(object)
    def _request_succeeded(self, result: object) -> None:
        if isinstance(result, DesignStep):
            self._step = result
        else:
            self._error = "La réponse interne de l'assistant est invalide."

    @Slot(str)
    def _request_failed(self, message: str) -> None:
        self._error = message

    @Slot()
    def _request_finished(self) -> None:
        step = self._step
        error = self._error
        self._thread = None
        self._worker = None
        self._set_busy(False)
        if error:
            QMessageBox.critical(self, "Analyse impossible", error)
            return
        if step is None:
            QMessageBox.critical(
                self, "Analyse impossible", "OpenRouter n'a renvoyé aucun résultat."
            )
            return
        self.session.accept_step(self._pending_message, step)
        self.message_edit.clear()
        self._refresh()

    def _record_answer(self) -> None:
        item = self.questions_tree.currentItem()
        if item is None:
            return
        question_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(question_id, str):
            return
        try:
            self.session.record_answer(question_id, self.answer_choice.currentText())
        except DesignSessionError as error:
            QMessageBox.warning(self, "Réponse invalide", str(error))
            return
        self._refresh_questions()

    def _question_selected(
        self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        self.answer_choice.clear()
        if current is None:
            return
        question_id = current.data(0, Qt.ItemDataRole.UserRole)
        question = next(
            (
                candidate
                for candidate in self.session.pending_questions
                if candidate.id == question_id
            ),
            None,
        )
        if question is None:
            return
        self.answer_choice.addItems(question.choices)
        saved = self.session.answered_questions.get(question.id)
        if saved:
            self.answer_choice.setCurrentText(saved)

    def _rewind(self) -> None:
        if self.session.rewind():
            self._refresh()

    def _preview(self) -> None:
        report = self.session.revisions[-1].report
        preview = DesignDraftPreviewDialog(
            self.original_model,
            self.session.current_draft,
            self.session.current_json(),
            report,
            self,
        )
        if preview.exec() == QDialog.DialogCode.Accepted and preview.import_confirmed:
            self.imported_model = copy.deepcopy(self.session.current_draft)
            self.accept()

    def _set_busy(self, busy: bool) -> None:
        self.progress_label.setVisible(busy)
        self.progress.setVisible(busy)
        self.send_button.setEnabled(not busy)
        self.continue_button.setEnabled(not busy)
        self.preview_button.setEnabled(not busy and self._can_preview())
        self.rewind_button.setEnabled(not busy and len(self.session.revisions) > 1)
        self.message_edit.setReadOnly(busy)

    def _refresh(self) -> None:
        self.conversation.setPlainText(
            "\n\n".join(
                f"VOUS\n{turn.user_message}\n\nASSISTANT\n{turn.assistant_message}"
                for turn in self.session.turns
            )
        )
        self.conversation.verticalScrollBar().setValue(
            self.conversation.verticalScrollBar().maximum()
        )
        self._refresh_questions()
        self.concepts_tree.clear()
        for concept in self.session.detected_concepts:
            QTreeWidgetItem(
                self.concepts_tree,
                [concept.name, concept.kind.value, f"{concept.confidence:.0%}"],
            )
        self.assumptions_list.clear()
        self.assumptions_list.addItems(self.session.assumptions)
        self._refresh_draft()
        self.rewind_button.setEnabled(len(self.session.revisions) > 1)
        self.preview_button.setEnabled(self._can_preview())

    def _refresh_questions(self) -> None:
        self.questions_tree.clear()
        for question in self.session.pending_questions:
            answered = question.id in self.session.answered_questions
            item = QTreeWidgetItem(
                [
                    ("✓ " if answered else "? ") + question.text,
                    question.impact,
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, question.id)
            self.questions_tree.addTopLevelItem(item)
        if self.questions_tree.topLevelItemCount():
            first_item = self.questions_tree.topLevelItem(0)
            if first_item is not None:
                self.questions_tree.setCurrentItem(first_item)
        self.continue_button.setEnabled(self.session.all_pending_questions_answered)

    def _refresh_draft(self) -> None:
        model = self.session.current_draft
        self.draft_tree.clear()
        entities = QTreeWidgetItem(["Entités", str(len(model.entities))])
        for entity in model.entities.values():
            QTreeWidgetItem(
                entities, [entity.name, f"{len(entity.attributes)} attribut(s)"]
            )
        associations = QTreeWidgetItem(["Associations", str(len(model.associations))])
        for association in model.associations.values():
            QTreeWidgetItem(
                associations,
                [
                    association.name,
                    f"{len(model.connected_relations(association.id))} lien(s)",
                ],
            )
        self.draft_tree.addTopLevelItems([entities, associations])
        self.draft_tree.expandAll()
        revision = self.session.revisions[-1]
        self.revision_label.setText(f"Révision {revision.number} — {revision.summary}")
        self.validation_text.setPlainText(
            "\n".join(
                f"{'ERREUR' if issue in revision.report.errors else 'AVERTISSEMENT'} — "
                f"{issue.message}"
                for issue in revision.report.issues
            )
            or "Aucun problème détecté."
        )

    def _can_preview(self) -> bool:
        report = self.session.revisions[-1].report
        return (
            self.session.ready_for_preview
            and bool(self.session.current_draft.entities)
            and not report.errors
        )

    def reject(self) -> None:
        if self._thread is not None:
            self.progress_label.setText(
                "La requête OpenRouter est encore en cours ; attendez sa fin."
            )
            return
        super().reject()
