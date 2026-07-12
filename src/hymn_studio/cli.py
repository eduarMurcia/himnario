from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from hymn_studio.exporter import ExportError, FfmpegExporter
from hymn_studio.models import HymnProject, Lyrics, SlideTemplate
from hymn_studio.project import ProjectRepository
from hymn_studio.services.audio_matcher import AudioMatcher
from hymn_studio.services.lyrics import LyricsExtractionError, LyricsExtractor, MultiHymnExtractor
from hymn_studio.services.slide_generator import (
    PillowSlideBuilder,
    PowerPointPngExporter,
    PptxSlideBuilder,
    SlideGenerationError,
)
from hymn_studio.services.slides import SlideLoader
from hymn_studio.services.template_config import PillowTemplateConfig, TemplateConfigError

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')


def _safe_filename(name: str) -> str:
    return _INVALID_FILENAME_CHARS.sub("_", name).strip()


def _first_lyric_line(lyrics: Lyrics) -> str:
    """Some old audio archives are named after a hymn's first line rather than its
    formal title (e.g. "Dad loor al Señor" saved as "A Dios demos gloria.mp3")."""
    if not lyrics.stanzas or not lyrics.stanzas[0].text:
        return ""
    return lyrics.stanzas[0].text.splitlines()[0]


def _build_slides(lyrics: Lyrics, output_dir: Path, args: argparse.Namespace) -> Path:
    slides_dir = output_dir / "slides"

    if args.engine == "pillow":
        if not (args.cover_background and args.stanza_background):
            raise SlideGenerationError(
                "--cover-background and --stanza-background are required for the pillow engine."
            )

        if args.template:
            template_config = PillowTemplateConfig(Path(args.template))
            cover_template = template_config.build_cover_template(Path(args.cover_background))
            stanza_template = template_config.build_stanza_template(Path(args.stanza_background))
        else:
            if not args.font:
                raise SlideGenerationError(
                    "--font is required for the pillow engine when --template is not given."
                )
            cover_template = SlideTemplate(
                background=Path(args.cover_background),
                font_path=Path(args.font),
                font_size=args.font_size,
            )
            stanza_template = SlideTemplate(
                background=Path(args.stanza_background),
                font_path=Path(args.font),
                font_size=args.font_size,
            )

        PillowSlideBuilder(cover_template, stanza_template).build(lyrics, slides_dir)
    else:
        if not (args.cover and args.stanza):
            raise SlideGenerationError("--cover and --stanza are required for the pptx engine.")
        combined_pptx = PptxSlideBuilder(Path(args.cover), Path(args.stanza)).build(
            lyrics, output_dir
        )
        PowerPointPngExporter().export(combined_pptx, slides_dir)

    return slides_dir


def _save_project(lyrics: Lyrics, audio_path: Path, slides_dir: Path, output_dir: Path) -> Path:
    repository = ProjectRepository()
    project_path = output_dir / f"{lyrics.title}.hymn"
    timestamps: list[float] = []
    if project_path.exists():
        timestamps = repository.load(project_path).timestamps

    project = HymnProject(
        name=lyrics.title,
        image_folder=slides_dir,
        audio_path=audio_path,
        timestamps=timestamps,
    )
    repository.save(project, project_path)
    return project_path


def build_command(args: argparse.Namespace) -> None:
    lyrics_path = Path(args.lyrics)
    audio_path = Path(args.audio)
    output_dir = Path(args.out)

    lyrics = LyricsExtractor(
        max_lines_per_stanza=args.max_lines_per_slide,
        repeat_chorus_after_verses=not args.no_repeat_chorus,
    ).extract(lyrics_path)

    slides_dir = _build_slides(lyrics, output_dir, args)
    project_path = _save_project(lyrics, audio_path, slides_dir, output_dir)
    print(f"Project ready: {project_path}")


def build_all_command(args: argparse.Namespace) -> None:
    lyrics_path = Path(args.lyrics)
    audio_dirs = [Path(d) for d in args.audio_dirs]
    output_dir = Path(args.out)

    hymns = MultiHymnExtractor(
        LyricsExtractor(
            max_lines_per_stanza=args.max_lines_per_slide,
            repeat_chorus_after_verses=not args.no_repeat_chorus,
        )
    ).extract_docx(lyrics_path)

    matcher = AudioMatcher(audio_dirs)

    built: list[str] = []
    skipped: list[str] = []
    for lyrics in hymns:
        audio_path = matcher.find(lyrics.title) or matcher.find(_first_lyric_line(lyrics))
        if audio_path is None:
            skipped.append(lyrics.title)
            continue

        hymn_dir = output_dir / _safe_filename(lyrics.title)
        slides_dir = _build_slides(lyrics, hymn_dir, args)
        project_path = _save_project(lyrics, audio_path, slides_dir, hymn_dir)
        built.append(lyrics.title)
        print(f"Project ready: {project_path}")

    print(f"\n{len(built)} project(s) built, {len(skipped)} skipped (no matching audio).")
    if skipped:
        print("Skipped (no audio found):")
        for title in skipped:
            print(f"  - {title}")


def export_command(args: argparse.Namespace) -> None:
    projects_dir = Path(args.projects_dir)
    output_dir = Path(args.out) if args.out else projects_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    repository = ProjectRepository()
    slide_loader = SlideLoader()
    exporter = FfmpegExporter()

    for project_path in sorted(projects_dir.glob("*.hymn")):
        project = repository.load(project_path)
        if not project.timestamps:
            print(f"Skipping {project_path.name}: no timestamps marked yet.")
            continue
        if project.image_folder is None:
            print(f"Skipping {project_path.name}: no image folder set.")
            continue

        slides = slide_loader.load_folder(project.image_folder)
        mp4_path = output_dir / f"{project.name}.mp4"
        try:
            exporter.export(project, slides, mp4_path)
            print(f"Exported: {mp4_path}")
        except ExportError as error:
            print(f"Failed to export {project_path.name}: {error}")


def _add_lyrics_parsing_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--max-lines-per-slide",
        type=int,
        default=4,
        help="Stanzas longer than this are split across several slides (default: 4).",
    )
    parser.add_argument(
        "--no-repeat-chorus",
        action="store_true",
        help="Do not repeat the chorus after every verse (by default it is repeated).",
    )


def _add_slide_engine_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--engine", choices=["pptx", "pillow"], default="pptx", help="Slide rendering engine."
    )
    parser.add_argument("--cover", help="Cover .pptx template (pptx engine).")
    parser.add_argument("--stanza", help="Stanza .pptx template (pptx engine).")
    parser.add_argument("--cover-background", help="Cover background image (pillow engine).")
    parser.add_argument("--stanza-background", help="Stanza background image (pillow engine).")
    parser.add_argument("--font", help="TTF font path (pillow engine).")
    parser.add_argument(
        "--font-size", type=int, default=80, help="Base font size (pillow engine)."
    )
    parser.add_argument(
        "--template",
        help=(
            "Reusable Pillow styling config (JSON): font, positions, colors and "
            "overlays. Overrides --font/--font-size (pillow engine)."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hymn-studio-build",
        description="Automate hymn video project setup: lyrics + audio -> slides + .hymn project.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser_cmd = subparsers.add_parser(
        "build", help="Build a hymn project from a lyrics file and an audio file."
    )
    build_parser_cmd.add_argument("lyrics", help="Path to the lyrics PDF or Word (.docx) document.")
    build_parser_cmd.add_argument("audio", help="Path to the audio file.")
    build_parser_cmd.add_argument("--out", required=True, help="Output project folder.")
    _add_lyrics_parsing_arguments(build_parser_cmd)
    _add_slide_engine_arguments(build_parser_cmd)
    build_parser_cmd.set_defaults(func=build_command)

    build_all_parser_cmd = subparsers.add_parser(
        "build-all",
        help=(
            "Build one project per hymn from a single Word document containing many "
            "hymns (each starting with a Heading-1 title), matching each to an audio "
            "file in a folder by (normalized) title."
        ),
    )
    build_all_parser_cmd.add_argument(
        "lyrics", help="Path to the multi-hymn Word (.docx) document."
    )
    build_all_parser_cmd.add_argument(
        "--audio-dir",
        dest="audio_dirs",
        action="append",
        required=True,
        help="Folder containing audio files; repeat to search several folders.",
    )
    build_all_parser_cmd.add_argument(
        "--out", required=True, help="Output folder; one subfolder per hymn is created inside."
    )
    _add_lyrics_parsing_arguments(build_all_parser_cmd)
    _add_slide_engine_arguments(build_all_parser_cmd)
    build_all_parser_cmd.set_defaults(func=build_all_command)

    export_parser_cmd = subparsers.add_parser(
        "export", help="Batch-export MP4s from already-synced .hymn projects."
    )
    export_parser_cmd.add_argument("projects_dir", help="Folder containing .hymn project files.")
    export_parser_cmd.add_argument(
        "--out", help="Output folder for MP4s (defaults to projects_dir)."
    )
    export_parser_cmd.set_defaults(func=export_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    try:
        args.func(args)
    except (
        LyricsExtractionError,
        SlideGenerationError,
        TemplateConfigError,
        ExportError,
        ValueError,
    ) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
