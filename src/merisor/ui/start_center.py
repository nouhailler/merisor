"""Écran d'accueil et points d'entrée du parcours MERISOR."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from merisor.ui.theme import Spacing


class StartCenter(QWidget):
    """Accueil sans logique de fichier : les actions sont déléguées au shell."""

    new_requested = Signal()
    open_requested = Signal()
    ai_requested = Signal()
    import_ddl_requested = Signal()
    import_pwa_requested = Signal()
    recent_requested = Signal(str)
    example_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("startCenter")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget(scroll)
        content.setObjectName("startCenterContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(48, 38, 48, 38)
        layout.setSpacing(Spacing.XL)
        scroll.setWidget(content)

        eyebrow = QLabel("MERISOR", content)
        eyebrow.setObjectName("startBrand")
        eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(eyebrow)
        title = QLabel(
            "Concevez vos systèmes d'information\navec la méthode MERISE", content
        )
        title.setProperty("role", "pageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        subtitle = QLabel(
            "Du modèle conceptuel au SQL, avec validation et explications à chaque étape.",
            content,
        )
        subtitle.setProperty("role", "secondary")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        primary_actions = QHBoxLayout()
        primary_actions.setSpacing(Spacing.MD)
        self.new_button = self._action_button("+  Nouveau modèle", primary=True)
        self.open_button = self._action_button("Ouvrir un modèle")
        self.ai_button = self._action_button("✨  Assistant IA")
        primary_actions.addStretch(1)
        primary_actions.addWidget(self.new_button)
        primary_actions.addWidget(self.open_button)
        primary_actions.addWidget(self.ai_button)
        primary_actions.addStretch(1)
        layout.addLayout(primary_actions)

        paths = QGridLayout()
        paths.setHorizontalSpacing(Spacing.LG)
        paths.setVerticalSpacing(Spacing.LG)
        self.recent_list = self._list_panel(
            paths, 0, 0, "Modèles récents", "Aucun modèle récent"
        )
        self.example_list = self._list_panel(
            paths, 0, 1, "Exemples", "Aucun exemple installé"
        )
        layout.addLayout(paths)

        import_title = QLabel("Importer un modèle existant", content)
        import_title.setProperty("role", "sectionTitle")
        layout.addWidget(import_title)
        imports = QHBoxLayout()
        self.import_ddl_button = self._action_button("Importer SQL / DDL…")
        self.import_pwa_button = self._action_button("Analyser un projet PWA…")
        imports.addWidget(self.import_ddl_button)
        imports.addWidget(self.import_pwa_button)
        imports.addStretch(1)
        layout.addLayout(imports)
        layout.addStretch(1)

        self.new_button.clicked.connect(self.new_requested)
        self.open_button.clicked.connect(self.open_requested)
        self.ai_button.clicked.connect(self.ai_requested)
        self.import_ddl_button.clicked.connect(self.import_ddl_requested)
        self.import_pwa_button.clicked.connect(self.import_pwa_requested)
        self.recent_list.itemActivated.connect(self._recent_activated)
        self.example_list.itemActivated.connect(self._example_activated)

    def set_recent_files(self, paths: list[str]) -> None:
        self._populate_paths(self.recent_list, paths, "Aucun modèle récent")

    def set_examples(self, paths: list[Path]) -> None:
        self.example_list.clear()
        if not paths:
            self._placeholder(self.example_list, "Aucun exemple installé")
            return
        for path in paths:
            item = QListWidgetItem(path.stem.replace("_", " ").title())
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            self.example_list.addItem(item)

    @staticmethod
    def _action_button(text: str, *, primary: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setMinimumWidth(180)
        button.setMinimumHeight(42)
        if primary:
            button.setProperty("role", "primary")
        return button

    @staticmethod
    def _list_panel(
        layout: QGridLayout, row: int, column: int, title: str, placeholder: str
    ) -> QListWidget:
        panel = QFrame()
        panel.setProperty("role", "card")
        panel_layout = QVBoxLayout(panel)
        label = QLabel(title)
        label.setProperty("role", "sectionTitle")
        panel_layout.addWidget(label)
        items = QListWidget()
        items.setMinimumHeight(170)
        StartCenter._placeholder(items, placeholder)
        panel_layout.addWidget(items)
        layout.addWidget(panel, row, column)
        return items

    @staticmethod
    def _placeholder(widget: QListWidget, text: str) -> None:
        item = QListWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        widget.addItem(item)

    @classmethod
    def _populate_paths(
        cls, widget: QListWidget, paths: list[str], placeholder: str
    ) -> None:
        widget.clear()
        if not paths:
            cls._placeholder(widget, placeholder)
            return
        for filename in paths:
            path = Path(filename)
            item = QListWidgetItem(path.stem)
            item.setData(Qt.ItemDataRole.UserRole, filename)
            item.setToolTip(filename)
            widget.addItem(item)

    def _recent_activated(self, item: QListWidgetItem) -> None:
        filename = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(filename, str):
            self.recent_requested.emit(filename)

    def _example_activated(self, item: QListWidgetItem) -> None:
        filename = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(filename, str):
            self.example_requested.emit(filename)
