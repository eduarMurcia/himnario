from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from hymn_studio.models import HymnProject, Slide


class ExportError(RuntimeError):
    pass


class FfmpegExporter:
    """Exports synchronized slides and audio through FFmpeg."""

    def export(self, project: HymnProject, slides: list[Slide], output_path: Path) -> None:
        if not project.has_export_inputs():
            raise ExportError("Project needs an image folder and audio file before export.")
        if not slides:
            raise ExportError("Project needs at least one slide before export.")
        if output_path.suffix.lower() != ".mp4":
            raise ExportError("Output file must be an MP4.")
        if project.audio_path is None:
            raise ExportError("Project needs an audio file before export.")

        audio_duration = self._probe_audio_duration(project.audio_path)
        timeline = self._build_slide_timeline(project.timestamps, len(slides), audio_duration)

        with tempfile.TemporaryDirectory(prefix="hymn-studio-") as temp_dir:
            concat_path = Path(temp_dir) / "slides.txt"
            self._write_concat_file(concat_path, slides, timeline)
            self._run_ffmpeg(project, concat_path, output_path)

    def _probe_audio_duration(self, audio_path: Path) -> float:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        result = self._run_process(command)

        try:
            duration = float(result.stdout.strip())
        except ValueError as error:
            raise ExportError("FFprobe could not read the audio duration.") from error

        if duration <= 0:
            raise ExportError("Audio duration must be greater than zero.")

        return duration

    def _build_slide_timeline(
        self,
        timestamps: list[float],
        slide_count: int,
        audio_duration: float,
    ) -> list[float]:
        clean_timestamps: list[float] = []
        previous = 0.0
        for timestamp in timestamps[: max(slide_count - 1, 0)]:
            if previous < timestamp < audio_duration:
                clean_timestamps.append(timestamp)
                previous = timestamp
        boundaries = [0.0, *clean_timestamps, audio_duration]

        durations: list[float] = []
        for index in range(min(slide_count, len(boundaries) - 1)):
            duration = boundaries[index + 1] - boundaries[index]
            if duration > 0:
                durations.append(duration)

        if not durations:
            raise ExportError("No valid slide durations were found.")

        return durations

    def _write_concat_file(self, path: Path, slides: list[Slide], durations: list[float]) -> None:
        lines: list[str] = []
        used_slides = slides[: len(durations)]

        for slide, duration in zip(used_slides, durations, strict=True):
            lines.append(f"file '{self._concat_path(slide.path)}'")
            lines.append(f"duration {duration:.6f}")

        # The concat demuxer needs the last file repeated to honor its duration.
        lines.append(f"file '{self._concat_path(used_slides[-1].path)}'")
        path.write_text("\n".join(lines), encoding="utf-8")

    def _run_ffmpeg(self, project: HymnProject, concat_path: Path, output_path: Path) -> None:
        if project.audio_path is None:
            raise ExportError("Project needs an audio file before export.")

        video = project.video
        scale_filter = (
            f"scale={video.width}:{video.height}:force_original_aspect_ratio=decrease,"
            f"pad={video.width}:{video.height}:(ow-iw)/2:(oh-ih)/2"
        )
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-i",
            str(project.audio_path),
            "-vf",
            scale_filter,
            "-r",
            str(video.fps),
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
        self._run_process(command)

    def _run_process(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as error:
            tool_name = command[0]
            raise ExportError(f"{tool_name} was not found. Install FFmpeg and add it to PATH.") from error
        except subprocess.CalledProcessError as error:
            details = error.stderr.strip() or error.stdout.strip()
            message = details if details else "FFmpeg failed without details."
            raise ExportError(message) from error

    def _concat_path(self, path: Path) -> str:
        return str(path.resolve()).replace("\\", "/").replace("'", "\\'")
