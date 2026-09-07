"""Génère les captures de référence UI/UX 2.0 en mode Qt hors écran."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from merisor.ui.main_window import MainWindow


def capture(window: MainWindow, output: Path, name: str) -> None:
    QApplication.processEvents()
    pixmap = window.grab()
    if not pixmap.save(str(output / name), "PNG"):
        raise RuntimeError(f"Impossible d'enregistrer {name}")


def main() -> int:
    application = QApplication.instance() or QApplication([])
    root = Path(__file__).resolve().parents[1]
    output = root / "docs" / "images"
    output.mkdir(parents=True, exist_ok=True)
    window = MainWindow()
    window.resize(1366, 768)
    window._apply_theme("light")
    window.show()
    capture(window, output, "ui2-start-center.png")

    model = window.controller.repository.load(root / "examples" / "motogp.json")
    window.controller.load_transient_model(model)
    window.controller.auto_layout()
    window.workspace_tabs.setCurrentWidget(window.view)
    window.view.fit_scene()
    capture(window, output, "ui2-mcd.png")

    window.show_validation()
    capture(window, output, "ui2-validation.png")

    window.generate_mld()
    capture(window, output, "ui2-mld.png")
    window.generate_sql()
    capture(window, output, "ui2-sql.png")
    window.show_ai_hub()
    capture(window, output, "ui2-ai.png")
    window._apply_theme("dark")
    capture(window, output, "ui2-dark.png")
    window._apply_theme("light")
    window.show_documentation("getting-started")
    capture(window, output, "ui2-documentation.png")
    window.controller.undo_stack.setClean()
    window.close()
    application.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
