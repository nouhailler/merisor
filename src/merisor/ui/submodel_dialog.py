"""Gestion des domaines et des vues métier/technique du MCD."""

from __future__ import annotations

import copy
from collections.abc import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.domain import (
    Association,
    DiagramError,
    Entity,
    MCDModel,
    ModelDomain,
    SubmodelView,
    SubmodelViewKind,
)


class SubmodelManagerDialog(QDialog):
    """Édite une copie de la configuration avant confirmation globale."""

    def __init__(self, model: MCDModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Domaines et sous-modèles")
        self.resize(980, 720)
        self.model = model
        self.domains = copy.deepcopy(model.domains)
        self.views = copy.deepcopy(model.submodel_views)

        layout = QVBoxLayout(self)
        explanation = QLabel(
            "Regroupez les objets en domaines, puis composez des vues métier ou "
            "techniques. La vue globale reste toujours disponible."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        tabs = QTabWidget()
        tabs.addTab(self._domain_tab(), "Domaines")
        tabs.addTab(self._view_tab(), "Vues métier et techniques")
        layout.addWidget(tabs, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        if save_button is not None:
            save_button.setText("Appliquer au MCD")
        buttons.accepted.connect(self._accept_configuration)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh_domain_list()
        self._refresh_view_list()

    def _domain_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        list_panel = QWidget()
        list_layout = QVBoxLayout(list_panel)
        self.domain_list = QListWidget()
        self.domain_list.currentItemChanged.connect(self._domain_selected)
        list_layout.addWidget(self.domain_list, 1)
        domain_buttons = QHBoxLayout()
        add_button = QPushButton("Ajouter")
        remove_button = QPushButton("Supprimer")
        add_button.clicked.connect(self._add_domain)
        remove_button.clicked.connect(self._remove_domain)
        domain_buttons.addWidget(add_button)
        domain_buttons.addWidget(remove_button)
        list_layout.addLayout(domain_buttons)
        splitter.addWidget(list_panel)

        editor = QWidget()
        editor_layout = QVBoxLayout(editor)
        editor_layout.addWidget(QLabel("Nom du domaine"))
        self.domain_name = QLineEdit()
        editor_layout.addWidget(self.domain_name)
        editor_layout.addWidget(QLabel("Description"))
        self.domain_description = QPlainTextEdit()
        self.domain_description.setMaximumHeight(90)
        editor_layout.addWidget(self.domain_description)
        editor_layout.addWidget(QLabel("Objets appartenant au domaine"))
        self.domain_nodes = self._create_node_tree()
        editor_layout.addWidget(self.domain_nodes, 1)
        save_domain = QPushButton("Enregistrer le domaine")
        save_domain.clicked.connect(self._save_domain)
        editor_layout.addWidget(save_domain)
        splitter.addWidget(editor)
        splitter.setSizes([280, 650])
        layout.addWidget(splitter)
        return tab

    def _view_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        list_panel = QWidget()
        list_layout = QVBoxLayout(list_panel)
        self.view_list = QListWidget()
        self.view_list.currentItemChanged.connect(self._view_selected)
        list_layout.addWidget(self.view_list, 1)
        view_buttons = QHBoxLayout()
        add_button = QPushButton("Ajouter")
        remove_button = QPushButton("Supprimer")
        add_button.clicked.connect(self._add_view)
        remove_button.clicked.connect(self._remove_view)
        view_buttons.addWidget(add_button)
        view_buttons.addWidget(remove_button)
        list_layout.addLayout(view_buttons)
        splitter.addWidget(list_panel)

        editor = QWidget()
        editor_layout = QVBoxLayout(editor)
        editor_layout.addWidget(QLabel("Nom de la vue"))
        self.view_name = QLineEdit()
        editor_layout.addWidget(self.view_name)
        editor_layout.addWidget(QLabel("Usage"))
        self.view_kind = QComboBox()
        self.view_kind.addItem("Vue métier", SubmodelViewKind.BUSINESS.value)
        self.view_kind.addItem("Vue technique", SubmodelViewKind.TECHNICAL.value)
        editor_layout.addWidget(self.view_kind)
        editor_layout.addWidget(QLabel("Domaines inclus"))
        self.view_domains = QListWidget()
        self.view_domains.setMaximumHeight(150)
        editor_layout.addWidget(self.view_domains)
        editor_layout.addWidget(
            QLabel("Objets ajoutés explicitement, en complément des domaines")
        )
        self.view_nodes = self._create_node_tree()
        editor_layout.addWidget(self.view_nodes, 1)
        save_view = QPushButton("Enregistrer la vue")
        save_view.clicked.connect(self._save_view)
        editor_layout.addWidget(save_view)
        splitter.addWidget(editor)
        splitter.setSizes([280, 650])
        layout.addWidget(splitter)
        return tab

    def _create_node_tree(self) -> QTreeWidget:
        tree = QTreeWidget()
        tree.setHeaderLabels(["Objet", "Type"])
        entities = QTreeWidgetItem(["Entités", str(len(self.model.entities))])
        associations = QTreeWidgetItem(
            ["Associations", str(len(self.model.associations))]
        )
        for entity in sorted(
            self.model.entities.values(), key=lambda item: item.name.casefold()
        ):
            self._checkable_node_item(entities, entity, "Entité")
        for association in sorted(
            self.model.associations.values(), key=lambda item: item.name.casefold()
        ):
            self._checkable_node_item(associations, association, "Association")
        tree.addTopLevelItems([entities, associations])
        tree.expandAll()
        return tree

    @staticmethod
    def _checkable_node_item(
        parent: QTreeWidgetItem,
        node: Entity | Association,
        kind: str,
    ) -> None:
        item = QTreeWidgetItem(parent, [node.name, kind])
        item.setData(0, Qt.ItemDataRole.UserRole, node.id)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Unchecked)

    def _refresh_domain_list(self, selected_id: str | None = None) -> None:
        self.domain_list.blockSignals(True)
        self.domain_list.clear()
        selected_item: QListWidgetItem | None = None
        for domain in sorted(
            self.domains.values(), key=lambda item: item.name.casefold()
        ):
            item = QListWidgetItem(domain.name)
            item.setData(Qt.ItemDataRole.UserRole, domain.id)
            self.domain_list.addItem(item)
            if domain.id == selected_id:
                selected_item = item
        self.domain_list.blockSignals(False)
        if selected_item is not None:
            self.domain_list.setCurrentItem(selected_item)
        elif self.domain_list.count():
            self.domain_list.setCurrentRow(0)
        else:
            self._clear_domain_editor()
        self._refresh_view_domain_choices()

    def _refresh_view_list(self, selected_id: str | None = None) -> None:
        self.view_list.blockSignals(True)
        self.view_list.clear()
        selected_item: QListWidgetItem | None = None
        labels = {
            SubmodelViewKind.BUSINESS: "Métier",
            SubmodelViewKind.TECHNICAL: "Technique",
        }
        for view in sorted(
            self.views.values(),
            key=lambda item: (item.kind.value, item.name.casefold()),
        ):
            item = QListWidgetItem(f"{view.name} — {labels[view.kind]}")
            item.setData(Qt.ItemDataRole.UserRole, view.id)
            self.view_list.addItem(item)
            if view.id == selected_id:
                selected_item = item
        self.view_list.blockSignals(False)
        if selected_item is not None:
            self.view_list.setCurrentItem(selected_item)
        elif self.view_list.count():
            self.view_list.setCurrentRow(0)
        else:
            self._clear_view_editor()

    def _domain_selected(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        domain_id = self._item_id(current)
        domain = self.domains.get(domain_id or "")
        if domain is None:
            self._clear_domain_editor()
            return
        self.domain_name.setText(domain.name)
        self.domain_description.setPlainText(domain.description)
        self._set_checked_nodes(self.domain_nodes, set(domain.node_ids))

    def _view_selected(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        view_id = self._item_id(current)
        view = self.views.get(view_id or "")
        if view is None:
            self._clear_view_editor()
            return
        self.view_name.setText(view.name)
        index = self.view_kind.findData(view.kind.value)
        self.view_kind.setCurrentIndex(max(0, index))
        self._refresh_view_domain_choices(set(view.domain_ids))
        self._set_checked_nodes(self.view_nodes, set(view.node_ids))

    def _add_domain(self) -> None:
        name = self._next_name(
            "Nouveau domaine", (item.name for item in self.domains.values())
        )
        domain = ModelDomain(name)
        self.domains[domain.id] = domain
        self._refresh_domain_list(domain.id)

    def _remove_domain(self) -> None:
        domain_id = self._item_id(self.domain_list.currentItem())
        if domain_id is None:
            return
        self.domains.pop(domain_id, None)
        for view in self.views.values():
            view.domain_ids = tuple(
                item_id for item_id in view.domain_ids if item_id != domain_id
            )
        self._refresh_domain_list()
        self._refresh_view_list()

    def _save_domain(self, _checked: bool = False) -> bool:
        domain_id = self._item_id(self.domain_list.currentItem())
        if domain_id is None:
            return True
        try:
            replacement = ModelDomain(
                self.domain_name.text(),
                self._checked_node_ids(self.domain_nodes),
                id=domain_id,
                description=self.domain_description.toPlainText(),
            )
            self._ensure_unique_name(
                replacement.name, domain_id, self.domains, "domaine"
            )
        except DiagramError as error:
            QMessageBox.warning(self, "Domaine invalide", str(error))
            return False
        self.domains[domain_id] = replacement
        self._refresh_domain_list(domain_id)
        return True

    def _add_view(self) -> None:
        name = self._next_name(
            "Nouvelle vue", (item.name for item in self.views.values())
        )
        view = SubmodelView(name, SubmodelViewKind.BUSINESS)
        self.views[view.id] = view
        self._refresh_view_list(view.id)

    def _remove_view(self) -> None:
        view_id = self._item_id(self.view_list.currentItem())
        if view_id is not None:
            self.views.pop(view_id, None)
            self._refresh_view_list()

    def _save_view(self, _checked: bool = False) -> bool:
        view_id = self._item_id(self.view_list.currentItem())
        if view_id is None:
            return True
        try:
            replacement = SubmodelView(
                self.view_name.text(),
                self.view_kind.currentData(),
                self._checked_domain_ids(),
                self._checked_node_ids(self.view_nodes),
                id=view_id,
            )
            self._ensure_unique_name(replacement.name, view_id, self.views, "vue")
        except DiagramError as error:
            QMessageBox.warning(self, "Vue invalide", str(error))
            return False
        self.views[view_id] = replacement
        self._refresh_view_list(view_id)
        return True

    def _accept_configuration(self) -> None:
        if not self._save_domain() or not self._save_view():
            return
        validation_model = copy.deepcopy(self.model)
        try:
            validation_model.replace_submodels(
                self.domains.values(), self.views.values()
            )
        except DiagramError as error:
            QMessageBox.warning(self, "Configuration invalide", str(error))
            return
        self.accept()

    def _refresh_view_domain_choices(
        self, selected_ids: set[str] | None = None
    ) -> None:
        selected = selected_ids
        if selected is None:
            selected = {
                item.data(Qt.ItemDataRole.UserRole)
                for index in range(self.view_domains.count())
                if (item := self.view_domains.item(index)) is not None
                and item.checkState() == Qt.CheckState.Checked
                and isinstance(item.data(Qt.ItemDataRole.UserRole), str)
            }
        self.view_domains.clear()
        for domain in sorted(
            self.domains.values(), key=lambda item: item.name.casefold()
        ):
            item = QListWidgetItem(domain.name)
            item.setData(Qt.ItemDataRole.UserRole, domain.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if domain.id in selected
                else Qt.CheckState.Unchecked
            )
            self.view_domains.addItem(item)

    def _checked_domain_ids(self) -> tuple[str, ...]:
        result: list[str] = []
        for index in range(self.view_domains.count()):
            item = self.view_domains.item(index)
            if item is None or item.checkState() != Qt.CheckState.Checked:
                continue
            domain_id = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(domain_id, str):
                result.append(domain_id)
        return tuple(result)

    @staticmethod
    def _checked_node_ids(tree: QTreeWidget) -> tuple[str, ...]:
        result: list[str] = []
        for group_index in range(tree.topLevelItemCount()):
            group = tree.topLevelItem(group_index)
            if group is None:
                continue
            for child_index in range(group.childCount()):
                child = group.child(child_index)
                if child is None:
                    continue
                node_id = child.data(0, Qt.ItemDataRole.UserRole)
                if child.checkState(0) == Qt.CheckState.Checked and isinstance(
                    node_id, str
                ):
                    result.append(node_id)
        return tuple(result)

    @staticmethod
    def _set_checked_nodes(tree: QTreeWidget, selected_ids: set[str]) -> None:
        for group_index in range(tree.topLevelItemCount()):
            group = tree.topLevelItem(group_index)
            if group is None:
                continue
            for child_index in range(group.childCount()):
                child = group.child(child_index)
                if child is None:
                    continue
                node_id = child.data(0, Qt.ItemDataRole.UserRole)
                child.setCheckState(
                    0,
                    Qt.CheckState.Checked
                    if node_id in selected_ids
                    else Qt.CheckState.Unchecked,
                )

    @staticmethod
    def _item_id(item: QListWidgetItem | None) -> str | None:
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return value if isinstance(value, str) else None

    @staticmethod
    def _next_name(prefix: str, names: Iterable[str]) -> str:
        existing = {name.casefold() for name in names}
        if prefix.casefold() not in existing:
            return prefix
        index = 2
        while f"{prefix} {index}".casefold() in existing:
            index += 1
        return f"{prefix} {index}"

    @staticmethod
    def _ensure_unique_name(
        name: str,
        current_id: str,
        values: dict[str, ModelDomain] | dict[str, SubmodelView],
        kind: str,
    ) -> None:
        if any(
            item_id != current_id and item.name.casefold() == name.casefold()
            for item_id, item in values.items()
        ):
            raise DiagramError(f"Un autre {kind} porte déjà le nom {name}.")

    def _clear_domain_editor(self) -> None:
        self.domain_name.clear()
        self.domain_description.clear()
        self._set_checked_nodes(self.domain_nodes, set())

    def _clear_view_editor(self) -> None:
        self.view_name.clear()
        self.view_kind.setCurrentIndex(0)
        self._refresh_view_domain_choices(set())
        self._set_checked_nodes(self.view_nodes, set())
