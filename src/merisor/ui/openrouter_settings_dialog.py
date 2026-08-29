"""Dialogue de configuration locale d'OpenRouter."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
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

        self.status_label = QLabel("Une clé est nécessaire pour l'étape suivante.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

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
        self.accept()
