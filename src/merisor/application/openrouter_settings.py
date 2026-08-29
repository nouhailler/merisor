"""Stockage local de la configuration OpenRouter."""

from __future__ import annotations

from PySide6.QtCore import QSettings


class OpenRouterKeyStore:
    """Utilise le trousseau système quand keyring est disponible.

    Le repli QSettings permet à l'application de fonctionner sur une Debian
    minimale, mais il est signalé à l'utilisateur car il n'est pas chiffré.
    """

    SERVICE = "merisor"
    USER = "openrouter"
    FALLBACK_KEY = "openrouter/api_key"

    def __init__(self, settings: QSettings | None = None) -> None:
        self.settings = settings or QSettings("MERISOR", "MERISOR")
        self._keyring = None
        try:
            import keyring  # type: ignore[import-not-found]

            backend = keyring.get_keyring()
            if backend.__class__.__module__.startswith("keyring.backends.fail"):
                return
            self._keyring = keyring
        except Exception:
            self._keyring = None

    @property
    def uses_keyring(self) -> bool:
        return self._keyring is not None

    @property
    def storage_description(self) -> str:
        if self.uses_keyring:
            return "Stockée dans le trousseau système."
        return (
            "Stockée localement dans QSettings (non chiffré). "
            "Installez le paquet Python keyring pour utiliser le trousseau."
        )

    def get(self) -> str:
        if self._keyring is not None:
            try:
                return self._keyring.get_password(self.SERVICE, self.USER) or ""
            except Exception:
                pass
        return str(self.settings.value(self.FALLBACK_KEY, "") or "")

    def set(self, value: str) -> None:
        value = value.strip()
        if self._keyring is not None:
            try:
                if value:
                    self._keyring.set_password(self.SERVICE, self.USER, value)
                else:
                    self._keyring.delete_password(self.SERVICE, self.USER)
                self.settings.remove(self.FALLBACK_KEY)
                return
            except Exception:
                pass
        self.settings.setValue(self.FALLBACK_KEY, value)

