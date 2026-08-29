"""Fenêtre principale de l'éditeur MERISOR."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QTabWidget,
    QToolBar,
)

from merisor.application import (
    DiagramController,
    MLDGenerationBlocked,
    MLDTransformationError,
)
from merisor.domain import MLDModel
from merisor.persistence import PersistenceError
from merisor.ui.canvas import DiagramScene, DiagramView, ToolMode
from merisor.ui.mld_view import MLDView
from merisor.ui.properties_panel import PropertiesPanel
from merisor.ui.sql_dialog import SQLPreviewDialog
from merisor.ui.validation_dialog import ValidationDialog


class MainWindow(QMainWindow):
    MAX_RECENT_FILES = 10

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("mainWindow")
        self.resize(1280, 800)
        self._settings = QSettings("MERISOR", "MERISOR")
        self.recent_menu: QMenu | None = None

        self.scene = DiagramScene(self)
        self.view = DiagramView(self.scene, self)
        self.controller = DiagramController(self.scene, self)
        self.mld_view = MLDView(self)
        self.workspace_tabs = QTabWidget(self)
        self.workspace_tabs.addTab(self.view, "MCD")
        self.workspace_tabs.addTab(self.mld_view, "MLD")
        self.setCentralWidget(self.workspace_tabs)

        self.properties_panel = PropertiesPanel(self.controller)
        properties_dock = QDockWidget("Propriétés", self)
        properties_dock.setObjectName("propertiesDock")
        properties_dock.setWidget(self.properties_panel)
        properties_dock.setMinimumWidth(340)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, properties_dock)

        self._create_actions()
        self._create_menus()
        self._create_toolbar()
        self._connect_signals()
        self.statusBar().showMessage("Prêt — utilisez les outils pour commencer.")
        self._update_title()

    def _create_actions(self) -> None:
        self.new_action = QAction("Nouveau", self)
        self.new_action.setShortcut(QKeySequence.StandardKey.New)
        self.open_action = QAction("Ouvrir…", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.save_action = QAction("Enregistrer", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_as_action = QAction("Enregistrer sous…", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.quit_action = QAction("Quitter", self)
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)

        self.undo_action = self.controller.undo_stack.createUndoAction(self, "Annuler")
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.redo_action = self.controller.undo_stack.createRedoAction(self, "Rétablir")
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.delete_action = QAction("Supprimer", self)
        self.delete_action.setShortcut(QKeySequence(Qt.Key.Key_Delete))

        self.zoom_in_action = QAction("Zoom avant", self)
        self.zoom_in_action.setShortcuts(
            [QKeySequence("Ctrl++"), QKeySequence("Ctrl+=")]
        )
        self.zoom_out_action = QAction("Zoom arrière", self)
        self.zoom_out_action.setShortcut(QKeySequence("Ctrl+-"))
        self.reset_zoom_action = QAction("Réinitialiser le zoom", self)
        self.reset_zoom_action.setShortcut(QKeySequence("Ctrl+0"))

        self.validate_action = QAction("Valider le MCD…", self)
        self.validate_action.setShortcut(QKeySequence("Ctrl+Shift+V"))
        self.generate_mld_action = QAction("Générer le MLD", self)
        self.generate_mld_action.setShortcut(QKeySequence("Ctrl+Shift+M"))
        self.generate_sql_action = QAction("Générer SQL", self)
        self.generate_sql_action.setShortcut(QKeySequence("Ctrl+Alt+S"))
        self.generate_sql_action.setEnabled(False)

        self.tool_group = QActionGroup(self)
        self.tool_group.setExclusive(True)
        self.select_action = self._tool_action("Sélection", ToolMode.SELECT)
        self.entity_action = self._tool_action("Entité", ToolMode.ENTITY)
        self.association_action = self._tool_action("Association", ToolMode.ASSOCIATION)
        self.relation_action = self._tool_action("Relation", ToolMode.RELATION)
        self.select_action.setChecked(True)

    def _tool_action(self, text: str, mode: ToolMode) -> QAction:
        action = QAction(text, self)
        action.setCheckable(True)
        action.setData(mode)
        self.tool_group.addAction(action)
        return action

    def _create_menus(self) -> None:
        file_menu = self.menuBar().addMenu("Fichier")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        self.recent_menu = file_menu.addMenu("Ouvrir récent")
        self._refresh_recent_menu()
        file_menu.addSeparator()
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)

        edit_menu = self.menuBar().addMenu("Édition")
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.delete_action)

        model_menu = self.menuBar().addMenu("Modèle")
        model_menu.addAction(self.validate_action)
        model_menu.addSeparator()
        model_menu.addAction(self.generate_mld_action)
        model_menu.addAction(self.generate_sql_action)

        view_menu = self.menuBar().addMenu("Affichage")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.reset_zoom_action)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Outils du diagramme", self)
        toolbar.setObjectName("diagramToolbar")
        toolbar.setMovable(False)
        toolbar.addAction(self.select_action)
        toolbar.addSeparator()
        toolbar.addAction(self.entity_action)
        toolbar.addAction(self.association_action)
        toolbar.addAction(self.relation_action)
        toolbar.addSeparator()
        toolbar.addAction(self.delete_action)
        toolbar.addSeparator()
        toolbar.addAction(self.validate_action)
        toolbar.addAction(self.generate_mld_action)
        toolbar.addAction(self.generate_sql_action)
        self.addToolBar(toolbar)

    def _connect_signals(self) -> None:
        self.new_action.triggered.connect(self.new_document)
        self.open_action.triggered.connect(self.open_document)
        self.save_action.triggered.connect(self.save_document)
        self.save_as_action.triggered.connect(self.save_document_as)
        self.quit_action.triggered.connect(self.close)
        self.delete_action.triggered.connect(self.controller.delete_selected)
        self.zoom_in_action.triggered.connect(self.view.zoom_in)
        self.zoom_out_action.triggered.connect(self.view.zoom_out)
        self.reset_zoom_action.triggered.connect(self.view.reset_zoom)
        self.validate_action.triggered.connect(self.show_validation)
        self.generate_mld_action.triggered.connect(self.generate_mld)
        self.generate_sql_action.triggered.connect(self.generate_sql)
        self.tool_group.triggered.connect(self._tool_triggered)

        self.scene.entity_creation_requested.connect(self._request_entity)
        self.scene.association_creation_requested.connect(self._request_association)
        self.scene.interaction_message.connect(self.statusBar().showMessage)
        self.controller.message.connect(self.statusBar().showMessage)
        self.controller.selection_changed.connect(self.properties_panel.display)
        self.controller.model_changed.connect(self._refresh_properties)
        self.controller.dirty_changed.connect(self._update_title)
        self.controller.document_path_changed.connect(self._update_title)
        self.controller.mld_changed.connect(self._display_mld)
        self.controller.mld_stale_changed.connect(self._set_mld_stale)
        self.view.zoom_changed.connect(
            lambda factor: self.statusBar().showMessage(
                f"Zoom : {factor * 100:.0f} %", 1800
            )
        )

    def _tool_triggered(self, action: QAction) -> None:
        mode = action.data()
        if isinstance(mode, ToolMode):
            self.scene.set_mode(mode)

    def _request_entity(self, position: QPointF) -> None:
        name, accepted = QInputDialog.getText(
            self, "Nouvelle entité", "Nom (vide = nom automatique) :"
        )
        if accepted:
            self.controller.create_entity(name, position)

    def _request_association(self, position: QPointF) -> None:
        name, accepted = QInputDialog.getText(
            self, "Nouvelle association", "Nom (vide = nom automatique) :"
        )
        if accepted:
            self.controller.create_association(name, position)

    def _refresh_properties(self) -> None:
        self.properties_panel.display(self.controller.selected_elements())

    def show_validation(self, _checked: bool = False) -> None:
        dialog = ValidationDialog(self.controller.validate(), self)
        dialog.exec()

    def generate_mld(self, _checked: bool = False) -> None:
        try:
            self.controller.generate_mld()
        except MLDGenerationBlocked as error:
            self.statusBar().showMessage(
                "Impossible de générer le MLD : corrigez les erreurs du MCD."
            )
            ValidationDialog(error.report, self).exec()
            return
        except MLDTransformationError as error:
            QMessageBox.critical(
                self,
                "Génération MLD impossible",
                "Impossible de générer le MLD.\n\n"
                + "\n".join(f"• {problem}" for problem in error.problems),
            )
            return
        self.workspace_tabs.setCurrentWidget(self.mld_view)
        report = self.controller.validate()
        if report.warnings:
            self.statusBar().showMessage(
                f"MLD généré avec {len(report.warnings)} avertissement(s)."
            )

    def _display_mld(self, model: MLDModel | None) -> None:
        if model is None:
            self.mld_view.clear_model()
        else:
            self.mld_view.set_model(model)
        self._update_sql_action()

    def _set_mld_stale(self, stale: bool) -> None:
        self.mld_view.set_stale(stale)
        self._update_sql_action()

    def _update_sql_action(self) -> None:
        self.generate_sql_action.setEnabled(
            self.controller.mld_model is not None
            and not self.controller.mld_is_stale
        )

    def generate_sql(self, _checked: bool = False) -> None:
        model = self.controller.mld_model
        if model is None or self.controller.mld_is_stale:
            QMessageBox.warning(
                self,
                "MLD requis",
                "Aucun MLD valide et à jour n'est disponible. "
                "Générez ou régénérez d'abord le MLD.",
            )
            return
        project_name = (
            self.controller.document_path.stem
            if self.controller.document_path is not None
            else "Sans titre"
        )
        SQLPreviewDialog(model, project_name, self).exec()

    def new_document(self, _checked: bool = False) -> None:
        if self._maybe_save():
            self.controller.new_document()
            self.select_action.setChecked(True)

    def open_document(self, _checked: bool = False) -> None:
        if not self._maybe_save():
            return
        filename, _filter = QFileDialog.getOpenFileName(
            self,
            "Ouvrir un modèle MERISOR",
            str(self._dialog_directory()),
            "Modèles MERISOR (*.json);;Tous les fichiers (*)",
        )
        if not filename:
            return
        try:
            self.controller.load(filename)
            self._add_recent_file(filename)
            self.select_action.setChecked(True)
        except PersistenceError as error:
            QMessageBox.critical(self, "Ouverture impossible", str(error))

    def _confirm_invalid_save(self) -> bool:
        report = self.controller.validate()
        if not report.errors:
            return True
        choice = QMessageBox.warning(
            self,
            "MCD invalide",
            f"Le modèle contient {len(report.errors)} erreur(s). "
            "Voulez-vous quand même l'enregistrer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        return choice == QMessageBox.StandardButton.Yes

    def save_document(self, _checked: bool = False) -> bool:
        if not self._confirm_invalid_save():
            return False
        if self.controller.document_path is None:
            return self.save_document_as(skip_validation=True)
        try:
            self.controller.save()
            self._add_recent_file(self.controller.document_path)
            return True
        except PersistenceError as error:
            QMessageBox.critical(self, "Enregistrement impossible", str(error))
            return False

    def save_document_as(
        self, _checked: bool = False, *, skip_validation: bool = False
    ) -> bool:
        if not skip_validation and not self._confirm_invalid_save():
            return False
        filename, _filter = QFileDialog.getSaveFileName(
            self,
            "Enregistrer le modèle MERISOR",
            str(self._dialog_directory() / "modele.json"),
            "Modèles MERISOR (*.json);;Tous les fichiers (*)",
        )
        if not filename:
            return False
        path = Path(filename)
        if not path.suffix:
            path = path.with_suffix(".json")
        try:
            self.controller.save(path)
            self._add_recent_file(path)
            return True
        except PersistenceError as error:
            QMessageBox.critical(self, "Enregistrement impossible", str(error))
            return False

    def _dialog_directory(self) -> Path:
        if self.controller.document_path is not None:
            return self.controller.document_path.parent
        return Path.home()

    def _recent_files(self) -> list[str]:
        values = self._settings.value("recent_files", [])
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list):
            return []
        return [value for value in values if isinstance(value, str) and value]

    def _add_recent_file(self, path: str | Path | None) -> None:
        if path is None:
            return
        filename = str(Path(path).expanduser().resolve())
        files = [item for item in self._recent_files() if item != filename]
        files.insert(0, filename)
        self._settings.setValue("recent_files", files[: self.MAX_RECENT_FILES])
        self._refresh_recent_menu()

    def _refresh_recent_menu(self) -> None:
        if self.recent_menu is None:
            return
        self.recent_menu.clear()
        existing: list[str] = []
        for filename in self._recent_files():
            path = Path(filename)
            if not path.is_file():
                continue
            existing.append(filename)
            action = QAction(path.name, self)
            action.setToolTip(filename)
            action.triggered.connect(
                lambda _checked=False, selected=filename: self._open_recent_file(
                    selected
                )
            )
            self.recent_menu.addAction(action)
        if existing != self._recent_files():
            self._settings.setValue("recent_files", existing)
        if not existing:
            empty_action = QAction("(Aucun fichier récent)", self)
            empty_action.setEnabled(False)
            self.recent_menu.addAction(empty_action)

    def _open_recent_file(self, filename: str) -> None:
        if not self._maybe_save():
            return
        try:
            self.controller.load(filename)
            self._add_recent_file(filename)
            self.select_action.setChecked(True)
        except PersistenceError as error:
            self._refresh_recent_menu()
            QMessageBox.critical(self, "Ouverture impossible", str(error))

    def _maybe_save(self) -> bool:
        if not self.controller.is_dirty:
            return True
        choice = QMessageBox.warning(
            self,
            "Modifications non enregistrées",
            "Le diagramme a été modifié. Voulez-vous l'enregistrer ?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if choice == QMessageBox.StandardButton.Save:
            return self.save_document()
        return choice == QMessageBox.StandardButton.Discard

    def _update_title(self, *_args: object) -> None:
        name = (
            self.controller.document_path.name
            if self.controller.document_path is not None
            else "Sans titre"
        )
        dirty_marker = " *" if self.controller.is_dirty else ""
        self.setWindowTitle(f"{name}{dirty_marker} — MERISOR 0.4")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._maybe_save():
            event.accept()
        else:
            event.ignore()
