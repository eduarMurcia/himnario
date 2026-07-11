from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class VideoSettings:
    width: int = 1920
    height: int = 1080
    fps: int = 30


@dataclass
class Slide:
    path: Path

    @property
    def name(self) -> str:
        return self.path.name


@dataclass
class HymnProject:
    name: str = "Untitled Hymn"
    image_folder: Path | None = None
    audio_path: Path | None = None
    timestamps: list[float] = field(default_factory=list)
    video: VideoSettings = field(default_factory=VideoSettings)
    project_path: Path | None = None

    def has_export_inputs(self) -> bool:
        return self.image_folder is not None and self.audio_path is not None
