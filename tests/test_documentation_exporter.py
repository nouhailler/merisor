from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QApplication, QGraphicsRectItem, QGraphicsScene

from merisor.application import ModelDocumentation, ModelDocumentationGenerator
from merisor.domain import Attribute, Entity, MCDModel
from merisor.ui.documentation_exporter import (
    DocumentationExportError,
    DocumentationFileExporter,
)
from merisor.ui.main_window import MainWindow


def _documentation() -> ModelDocumentation:
    model = MCDModel()
    model.add_entity(
        Entity(
            "CLIENT",
            id="client",
            attributes=[Attribute("id_client", True, id="client-id")],
        )
    )
    return ModelDocumentationGenerator().generate(model, project_name="Commerce")


@pytest.mark.parametrize("suffix", [".md", ".html", ".pdf"])
def test_documentation_export_writes_supported_formats(
    qapp: QApplication, tmp_path: Path, suffix: str
) -> None:
    del qapp
    destination = tmp_path / f"documentation{suffix}"

    exported = DocumentationFileExporter().export(_documentation(), destination)

    assert exported == destination
    assert destination.stat().st_size > 100
    if suffix == ".md":
        assert "## Modèle conceptuel" in destination.read_text(encoding="utf-8")
    elif suffix == ".html":
        assert "<!doctype html>" in destination.read_text(encoding="utf-8")
    else:
        assert destination.read_bytes().startswith(b"%PDF")


def test_documentation_export_rejects_unknown_format(tmp_path: Path) -> None:
    with pytest.raises(DocumentationExportError, match="Format non pris en charge"):
        DocumentationFileExporter().export(
            _documentation(), tmp_path / "documentation.docx"
        )


def test_scene_data_uri_embeds_a_non_empty_diagram(qapp: QApplication) -> None:
    del qapp
    scene = QGraphicsScene()
    scene.addItem(QGraphicsRectItem(QRectF(0, 0, 100, 50)))

    data_uri = DocumentationFileExporter.scene_data_uri(scene)

    assert data_uri is not None
    assert data_uri.startswith("data:image/png;base64,")
    assert DocumentationFileExporter.scene_data_uri(QGraphicsScene()) is None


def test_main_window_exposes_and_runs_documentation_export(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow()
    destination = tmp_path / "modele_documentation.html"
    exported: list[tuple[ModelDocumentation, Path]] = []
    monkeypatch.setattr(
        "merisor.ui.main_window.QFileDialog.getSaveFileName",
        lambda *_args: (str(destination), "Page HTML (*.html *.htm)"),
    )

    def record_export(
        self: DocumentationFileExporter,
        documentation: ModelDocumentation,
        path: str | Path,
    ) -> Path:
        del self
        exported.append((documentation, Path(path)))
        return Path(path)

    monkeypatch.setattr(DocumentationFileExporter, "export", record_export)

    window.generate_documentation()

    assert window.generate_documentation_action.shortcut().toString() == "Ctrl+Shift+D"
    assert exported[0][1] == destination
    assert "Modèle conceptuel" in exported[0][0].html
    window.controller.undo_stack.setClean()
    window.close()
    qapp.processEvents()
