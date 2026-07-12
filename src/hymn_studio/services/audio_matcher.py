from __future__ import annotations

import re
import unicodedata
from pathlib import Path

_DUPLICATE_SUFFIX = re.compile(r"\(\d+\)$")
_TRACK_NUMBER_PREFIX = re.compile(r"^\s*\d+\.?\s+")


def normalize_title(text: str) -> str:
    """Case/accent/punctuation-insensitive key used to match hymn titles to filenames."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    lowered = without_accents.lower()
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def _strip_track_number(stem: str) -> str:
    """Strips a leading track-number prefix such as "003. " or "02 " from a filename."""
    return _TRACK_NUMBER_PREFIX.sub("", stem)


class AudioMatcher:
    """Matches hymn titles to audio files in one or more folders by normalized filename."""

    def __init__(
        self,
        audio_dirs: Path | list[Path],
        extensions: tuple[str, ...] = (".mp3",),
    ) -> None:
        dirs = [audio_dirs] if isinstance(audio_dirs, Path) else list(audio_dirs)

        self._index: dict[str, list[Path]] = {}
        for audio_dir in dirs:
            for path in sorted(Path(audio_dir).iterdir()):
                if path.is_file() and path.suffix.lower() in extensions:
                    key = normalize_title(_strip_track_number(path.stem))
                    self._index.setdefault(key, []).append(path)

    def find(self, title: str) -> Path | None:
        candidates = self._index.get(normalize_title(title))
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        without_duplicate_suffix = [
            path for path in candidates if not _DUPLICATE_SUFFIX.search(path.stem.strip())
        ]
        return without_duplicate_suffix[0] if without_duplicate_suffix else candidates[0]
