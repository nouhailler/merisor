"""Point d'entrée de l'application de bureau."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from merisor import __version__
from merisor.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MERISOR")
    app.setApplicationDisplayName("MERISOR")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("MERISOR")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

