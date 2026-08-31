from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
)

from merisor.ui.diagram_exporter import DiagramExportError, DiagramVisualExporter
from merisor.ui.main_window import MainWindow


def _populated_scene() -> QGraphicsScene:
    scene = QGraphicsScene()
    scene.addItem(QGraphicsRectItem(QRectF(10, 20, 240, 120)))
    label = QGraphicsTextItem("PILOTE\n# id_pilote\nnom")
    label.setPos(30, 35)
    scene.addItem(label)
    return scene


@pytest.mark.parametrize("suffix", [".png", ".svg", ".pdf"])
def test_export_visual_writes_supported_formats(qapp, tmp_path, suffix: str) -> None:  # type: ignore[no-untyped-def]
    del qapp
    output = tmp_path / f"diagramme{suffix}"

    exported = DiagramVisualExporter().export(_populated_scene(), output)

    assert exported == output
    assert output.stat().st_size > 100
    if suffix == ".png":
        image = QImage(str(output))
        assert not image.isNull()
        assert image.width() > 400
    elif suffix == ".svg":
        assert "<svg" in output.read_text(encoding="utf-8")
    else:
        assert output.read_bytes().startswith(b"%PDF")


def test_export_visual_rejects_empty_scene(qapp, tmp_path) -> None:  # type: ignore[no-untyped-def]
    del qapp
    with pytest.raises(DiagramExportError, match="vide"):
        DiagramVisualExporter().export(QGraphicsScene(), tmp_path / "empty.png")


def test_export_visual_rejects_unknown_extension(qapp, tmp_path) -> None:  # type: ignore[no-untyped-def]
    del qapp
    with pytest.raises(DiagramExportError, match="Format non pris en charge"):
        DiagramVisualExporter().export(_populated_scene(), tmp_path / "diagram.bmp")


def test_main_window_exports_the_scene_of_the_active_workspace(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow()
    selected_scenes: list[QGraphicsScene] = []
    destinations = iter([tmp_path / "active_mcd.png", tmp_path / "active_mld.svg"])

    def choose_path(*_args):  # type: ignore[no-untyped-def]
        return str(next(destinations)), "Image PNG (*.png)"

    def record_export(self, scene, path, *, title):  # type: ignore[no-untyped-def]
        del self, title
        selected_scenes.append(scene)
        return Path(path)

    monkeypatch.setattr(
        "merisor.ui.main_window.QFileDialog.getSaveFileName", choose_path
    )
    monkeypatch.setattr(DiagramVisualExporter, "export", record_export)

    window.export_visual()
    window.workspace_tabs.setCurrentWidget(window.mld_view)
    window.export_visual()

    assert selected_scenes == [window.scene, window.mld_view.graphics_view.mld_scene]
    assert window.export_visual_action.shortcut().toString() == "Ctrl+Shift+E"
    window.controller.undo_stack.setClean()
    window.close()
    qapp.processEvents()
