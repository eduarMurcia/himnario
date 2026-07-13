from __future__ import annotations

import json
from pathlib import Path

from hymn_studio.models import ImageOverlay, SlideTemplate, TextOverlay


class TemplateConfigError(RuntimeError):
    pass


class PillowTemplateConfig:
    """Loads reusable Pillow slide styling (font, positions, colors, overlays) from JSON.

    Only styling is stored here; each build call still supplies its own background
    image per hymn via build_cover_template/build_stanza_template.
    """

    def __init__(self, config_path: Path) -> None:
        self._base_dir = config_path.parent
        try:
            self._data = json.loads(config_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise TemplateConfigError(f"Could not read template config: {config_path}") from error
        except json.JSONDecodeError as error:
            raise TemplateConfigError(f"Invalid JSON in template config: {config_path}") from error

    def build_cover_template(self, background: Path | None = None) -> SlideTemplate:
        return self._build_template(self._section("cover"), background)

    def build_stanza_template(self, background: Path | None = None) -> SlideTemplate:
        return self._build_template(self._section("stanza"), background)

    def _section(self, name: str) -> dict:
        if name not in self._data:
            raise TemplateConfigError(f"Template config is missing the '{name}' section.")
        return self._data[name]

    def _resolve_path(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else self._base_dir / path

    def _build_template(self, section: dict, background: Path | None) -> SlideTemplate:
        resolved_background = background
        if resolved_background is None:
            if "background" not in section:
                raise TemplateConfigError(
                    "Missing required template field: 'background' (not provided "
                    "on the command line or in the template config)."
                )
            resolved_background = self._resolve_path(section["background"])

        try:
            return SlideTemplate(
                background=resolved_background,
                font_path=self._resolve_path(section["font"]),
                font_size=int(section["font_size"]),
                text_color=tuple(section.get("text_color", (255, 255, 255))),
                text_box=tuple(section.get("text_box", (100, 100, 1720, 880))),
                align=section.get("align", "center"),
                line_spacing=float(section.get("line_spacing", 1.2)),
                stroke_width=int(section.get("stroke_width", 0)),
                stroke_color=tuple(section.get("stroke_color", (0, 0, 0))),
                wrap=bool(section.get("wrap", True)),
                extra_overlays=tuple(
                    self._build_text_overlay(item) for item in section.get("extra_overlays", [])
                ),
                image_overlays=tuple(
                    self._build_image_overlay(item) for item in section.get("image_overlays", [])
                ),
            )
        except KeyError as error:
            raise TemplateConfigError(f"Missing required template field: {error}") from error

    def _build_text_overlay(self, item: dict) -> TextOverlay:
        return TextOverlay(
            text=item["text"],
            font_path=self._resolve_path(item["font"]),
            font_size=int(item["font_size"]),
            text_box=tuple(item["text_box"]),
            text_color=tuple(item.get("text_color", (255, 255, 255))),
            align=item.get("align", "center"),
            line_spacing=float(item.get("line_spacing", 1.2)),
            wrap=bool(item.get("wrap", True)),
        )

    def _build_image_overlay(self, item: dict) -> ImageOverlay:
        return ImageOverlay(image=self._resolve_path(item["image"]), box=tuple(item["box"]))
