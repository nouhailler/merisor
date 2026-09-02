"""Lecteur intégré de la documentation Markdown de MERISOR."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.application.documentation_catalog import (
    DocumentationCatalog,
    DocumentationError,
)

ONLINE_DOCUMENTATION_URL = "https://github.com/nouhailler/merisor/tree/main/docs"


class DocumentationDialog(QDialog):
    """Navigue dans les guides hors ligne inclus avec l'application."""

    def __init__(
        self,
        page_id: str = "index",
        parent: QWidget | None = None,
        catalog: DocumentationCatalog | None = None,
    ) -> None:
        super().__init__(parent)
        self.catalog = catalog or DocumentationCatalog()
        self.current_path: Path | None = None
        self.setWindowTitle("Documentation MERISOR")
        self.resize(1120, 760)

        root = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel("📚 Documentation MERISOR")
        title_font = title.font()
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        header.addWidget(title)
        header.addStretch(1)
        online_button = QPushButton("Documentation en ligne")
        online_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(ONLINE_DOCUMENTATION_URL))
        )
        header.addWidget(online_button)
        root.addLayout(header)

        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.setPlaceholderText("Rechercher une rubrique…")
        root.addWidget(self.search)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.navigation = QTreeWidget()
        self.navigation.setHeaderHidden(True)
        self.navigation.setMinimumWidth(270)
        self.browser = QTextBrowser()
        self.browser.setOpenLinks(False)
        self.browser.setOpenExternalLinks(False)
        splitter.addWidget(self.navigation)
        splitter.addWidget(self.browser)
        splitter.setSizes([290, 810])
        root.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        close_button = QPushButton("Fermer")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)
        root.addLayout(buttons)

        self._populate_navigation()
        self.search.textChanged.connect(self._filter_navigation)
        self.navigation.currentItemChanged.connect(self._navigation_changed)
        self.browser.anchorClicked.connect(self._open_link)
        self.open_page(page_id)

    def _populate_navigation(self) -> None:
        categories: dict[str, QTreeWidgetItem] = {}
        for page in self.catalog.pages:
            parent = categories.get(page.category)
            if parent is None:
                parent = QTreeWidgetItem([page.category])
                parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                font = parent.font(0)
                font.setBold(True)
                parent.setFont(0, font)
                self.navigation.addTopLevelItem(parent)
                categories[page.category] = parent
            item = QTreeWidgetItem([page.title])
            item.setData(0, Qt.ItemDataRole.UserRole, page.id)
            parent.addChild(item)
        self.navigation.expandAll()

    def open_page(self, page_id: str) -> None:
        try:
            path = self.catalog.path(page_id)
            markdown = path.read_text(encoding="utf-8")
        except (DocumentationError, OSError, UnicodeError) as error:
            self.browser.setPlainText(str(error))
            return
        self.current_path = path
        self.browser.document().setBaseUrl(QUrl.fromLocalFile(f"{path.parent}/"))
        self.browser.setMarkdown(markdown)
        self.browser.verticalScrollBar().setValue(0)
        self._select_page(page_id)

    def _select_page(self, page_id: str) -> None:
        iterator = self.navigation.invisibleRootItem()
        for category_index in range(iterator.childCount()):
            category = iterator.child(category_index)
            if category is None:
                continue
            for page_index in range(category.childCount()):
                item = category.child(page_index)
                if item is None:
                    continue
                if item.data(0, Qt.ItemDataRole.UserRole) == page_id:
                    self.navigation.blockSignals(True)
                    self.navigation.setCurrentItem(item)
                    self.navigation.blockSignals(False)
                    return

    def _navigation_changed(
        self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        if current is None:
            return
        page_id = current.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(page_id, str):
            self.open_page(page_id)

    def _filter_navigation(self, query: str) -> None:
        needle = query.strip().casefold()
        root = self.navigation.invisibleRootItem()
        for category_index in range(root.childCount()):
            category = root.child(category_index)
            if category is None:
                continue
            visible_children = 0
            for page_index in range(category.childCount()):
                item = category.child(page_index)
                if item is None:
                    continue
                visible = not needle or needle in item.text(0).casefold()
                item.setHidden(not visible)
                visible_children += int(visible)
            category.setHidden(visible_children == 0)

    def _open_link(self, url: QUrl) -> None:
        if url.scheme() in {"http", "https", "mailto"}:
            QDesktopServices.openUrl(url)
            return
        if self.current_path is None:
            return
        raw = url.toString()
        relative, _separator, anchor = raw.partition("#")
        if not relative:
            self.browser.scrollToAnchor(anchor)
            return
        target = (self.current_path.parent / relative).resolve()
        try:
            root = self.catalog.root
        except DocumentationError as error:
            QMessageBox.warning(self, "Lien inaccessible", str(error))
            return
        if not target.is_relative_to(root) or not target.is_file():
            QMessageBox.warning(
                self, "Lien inaccessible", "La page demandée est absente du manuel."
            )
            return
        page_id = self.catalog.page_id_for_path(target)
        if page_id is not None:
            self.open_page(page_id)
        else:
            self.current_path = target
            self.browser.document().setBaseUrl(QUrl.fromLocalFile(f"{target.parent}/"))
            self.browser.setMarkdown(target.read_text(encoding="utf-8"))
        if anchor:
            self.browser.scrollToAnchor(anchor)
