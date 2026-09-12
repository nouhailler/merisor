"""Éditeur du dictionnaire de données et du glossaire métier."""

from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from merisor.application import DataDictionaryService
from merisor.domain import Association, BusinessTerm, DiagramError, Entity, MCDModel


class DataDictionaryDialog(QDialog):
    """Modifie une copie du dictionnaire, importée seulement après confirmation."""

    def __init__(self, model: MCDModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.working_model = copy.deepcopy(model)
        self.setWindowTitle("Dictionnaire de données — MERISOR")
        self.resize(1080, 730)

        intro = QLabel(
            "<h2>📖 Dictionnaire de données</h2>"
            "<p>Documentez les concepts et attributs du MCD, puis maintenez un "
            "glossaire de termes métier et de synonymes. Ces informations restent "
            "dans le projet JSON.</p>"
        )
        intro.setWordWrap(True)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Concepts et termes")
        self.tree.setMinimumWidth(330)
        self.name_edit = QLineEdit()
        self.name_edit.setReadOnly(True)
        self.kind_label = QLabel("—")
        self.owner_label = QLabel("—")
        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText(
            "Définition métier ou commentaire de l'attribut"
        )
        self.synonyms_edit = QLineEdit()
        self.synonyms_edit.setPlaceholderText("acheteur, utilisateur")
        self.synonyms_edit.setEnabled(False)
        self.details_preview = QPlainTextEdit()
        self.details_preview.setReadOnly(True)
        self.details_preview.setMaximumHeight(190)

        form = QFormLayout()
        form.addRow("Nature :", self.kind_label)
        form.addRow("Nom :", self.name_edit)
        form.addRow("Propriétaire :", self.owner_label)
        form.addRow("Description :", self.description_edit)
        form.addRow("Synonymes :", self.synonyms_edit)
        form.addRow("Fiche calculée :", self.details_preview)
        editor = QWidget()
        editor.setLayout(form)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.tree)
        splitter.addWidget(editor)
        splitter.setSizes([350, 730])

        self.add_term_button = QPushButton("+ Ajouter un terme")
        self.remove_term_button = QPushButton("Supprimer le terme")
        self.remove_term_button.setProperty("role", "danger")
        self.remove_term_button.setEnabled(False)
        self.save_entry_button = QPushButton("Enregistrer la fiche")
        self.save_entry_button.setProperty("role", "primary")
        actions = QHBoxLayout()
        actions.addWidget(self.add_term_button)
        actions.addWidget(self.remove_term_button)
        actions.addStretch(1)
        actions.addWidget(self.save_entry_button)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        save = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        save.setText("Appliquer au MCD")

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(splitter, 1)
        layout.addLayout(actions)
        layout.addWidget(self.buttons)

        self.tree.currentItemChanged.connect(self._selection_changed)
        self.add_term_button.clicked.connect(self._add_term)
        self.remove_term_button.clicked.connect(self._remove_term)
        self.save_entry_button.clicked.connect(self._save_current)
        self.buttons.accepted.connect(self._accept)
        self.buttons.rejected.connect(self.reject)
        self._rebuild_tree()

    def _rebuild_tree(self, selected_id: str | None = None) -> None:
        self.tree.clear()
        concepts = QTreeWidgetItem(["MCD"])
        glossary = QTreeWidgetItem(["Termes métier"])
        self.tree.addTopLevelItems([concepts, glossary])
        selected: QTreeWidgetItem | None = None
        nodes: tuple[Entity | Association, ...] = (
            *self.working_model.entities.values(),
            *self.working_model.associations.values(),
        )
        for node in sorted(nodes, key=lambda item: (item.name.casefold(), item.id)):
            kind = "entity" if node.id in self.working_model.entities else "association"
            item = QTreeWidgetItem([node.name])
            item.setData(0, Qt.ItemDataRole.UserRole, (kind, node.id, ""))
            concepts.addChild(item)
            if node.id == selected_id:
                selected = item
            for attribute in node.attributes:
                child = QTreeWidgetItem([attribute.name])
                child.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    ("attribute", attribute.id, node.id),
                )
                item.addChild(child)
                if attribute.id == selected_id:
                    selected = child
        for term in sorted(
            self.working_model.business_terms.values(),
            key=lambda item: (item.name.casefold(), item.id),
        ):
            item = QTreeWidgetItem([term.name])
            item.setData(0, Qt.ItemDataRole.UserRole, ("term", term.id, ""))
            glossary.addChild(item)
            if term.id == selected_id:
                selected = item
        concepts.setExpanded(True)
        glossary.setExpanded(True)
        if selected is not None:
            self.tree.setCurrentItem(selected)
        elif concepts.childCount():
            first = concepts.child(0)
            if first is not None:
                self.tree.setCurrentItem(first)

    def _selection(self) -> tuple[str, str, str] | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if (
            isinstance(data, tuple)
            and len(data) == 3
            and all(isinstance(value, str) for value in data)
        ):
            return data
        return None

    def _selection_changed(
        self, _current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        selection = self._selection()
        if selection is None:
            self._clear_editor()
            return
        kind, element_id, owner_id = selection
        self.name_edit.setReadOnly(kind != "term")
        self.synonyms_edit.setEnabled(kind == "term")
        self.remove_term_button.setEnabled(kind == "term")
        self.owner_label.setText("—")
        if kind in {"entity", "association"}:
            node = self.working_model.node(element_id)
            self.kind_label.setText("Entité" if kind == "entity" else "Association")
            self.name_edit.setText(node.name)
            self.description_edit.setPlainText(node.description)
            self.synonyms_edit.clear()
        elif kind == "attribute":
            owner = self.working_model.node(owner_id)
            attribute = self.working_model.attribute(owner_id, element_id)
            self.kind_label.setText("Attribut")
            self.owner_label.setText(owner.name)
            self.name_edit.setText(attribute.name)
            self.description_edit.setPlainText(attribute.comment)
            self.synonyms_edit.clear()
        else:
            term = self.working_model.business_terms[element_id]
            self.kind_label.setText("Terme métier")
            self.name_edit.setText(term.name)
            self.description_edit.setPlainText(term.definition)
            self.synonyms_edit.setText(", ".join(term.synonyms))
        self._refresh_preview(element_id)

    def _clear_editor(self) -> None:
        self.kind_label.setText("—")
        self.owner_label.setText("—")
        self.name_edit.clear()
        self.description_edit.clear()
        self.synonyms_edit.clear()
        self.details_preview.clear()
        self.remove_term_button.setEnabled(False)

    def _save_current(self, _checked: bool = False) -> bool:
        selection = self._selection()
        if selection is None:
            return True
        kind, element_id, owner_id = selection
        description = self.description_edit.toPlainText().strip()
        try:
            if kind in {"entity", "association"}:
                self.working_model.node(element_id).description = description
            elif kind == "attribute":
                self.working_model.attribute(owner_id, element_id).comment = description
            else:
                synonyms = tuple(
                    item.strip()
                    for item in self.synonyms_edit.text().split(",")
                    if item.strip()
                )
                self.working_model.replace_business_term(
                    element_id,
                    BusinessTerm(
                        id=element_id,
                        name=self.name_edit.text(),
                        definition=description,
                        synonyms=synonyms,
                    ),
                )
        except DiagramError as error:
            QMessageBox.warning(self, "Fiche invalide", str(error))
            return False
        self._rebuild_tree(element_id)
        return True

    def _add_term(self, _checked: bool = False) -> None:
        name, accepted = QInputDialog.getText(self, "Nouveau terme métier", "Nom :")
        if not accepted:
            return
        try:
            term = BusinessTerm(name)
            self.working_model.add_business_term(term)
        except DiagramError as error:
            QMessageBox.warning(self, "Terme invalide", str(error))
            return
        self._rebuild_tree(term.id)

    def _remove_term(self, _checked: bool = False) -> None:
        selection = self._selection()
        if selection is None or selection[0] != "term":
            return
        self.working_model.remove_business_term(selection[1])
        self._rebuild_tree()

    def _refresh_preview(self, element_id: str) -> None:
        entry = next(
            (
                item
                for item in DataDictionaryService().build(self.working_model).entries
                if item.id == element_id
            ),
            None,
        )
        self.details_preview.setPlainText(entry.render() if entry else "")

    def _accept(self) -> None:
        if self._save_current():
            self.accept()
