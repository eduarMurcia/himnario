from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class AudioPlayer:
    """Thin wrapper around Qt multimedia playback."""

    def __init__(self) -> None:
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)

    @property
    def position_seconds(self) -> float:
        return self._player.position() / 1000

    @property
    def duration_seconds(self) -> float:
        return self._player.duration() / 1000

    def load(self, path: Path) -> None:
        self._player.setSource(QUrl.fromLocalFile(str(path)))

    def seek(self, seconds: float) -> None:
        self._player.setPosition(max(0, int(seconds * 1000)))

    def play_pause(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def stop(self) -> None:
        self._player.stop()
