"""Fenêtre principale de l'éditeur MERISOR."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QSettings, Qt
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QIcon,
    QKeySequence,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QTabWidget,
    QToolBar,
)

from merisor import __version__
from merisor.application import (
    DDLImportError,
    DiagramController,
    DiagramTextExporter,
    DiagramTextExportError,
    MLDGenerationBlocked,
    MLDTransformationError,
    MldTransformationExplainer,
    ModelDocumentationGenerator,
    ModelVersionComparator,
    PwaImportError,
    PwaSourceImporter,
    SQLDDLImporter,
)
from merisor.domain import InheritanceStrategy, MLDModel, MLDTable
from merisor.persistence import JsonDiagramRepository, PersistenceError
from merisor.ui.ai_mcd_dialog import AiMcdDialog
from merisor.ui.ai_repair_dialog import AiRepairDialog
from merisor.ui.canvas import DiagramScene, DiagramView, MiniMapView, ToolMode
from merisor.ui.conversational_design_dialog import ConversationalDesignDialog
from merisor.ui.ddl_import_dialog import DDLImportPreviewDialog
from merisor.ui.diagram_exporter import DiagramExportError, DiagramVisualExporter
from merisor.ui.documentation_dialog import DocumentationDialog
from merisor.ui.documentation_exporter import (
    DocumentationExportError,
    DocumentationFileExporter,
)
from merisor.ui.impact_analysis_dialog import ImpactAnalysisDialog
from merisor.ui.mld_properties_panel import MLDPropertiesPanel
from merisor.ui.mld_view import MLDView
from merisor.ui.model_explorer_dialog import ModelExplorerDialog
from merisor.ui.normalization_dialog import NormalizationAssistantDialog
from merisor.ui.openrouter_settings_dialog import OpenRouterSettingsDialog
from merisor.ui.properties_panel import PropertiesPanel
from merisor.ui.pwa_import_dialog import PwaImportPreviewDialog
from merisor.ui.quality_dialog import QualityReportDialog
from merisor.ui.query_generator_dialog import QueryGeneratorDialog
from merisor.ui.sql_dialog import SQLPreviewDialog
from merisor.ui.submodel_dialog import SubmodelManagerDialog
from merisor.ui.test_data_dialog import TestDataDialog
from merisor.ui.transformation_explanation_dialog import (
    TransformationExplanationDialog,
)
from merisor.ui.validation_dialog import ValidationDialog
from merisor.ui.version_comparison_dialog import VersionComparisonDialog


class MainWindow(QMainWindow):
    MAX_RECENT_FILES = 10
    LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "merisor.png"

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("mainWindow")
        self.setWindowIcon(QIcon(str(self.LOGO_PATH)))
        self.resize(1280, 800)
        self._settings = QSettings("MERISOR", "MERISOR")
        self.recent_menu: QMenu | None = None

        self.scene = DiagramScene(self)
        self.view = DiagramView(self.scene, self)
        self.controller = DiagramController(self.scene, self)
        self.mld_view = MLDView(self)
        self.mld_properties_panel = MLDPropertiesPanel(self)
        self.workspace_tabs = QTabWidget(self)
        self.workspace_tabs.addTab(self.view, "MCD")
        self.workspace_tabs.addTab(self.mld_view, "MLD")
        self.setCentralWidget(self.workspace_tabs)

        self.properties_panel = PropertiesPanel(self.controller)
        properties_dock = QDockWidget("Propriétés", self)
        self.properties_dock = properties_dock
        properties_dock.setObjectName("propertiesDock")
        properties_dock.setWidget(self.properties_panel)
        properties_dock.setMinimumWidth(340)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, properties_dock)

        self.minimap = MiniMapView(self.view, self)
        self.minimap_dock = QDockWidget("Minimap", self)
        self.minimap_dock.setObjectName("minimapDock")
        self.minimap_dock.setWidget(self.minimap)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.minimap_dock)
        self.minimap_dock.setVisible(
            bool(self._settings.value("canvas/minimap", True, type=bool))
        )

        self._create_actions()
        self._create_menus()
        self._create_toolbar()
        self._connect_signals()
        self.workspace_tabs.currentChanged.connect(self._workspace_changed)
        self.statusBar().showMessage("Prêt — utilisez les outils pour commencer.")
        self._update_title()

    def _create_actions(self) -> None:
        self.new_action = QAction("Nouveau", self)
        self.new_action.setShortcut(QKeySequence.StandardKey.New)
        self.open_action = QAction("Ouvrir…", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.import_ddl_action = QAction("Importer SQL / DDL…", self)
        self.import_ddl_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        self.import_pwa_action = QAction("Importer un projet PWA / IndexedDB…", self)
        self.import_pwa_action.setShortcut(QKeySequence("Ctrl+Alt+P"))
        self.save_action = QAction("Enregistrer", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_as_action = QAction("Enregistrer sous…", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.export_visual_action = QAction("Exporter le diagramme…", self)
        self.export_visual_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        self.generate_documentation_action = QAction("Générer la documentation…", self)
        self.generate_documentation_action.setShortcut(QKeySequence("Ctrl+Shift+D"))
        self.quit_action = QAction("Quitter", self)
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.openrouter_settings_action = QAction("Paramètres OpenRouter…", self)

        self.undo_action = self.controller.undo_stack.createUndoAction(self, "Annuler")
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.redo_action = self.controller.undo_stack.createRedoAction(self, "Rétablir")
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.delete_action = QAction("Supprimer", self)
        self.delete_action.setShortcut(QKeySequence(Qt.Key.Key_Delete))
        self.copy_action = QAction("Copier", self)
        self.copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        self.paste_action = QAction("Coller", self)
        self.paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        self.duplicate_action = QAction("Dupliquer", self)
        self.duplicate_action.setShortcut(QKeySequence("Ctrl+D"))
        self.select_all_action = QAction("Tout sélectionner", self)
        self.select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)

        self.zoom_in_action = QAction("Zoom avant", self)
        self.zoom_in_action.setShortcuts(
            [QKeySequence("Ctrl++"), QKeySequence("Ctrl+=")]
        )
        self.zoom_out_action = QAction("Zoom arrière", self)
        self.zoom_out_action.setShortcut(QKeySequence("Ctrl+-"))
        self.reset_zoom_action = QAction("Réinitialiser le zoom", self)
        self.reset_zoom_action.setShortcut(QKeySequence("Ctrl+0"))
        self.grid_action = QAction("Afficher la grille", self)
        self.grid_action.setCheckable(True)
        self.grid_action.setChecked(
            bool(self._settings.value("canvas/grid", False, type=bool))
        )
        self.snap_action = QAction("Aimantation à la grille", self)
        self.snap_action.setCheckable(True)
        self.snap_action.setChecked(
            bool(self._settings.value("canvas/snap", False, type=bool))
        )
        self.guides_action = QAction("Guides d'alignement", self)
        self.guides_action.setCheckable(True)
        self.guides_action.setChecked(
            bool(self._settings.value("canvas/guides", True, type=bool))
        )
        self.attributes_action = QAction("Afficher les attributs", self)
        self.attributes_action.setCheckable(True)
        self.attributes_action.setChecked(True)
        self.fold_action = QAction("Plier/déplier la sélection", self)
        self.fold_action.setShortcut(QKeySequence("Ctrl+Alt+F"))
        self.fullscreen_action = QAction("Mode plein écran", self)
        self.fullscreen_action.setCheckable(True)
        self.fullscreen_action.setShortcut(QKeySequence("F11"))
        self.explore_model_action = QAction("Explorer le modèle…", self)
        self.explore_model_action.setShortcut(QKeySequence("Ctrl+Alt+E"))

        self.documentation_action = QAction("Centre de documentation…", self)
        self.documentation_action.setShortcut(QKeySequence("F1"))
        self.getting_started_documentation_action = QAction("Prise en main", self)
        self.user_guide_documentation_action = QAction("Guide utilisateur", self)
        self.merise_documentation_action = QAction("Comprendre MERISE", self)
        self.mcd_mld_documentation_action = QAction("Règles MCD → MLD", self)
        self.faq_documentation_action = QAction("Questions fréquentes", self)

        self.validate_action = QAction("Valider le MCD…", self)
        self.validate_action.setShortcut(QKeySequence("Ctrl+Shift+V"))
        self.compare_version_action = QAction("Comparer avec une version…", self)
        self.compare_version_action.setShortcut(QKeySequence("Ctrl+Alt+C"))
        self.quality_action = QAction("Analyser la qualité du modèle…", self)
        self.ai_repair_action = QAction("✨ Analyser avec l'IA…", self)
        self.impact_analysis_action = QAction("Analyser l'impact…", self)
        self.impact_analysis_action.setShortcut(QKeySequence("Ctrl+Alt+I"))
        self.quality_action.setShortcut(QKeySequence("Ctrl+Shift+Q"))
        self.normalization_action = QAction("Assistant de normalisation…", self)
        self.normalization_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        self.generate_mld_action = QAction("Générer le MLD", self)
        self.generate_mld_action.setShortcut(QKeySequence("Ctrl+Shift+M"))
        self.generate_sql_action = QAction("Générer SQL", self)
        self.generate_sql_action.setShortcut(QKeySequence("Ctrl+Alt+S"))
        self.generate_sql_action.setEnabled(False)
        self.generate_test_data_action = QAction("Générer des données de test…", self)
        self.generate_test_data_action.setShortcut(QKeySequence("Ctrl+Alt+T"))
        self.generate_test_data_action.setEnabled(False)
        self.generate_query_action = QAction("Générer une requête SQL…", self)
        self.generate_query_action.setShortcut(QKeySequence("Ctrl+Alt+R"))
        self.generate_query_action.setEnabled(False)
        self.generate_ai_mcd_action = QAction("Générer un MCD avec l'IA…", self)
        self.conversational_assistant_action = QAction(
            "Assistant MERISE conversationnel…", self
        )
        self.conversational_assistant_action.setShortcut(QKeySequence("Ctrl+Alt+M"))
        self.auto_layout_action = QAction("Réorganiser automatiquement le MCD", self)
        self.add_inheritance_action = QAction("Ajouter une spécialisation ISA…", self)
        self.manage_submodels_action = QAction("Gérer les domaines et vues…", self)
        self.manage_submodels_action.setShortcut(QKeySequence("Ctrl+Alt+D"))
        self.auto_layout_action.setShortcut(QKeySequence("Ctrl+Shift+L"))

        self.align_actions: dict[str, QAction] = {}
        for key, label in (
            ("left", "Aligner à gauche"),
            ("horizontal_center", "Centrer horizontalement"),
            ("right", "Aligner à droite"),
            ("top", "Aligner en haut"),
            ("vertical_center", "Centrer verticalement"),
            ("bottom", "Aligner en bas"),
            ("distribute_horizontal", "Distribuer horizontalement"),
            ("distribute_vertical", "Distribuer verticalement"),
        ):
            action = QAction(label, self)
            action.setData(key)
            self.align_actions[key] = action

        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_actions: dict[str, QAction] = {}
        configured_theme = str(self._settings.value("appearance/theme", "system"))
        for key, label in (
            ("system", "Thème système"),
            ("light", "Thème clair"),
            ("dark", "Thème sombre"),
        ):
            action = QAction(label, self)
            action.setCheckable(True)
            action.setData(key)
            action.setChecked(key == configured_theme)
            self.theme_group.addAction(action)
            self.theme_actions[key] = action

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
        file_menu.addAction(self.import_ddl_action)
        file_menu.addAction(self.import_pwa_action)
        self.recent_menu = file_menu.addMenu("Ouvrir récent")
        self._refresh_recent_menu()
        file_menu.addSeparator()
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addAction(self.export_visual_action)
        file_menu.addAction(self.generate_documentation_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)

        settings_menu = self.menuBar().addMenu("Paramètres")
        settings_menu.addAction(self.openrouter_settings_action)

        edit_menu = self.menuBar().addMenu("Édition")
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.copy_action)
        edit_menu.addAction(self.paste_action)
        edit_menu.addAction(self.duplicate_action)
        edit_menu.addAction(self.select_all_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.delete_action)
        align_menu = edit_menu.addMenu("Aligner et distribuer")
        for action in self.align_actions.values():
            align_menu.addAction(action)

        model_menu = self.menuBar().addMenu("Modèle")
        model_menu.addAction(self.validate_action)
        model_menu.addAction(self.compare_version_action)
        model_menu.addAction(self.quality_action)
        model_menu.addAction(self.ai_repair_action)
        model_menu.addAction(self.impact_analysis_action)
        model_menu.addAction(self.normalization_action)
        model_menu.addAction(self.add_inheritance_action)
        model_menu.addAction(self.manage_submodels_action)
        model_menu.addSeparator()
        model_menu.addAction(self.generate_mld_action)
        model_menu.addAction(self.generate_sql_action)
        model_menu.addSeparator()
        model_menu.addAction(self.conversational_assistant_action)
        model_menu.addAction(self.generate_ai_mcd_action)
        model_menu.addAction(self.auto_layout_action)

        tools_menu = self.menuBar().addMenu("Outils")
        tools_menu.addAction(self.generate_test_data_action)
        tools_menu.addAction(self.generate_query_action)

        view_menu = self.menuBar().addMenu("Affichage")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.reset_zoom_action)
        view_menu.addSeparator()
        view_menu.addAction(self.grid_action)
        view_menu.addAction(self.snap_action)
        view_menu.addAction(self.guides_action)
        view_menu.addAction(self.attributes_action)
        view_menu.addAction(self.fold_action)
        view_menu.addAction(self.minimap_dock.toggleViewAction())
        theme_menu = view_menu.addMenu("Thème")
        for action in self.theme_actions.values():
            theme_menu.addAction(action)
        view_menu.addAction(self.fullscreen_action)
        view_menu.addSeparator()
        view_menu.addAction(self.explore_model_action)

        documentation_menu = self.menuBar().addMenu("Documentation")
        documentation_menu.addAction(self.documentation_action)
        documentation_menu.addSeparator()
        documentation_menu.addAction(self.getting_started_documentation_action)
        documentation_menu.addAction(self.user_guide_documentation_action)
        documentation_menu.addAction(self.merise_documentation_action)
        documentation_menu.addAction(self.mcd_mld_documentation_action)
        documentation_menu.addAction(self.faq_documentation_action)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Outils du diagramme", self)
        toolbar.setObjectName("diagramToolbar")
        toolbar.setMovable(False)
        self.brand_logo = QLabel(self)
        self.brand_logo.setObjectName("brandLogo")
        self.brand_logo.setAccessibleName("Logo MERISOR")
        self.brand_logo.setToolTip("MERISOR — Éditeur graphique MERISE")
        self.brand_logo.setPixmap(
            QPixmap(str(self.LOGO_PATH)).scaled(
                40,
                40,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.brand_logo.setContentsMargins(4, 2, 8, 2)
        toolbar.addWidget(self.brand_logo)
        toolbar.addSeparator()
        toolbar.addAction(self.select_action)
        toolbar.addSeparator()
        toolbar.addAction(self.entity_action)
        toolbar.addAction(self.association_action)
        toolbar.addAction(self.relation_action)
        toolbar.addSeparator()
        toolbar.addAction(self.delete_action)
        toolbar.addSeparator()
        toolbar.addAction(self.validate_action)
        toolbar.addAction(self.quality_action)
        toolbar.addAction(self.ai_repair_action)
        toolbar.addAction(self.normalization_action)
        toolbar.addAction(self.generate_mld_action)
        toolbar.addAction(self.generate_sql_action)
        toolbar.addSeparator()
        self.visual_search = QLineEdit(self)
        self.visual_search.setObjectName("visualSearch")
        self.visual_search.setClearButtonEnabled(True)
        self.visual_search.setMaximumWidth(250)
        self.visual_search.setPlaceholderText("Rechercher dans le MCD…")
        toolbar.addWidget(self.visual_search)
        self.addToolBar(toolbar)

    def _connect_signals(self) -> None:
        self.new_action.triggered.connect(self.new_document)
        self.open_action.triggered.connect(self.open_document)
        self.import_ddl_action.triggered.connect(self.import_ddl)
        self.import_pwa_action.triggered.connect(self.import_pwa_project)
        self.save_action.triggered.connect(self.save_document)
        self.save_as_action.triggered.connect(self.save_document_as)
        self.export_visual_action.triggered.connect(self.export_visual)
        self.generate_documentation_action.triggered.connect(
            self.generate_documentation
        )
        self.documentation_action.triggered.connect(
            lambda _checked=False: self.show_documentation("index")
        )
        self.getting_started_documentation_action.triggered.connect(
            lambda _checked=False: self.show_documentation("getting-started")
        )
        self.user_guide_documentation_action.triggered.connect(
            lambda _checked=False: self.show_documentation("user-guide")
        )
        self.merise_documentation_action.triggered.connect(
            lambda _checked=False: self.show_documentation("merise")
        )
        self.mcd_mld_documentation_action.triggered.connect(
            lambda _checked=False: self.show_documentation("mcd-mld-rules")
        )
        self.faq_documentation_action.triggered.connect(
            lambda _checked=False: self.show_documentation("faq")
        )
        self.quit_action.triggered.connect(self.close)
        self.openrouter_settings_action.triggered.connect(self.show_openrouter_settings)
        self.delete_action.triggered.connect(self.controller.delete_selected)
        self.copy_action.triggered.connect(self.controller.copy_selected)
        self.paste_action.triggered.connect(self.controller.paste_copied)
        self.duplicate_action.triggered.connect(self.controller.duplicate_selected)
        self.select_all_action.triggered.connect(self.controller.select_all_nodes)
        for action in self.align_actions.values():
            action.triggered.connect(
                lambda _checked=False, item=action: self.controller.align_selected(
                    str(item.data())
                )
            )
        self.zoom_in_action.triggered.connect(self.view.zoom_in)
        self.zoom_out_action.triggered.connect(self.view.zoom_out)
        self.reset_zoom_action.triggered.connect(self.view.reset_zoom)
        self.grid_action.toggled.connect(self._canvas_preferences_changed)
        self.snap_action.toggled.connect(self._canvas_preferences_changed)
        self.guides_action.toggled.connect(self._canvas_preferences_changed)
        self.attributes_action.toggled.connect(
            self.controller.set_all_attributes_visible
        )
        self.fold_action.triggered.connect(self.controller.toggle_selected_fold)
        self.fullscreen_action.toggled.connect(self._toggle_fullscreen)
        self.minimap_dock.visibilityChanged.connect(
            lambda visible: self._settings.setValue("canvas/minimap", visible)
        )
        self.theme_group.triggered.connect(self._theme_selected)
        self.visual_search.textChanged.connect(self._visual_search_changed)
        self.explore_model_action.triggered.connect(self.show_model_explorer)
        self.validate_action.triggered.connect(self.show_validation)
        self.compare_version_action.triggered.connect(self.compare_with_version)
        self.quality_action.triggered.connect(self.show_quality_report)
        self.ai_repair_action.triggered.connect(self.show_ai_repair)
        self.impact_analysis_action.triggered.connect(self.show_impact_analysis)
        self.normalization_action.triggered.connect(self.show_normalization_assistant)
        self.generate_mld_action.triggered.connect(self.generate_mld)
        self.generate_sql_action.triggered.connect(self.generate_sql)
        self.generate_test_data_action.triggered.connect(self.generate_test_data)
        self.generate_query_action.triggered.connect(self.generate_query)
        self.generate_ai_mcd_action.triggered.connect(self.generate_ai_mcd)
        self.conversational_assistant_action.triggered.connect(
            self.show_conversational_assistant
        )
        self.auto_layout_action.triggered.connect(self.auto_layout_mcd)
        self.add_inheritance_action.triggered.connect(self.add_inheritance)
        self.manage_submodels_action.triggered.connect(self.manage_submodels)
        self.tool_group.triggered.connect(self._tool_triggered)

        self.scene.entity_creation_requested.connect(self._request_entity)
        self.scene.association_creation_requested.connect(self._request_association)
        self.scene.interaction_message.connect(self.statusBar().showMessage)
        self.controller.message.connect(self.statusBar().showMessage)
        self.controller.selection_changed.connect(self.properties_panel.display)
        self.properties_panel.impact_requested.connect(self.show_impact_analysis)
        self.controller.model_changed.connect(self._refresh_properties)
        self.controller.dirty_changed.connect(self._update_title)
        self.controller.document_path_changed.connect(self._update_title)
        self.controller.mld_changed.connect(self._display_mld)
        self.controller.mld_stale_changed.connect(self._set_mld_stale)
        self.mld_view.graphics_view.table_selected.connect(
            self.mld_properties_panel.display
        )
        self.mld_properties_panel.why_requested.connect(self.show_mld_explanation)
        self.view.zoom_changed.connect(
            lambda factor: self.statusBar().showMessage(
                f"Zoom : {factor * 100:.0f} %", 1800
            )
        )
        self._canvas_preferences_changed()
        self._apply_theme(str(self._settings.value("appearance/theme", "system")))

    def _tool_triggered(self, action: QAction) -> None:
        mode = action.data()
        if isinstance(mode, ToolMode):
            self.scene.set_mode(mode)

    def _canvas_preferences_changed(self, _value: object = None) -> None:
        self.scene.configure_canvas(
            grid_visible=self.grid_action.isChecked(),
            snap_enabled=self.snap_action.isChecked(),
            guides_enabled=self.guides_action.isChecked(),
        )
        self._settings.setValue("canvas/grid", self.grid_action.isChecked())
        self._settings.setValue("canvas/snap", self.snap_action.isChecked())
        self._settings.setValue("canvas/guides", self.guides_action.isChecked())

    def _theme_selected(self, action: QAction) -> None:
        self._apply_theme(str(action.data()))

    def _apply_theme(self, theme: str) -> None:
        application = QApplication.instance()
        if not isinstance(application, QApplication):
            return
        dark = theme == "dark"
        if theme == "system":
            dark = (
                application.palette()
                .color(application.palette().ColorRole.Window)
                .lightness()
                < 128
            )
        if dark:
            application.setStyleSheet(
                "QWidget { background-color: #242a33; color: #e8edf5; }"
                "QLineEdit, QPlainTextEdit, QTextEdit, QTreeWidget, QListWidget, "
                "QComboBox, QSpinBox { background-color: #1d222b; "
                "color: #e8edf5; border: 1px solid #586579; }"
                "QMenuBar, QMenu, QToolBar { background-color: #2a313d; }"
                "QPushButton { background-color: #354052; padding: 4px; }"
            )
        else:
            application.setStyleSheet("")
        self.scene.set_dark_theme(dark)
        self.controller.apply_canvas_style(dark=dark)
        self._settings.setValue("appearance/theme", theme)

    def _toggle_fullscreen(self, enabled: bool) -> None:
        if enabled:
            self.showFullScreen()
        else:
            self.showNormal()

    def _visual_search_changed(self, query: str) -> None:
        count = self.controller.apply_visual_search(query)
        if query.strip():
            self.statusBar().showMessage(f"Recherche visuelle : {count} résultat(s).")
        else:
            self.statusBar().showMessage("Recherche visuelle effacée.", 1500)

    def show_openrouter_settings(self, _checked: bool = False) -> None:
        OpenRouterSettingsDialog(self).exec()

    def show_documentation(self, page_id: str = "index") -> None:
        DocumentationDialog(page_id, self).exec()

    def _workspace_changed(self, index: int) -> None:
        if index == self.workspace_tabs.indexOf(self.mld_view):
            self.properties_dock.setWidget(self.mld_properties_panel)
        else:
            self.properties_dock.setWidget(self.properties_panel)

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

    def add_inheritance(self, _checked: bool = False) -> None:
        entities = sorted(
            self.controller.model.entities.values(),
            key=lambda item: (item.name.casefold(), item.id),
        )
        if len(entities) < 2:
            QMessageBox.warning(
                self,
                "Spécialisation ISA",
                "Créez au moins deux entités avant d'ajouter un héritage.",
            )
            return
        labels = [entity.name for entity in entities]
        parent_name, accepted = QInputDialog.getItem(
            self,
            "Spécialisation ISA",
            "Entité mère :",
            labels,
            0,
            False,
        )
        if not accepted:
            return
        parent = next(entity for entity in entities if entity.name == parent_name)
        candidates = [entity for entity in entities if entity.id != parent.id]
        default_children = ", ".join(entity.name for entity in candidates)
        child_names, accepted = QInputDialog.getText(
            self,
            "Spécialisation ISA",
            "Entités filles (noms séparés par des virgules) :",
            text=default_children,
        )
        if not accepted:
            return
        requested = [name.strip() for name in child_names.split(",") if name.strip()]
        by_name = {entity.name.casefold(): entity for entity in candidates}
        children = [by_name.get(name.casefold()) for name in requested]
        if not children or any(child is None for child in children):
            QMessageBox.warning(
                self,
                "Spécialisation ISA",
                "Indiquez un ou plusieurs noms d'entités filles existantes.",
            )
            return
        strategy_labels = {
            "Mère + filles (PK/FK)": InheritanceStrategy.JOINED,
            "Table mère seule": InheritanceStrategy.PARENT_ONLY,
            "Tables filles seules": InheritanceStrategy.CHILDREN_ONLY,
        }
        strategy_label, accepted = QInputDialog.getItem(
            self,
            "Stratégie MLD de l'ISA",
            "Export logique :",
            list(strategy_labels),
            0,
            False,
        )
        if accepted:
            self.controller.create_inheritance(
                parent.id,
                [child.id for child in children if child is not None],
                strategy_labels[strategy_label],
            )

    def _refresh_properties(self) -> None:
        self.properties_panel.display(self.controller.selected_elements())

    def show_validation(self, _checked: bool = False) -> None:
        dialog = ValidationDialog(self.controller.validate(), self)
        dialog.exec()

    def compare_with_version(self, _checked: bool = False) -> None:
        filename, _filter = QFileDialog.getOpenFileName(
            self,
            "Choisir la version MERISOR de référence",
            str(self._dialog_directory()),
            "Modèles MERISOR (*.json);;Tous les fichiers (*)",
        )
        if not filename:
            return
        try:
            reference = JsonDiagramRepository().load(filename)
        except PersistenceError as error:
            QMessageBox.critical(
                self, "Comparaison impossible", f"Version illisible : {error}"
            )
            return
        comparison = ModelVersionComparator().compare(reference, self.controller.model)
        VersionComparisonDialog(comparison, Path(filename).name, self).exec()

    def show_quality_report(self, _checked: bool = False) -> None:
        dialog = QualityReportDialog(self.controller.analyze_quality(), self)
        dialog.exec()

    def show_ai_repair(self, _checked: bool = False) -> None:
        dialog = AiRepairDialog(self.controller.model, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.repaired_model is None:
            return
        self.controller.apply_ai_repair_model(dialog.repaired_model)
        self.workspace_tabs.setCurrentWidget(self.view)
        self.select_action.setChecked(True)
        self.view.fit_scene()

    def show_impact_analysis(self, selected: bool | str = False) -> None:
        selected_id = selected if isinstance(selected, str) else None
        if selected_id is None:
            elements = self.controller.selected_elements()
            if len(elements) == 1:
                selected_id = elements[0].id
        ImpactAnalysisDialog(self.controller.model, selected_id, self).exec()

    def show_model_explorer(self, _checked: bool = False) -> None:
        ModelExplorerDialog(self.controller.model, self).exec()

    def manage_submodels(self, _checked: bool = False) -> None:
        dialog = SubmodelManagerDialog(self.controller.model, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.controller.apply_submodel_configuration(
            dialog.domains.values(), dialog.views.values()
        )

    def show_normalization_assistant(self, _checked: bool = False) -> None:
        NormalizationAssistantDialog(self.controller, self).exec()

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
        self.mld_properties_panel.clear()
        self.mld_properties_panel.set_stale(False)
        if model is None:
            self.mld_view.clear_model()
        else:
            self.mld_view.set_model(model)
        self._update_sql_action()

    def _set_mld_stale(self, stale: bool) -> None:
        self.mld_view.set_stale(stale)
        self.mld_properties_panel.set_stale(stale)
        self._update_sql_action()

    def show_mld_explanation(self, table: object) -> None:
        model = self.controller.mld_model
        if (
            model is None
            or self.controller.mld_is_stale
            or not isinstance(table, MLDTable)
        ):
            return
        report = MldTransformationExplainer().explain_table(
            self.controller.model, model, table
        )
        TransformationExplanationDialog(report, self).exec()

    def _update_sql_action(self) -> None:
        mld_available = (
            self.controller.mld_model is not None and not self.controller.mld_is_stale
        )
        self.generate_sql_action.setEnabled(mld_available)
        self.generate_test_data_action.setEnabled(mld_available)
        self.generate_query_action.setEnabled(mld_available)

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

    def generate_test_data(self, _checked: bool = False) -> None:
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
        TestDataDialog(model, project_name, self).exec()

    def generate_query(self, _checked: bool = False) -> None:
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
        QueryGeneratorDialog(model, project_name, self).exec()

    def generate_ai_mcd(self, _checked: bool = False) -> None:
        dialog = AiMcdDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        candidate = dialog.imported_candidate
        if candidate is None or candidate.report.errors:
            return
        if not self._maybe_save():
            return
        self.controller.import_generated_model(candidate.model)
        self.controller.auto_layout()
        self.workspace_tabs.setCurrentWidget(self.view)
        self.select_action.setChecked(True)
        self.view.fit_scene()

    def show_conversational_assistant(self, _checked: bool = False) -> None:
        dialog = ConversationalDesignDialog(self.controller.model, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.imported_model is None:
            return
        self.controller.import_conversational_model(dialog.imported_model)
        self.workspace_tabs.setCurrentWidget(self.view)
        self.select_action.setChecked(True)
        self.view.fit_scene()

    def auto_layout_mcd(self, _checked: bool = False) -> None:
        self.controller.auto_layout()
        self.workspace_tabs.setCurrentWidget(self.view)
        self.view.fit_scene()

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

    def import_ddl(self, _checked: bool = False) -> None:
        filename, _filter = QFileDialog.getOpenFileName(
            self,
            "Importer un schéma SQL / DDL",
            str(self._dialog_directory()),
            "Schémas SQL (*.sql *.ddl);;Tous les fichiers (*)",
        )
        if not filename:
            return
        try:
            source_sql = Path(filename).read_text(encoding="utf-8")
            result = SQLDDLImporter().import_text(source_sql)
        except (OSError, UnicodeError) as error:
            QMessageBox.critical(
                self,
                "Import DDL impossible",
                f"Impossible de lire le fichier : {error}",
            )
            return
        except DDLImportError as error:
            QMessageBox.critical(
                self,
                "Import DDL impossible",
                "Le schéma SQL ne peut pas être importé.\n\n"
                + "\n".join(f"• {problem}" for problem in error.problems),
            )
            return
        preview = DDLImportPreviewDialog(result, source_sql, self)
        if preview.exec() != QDialog.DialogCode.Accepted:
            return
        if not self._maybe_save():
            return
        self.controller.import_reverse_engineered_model(result.mcd, result.mld)
        self.controller.auto_layout()
        self.workspace_tabs.setCurrentWidget(self.view)
        self.select_action.setChecked(True)
        self.view.fit_scene()

    def import_pwa_project(self, _checked: bool = False) -> None:
        source_kind, accepted = QInputDialog.getItem(
            self,
            "Importer un projet PWA / IndexedDB",
            "Source à analyser :",
            ["Dossier local cloné", "Archive ZIP"],
            0,
            False,
        )
        if not accepted:
            return
        if source_kind == "Archive ZIP":
            source, _filter = QFileDialog.getOpenFileName(
                self,
                "Choisir l'archive du projet PWA",
                str(self._dialog_directory()),
                "Archives ZIP (*.zip)",
            )
        else:
            source = QFileDialog.getExistingDirectory(
                self,
                "Choisir le dossier du projet PWA",
                str(self._dialog_directory()),
            )
        if not source:
            return
        try:
            result = PwaSourceImporter().import_path(source)
        except PwaImportError as error:
            QMessageBox.critical(
                self,
                "Analyse PWA impossible",
                f"Aucun MCD exploitable n'a pu être proposé.\n\n{error}",
            )
            return
        preview = PwaImportPreviewDialog(result, source, self)
        if preview.exec() != QDialog.DialogCode.Accepted:
            return
        if not self._maybe_save():
            return
        self.controller.import_pwa_source_model(result.mcd)
        self.workspace_tabs.setCurrentWidget(self.view)
        self.select_action.setChecked(True)
        self.view.fit_scene()

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

    def export_visual(self, _checked: bool = False) -> None:
        exporting_mld = self.workspace_tabs.currentWidget() is self.mld_view
        scene = self.mld_view.graphics_view.mld_scene if exporting_mld else self.scene
        diagram_kind = "MLD" if exporting_mld else "MCD"
        project_name = (
            self.controller.document_path.stem
            if self.controller.document_path is not None
            else "diagramme"
        )
        default_path = (
            self._dialog_directory() / f"{project_name}_{diagram_kind.lower()}.png"
        )
        filename, selected_filter = QFileDialog.getSaveFileName(
            self,
            f"Exporter le {diagram_kind}",
            str(default_path),
            "Image PNG (*.png);;Image vectorielle SVG (*.svg);;Document PDF (*.pdf);;"
            "Diagramme Mermaid (*.mmd *.mermaid);;Graphviz DOT (*.dot *.gv)",
        )
        if not filename:
            return
        path = Path(filename)
        format_suffixes = {
            "Image PNG (*.png)": (".png",),
            "Image vectorielle SVG (*.svg)": (".svg",),
            "Document PDF (*.pdf)": (".pdf",),
            "Diagramme Mermaid (*.mmd *.mermaid)": (".mmd", ".mermaid"),
            "Graphviz DOT (*.dot *.gv)": (".dot", ".gv"),
        }
        selected_suffixes = format_suffixes.get(selected_filter, (".png",))
        if path.suffix.casefold() not in selected_suffixes:
            path = path.with_suffix(selected_suffixes[0])
        try:
            if path.suffix.casefold() in DiagramTextExporter.SUPPORTED_SUFFIXES:
                exporter = DiagramTextExporter()
                if exporting_mld:
                    if self.controller.mld_model is None:
                        raise DiagramTextExportError(
                            "Aucun MLD n'est disponible. Générez d'abord le MLD."
                        )
                    exporter.export_mld(self.controller.mld_model, path)
                else:
                    exporter.export_mcd(self.controller.model, path)
            else:
                DiagramVisualExporter().export(
                    scene,
                    path,
                    title=f"{diagram_kind} — {project_name}",
                )
        except (DiagramExportError, DiagramTextExportError) as error:
            QMessageBox.critical(self, "Export impossible", str(error))
            return
        self.statusBar().showMessage(
            f"{diagram_kind} exporté : {path}",
            5000,
        )

    def generate_documentation(self, _checked: bool = False) -> None:
        project_name = (
            self.controller.document_path.stem
            if self.controller.document_path is not None
            else "Sans titre"
        )
        default_path = self._dialog_directory() / f"{project_name}_documentation.md"
        filename, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Générer la documentation du modèle",
            str(default_path),
            "Markdown (*.md *.markdown);;Page HTML (*.html *.htm);;Document PDF (*.pdf)",
        )
        if not filename:
            return
        path = Path(filename)
        format_suffixes = {
            "Markdown (*.md *.markdown)": (".md", ".markdown"),
            "Page HTML (*.html *.htm)": (".html", ".htm"),
            "Document PDF (*.pdf)": (".pdf",),
        }
        selected_suffixes = format_suffixes.get(selected_filter, (".md",))
        if path.suffix.casefold() not in selected_suffixes:
            path = path.with_suffix(selected_suffixes[0])

        current_mld = (
            self.controller.mld_model if not self.controller.mld_is_stale else None
        )
        file_exporter = DocumentationFileExporter()
        mcd_image = file_exporter.scene_data_uri(self.scene)
        mld_image = None
        if current_mld is not None:
            mld_image = file_exporter.scene_data_uri(
                self.mld_view.graphics_view.mld_scene
            )
        documentation = ModelDocumentationGenerator().generate(
            self.controller.model,
            project_name=project_name,
            mld=current_mld,
            mcd_image_data_uri=mcd_image,
            mld_image_data_uri=mld_image,
        )
        try:
            file_exporter.export(documentation, path)
        except DocumentationExportError as error:
            QMessageBox.critical(self, "Documentation impossible", str(error))
            return
        message = f"Documentation générée : {path}"
        if documentation.warnings:
            message += f" — {len(documentation.warnings)} avertissement(s)"
        self.statusBar().showMessage(message, 7000)

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
        self.setWindowTitle(f"{name}{dirty_marker} — MERISOR {__version__}")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._maybe_save():
            event.accept()
        else:
            event.ignore()
