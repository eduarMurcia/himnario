from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hymn_studio.models import HymnProject, VideoSettings

PROJECT_VERSION = 1


class ProjectRepository:
    """Read and write Hymn Studio project files."""

    def load(self, path: Path) -> HymnProject:
        data = json.loads(path.read_text(encoding="utf-8"))
        self._validate(data)

        video = data["video"]
        project = HymnProject(
            name=data["name"],
            image_folder=self._path_or_none(data.get("image_folder")),
            audio_path=self._path_or_none(data.get("audio")),
            timestamps=[float(value) for value in data.get("timestamps", [])],
            video=VideoSettings(
                width=int(video["width"]),
                height=int(video["height"]),
                fps=int(video["fps"]),
            ),
            project_path=path,
        )
        return project

    def save(self, project: HymnProject, path: Path) -> None:
        data = {
            "version": PROJECT_VERSION,
            "name": project.name,
            "audio": self._path_to_string(project.audio_path),
            "image_folder": self._path_to_string(project.image_folder),
            "timestamps": project.timestamps,
            "video": {
                "width": project.video.width,
                "height": project.video.height,
                "fps": project.video.fps,
            },
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        project.project_path = path

    def _validate(self, data: dict[str, Any]) -> None:
        if data.get("version") != PROJECT_VERSION:
            raise ValueError("Unsupported Hymn Studio project version.")

        required_keys = {"name", "timestamps", "video"}
        missing = required_keys - data.keys()
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(f"Invalid project file. Missing: {missing_list}")

    def _path_or_none(self, value: str | None) -> Path | None:
        return Path(value) if value else None

    def _path_to_string(self, value: Path | None) -> str | None:
        return str(value) if value else None
