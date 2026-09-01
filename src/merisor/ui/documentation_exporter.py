"""Écriture des documentations MERISOR en Markdown, HTML ou PDF."""

from __future__ import annotations

import base64
import os
import tempfile
from contextlib import suppress
from pathlib import Path

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument
from PySide6.QtWidgets import QGraphicsScene

from merisor.application.documentation_generator import ModelDocumentation
from merisor.ui.diagram_exporter import DiagramExportError, DiagramVisualExporter


class DocumentationExportError(RuntimeError):
    """Erreur compréhensible lors de l'écriture d'une documentation."""


class DocumentationFileExporter:
    """Exporte une documentation sans laisser de fichier partiel."""

    SUPPORTED_SUFFIXES = frozenset({".md", ".markdown", ".html", ".htm", ".pdf"})

    def export(self, documentation: ModelDocumentation, path: str | Path) -> Path:
        target = Path(path)
        suffix = target.suffix.casefold()
        if suffix not in self.SUPPORTED_SUFFIXES:
            raise DocumentationExportError(
                "Format non pris en charge. Utilisez Markdown, HTML ou PDF."
            )
        if not target.parent.exists():
            raise DocumentationExportError(
                f"Le dossier de destination n'existe pas : {target.parent}"
            )

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f".{target.stem}-",
                suffix=suffix,
                dir=target.parent,
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
            if suffix in {".md", ".markdown"}:
                temporary_path.write_text(documentation.markdown, encoding="utf-8")
            elif suffix in {".html", ".htm"}:
                temporary_path.write_text(documentation.html, encoding="utf-8")
            else:
                self._write_pdf(documentation, temporary_path)
            os.replace(temporary_path, target)
        except DocumentationExportError:
            raise
        except (OSError, RuntimeError) as error:
            raise DocumentationExportError(
                f"Impossible d'écrire la documentation : {error}"
            ) from error
        finally:
            if temporary_path is not None and temporary_path.exists():
                with suppress(OSError):
                    temporary_path.unlink()
        return target

    @staticmethod
    def scene_data_uri(scene: QGraphicsScene) -> str | None:
        """Rend une scène en PNG embarqué, ou retourne None si elle est vide."""

        if not scene.items():
            return None
        try:
            with tempfile.TemporaryDirectory(prefix="merisor-documentation-") as folder:
                path = Path(folder) / "diagramme.png"
                DiagramVisualExporter().export(scene, path)
                encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        except (DiagramExportError, OSError):
            return None
        return f"data:image/png;base64,{encoded}"

    @staticmethod
    def _write_pdf(documentation: ModelDocumentation, path: Path) -> None:
        writer = QPdfWriter(str(path))
        writer.setTitle(documentation.title)
        writer.setCreator("MERISOR")
        writer.setResolution(144)
        writer.setPageLayout(
            QPageLayout(
                QPageSize(QPageSize.PageSizeId.A4),
                QPageLayout.Orientation.Portrait,
                QMarginsF(15, 15, 15, 15),
                QPageLayout.Unit.Millimeter,
            )
        )
        document = QTextDocument()
        document.setDocumentMargin(20)
        document.setHtml(documentation.html)
        document.print_(writer)
        if (
            not path.exists()
            or path.stat().st_size < 100
            or not path.read_bytes().startswith(b"%PDF")
        ):
            raise DocumentationExportError("Qt n'a pas pu produire le document PDF.")
