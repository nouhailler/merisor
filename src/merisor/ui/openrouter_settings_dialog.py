"""Dialogue de configuration locale d'OpenRouter."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from merisor.application.openrouter_client import (
    OpenRouterClient,
    OpenRouterError,
    OpenRouterModel,
)
from merisor.application.openrouter_settings import OpenRouterKeyStore


class OpenRouterSettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setWindowTitle("Paramètres OpenRouter")
        self.setMinimumWidth(520)
        self.store = OpenRouterKeyStore()

        layout = QVBoxLayout(self)
        intro = QLabel(
            "La clé est utilisée uniquement pour les appels OpenRouter et "
            "n'est jamais enregistrée dans les fichiers MCD."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        layout.addWidget(QLabel("Clé API OpenRouter"))
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("sk-or-v1-…")
        self.key_edit.setText(self.store.get())
        self.key_edit.setClearButtonEnabled(True)
        layout.addWidget(self.key_edit)

        self.show_key = QCheckBox("Afficher la clé")
        self.show_key.toggled.connect(self._toggle_visibility)
        layout.addWidget(self.show_key)

        self.storage_label = QLabel(self.store.storage_description)
        self.storage_label.setWordWrap(True)
        self.storage_label.setStyleSheet("color: #637083;")
        layout.addWidget(self.storage_label)

        self.test_button = QPushButton("Tester la clé")
        self.refresh_button = QPushButton("Actualiser les modèles gratuits")
        layout.addWidget(self.test_button)
        layout.addWidget(self.refresh_button)

        layout.addWidget(QLabel("Modèle gratuit sélectionné"))
        self.model_combo = QComboBox()
        self.model_combo.setPlaceholderText("Actualisez la liste des modèles")
        layout.addWidget(self.model_combo)

        self.enabled_checkbox = QCheckBox("Activer la génération assistée par IA")
        self.enabled_checkbox.setChecked(self.store.is_enabled())
        self.enabled_checkbox.setToolTip(
            "Cette option sera utilisée par la génération de MCD de la prochaine étape."
        )
        layout.addWidget(self.enabled_checkbox)

        self.status_label = QLabel("Une clé est nécessaire pour l'étape suivante.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.test_button.clicked.connect(self._test_key)
        self.refresh_button.clicked.connect(self._refresh_models)
        self._refresh_models_from_settings()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _toggle_visibility(self, visible: bool) -> None:
        self.key_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        )

    def _save(self) -> None:
        key = self.key_edit.text().strip()
        if key and not key.startswith("sk-or-"):
            self.status_label.setText(
                "Attention : le format ne ressemble pas à une clé OpenRouter. "
                "Vous pouvez néanmoins la conserver."
            )
            self.status_label.setStyleSheet("color: #9a6700;")
        else:
            self.status_label.setText("Configuration enregistrée.")
            self.status_label.setStyleSheet("color: #18794e;")
        self.store.set(key)
        selected = self.model_combo.currentData()
        self.store.set_model(str(selected) if selected else "")
        self.store.set_enabled(self.enabled_checkbox.isChecked() and bool(key))
        self.accept()

    def _test_key(self) -> None:
        try:
            OpenRouterClient(self.key_edit.text()).test_key()
        except OpenRouterError as error:
            self.status_label.setText(str(error))
            self.status_label.setStyleSheet("color: #b3261e;")
        else:
            self.status_label.setText("Clé valide : OpenRouter est accessible.")
            self.status_label.setStyleSheet("color: #18794e;")

    def _refresh_models(self) -> None:
        try:
            models = OpenRouterClient(self.key_edit.text()).list_models()
        except OpenRouterError as error:
            self.status_label.setText(str(error))
            self.status_label.setStyleSheet("color: #b3261e;")
            return
        self._populate_models(models)
        suffix = " modèle gratuit" if len(models) == 1 else " modèles gratuits"
        self.status_label.setText(f"{len(models)}{suffix} disponible(s).")
        self.status_label.setStyleSheet("color: #18794e;")

    def _refresh_models_from_settings(self) -> None:
        saved_model = self.store.get_model()
        if saved_model:
            self.model_combo.addItem(saved_model, saved_model)
            self.model_combo.setCurrentIndex(0)

    def _populate_models(self, models: list[OpenRouterModel]) -> None:
        saved_model = self.store.get_model()
        self.model_combo.clear()
        for model in models:
            suffix = " — JSON" if model.supports_json else ""
            self.model_combo.addItem(f"{model.name} ({model.id}){suffix}", model.id)
        index = self.model_combo.findData(saved_model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
