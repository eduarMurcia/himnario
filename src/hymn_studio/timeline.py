from __future__ import annotations


class Timeline:
    """Stores slide transition times in seconds."""

    def __init__(self, timestamps: list[float] | None = None) -> None:
        self._timestamps = list(timestamps or [])

    @property
    def timestamps(self) -> list[float]:
        return list(self._timestamps)

    def add_transition(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("Transition time cannot be negative.")
        self._timestamps.append(seconds)

    def clear(self) -> None:
        self._timestamps.clear()

    def current_slide_index(self, seconds: float) -> int:
        index = 0
        for timestamp in self._timestamps:
            if seconds >= timestamp:
                index += 1
            else:
                break
        return index
