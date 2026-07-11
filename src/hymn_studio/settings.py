from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppSettings:
    supported_image_extensions: tuple[str, ...] = (".png", ".jpg", ".jpeg")
    project_extension: str = ".hymn"
