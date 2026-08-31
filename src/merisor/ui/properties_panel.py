"""Éditeur contextuel des propriétés du modèle sélectionné."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.application import DiagramController
from merisor.domain import (
    Association,
    Attribute,
    Cardinality,
    Entity,
    MLDDataType,
    MLDDataTypeName,
    MaterializationStrategy,
    Relation,
)


class PropertiesPanel(QWidget):
    """Panneau d'édition ; toute mutation passe par le contrôleur annulable."""

    def __init__(self, controller: DiagramController, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self._controller = controller
        self._updating = False
        self._current_node_id: str | None = None
        self._current_relation_id: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        title = QLabel("PROPRIÉTÉS")
        title_font = title.font()
        title_font.setBold(True)
        title.setFont(title_font)
        root.addWidget(title)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(separator)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.empty_page = QLabel("Sélectionnez une entité, une association ou une relation.")
        self.empty_page.setWordWrap(True)
        self.empty_page.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.node_page = self._build_node_page()
        self.relation_page = self._build_relation_page()
        self.stack.addWidget(self.empty_page)
        self.stack.addWidget(self.node_page)
        self.stack.addWidget(self.relation_page)

    def _build_node_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        form = QFormLayout()
        self.node_type = QLabel("—")
        self.node_name = QLineEdit()
        self.node_identifier = QLabel("—")
        self.node_identifier.setWordWrap(True)
        self.node_identifier.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.node_position = QLabel("—")
        form.addRow("Type", self.node_type)
        form.addRow("Nom", self.node_name)
        form.addRow("ID interne", self.node_identifier)
        form.addRow("Position", self.node_position)
        layout.addLayout(form)

        self.association_transformation_group = QGroupBox("Transformation MLD")
        transformation_form = QFormLayout(self.association_transformation_group)
        self.historized_checkbox = QCheckBox("Oui")
        self.historized_checkbox.setToolTip(
            "Indique que cette association doit conserver plusieurs occurrences "
            "indépendantes dans le temps. Cette propriété ne doit pas être "
            "déduite automatiquement de la présence de dates."
        )
        self.materialization_combo = QComboBox()
        strategies = (
            (
                "Automatique",
                MaterializationStrategy.AUTO,
                "Le générateur MCD → MLD applique les règles normales de "
                "transformation.",
            ),
            (
                "Forcer une table",
                MaterializationStrategy.FORCE_TABLE,
                "L'association sera représentée par une table indépendante "
                "dans le MLD.",
            ),
            (
                "Forcer une clé étrangère",
                MaterializationStrategy.FORCE_FK,
                "Le générateur privilégiera une FK dans la table appropriée "
                "lorsque la transformation est compatible avec les cardinalités.",
            ),
        )
        for label, strategy, tooltip in strategies:
            self.materialization_combo.addItem(label, strategy.value)
            index = self.materialization_combo.count() - 1
            self.materialization_combo.setItemData(
                index, tooltip, Qt.ItemDataRole.ToolTipRole
            )
        self.materialization_combo.setToolTip(strategies[0][2])
        transformation_form.addRow("Historisée", self.historized_checkbox)
        transformation_form.addRow(
            "Stratégie de matérialisation", self.materialization_combo
        )
        layout.addWidget(self.association_transformation_group)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)
        attribute_title = QLabel("Attributs")
        font = attribute_title.font()
        font.setBold(True)
        attribute_title.setFont(font)
        layout.addWidget(attribute_title)

        self.attribute_tree = QTreeWidget()
        self.attribute_tree.setHeaderLabels(["Identifiant", "Nom", "Type"])
        self.attribute_tree.setRootIsDecorated(False)
        self.attribute_tree.setAlternatingRowColors(True)
        self.attribute_tree.setSelectionMode(
            QTreeWidget.SelectionMode.SingleSelection
        )
        self.attribute_tree.header().setStretchLastSection(True)
        self.attribute_tree.setColumnWidth(0, 78)
        self.attribute_tree.setColumnWidth(1, 105)
        layout.addWidget(self.attribute_tree, 1)

        self.attribute_type_group = QGroupBox("Type de l'attribut sélectionné")
        attribute_type_form = QFormLayout(self.attribute_type_group)
        self.attribute_type_combo = QComboBox()
        self.attribute_type_combo.addItem(
            "Automatique",
            None,
        )
        for data_type_name in MLDDataTypeName:
            label = data_type_name.value
            if data_type_name is MLDDataTypeName.VARCHAR:
                label = "VARCHAR(n)"
            elif data_type_name is MLDDataTypeName.DECIMAL:
                label = "DECIMAL(p,s)"
            self.attribute_type_combo.addItem(label, data_type_name.value)
        self.attribute_type_combo.setToolTip(
            "Automatique conserve le comportement historique : INTEGER pour "
            "un identifiant, VARCHAR(100) pour un autre attribut."
        )
        self.attribute_length = QSpinBox()
        self.attribute_length.setRange(1, 65535)
        self.attribute_length.setValue(100)
        self.attribute_precision = QSpinBox()
        self.attribute_precision.setRange(1, 65)
        self.attribute_precision.setValue(10)
        self.attribute_scale = QSpinBox()
        self.attribute_scale.setRange(0, 10)
        self.attribute_scale.setValue(2)
        self.attribute_length_label = QLabel("Longueur")
        self.attribute_precision_label = QLabel("Précision")
        self.attribute_scale_label = QLabel("Échelle")
        attribute_type_form.addRow("Type", self.attribute_type_combo)
        attribute_type_form.addRow(
            self.attribute_length_label, self.attribute_length
        )
        attribute_type_form.addRow(
            self.attribute_precision_label, self.attribute_precision
        )
        attribute_type_form.addRow(self.attribute_scale_label, self.attribute_scale)
        self.apply_attribute_type_button = QPushButton("Appliquer le type")
        attribute_type_form.addRow(self.apply_attribute_type_button)
        self.attribute_type_group.setEnabled(False)
        layout.addWidget(self.attribute_type_group)

        buttons = QHBoxLayout()
        self.add_attribute_button = QPushButton("+ Ajouter")
        self.rename_attribute_button = QPushButton("Modifier")
        self.remove_attribute_button = QPushButton("Supprimer")
        buttons.addWidget(self.add_attribute_button)
        buttons.addWidget(self.rename_attribute_button)
        buttons.addWidget(self.remove_attribute_button)
        layout.addLayout(buttons)

        self.node_name.editingFinished.connect(self._rename_node)
        self.add_attribute_button.clicked.connect(self._add_attribute)
        self.rename_attribute_button.clicked.connect(self._rename_attribute)
        self.remove_attribute_button.clicked.connect(self._remove_attribute)
        self.attribute_tree.itemChanged.connect(self._identifier_changed)
        self.attribute_tree.itemDoubleClicked.connect(
            lambda _item, _column: self._rename_attribute()
        )
        self.attribute_tree.itemSelectionChanged.connect(
            self._attribute_selection_changed
        )
        self.attribute_type_combo.currentIndexChanged.connect(
            self._attribute_type_selection_changed
        )
        self.attribute_precision.valueChanged.connect(
            self._decimal_precision_changed
        )
        self.apply_attribute_type_button.clicked.connect(
            self._apply_attribute_type
        )
        self.historized_checkbox.toggled.connect(self._historization_changed)
        self.materialization_combo.currentIndexChanged.connect(
            self._materialization_changed
        )
        return page

    def _build_relation_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        self.relation_identifier = QLabel("—")
        self.relation_identifier.setWordWrap(True)
        self.relation_identifier.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.relation_endpoints = QLabel("—")
        self.relation_endpoints.setWordWrap(True)
        self.relation_role = QLineEdit()
        self.relation_role.setPlaceholderText("ex. superviseur, supervisé")
        self.relation_role.setToolTip(
            "Le rôle distingue les participations d'une même entité à une "
            "association réflexive. Il est obligatoire lorsque l'entité est "
            "reliée plusieurs fois à cette association."
        )
        self.minimum_combo = QComboBox()
        self.minimum_combo.addItems(["0", "1"])
        self.maximum_combo = QComboBox()
        self.maximum_combo.addItems(["1", "N"])
        layout.addRow("Type", QLabel("Relation"))
        layout.addRow("ID interne", self.relation_identifier)
        layout.addRow("Extrémités", self.relation_endpoints)
        layout.addRow("Rôle", self.relation_role)
        layout.addRow("Cardinalité minimale", self.minimum_combo)
        layout.addRow("Cardinalité maximale", self.maximum_combo)
        self.minimum_combo.currentIndexChanged.connect(self._cardinality_changed)
        self.maximum_combo.currentIndexChanged.connect(self._cardinality_changed)
        self.relation_role.editingFinished.connect(self._relation_role_changed)
        return page

    def display(self, elements: list[Entity | Association | Relation]) -> None:
        self._updating = True
        try:
            self._current_node_id = None
            self._current_relation_id = None
            if len(elements) != 1:
                if len(elements) > 1:
                    self.empty_page.setText(f"{len(elements)} objets sélectionnés.")
                else:
                    self.empty_page.setText(
                        "Sélectionnez une entité, une association ou une relation."
                    )
                self.stack.setCurrentWidget(self.empty_page)
                return
            element = elements[0]
            if isinstance(element, (Entity, Association)):
                self._display_node(element)
            else:
                self._display_relation(element)
        finally:
            self._updating = False
            self._update_buttons()

    def _display_node(self, node: Entity | Association) -> None:
        selected_attribute_id = self._selected_attribute_id()
        self._current_node_id = node.id
        self.stack.setCurrentWidget(self.node_page)
        is_entity = isinstance(node, Entity)
        self.node_type.setText("Entité" if is_entity else "Association")
        self.node_name.setText(node.name)
        self.node_identifier.setText(node.id)
        self.node_position.setText(
            f"x = {node.position.x:g}, y = {node.position.y:g}"
        )
        self.association_transformation_group.setVisible(not is_entity)
        if isinstance(node, Association):
            self.historized_checkbox.setChecked(node.is_historized)
            index = self.materialization_combo.findData(
                node.materialization_strategy.value
            )
            self.materialization_combo.setCurrentIndex(index)
            self._update_materialization_tooltip(index)
        self.attribute_tree.clear()
        for attribute in node.attributes:
            item = QTreeWidgetItem()
            item.setData(0, Qt.ItemDataRole.UserRole, attribute.id)
            item.setText(1, attribute.name)
            item.setText(2, self._attribute_type_label(attribute))
            item.setToolTip(
                2,
                "Type automatique selon le statut d'identifiant."
                if attribute.data_type is None
                else f"Type logique explicite : {attribute.data_type.label}",
            )
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setCheckState(
                0,
                Qt.CheckState.Checked
                if attribute.identifier
                else Qt.CheckState.Unchecked,
            )
            self.attribute_tree.addTopLevelItem(item)
            if attribute.id == selected_attribute_id:
                self.attribute_tree.setCurrentItem(item)
        self._load_selected_attribute_type()

    def _display_relation(self, relation: Relation) -> None:
        self._current_relation_id = relation.id
        self.stack.setCurrentWidget(self.relation_page)
        self.relation_identifier.setText(relation.id)
        entity = self._controller.model.entities.get(relation.entity_id)
        association = self._controller.model.associations.get(relation.association_id)
        entity_name = entity.name if entity is not None else relation.entity_id
        association_name = (
            association.name if association is not None else relation.association_id
        )
        self.relation_endpoints.setText(f"{entity_name} ↔ {association_name}")
        self.relation_role.setText(relation.role)
        if relation.cardinality is None:
            self.minimum_combo.setCurrentIndex(-1)
            self.maximum_combo.setCurrentIndex(-1)
        else:
            self.minimum_combo.setCurrentText(relation.cardinality.minimum.value)
            self.maximum_combo.setCurrentText(relation.cardinality.maximum.value)

    def _rename_node(self) -> None:
        if self._updating or self._current_node_id is None:
            return
        self._controller.rename_node(self._current_node_id, self.node_name.text())

    def _add_attribute(self) -> None:
        if self._current_node_id is None:
            return
        name, accepted = QInputDialog.getText(
            self, "Nouvel attribut", "Nom de l'attribut :"
        )
        if not accepted:
            return
        if not name.strip():
            QMessageBox.warning(self, "Nom requis", "Le nom de l'attribut est vide.")
            return
        self._controller.add_attribute(self._current_node_id, name.strip())

    def _selected_attribute_id(self) -> str | None:
        item = self.attribute_tree.currentItem()
        if item is None:
            return None
        value = item.data(0, Qt.ItemDataRole.UserRole)
        return value if isinstance(value, str) else None

    @staticmethod
    def _attribute_type_label(attribute: Attribute) -> str:
        if attribute.data_type is not None:
            return attribute.data_type.label
        automatic = "INTEGER" if attribute.identifier else "VARCHAR(100)"
        return f"AUTO → {automatic}"

    def _attribute_selection_changed(self) -> None:
        self._load_selected_attribute_type()
        self._update_buttons()

    def _load_selected_attribute_type(self) -> None:
        attribute_id = self._selected_attribute_id()
        if self._current_node_id is None or attribute_id is None:
            self.attribute_type_group.setEnabled(False)
            self.attribute_type_combo.setCurrentIndex(0)
            self._attribute_type_selection_changed(0)
            return
        try:
            attribute = self._controller.model.attribute(
                self._current_node_id, attribute_id
            )
        except ValueError:
            self.attribute_type_group.setEnabled(False)
            return
        self.attribute_type_group.setEnabled(True)
        data_type = attribute.data_type
        value = None if data_type is None else data_type.name.value
        index = self.attribute_type_combo.findData(value)
        self.attribute_type_combo.setCurrentIndex(max(0, index))
        if data_type is not None:
            if data_type.length is not None:
                self.attribute_length.setValue(data_type.length)
            if data_type.precision is not None:
                self.attribute_precision.setValue(data_type.precision)
            if data_type.scale is not None:
                self.attribute_scale.setValue(data_type.scale)
        self._attribute_type_selection_changed(
            self.attribute_type_combo.currentIndex()
        )

    def _attribute_type_selection_changed(self, _index: int) -> None:
        value = self.attribute_type_combo.currentData()
        is_varchar = value == MLDDataTypeName.VARCHAR.value
        is_decimal = value == MLDDataTypeName.DECIMAL.value
        self.attribute_length_label.setVisible(is_varchar)
        self.attribute_length.setVisible(is_varchar)
        self.attribute_precision_label.setVisible(is_decimal)
        self.attribute_precision.setVisible(is_decimal)
        self.attribute_scale_label.setVisible(is_decimal)
        self.attribute_scale.setVisible(is_decimal)

    def _decimal_precision_changed(self, precision: int) -> None:
        self.attribute_scale.setMaximum(precision)

    def _apply_attribute_type(self) -> None:
        if self._current_node_id is None:
            return
        attribute_id = self._selected_attribute_id()
        if attribute_id is None:
            return
        value = self.attribute_type_combo.currentData()
        if value is None:
            data_type = None
        else:
            name = MLDDataTypeName(value)
            if name is MLDDataTypeName.VARCHAR:
                data_type = MLDDataType.varchar(self.attribute_length.value())
            elif name is MLDDataTypeName.DECIMAL:
                data_type = MLDDataType(
                    name,
                    precision=self.attribute_precision.value(),
                    scale=self.attribute_scale.value(),
                )
            else:
                data_type = MLDDataType(name)
        self._controller.set_attribute_data_type(
            self._current_node_id, attribute_id, data_type
        )

    def _rename_attribute(self) -> None:
        if self._current_node_id is None:
            return
        attribute_id = self._selected_attribute_id()
        if attribute_id is None:
            return
        attribute = self._controller.model.attribute(
            self._current_node_id, attribute_id
        )
        name, accepted = QInputDialog.getText(
            self,
            "Renommer l'attribut",
            "Nouveau nom :",
            text=attribute.name,
        )
        if not accepted:
            return
        if not name.strip():
            QMessageBox.warning(self, "Nom requis", "Le nom de l'attribut est vide.")
            return
        self._controller.rename_attribute(
            self._current_node_id, attribute_id, name.strip()
        )

    def _remove_attribute(self) -> None:
        if self._current_node_id is None:
            return
        attribute_id = self._selected_attribute_id()
        if attribute_id is not None:
            self._controller.remove_attribute(self._current_node_id, attribute_id)

    def _identifier_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._updating or column != 0 or self._current_node_id is None:
            return
        if (
            self._current_node_id not in self._controller.model.entities
            and self._current_node_id not in self._controller.model.associations
        ):
            return
        attribute_id = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(attribute_id, str):
            self._controller.set_attribute_identifier(
                self._current_node_id,
                attribute_id,
                item.checkState(0) == Qt.CheckState.Checked,
            )

    def _cardinality_changed(self) -> None:
        if self._updating or self._current_relation_id is None:
            return
        if self.minimum_combo.currentIndex() < 0 or self.maximum_combo.currentIndex() < 0:
            return
        cardinality = Cardinality(
            self.minimum_combo.currentText(), self.maximum_combo.currentText()
        )
        self._controller.set_relation_cardinality(
            self._current_relation_id, cardinality
        )

    def _relation_role_changed(self) -> None:
        if self._updating or self._current_relation_id is None:
            return
        self._controller.set_relation_role(
            self._current_relation_id, self.relation_role.text()
        )

    def _historization_changed(self, checked: bool) -> None:
        if self._updating or self._current_node_id is None:
            return
        if self._current_node_id in self._controller.model.associations:
            self._controller.set_association_historized(
                self._current_node_id, checked
            )

    def _materialization_changed(self, index: int) -> None:
        self._update_materialization_tooltip(index)
        if self._updating or self._current_node_id is None or index < 0:
            return
        if self._current_node_id not in self._controller.model.associations:
            return
        value = self.materialization_combo.itemData(index)
        self._controller.set_association_materialization_strategy(
            self._current_node_id, MaterializationStrategy(value)
        )

    def _update_materialization_tooltip(self, index: int) -> None:
        tooltip = self.materialization_combo.itemData(
            index, Qt.ItemDataRole.ToolTipRole
        )
        self.materialization_combo.setToolTip(
            tooltip if isinstance(tooltip, str) else ""
        )

    def _update_buttons(self) -> None:
        has_attribute = self._selected_attribute_id() is not None
        self.rename_attribute_button.setEnabled(has_attribute)
        self.remove_attribute_button.setEnabled(has_attribute)
        self.attribute_type_group.setEnabled(has_attribute)
        self.apply_attribute_type_button.setEnabled(has_attribute)
