from __future__ import annotations

import copy
import shutil
import tempfile
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.slide import Slide

from hymn_studio.models import ImageOverlay, Lyrics, SlideTemplate, TextOverlay


class SlideGenerationError(RuntimeError):
    pass


class SlideGenerator(Protocol):
    """Builds slide PNGs for a hymn's lyrics."""

    def build(self, lyrics: Lyrics, output_dir: Path) -> list[Path]: ...


class PillowSlideBuilder:
    """Renders hymn slides by drawing text onto template backgrounds with Pillow.

    Prototype engine kept independent of PowerPoint/COM automation, so it can run
    and be tested anywhere Pillow is installed.
    """

    def __init__(self, cover_template: SlideTemplate, stanza_template: SlideTemplate) -> None:
        self._cover_template = cover_template
        self._stanza_template = stanza_template

    def build(self, lyrics: Lyrics, output_dir: Path) -> list[Path]:
        if not lyrics.stanzas:
            raise SlideGenerationError("Lyrics must have at least one stanza.")

        output_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []

        cover_path = output_dir / "0000_cover.png"
        self._render_slide(self._cover_template, lyrics.title, cover_path)
        paths.append(cover_path)

        for index, stanza in enumerate(lyrics.stanzas, start=1):
            slide_path = output_dir / f"{index:04d}_slide.png"
            self._render_slide(self._stanza_template, stanza.text, slide_path)
            paths.append(slide_path)

        return paths

    def _render_slide(self, template: SlideTemplate, text: str, output_path: Path) -> None:
        with Image.open(template.background) as background:
            image = background.convert("RGBA").copy()

        for overlay in template.image_overlays:
            self._paste_image_overlay(image, overlay)

        draw = ImageDraw.Draw(image)
        self._draw_text_block(
            draw,
            text=text,
            font_path=template.font_path,
            font_size=template.font_size,
            text_box=template.text_box,
            text_color=template.text_color,
            align=template.align,
            line_spacing=template.line_spacing,
            stroke_width=template.stroke_width,
            stroke_color=template.stroke_color,
            fit_to_box=True,
            wrap=template.wrap,
        )

        for overlay in template.extra_overlays:
            self._draw_overlay(draw, overlay)

        image.save(output_path, "PNG")

    def _paste_image_overlay(self, image: Image.Image, overlay: ImageOverlay) -> None:
        box_x, box_y, box_width, box_height = overlay.box
        with Image.open(overlay.image) as ornament:
            resized = ornament.convert("RGBA").resize((int(box_width), int(box_height)))
        image.paste(resized, (int(box_x), int(box_y)), resized)

    def _draw_overlay(self, draw: ImageDraw.ImageDraw, overlay: TextOverlay) -> None:
        self._draw_text_block(
            draw,
            text=overlay.text,
            font_path=overlay.font_path,
            font_size=overlay.font_size,
            text_box=overlay.text_box,
            text_color=overlay.text_color,
            align=overlay.align,
            line_spacing=overlay.line_spacing,
            stroke_width=0,
            stroke_color=(0, 0, 0),
            fit_to_box=False,
            wrap=overlay.wrap,
        )

    def _draw_text_block(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        text: str,
        font_path: Path,
        font_size: int,
        text_box: tuple[int, int, int, int],
        text_color: tuple[int, int, int],
        align: str,
        line_spacing: float,
        stroke_width: int,
        stroke_color: tuple[int, int, int],
        fit_to_box: bool,
        wrap: bool = True,
    ) -> None:
        box_x, box_y, box_width, box_height = text_box

        if not wrap:
            # Mirrors PowerPoint's wrap="none" + spAutoFit boxes: single line,
            # left-anchored at the box, vertically centered in the box height.
            font = ImageFont.truetype(str(font_path), font_size)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_height = bbox[3] - bbox[1]
            y = box_y + max(box_height - text_height, 0) / 2
            draw.text((box_x, y), text, font=font, fill=text_color)
            return

        if fit_to_box:
            resolved_size, lines = self._fit_text(
                draw, font_path, font_size, line_spacing, text, box_width, box_height
            )
        else:
            resolved_size = font_size
            font = ImageFont.truetype(str(font_path), resolved_size)
            lines = self._wrap_text(draw, font, text, box_width)

        font = ImageFont.truetype(str(font_path), resolved_size)
        line_height = resolved_size * line_spacing
        total_height = line_height * len(lines)
        start_y = box_y + max(box_height - total_height, 0) / 2

        for offset, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font, stroke_width=stroke_width)
            line_width = bbox[2] - bbox[0]
            if align == "center":
                x = box_x + max(box_width - line_width, 0) / 2
            else:
                x = box_x
            y = start_y + offset * line_height
            draw.text(
                (x, y),
                line,
                font=font,
                fill=text_color,
                stroke_width=stroke_width,
                stroke_fill=stroke_color,
            )

    def _fit_text(
        self,
        draw: ImageDraw.ImageDraw,
        font_path: Path,
        font_size: int,
        line_spacing: float,
        text: str,
        box_width: float,
        box_height: float,
    ) -> tuple[int, list[str]]:
        while font_size > 8:
            font = ImageFont.truetype(str(font_path), font_size)
            lines = self._wrap_text(draw, font, text, box_width)
            line_height = font_size * line_spacing
            total_height = line_height * len(lines)
            if total_height <= box_height:
                return font_size, lines
            font_size -= 2

        font = ImageFont.truetype(str(font_path), font_size)
        return font_size, self._wrap_text(draw, font, text, box_width)

    def _wrap_text(
        self,
        draw: ImageDraw.ImageDraw,
        font: ImageFont.FreeTypeFont,
        text: str,
        box_width: float,
    ) -> list[str]:
        lines: list[str] = []
        for raw_line in text.splitlines() or [""]:
            words = raw_line.split()
            if not words:
                lines.append("")
                continue

            current = words[0]
            for word in words[1:]:
                candidate = f"{current} {word}"
                bbox = draw.textbbox((0, 0), candidate, font=font)
                if bbox[2] - bbox[0] <= box_width:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            lines.append(current)

        return lines


class PptxSlideBuilder:
    """Builds a combined .pptx by filling the existing cover and stanza templates.

    Assumes each template is a single-slide .pptx with one text placeholder to fill
    (the title on the cover template, the lyrics on the stanza template). The stanza
    slide is duplicated once per stanza and its placeholder text replaced.
    """

    def __init__(self, cover_template: Path, stanza_template: Path) -> None:
        self._cover_template = cover_template
        self._stanza_template = stanza_template

    def build(self, lyrics: Lyrics, output_dir: Path) -> Path:
        if not lyrics.stanzas:
            raise SlideGenerationError("Lyrics must have at least one stanza.")

        output_dir.mkdir(parents=True, exist_ok=True)
        combined_path = output_dir / "combined.pptx"
        shutil.copyfile(self._cover_template, combined_path)

        presentation = Presentation(str(combined_path))
        if not presentation.slides:
            raise SlideGenerationError(f"Cover template has no slides: {self._cover_template}")

        self._fill_placeholder_text(presentation.slides[0], lyrics.title)

        stanza_source = Presentation(str(self._stanza_template))
        if not stanza_source.slides:
            raise SlideGenerationError(f"Stanza template has no slides: {self._stanza_template}")

        stanza_slide_source = stanza_source.slides[0]
        stanza_layout = self._ensure_layout(presentation, stanza_slide_source.slide_layout)

        for stanza in lyrics.stanzas:
            new_slide = self._duplicate_slide(presentation, stanza_slide_source, stanza_layout)
            self._fill_placeholder_text(new_slide, stanza.text)

        presentation.save(str(combined_path))
        return combined_path

    def _ensure_layout(self, presentation: Presentation, source_layout):
        for master in presentation.slide_masters:
            for layout in master.slide_layouts:
                if layout.name == source_layout.name:
                    return layout

        target_master = presentation.slide_masters[0]
        new_layout_element = copy.deepcopy(source_layout.element)
        target_master.slide_layouts._sldLayoutLst.append(new_layout_element)
        return target_master.slide_layouts[-1]

    def _duplicate_slide(self, presentation: Presentation, source_slide: Slide, layout) -> Slide:
        new_slide = presentation.slides.add_slide(layout)

        for shape in list(new_slide.shapes):
            shape._element.getparent().remove(shape._element)

        for shape in source_slide.shapes:
            new_element = copy.deepcopy(shape.element)
            new_slide.shapes._spTree.append(new_element)

            if getattr(shape, "image", None) is not None:
                self._copy_image_relationship(new_slide, shape, new_element)

        return new_slide

    def _copy_image_relationship(self, new_slide: Slide, shape, new_element) -> None:
        blip = new_element.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip")
        if blip is None:
            return

        r_embed_attr = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
        if blip.get(r_embed_attr) is None:
            return

        _, new_r_id = new_slide.part.get_or_add_image_part(shape.image.blob)
        blip.set(r_embed_attr, new_r_id)

    def _fill_placeholder_text(self, slide: Slide, text: str) -> None:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            shape.text_frame.text = text
            return

        raise SlideGenerationError("Template slide has no text placeholder to fill.")


class PowerPointPngExporter:
    """Exports every slide of a .pptx as a numbered PNG using PowerPoint COM automation.

    Windows-only: requires a local PowerPoint installation. This step cannot be
    exercised in a headless/non-Windows environment; verify manually with real
    templates and PowerPoint installed.
    """

    def export(self, pptx_path: Path, output_dir: Path) -> list[Path]:
        import win32com.client  # noqa: PLC0415 (Windows-only, optional dependency)

        output_dir.mkdir(parents=True, exist_ok=True)

        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        presentation = powerpoint.Presentations.Open(
            str(pptx_path.resolve()), WithWindow=False
        )
        try:
            with tempfile.TemporaryDirectory(prefix="hymn-studio-pptx-") as temp_dir:
                presentation.SaveAs(temp_dir, 18)  # ppSaveAsPNG = 18, exports one PNG per slide

                exported = sorted(Path(temp_dir).glob("*.PNG")) or sorted(
                    Path(temp_dir).glob("*.png")
                )
                paths: list[Path] = []
                for index, source in enumerate(exported, start=1):
                    destination = output_dir / f"{index:04d}_slide.png"
                    shutil.copyfile(source, destination)
                    paths.append(destination)
                return paths
        finally:
            presentation.Close()
            powerpoint.Quit()
