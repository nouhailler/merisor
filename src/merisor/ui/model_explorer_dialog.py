"""Vue de navigation non destructive pour les MCD volumineux."""

from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.application import (
    GLOBAL_SCOPE_ID,
    DiagramController,
    McdAutoLayout,
    SubmodelResolver,
)
from merisor.application.model_explorer import ExplorationOptions, ModelExplorer
from merisor.domain import Association, Entity, MCDModel
from merisor.ui.canvas import DiagramScene, DiagramView


class ModelExplorerDialog(QDialog):
    """Recherche, focus, filtres et masquages temporaires du MCD."""

    def __init__(self, model: MCDModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Exploration du modèle")
        self.resize(1320, 820)
        self.source_model = copy.deepcopy(model)
        self.explorer = ModelExplorer()
        self.submodels = SubmodelResolver()
        self.focus_id: str | None = None
        self.hidden_ids: set[str] = set()

        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Vue :"))
        self.scope_combo = QComboBox()
        category_labels = {
            "GLOBAL": "Globale",
            "DOMAIN": "Domaine",
            "BUSINESS": "Métier",
            "TECHNICAL": "Technique",
        }
        for scope in self.submodels.scopes(self.source_model):
            self.scope_combo.addItem(
                f"{category_labels[scope.category]} — {scope.label}", scope.id
            )
        toolbar.addWidget(self.scope_combo)
        toolbar.addWidget(QLabel("Recherche :"))
        self.search_edit = QLineEdit()
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setPlaceholderText(
            "Nom d'entité, d'association ou d'attribut…"
        )
        toolbar.addWidget(self.search_edit, 1)
        self.zoom_out_button = QPushButton("-")
        self.zoom_out_button.setToolTip("Zoom arrière")
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setToolTip("Zoom avant")
        self.fit_button = QPushButton("Ajuster")
        toolbar.addWidget(self.zoom_out_button)
        toolbar.addWidget(self.zoom_in_button)
        toolbar.addWidget(self.fit_button)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._navigation_panel())

        self.scene = DiagramScene(self)
        self.view = DiagramView(self.scene, self)
        self.controller = DiagramController(self.scene, self)
        splitter.addWidget(self.view)
        splitter.addWidget(self._dependency_panel())
        splitter.setSizes([300, 720, 300])
        root.addWidget(splitter, 1)

        footer = QHBoxLayout()
        self.status_label = QLabel()
        footer.addWidget(self.status_label, 1)
        close_button = QPushButton("Fermer")
        close_button.clicked.connect(self.accept)
        footer.addWidget(close_button)
        root.addLayout(footer)

        self.search_edit.textChanged.connect(self._search_changed)
        self.scope_combo.currentIndexChanged.connect(self._scope_changed)
        self.entity_filter.toggled.connect(self._rebuild)
        self.association_filter.toggled.connect(self._rebuild)
        self.links_filter.toggled.connect(self._rebuild)
        self.restrict_search.toggled.connect(self._rebuild)
        self.depth_combo.currentIndexChanged.connect(self._rebuild)
        self.focus_button.clicked.connect(self._focus_selected_result)
        self.clear_focus_button.clicked.connect(self._clear_focus)
        self.hide_button.clicked.connect(self._hide_selected)
        self.restore_button.clicked.connect(self._restore_hidden)
        self.results.itemDoubleClicked.connect(
            lambda _item, _column: self._focus_selected_result()
        )
        self.hidden_list.itemDoubleClicked.connect(self._restore_one)
        self.controller.selection_changed.connect(self._selection_changed)
        self.zoom_in_button.clicked.connect(self.view.zoom_in)
        self.zoom_out_button.clicked.connect(self.view.zoom_out)
        self.fit_button.clicked.connect(self.view.fit_scene)

        self._refresh_results()
        self._rebuild()

    def _navigation_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("Résultats"))
        self.results = QTreeWidget()
        self.results.setHeaderLabels(["Objet", "Type"])
        self.results.setRootIsDecorated(False)
        layout.addWidget(self.results, 1)

        self.focus_button = QPushButton("Centrer et isoler")
        layout.addWidget(self.focus_button)
        self.focus_label = QLabel("Focus : tout le modèle")
        self.focus_label.setWordWrap(True)
        layout.addWidget(self.focus_label)

        filter_group = QGroupBox("Filtres")
        filter_layout = QVBoxLayout(filter_group)
        self.entity_filter = QCheckBox("Entités")
        self.entity_filter.setChecked(True)
        self.association_filter = QCheckBox("Associations")
        self.association_filter.setChecked(True)
        self.links_filter = QCheckBox("Relations et héritages")
        self.links_filter.setChecked(True)
        self.restrict_search = QCheckBox("Limiter le graphe aux résultats")
        filter_layout.addWidget(self.entity_filter)
        filter_layout.addWidget(self.association_filter)
        filter_layout.addWidget(self.links_filter)
        filter_layout.addWidget(self.restrict_search)
        filter_layout.addWidget(QLabel("Profondeur autour du focus"))
        self.depth_combo = QComboBox()
        self.depth_combo.addItem("Voisinage direct", 2)
        self.depth_combo.addItem("Deux niveaux", 4)
        self.depth_combo.addItem("Objet seul", 0)
        self.depth_combo.addItem("Tout le modèle", None)
        filter_layout.addWidget(self.depth_combo)
        layout.addWidget(filter_group)

        self.clear_focus_button = QPushButton("Afficher tout le modèle")
        layout.addWidget(self.clear_focus_button)
        return panel

    def _dependency_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("Dépendances de l'objet sélectionné"))
        self.dependencies = QPlainTextEdit()
        self.dependencies.setReadOnly(True)
        self.dependencies.setPlaceholderText(
            "Sélectionnez une entité ou une association dans le graphe."
        )
        layout.addWidget(self.dependencies, 1)

        layout.addWidget(QLabel("Éléments masqués temporairement"))
        self.hidden_list = QListWidget()
        self.hidden_list.setMaximumHeight(170)
        self.hidden_list.setToolTip("Double-cliquez sur un élément pour le restaurer.")
        layout.addWidget(self.hidden_list)
        self.hide_button = QPushButton("Masquer la sélection")
        self.restore_button = QPushButton("Tout restaurer")
        layout.addWidget(self.hide_button)
        layout.addWidget(self.restore_button)
        return panel

    def _options(self) -> ExplorationOptions:
        scope = self.submodels.resolve(
            self.source_model, str(self.scope_combo.currentData() or GLOBAL_SCOPE_ID)
        )
        return ExplorationOptions(
            show_entities=self.entity_filter.isChecked(),
            show_associations=self.association_filter.isChecked(),
            show_links=self.links_filter.isChecked(),
            focus_id=self.focus_id,
            depth=self.depth_combo.currentData(),
            query=self.search_edit.text(),
            restrict_to_query=self.restrict_search.isChecked(),
            hidden_ids=frozenset(self.hidden_ids),
            scope_ids=None if scope.id == GLOBAL_SCOPE_ID else scope.node_ids,
        )

    def _rebuild(self, _value: object = None) -> None:
        result = self.explorer.project(self.source_model, self._options())
        layout = McdAutoLayout().calculate(result.model)
        for node_id, position in layout.items():
            result.model.move_node(node_id, position)
        self.controller.load_transient_model(result.model)
        self.scene.setSceneRect(
            self.scene.itemsBoundingRect().adjusted(-100, -100, 100, 100)
        )
        self.view.fit_scene()
        total = len(self.source_model.entities) + len(self.source_model.associations)
        scope = self.submodels.resolve(
            self.source_model, str(self.scope_combo.currentData() or GLOBAL_SCOPE_ID)
        )
        self.status_label.setText(
            f"{scope.label} — {len(result.visible_ids)} objet(s) affiché(s) "
            f"sur {total} — "
            f"{len(self.hidden_ids)} masqué(s) temporairement"
        )
        self._refresh_hidden_list()

    def _search_changed(self, _text: str) -> None:
        self._refresh_results()
        if self.restrict_search.isChecked():
            self._rebuild()

    def _scope_changed(self, _index: int) -> None:
        scope = self.submodels.resolve(
            self.source_model, str(self.scope_combo.currentData() or GLOBAL_SCOPE_ID)
        )
        if scope.id != GLOBAL_SCOPE_ID and self.focus_id not in scope.node_ids:
            self.focus_id = None
            self.focus_label.setText("Focus : tout le sous-modèle")
        self._refresh_results()
        self._rebuild()

    def _refresh_results(self) -> None:
        self.results.clear()
        scope = self.submodels.resolve(
            self.source_model, str(self.scope_combo.currentData() or GLOBAL_SCOPE_ID)
        )
        for result in self.explorer.search(self.source_model, self.search_edit.text()):
            if scope.id != GLOBAL_SCOPE_ID and result.element_id not in scope.node_ids:
                continue
            details = result.kind
            if result.matched_attributes:
                details += " — " + ", ".join(result.matched_attributes)
            item = QTreeWidgetItem([result.name, details])
            item.setData(0, Qt.ItemDataRole.UserRole, result.element_id)
            self.results.addTopLevelItem(item)
        self.focus_button.setEnabled(self.results.topLevelItemCount() > 0)

    def _selected_result_id(self) -> str | None:
        item = self.results.currentItem()
        if item is None and self.results.topLevelItemCount():
            item = self.results.topLevelItem(0)
        if item is None:
            return None
        element_id = item.data(0, Qt.ItemDataRole.UserRole)
        return element_id if isinstance(element_id, str) else None

    def _focus_selected_result(self) -> None:
        element_id = self._selected_result_id()
        if element_id is None:
            return
        self.focus_id = element_id
        node = self.source_model.node(element_id)
        self.focus_label.setText(f"Focus : {node.name}")
        self._rebuild()
        self._select_graph_node(element_id)

    def _clear_focus(self) -> None:
        self.focus_id = None
        self.focus_label.setText("Focus : tout le modèle")
        self._rebuild()

    def _hide_selected(self) -> None:
        selected_ids = {
            item.id
            for item in self.controller.selected_elements()
            if isinstance(item, (Entity, Association))
        }
        if not selected_ids:
            result_id = self._selected_result_id()
            if result_id is not None:
                selected_ids.add(result_id)
        if not selected_ids:
            return
        self.hidden_ids.update(selected_ids)
        if self.focus_id in selected_ids:
            self.focus_id = None
            self.focus_label.setText("Focus : tout le modèle")
        self._rebuild()

    def _restore_hidden(self) -> None:
        self.hidden_ids.clear()
        self._rebuild()

    def _restore_one(self, item: QListWidgetItem) -> None:
        element_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(element_id, str):
            self.hidden_ids.discard(element_id)
            self._rebuild()

    def _refresh_hidden_list(self) -> None:
        self.hidden_list.clear()
        for element_id in sorted(
            self.hidden_ids,
            key=lambda item_id: self.source_model.node(item_id).name.casefold(),
        ):
            node = self.source_model.node(element_id)
            item = QListWidgetItem(node.name)
            item.setData(Qt.ItemDataRole.UserRole, element_id)
            self.hidden_list.addItem(item)
        self.restore_button.setEnabled(bool(self.hidden_ids))

    def _selection_changed(self, selected: object) -> None:
        if not isinstance(selected, list):
            return
        node = next(
            (item for item in selected if isinstance(item, (Entity, Association))),
            None,
        )
        if node is None:
            self.dependencies.clear()
            return
        self.dependencies.setPlainText(
            self.explorer.dependency_text(self.source_model, node.id)
        )

    def _select_graph_node(self, element_id: str) -> None:
        for item in self.scene.items():
            if getattr(item, "element_id", None) == element_id:
                item.setSelected(True)
                self.view.centerOn(item)
                return
