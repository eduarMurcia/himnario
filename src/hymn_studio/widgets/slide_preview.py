from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel


class SlidePreview(QLabel):
    def __init__(self) -> None:
        super().__init__("No slide selected")
        self._pixmap: QPixmap | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(640, 360)
        self.setStyleSheet("background: #15171c; color: #d8dee9;")

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self._update_scaled_pixmap()

    def clear(self) -> None:
        self._pixmap = None
        self.setText("No slide selected")

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._update_scaled_pixmap()
        super().resizeEvent(event)

    def _update_scaled_pixmap(self) -> None:
        if self._pixmap is None or self._pixmap.isNull():
            return

        scaled = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)
