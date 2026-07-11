from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from hymn_studio.ui.main_window import MainWindow


def create_app(argv: Sequence[str]) -> QApplication:
    app = QApplication(list(argv))
    app.setApplicationName("Hymn Studio")
    app.setOrganizationName("Hymn Studio")

    window = MainWindow()
    window.show()

    return app
