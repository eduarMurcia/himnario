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


@dataclass
class Stanza:
    text: str
    is_chorus: bool = False


@dataclass
class Lyrics:
    title: str
    stanzas: list[Stanza] = field(default_factory=list)


@dataclass(frozen=True)
class TextOverlay:
    """A fixed piece of text drawn onto a slide, independent of the main lyrics text."""

    text: str
    font_path: Path
    font_size: int
    text_box: tuple[int, int, int, int]
    text_color: tuple[int, int, int] = (255, 255, 255)
    align: str = "center"
    line_spacing: float = 1.2
    wrap: bool = True
    """False mirrors PowerPoint's wrap="none" + auto-fit boxes: single line,
    left-anchored at the box, vertically centered in the box height, never shrunk."""


@dataclass(frozen=True)
class ImageOverlay:
    """A fixed decorative image (e.g. an ornament) pasted onto a slide."""

    image: Path
    box: tuple[int, int, int, int]


@dataclass(frozen=True)
class SlideTemplate:
    """Describes how to render a slide's text onto a background image with Pillow."""

    background: Path
    font_path: Path
    font_size: int
    text_color: tuple[int, int, int] = (255, 255, 255)
    text_box: tuple[int, int, int, int] = (100, 100, 1720, 880)
    align: str = "center"
    line_spacing: float = 1.2
    stroke_width: int = 0
    stroke_color: tuple[int, int, int] = (0, 0, 0)
    wrap: bool = True
    """False mirrors PowerPoint's wrap="none" + auto-fit boxes: single line,
    left-anchored at the box, vertically centered in the box height, never shrunk."""
    extra_overlays: tuple[TextOverlay, ...] = ()
    image_overlays: tuple[ImageOverlay, ...] = ()
