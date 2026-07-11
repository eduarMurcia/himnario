from __future__ import annotations

from pathlib import Path

from hymn_studio.models import HymnProject, Slide


class ExportError(RuntimeError):
    pass


class FfmpegExporter:
    """Builds the export boundary for FFmpeg.

    The full concat-file generation and process execution will be implemented in
    a later commit. Keeping this boundary now prevents UI code from knowing
    FFmpeg details.
    """

    def export(self, project: HymnProject, slides: list[Slide], output_path: Path) -> None:
        if not project.has_export_inputs():
            raise ExportError("Project needs an image folder and audio file before export.")
        if not slides:
            raise ExportError("Project needs at least one slide before export.")
        if output_path.suffix.lower() != ".mp4":
            raise ExportError("Output file must be an MP4.")

        raise NotImplementedError("FFmpeg export will be implemented after the base UI.")
