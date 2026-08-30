"""Point d'entrée de l'application de bureau."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from merisor import __version__
from merisor.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MERISOR")
    app.setApplicationDisplayName("MERISOR")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("MERISOR")
    icon = QIcon(str(Path(__file__).parent / "assets" / "merisor.png"))
    app.setWindowIcon(icon)
    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
