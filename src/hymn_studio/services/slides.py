from __future__ import annotations

from pathlib import Path

from hymn_studio.models import Slide
from hymn_studio.settings import AppSettings


class SlideLoader:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self._settings = settings or AppSettings()

    def load_folder(self, folder: Path) -> list[Slide]:
        if not folder.exists() or not folder.is_dir():
            raise ValueError("Image folder does not exist.")

        slides = [
            Slide(path)
            for path in sorted(folder.iterdir(), key=lambda item: item.name.lower())
            if path.suffix.lower() in self._settings.supported_image_extensions
        ]

        if not slides:
            raise ValueError("Image folder does not contain supported slide images.")

        return slides
