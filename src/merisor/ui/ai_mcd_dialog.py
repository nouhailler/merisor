"""Saisie, aperçu et import confirmé d'un MCD généré par OpenRouter."""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from merisor.application.ai_mcd_service import (
    AiMcdCandidate,
    AiMcdService,
    AiMcdValidationError,
)
from merisor.application.openrouter_client import OpenRouterClient, OpenRouterError
from merisor.application.openrouter_settings import OpenRouterKeyStore


class _AiGenerationWorker(QObject):
    """Exécute le seul appel réseau sans accéder à un widget Qt."""

    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        service: AiMcdService,
        api_key: str,
        model_id: str,
        description: str,
    ) -> None:
        super().__init__()
        self._service = service
        self._api_key = api_key
        self._model_id = model_id
        self._description = description

    @Slot()
    def run(self) -> None:
        try:
            client = OpenRouterClient(self._api_key, timeout=60)
            result = self._service.generate(client, self._model_id, self._description)
        except (OpenRouterError, AiMcdValidationError) as error:
            self.failed.emit(str(error))
        except Exception as error:  # filet de sécurité du thread réseau
            self.failed.emit(f"Erreur inattendue pendant la génération : {error}")
        else:
            self.succeeded.emit(result)


class MCDPreviewDialog(QDialog):
    """Aperçu éditable ; l'import reste impossible tant que le MCD est invalide."""

    def __init__(self, json_text: str, service: AiMcdService, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setWindowTitle("Aperçu du MCD généré")
        self.resize(900, 680)
        self.service = service
        self.candidate: AiMcdCandidate | None = None

        layout = QVBoxLayout(self)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.tabs = QTabWidget()
        self.summary_tree = QTreeWidget()
        self.summary_tree.setHeaderLabels(["Objet", "Détails"])
        self.summary_tree.header().setStretchLastSection(True)
        self.json_edit = QPlainTextEdit(json_text)
        self.json_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.tabs.addTab(self.summary_tree, "Aperçu")
        self.tabs.addTab(self.json_edit, "JSON éditable")
        layout.addWidget(self.tabs, 1)

        self.validation_text = QPlainTextEdit()
        self.validation_text.setReadOnly(True)
        self.validation_text.setMaximumHeight(150)
        layout.addWidget(QLabel("Validation"))
        layout.addWidget(self.validation_text)

        buttons = QHBoxLayout()
        self.revalidate_button = QPushButton("Revalider")
        self.import_button = QPushButton("Importer dans l'éditeur")
        self.cancel_button = QPushButton("Annuler")
        buttons.addWidget(self.revalidate_button)
        buttons.addStretch(1)
        buttons.addWidget(self.import_button)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)

        self.revalidate_button.clicked.connect(self.revalidate)
        self.import_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.json_edit.textChanged.connect(lambda: self.import_button.setEnabled(False))
        self.revalidate()

    def revalidate(self) -> None:
        try:
            candidate = self.service.validate_json(self.json_edit.toPlainText())
        except AiMcdValidationError as error:
            self.candidate = None
            self.import_button.setEnabled(False)
            self.summary_tree.clear()
            self.status_label.setText("❌ JSON non importable")
            self.status_label.setStyleSheet("color: #b3261e; font-weight: bold;")
            self.validation_text.setPlainText(str(error))
            return
        self.candidate = candidate
        self._populate_summary(candidate)
        issues = candidate.report.issues
        self.validation_text.setPlainText(
            "\n".join(
                f"{'ERREUR' if issue in candidate.report.errors else 'AVERTISSEMENT'} "
                f"— {issue.message}"
                for issue in issues
            )
            or "Aucun problème détecté."
        )
        if candidate.report.errors:
            self.status_label.setText(
                f"❌ {len(candidate.report.errors)} erreur(s) bloquante(s)"
            )
            self.status_label.setStyleSheet("color: #b3261e; font-weight: bold;")
            self.import_button.setEnabled(False)
        else:
            self.status_label.setText(
                f"✓ MCD importable — {len(candidate.report.warnings)} avertissement(s)"
            )
            self.status_label.setStyleSheet("color: #18794e; font-weight: bold;")
            self.import_button.setEnabled(True)
            self.json_edit.blockSignals(True)
            self.json_edit.setPlainText(candidate.json_text)
            self.json_edit.blockSignals(False)

    def _populate_summary(self, candidate: AiMcdCandidate) -> None:
        self.summary_tree.clear()
        entities = QTreeWidgetItem(["Entités", str(len(candidate.model.entities))])
        for entity in candidate.model.entities.values():
            identifiers = ", ".join(
                attribute.name for attribute in entity.identifier_attributes
            )
            QTreeWidgetItem(
                entities,
                [
                    entity.name,
                    f"{len(entity.attributes)} attribut(s), ID : {identifiers}",
                ],
            )
        associations = QTreeWidgetItem(
            ["Associations", str(len(candidate.model.associations))]
        )
        for association in candidate.model.associations.values():
            relations = candidate.model.connected_relations(association.id)
            details = f"{len(relations)} relation(s)"
            if association.is_historized:
                details += ", historisée"
            QTreeWidgetItem(associations, [association.name, details])
        relation_group = QTreeWidgetItem(
            ["Relations", str(len(candidate.model.relations))]
        )
        for relation in candidate.model.relations.values():
            entity = candidate.model.entities[relation.entity_id]
            association = candidate.model.associations[relation.association_id]
            cardinality = str(relation.cardinality) if relation.cardinality else "(?)"
            QTreeWidgetItem(
                relation_group,
                [f"{entity.name} ↔ {association.name}", cardinality],
            )
        self.summary_tree.addTopLevelItems([entities, associations, relation_group])
        self.summary_tree.expandAll()


class AiMcdDialog(QDialog):
    """Fenêtre de description et d'appel explicite à OpenRouter."""

    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setWindowTitle("Générer un MCD avec l'IA")
        self.resize(760, 560)
        self.store = OpenRouterKeyStore()
        self.service = AiMcdService()
        self.imported_candidate: AiMcdCandidate | None = None
        self._generation_thread: QThread | None = None
        self._generation_worker: _AiGenerationWorker | None = None
        self._generated_json: str | None = None
        self._generation_error: str | None = None

        layout = QVBoxLayout(self)
        model_id = self.store.get_model()
        self.model_label = QLabel(f"Modèle sélectionné : {model_id or '(aucun)'}")
        self.model_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.model_label)

        quota = QLabel(
            "Les modèles gratuits OpenRouter peuvent être soumis à des quotas, "
            "des limites de débit ou une indisponibilité temporaire."
        )
        quota.setWordWrap(True)
        quota.setStyleSheet("color: #637083;")
        layout.addWidget(quota)

        layout.addWidget(QLabel("Description de l'application"))
        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText(
            "Exemple : gérer des pilotes, des équipes et l'historique de leurs "
            "engagements. Un pilote possède un identifiant et un nom…"
        )
        layout.addWidget(self.description_edit, 1)

        example = QLabel(
            "Conseil : précisez les objets métier, leurs informations, leurs "
            "identifiants et les règles de liaison ou d'historisation."
        )
        example.setWordWrap(True)
        layout.addWidget(example)

        self.progress_label = QLabel(
            "OpenRouter prépare le MCD… L'interface reste disponible."
        )
        self.progress_label.setStyleSheet("color: #315d8a; font-weight: bold;")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.close_button = self.buttons.button(QDialogButtonBox.StandardButton.Close)
        self.generate_button = self.buttons.addButton(
            "Générer le MCD", QDialogButtonBox.ButtonRole.ActionRole
        )
        self.buttons.rejected.connect(self.reject)
        self.generate_button.clicked.connect(self.generate)
        layout.addWidget(self.buttons)

        enabled = self.store.is_enabled() and bool(self.store.get()) and bool(model_id)
        self.generate_button.setEnabled(enabled)
        if not enabled:
            self.model_label.setText(
                "Configurez et activez OpenRouter dans Paramètres avant de générer."
            )

    def generate(self) -> None:
        if self._generation_thread is not None:
            return
        description = self.description_edit.toPlainText().strip()
        if not description:
            QMessageBox.warning(
                self, "Description requise", "Décrivez d'abord l'application."
            )
            return
        self._generated_json = None
        self._generation_error = None
        self.progress_label.setVisible(True)
        self.progress_bar.setVisible(True)
        self.generate_button.setEnabled(False)
        self.description_edit.setReadOnly(True)
        if self.close_button is not None:
            self.close_button.setEnabled(False)

        thread = QThread(self)
        worker = _AiGenerationWorker(
            self.service,
            self.store.get(),
            self.store.get_model(),
            description,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._generation_succeeded)
        worker.failed.connect(self._generation_failed)
        worker.succeeded.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.succeeded.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(self._generation_finished)
        thread.finished.connect(thread.deleteLater)
        self._generation_thread = thread
        self._generation_worker = worker
        thread.start()

    @Slot(str)
    def _generation_succeeded(self, raw_json: str) -> None:
        self._generated_json = raw_json

    @Slot(str)
    def _generation_failed(self, message: str) -> None:
        self._generation_error = message

    @Slot()
    def _generation_finished(self) -> None:
        raw_json = self._generated_json
        error = self._generation_error
        self._generation_thread = None
        self._generation_worker = None
        self.progress_label.setVisible(False)
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        self.description_edit.setReadOnly(False)
        if self.close_button is not None:
            self.close_button.setEnabled(True)

        if error is not None:
            QMessageBox.critical(self, "Génération impossible", error)
            return
        if raw_json is None:
            QMessageBox.critical(
                self,
                "Génération impossible",
                "OpenRouter n'a renvoyé aucun résultat exploitable.",
            )
            return

        preview = MCDPreviewDialog(raw_json, self.service, self)
        if preview.exec() == QDialog.DialogCode.Accepted and preview.candidate:
            self.imported_candidate = preview.candidate
            self.accept()

    def reject(self) -> None:
        if self._generation_thread is not None:
            self.progress_label.setText(
                "La requête OpenRouter est encore en cours ; attendez sa fin "
                "avant de fermer cette fenêtre."
            )
            return
        super().reject()
