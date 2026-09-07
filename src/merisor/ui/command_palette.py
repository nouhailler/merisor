"""Palette de commandes et recherche globale accessibles au clavier."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.application.documentation_catalog import DocumentationCatalog
from merisor.domain import MCDModel, MLDModel


class CommandPalette(QDialog):
    """Recherche et déclenche les commandes existantes, sans les dupliquer."""

    def __init__(
        self, actions: Iterable[QAction], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Palette de commandes")
        self.resize(560, 430)
        self._actions = tuple(
            action for action in actions if action.text() and not action.isSeparator()
        )
        layout = QVBoxLayout(self)
        title = QLabel("Rechercher une commande")
        title.setProperty("role", "pageTitle")
        layout.addWidget(title)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Créer, valider, MLD, SQL, documentation…")
        self.search.setClearButtonEnabled(True)
        layout.addWidget(self.search)
        self.results = QListWidget()
        layout.addWidget(self.results, 1)
        self.search.textChanged.connect(self._populate)
        self.search.returnPressed.connect(self._activate_current)
        self.results.itemActivated.connect(self._activate)
        self._populate("")

    def _populate(self, query: str) -> None:
        needle = query.strip().casefold()
        self.results.clear()
        for action in self._actions:
            haystack = f"{action.text()} {action.toolTip()}".casefold()
            if needle and needle not in haystack:
                continue
            item = QListWidgetItem(action.icon(), action.text().replace("&", ""))
            item.setData(Qt.ItemDataRole.UserRole, action)
            if action.shortcut().toString():
                item.setToolTip(action.shortcut().toString())
            self.results.addItem(item)
        if self.results.count():
            self.results.setCurrentRow(0)

    def _activate_current(self) -> None:
        item = self.results.currentItem()
        if item is not None:
            self._activate(item)

    def _activate(self, item: QListWidgetItem) -> None:
        action = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(action, QAction) and action.isEnabled():
            self.accept()
            action.trigger()


@dataclass(frozen=True, slots=True)
class SearchEntry:
    title: str
    detail: str
    kind: str
    element_id: str


class GlobalSearchDialog(QDialog):
    """Recherche croisée dans le MCD, le MLD et la documentation."""

    result_requested = Signal(str, str)

    def __init__(
        self,
        mcd: MCDModel,
        mld: MLDModel | None,
        parent: QWidget | None = None,
        catalog: DocumentationCatalog | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Recherche globale")
        self.resize(620, 480)
        self._entries = self._build_entries(mcd, mld, catalog or DocumentationCatalog())
        layout = QVBoxLayout(self)
        title = QLabel("⌕ Rechercher dans MERISOR")
        title.setProperty("role", "pageTitle")
        layout.addWidget(title)
        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Entité, association, attribut, table ou documentation…"
        )
        self.search.setClearButtonEnabled(True)
        layout.addWidget(self.search)
        self.results = QListWidget()
        layout.addWidget(self.results, 1)
        self.search.textChanged.connect(self._populate)
        self.results.itemActivated.connect(self._activate)
        self.search.returnPressed.connect(self._activate_current)
        self._populate("")

    @staticmethod
    def _build_entries(
        mcd: MCDModel, mld: MLDModel | None, catalog: DocumentationCatalog
    ) -> tuple[SearchEntry, ...]:
        entries: list[SearchEntry] = []
        for kind, nodes in (
            ("entity", mcd.entities.values()),
            ("association", mcd.associations.values()),
        ):
            label = "Entité" if kind == "entity" else "Association"
            for node in nodes:
                entries.append(SearchEntry(node.name, label, "mcd", node.id))
                entries.extend(
                    SearchEntry(
                        attribute.name,
                        f"Attribut de {node.name}",
                        "mcd",
                        node.id,
                    )
                    for attribute in node.attributes
                )
        if mld is not None:
            for table in mld.tables:
                entries.append(SearchEntry(table.name, "Table MLD", "mld", table.id))
                entries.extend(
                    SearchEntry(
                        column.name,
                        f"Colonne de {table.name}",
                        "mld",
                        table.id,
                    )
                    for column in table.columns
                )
        entries.extend(
            SearchEntry(page.title, page.category, "documentation", page.id)
            for page in catalog.pages
        )
        return tuple(entries)

    def _populate(self, query: str) -> None:
        needle = query.strip().casefold()
        self.results.clear()
        for entry in self._entries:
            if needle and needle not in f"{entry.title} {entry.detail}".casefold():
                continue
            item = QListWidgetItem(f"{entry.title}   ·   {entry.detail}")
            item.setData(Qt.ItemDataRole.UserRole, (entry.kind, entry.element_id))
            self.results.addItem(item)
        if self.results.count():
            self.results.setCurrentRow(0)

    def _activate_current(self) -> None:
        item = self.results.currentItem()
        if item is not None:
            self._activate(item)

    def _activate(self, item: QListWidgetItem) -> None:
        value = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(value, tuple) and len(value) == 2:
            kind, element_id = value
            self.accept()
            self.result_requested.emit(str(kind), str(element_id))
