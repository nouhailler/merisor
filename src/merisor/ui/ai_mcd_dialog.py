"""Saisie, aperçu et import confirmé d'un MCD généré par OpenRouter."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
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


class MCDPreviewDialog(QDialog):
    """Aperçu éditable ; l'import reste impossible tant que le MCD est invalide."""

    def __init__(
        self, json_text: str, service: AiMcdService, parent=None
    ) -> None:  # type: ignore[no-untyped-def]
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
                [entity.name, f"{len(entity.attributes)} attribut(s), ID : {identifiers}"],
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
        relations = QTreeWidgetItem(
            ["Relations", str(len(candidate.model.relations))]
        )
        for relation in candidate.model.relations.values():
            entity = candidate.model.entities[relation.entity_id]
            association = candidate.model.associations[relation.association_id]
            cardinality = str(relation.cardinality) if relation.cardinality else "(?)"
            QTreeWidgetItem(
                relations,
                [f"{entity.name} ↔ {association.name}", cardinality],
            )
        self.summary_tree.addTopLevelItems([entities, associations, relations])
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

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.generate_button = buttons.addButton(
            "Générer le MCD", QDialogButtonBox.ButtonRole.ActionRole
        )
        buttons.rejected.connect(self.reject)
        self.generate_button.clicked.connect(self.generate)
        layout.addWidget(buttons)

        enabled = self.store.is_enabled() and bool(self.store.get()) and bool(model_id)
        self.generate_button.setEnabled(enabled)
        if not enabled:
            self.model_label.setText(
                "Configurez et activez OpenRouter dans Paramètres avant de générer."
            )

    def generate(self) -> None:
        description = self.description_edit.toPlainText().strip()
        if not description:
            QMessageBox.warning(
                self, "Description requise", "Décrivez d'abord l'application."
            )
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.generate_button.setEnabled(False)
        try:
            client = OpenRouterClient(self.store.get(), timeout=60)
            raw_json = self.service.generate(
                client, self.store.get_model(), description
            )
        except (OpenRouterError, AiMcdValidationError) as error:
            QMessageBox.critical(self, "Génération impossible", str(error))
            return
        finally:
            QApplication.restoreOverrideCursor()
            self.generate_button.setEnabled(True)

        preview = MCDPreviewDialog(raw_json, self.service, self)
        if preview.exec() == QDialog.DialogCode.Accepted and preview.candidate:
            self.imported_candidate = preview.candidate
            self.accept()

