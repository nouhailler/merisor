from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialogButtonBox

from merisor.application import DiagramController, PwaImportResult, PwaSourceImporter
from merisor.ui.canvas import DiagramScene
from merisor.ui.pwa_import_dialog import PwaImportPreviewDialog


def _result(tmp_path: Path) -> PwaImportResult:
    (tmp_path / "db.ts").write_text(
        """
        const db = new Dexie("Demo");
        db.version(1).stores({ clients: "++id, nom" });
        interface Client { id: number; nom: string; }
        """,
        encoding="utf-8",
    )
    return PwaSourceImporter().import_path(tmp_path)


def test_preview_requires_a_valid_candidate(qapp, tmp_path) -> None:  # type: ignore[no-untyped-def]
    dialog = PwaImportPreviewDialog(_result(tmp_path), str(tmp_path))

    import_button = dialog.buttons.button(QDialogButtonBox.StandardButton.Ok)
    assert import_button.isEnabled()
    assert import_button.text() == "Importer le MCD proposé"
    assert dialog.windowTitle() == "Aperçu de l'import PWA / IndexedDB"


def test_confirmed_pwa_import_is_one_undoable_operation(qapp, tmp_path) -> None:  # type: ignore[no-untyped-def]
    scene = DiagramScene()
    controller = DiagramController(scene)
    result = _result(tmp_path)

    controller.import_pwa_source_model(result.mcd)

    assert len(controller.model.entities) == 1
    assert controller.undo_stack.canUndo()
    controller.undo_stack.undo()
    assert not controller.model.entities
