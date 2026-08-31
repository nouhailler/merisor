"""Export vectoriel ou matriciel d'une scène de diagramme Qt."""

from __future__ import annotations

import math
import os
import tempfile
from contextlib import suppress
from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
)
from PySide6.QtSvg import QSvgGenerator
from PySide6.QtWidgets import QGraphicsScene


class DiagramExportError(RuntimeError):
    """Erreur compréhensible rencontrée pendant l'export d'un diagramme."""


class DiagramVisualExporter:
    """Rend une scène Qt complète sans dépendre du zoom de la vue courante."""

    SUPPORTED_SUFFIXES = frozenset({".png", ".svg", ".pdf"})
    MARGIN = 36.0
    PNG_SCALE = 2.0
    MAX_PNG_DIMENSION = 12_000

    def export(
        self,
        scene: QGraphicsScene,
        path: str | Path,
        *,
        title: str = "Diagramme MERISOR",
    ) -> Path:
        target = Path(path)
        suffix = target.suffix.lower()
        if suffix not in self.SUPPORTED_SUFFIXES:
            raise DiagramExportError(
                "Format non pris en charge. Utilisez PNG, SVG ou PDF."
            )
        if not scene.items():
            raise DiagramExportError(
                "Le diagramme est vide : aucun élément à exporter."
            )
        if not target.parent.exists():
            raise DiagramExportError(
                f"Le dossier de destination n'existe pas : {target.parent}"
            )

        source = scene.itemsBoundingRect().adjusted(
            -self.MARGIN,
            -self.MARGIN,
            self.MARGIN,
            self.MARGIN,
        )
        if source.isEmpty() or source.width() <= 0 or source.height() <= 0:
            raise DiagramExportError("La zone du diagramme ne peut pas être exportée.")

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f".{target.stem}-",
                suffix=suffix,
                dir=target.parent,
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)

            if suffix == ".png":
                self._export_png(scene, source, temporary_path)
            elif suffix == ".svg":
                self._export_svg(scene, source, temporary_path, title)
            else:
                self._export_pdf(scene, source, temporary_path, title)
            os.replace(temporary_path, target)
        except DiagramExportError:
            raise
        except (OSError, RuntimeError) as error:
            raise DiagramExportError(
                f"Impossible d'écrire le fichier : {error}"
            ) from error
        finally:
            if temporary_path is not None and temporary_path.exists():
                with suppress(OSError):
                    temporary_path.unlink()
        return target

    def _export_png(self, scene: QGraphicsScene, source: QRectF, path: Path) -> None:
        scale = min(
            self.PNG_SCALE,
            self.MAX_PNG_DIMENSION / max(source.width(), source.height()),
        )
        width = max(1, math.ceil(source.width() * scale))
        height = max(1, math.ceil(source.height() * scale))
        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor("#ffffff"))
        painter = QPainter(image)
        self._render_scene(scene, painter, QRectF(0, 0, width, height), source)
        if not image.save(str(path)):
            raise DiagramExportError("Qt n'a pas pu encoder l'image PNG.")

    def _export_svg(
        self,
        scene: QGraphicsScene,
        source: QRectF,
        path: Path,
        title: str,
    ) -> None:
        width = max(1, math.ceil(source.width()))
        height = max(1, math.ceil(source.height()))
        generator = QSvgGenerator()
        generator.setFileName(str(path))
        generator.setSize(QSize(width, height))
        generator.setViewBox(QRectF(0, 0, width, height))
        generator.setTitle(title)
        generator.setDescription("Diagramme exporté par MERISOR")
        painter = QPainter(generator)
        self._render_scene(scene, painter, QRectF(0, 0, width, height), source)

    def _export_pdf(
        self,
        scene: QGraphicsScene,
        source: QRectF,
        path: Path,
        title: str,
    ) -> None:
        writer = QPdfWriter(str(path))
        writer.setTitle(title)
        writer.setCreator("MERISOR")
        writer.setResolution(144)
        layout = QPageLayout(
            QPageSize(QPageSize.PageSizeId.A4),
            QPageLayout.Orientation.Landscape,
            QMarginsF(10, 10, 10, 10),
            QPageLayout.Unit.Millimeter,
        )
        writer.setPageLayout(layout)
        target = QRectF(layout.paintRectPixels(writer.resolution()))
        painter = QPainter(writer)
        self._render_scene(scene, painter, target, source)

    @staticmethod
    def _render_scene(
        scene: QGraphicsScene,
        painter: QPainter,
        target: QRectF,
        source: QRectF,
    ) -> None:
        if not painter.isActive():
            raise DiagramExportError("Le moteur de rendu Qt n'a pas pu démarrer.")
        selected_items = scene.selectedItems()
        original_background = scene.backgroundBrush()
        try:
            scene.clearSelection()
            scene.setBackgroundBrush(QBrush(QColor("#ffffff")))
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            painter.fillRect(target, QColor("#ffffff"))
            scene.render(
                painter,
                target,
                source,
                Qt.AspectRatioMode.KeepAspectRatio,
            )
        finally:
            painter.end()
            scene.setBackgroundBrush(original_background)
            for item in selected_items:
                with suppress(RuntimeError):
                    item.setSelected(True)
