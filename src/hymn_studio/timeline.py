from __future__ import annotations


class Timeline:
    """Stores slide transition times in seconds."""

    MIN_TRANSITION_GAP_SECONDS = 0.05

    def __init__(self, timestamps: list[float] | None = None) -> None:
        self._timestamps = []
        for timestamp in timestamps or []:
            self.add_transition(timestamp)

    @property
    def timestamps(self) -> list[float]:
        return list(self._timestamps)

    def add_transition(self, seconds: float) -> bool:
        if seconds < 0:
            raise ValueError("Transition time cannot be negative.")

        if self._timestamps and seconds <= self._timestamps[-1] + self.MIN_TRANSITION_GAP_SECONDS:
            return False

        self._timestamps.append(seconds)
        return True

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
