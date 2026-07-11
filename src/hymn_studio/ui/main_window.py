from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QKeyEvent, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from hymn_studio.audio import AudioPlayer
from hymn_studio.exporter import ExportError, FfmpegExporter
from hymn_studio.models import HymnProject, Slide
from hymn_studio.project import ProjectRepository
from hymn_studio.services.slides import SlideLoader
from hymn_studio.timeline import Timeline
from hymn_studio.widgets.slide_preview import SlidePreview


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.resize(1280, 760)

        self._project = HymnProject()
        self._timeline = Timeline()
        self._slides: list[Slide] = []
        self._is_dirty = False

        self._repository = ProjectRepository()
        self._slide_loader = SlideLoader()
        self._audio = AudioPlayer()
        self._exporter = FfmpegExporter()

        self._slide_list = QListWidget()
        self._slide_list.currentRowChanged.connect(self._select_slide)
        self._preview = SlidePreview()
        self._properties = QLabel("No project loaded")
        self._properties.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._time_label = QLabel("00:00.000")
        self._duration_label = QLabel("00:00.000")
        self._time_slider = QSlider(Qt.Orientation.Horizontal)
        self._time_slider.setEnabled(False)
        self._time_slider.setRange(0, 0)
        self._time_slider.sliderMoved.connect(self._seek_audio)
        self._is_updating_slider = False
        self._current_slide_index = -1
        self._ui_timer = QTimer(self)
        self._ui_timer.setInterval(100)
        self._ui_timer.timeout.connect(self._sync_with_audio)

        self._build_actions()
        self._build_layout()
        self.setStatusBar(QStatusBar())
        self._update_window_title()
        self._ui_timer.start()

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self._confirm_discard_changes():
            event.accept()
            return

        event.ignore()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space:
            self._record_transition()
            event.accept()
            return
        super().keyPressEvent(event)

    def _build_actions(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        open_images = QAction("Open Image Folder", self)
        open_images.triggered.connect(self._open_image_folder)
        file_menu.addAction(open_images)

        load_audio = QAction("Load Audio", self)
        load_audio.triggered.connect(self._load_audio)
        file_menu.addAction(load_audio)

        file_menu.addSeparator()

        save_project = QAction("Save Project", self)
        save_project.triggered.connect(self._save_project)
        file_menu.addAction(save_project)

        open_project = QAction("Open Project", self)
        open_project.triggered.connect(self._open_project)
        file_menu.addAction(open_project)

    def _build_layout(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)

        splitter = QSplitter()
        splitter.addWidget(self._slide_list)
        splitter.addWidget(self._preview)
        splitter.addWidget(self._properties)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 1)

        controls = QHBoxLayout()
        play_button = QPushButton("Play/Pause")
        play_button.clicked.connect(self._play_pause)
        next_button = QPushButton("Next Slide")
        next_button.clicked.connect(self._record_transition)
        export_button = QPushButton("Export MP4")
        export_button.clicked.connect(self._export_mp4)

        controls.addWidget(play_button)
        controls.addWidget(next_button)
        controls.addStretch()
        controls.addWidget(self._time_label)
        controls.addWidget(self._time_slider, 2)
        controls.addWidget(self._duration_label)
        controls.addWidget(export_button)

        root_layout.addWidget(splitter)
        root_layout.addLayout(controls)
        self.setCentralWidget(root)

    def _open_image_folder(self) -> None:
        if not self._confirm_discard_changes():
            return

        folder = QFileDialog.getExistingDirectory(self, "Open image folder")
        if not folder:
            return

        try:
            self._slides = self._slide_loader.load_folder(Path(folder))
        except ValueError as error:
            self._show_error(str(error))
            return

        self._project.image_folder = Path(folder)
        self._timeline.clear()
        self._project.timestamps = []
        self._current_slide_index = -1
        self._slide_list.clear()
        for slide in self._slides:
            self._slide_list.addItem(slide.name)

        self._show_slide(0)
        self._refresh_properties()
        self._mark_dirty()

    def _load_audio(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Load audio",
            "",
            "Audio Files (*.mp3 *.wav *.m4a);;All Files (*)",
        )
        if not file_name:
            return

        audio_path = Path(file_name)
        self._project.audio_path = audio_path
        self._audio.load(audio_path)
        self._time_slider.setEnabled(True)
        self._refresh_properties()
        self._mark_dirty()

    def _play_pause(self) -> None:
        self._audio.play_pause()

    def _record_transition(self) -> None:
        if not self._slides:
            return

        seconds = self._audio.position_seconds
        if not self._timeline.add_transition(seconds):
            self.statusBar().showMessage("Transition ignored", 1500)
            return

        self._project.timestamps = self._timeline.timestamps
        next_index = min(len(self._project.timestamps), len(self._slides) - 1)
        self._show_slide(next_index)
        self._update_time_label(seconds)
        self._refresh_properties()
        self._mark_dirty()
        self.statusBar().showMessage("Transition saved", 1500)

    def _save_project(self) -> None:
        path = self._project.project_path
        if path is None:
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Save project",
                "Proyecto.hymn",
                "Hymn Studio Project (*.hymn)",
            )
            if not file_name:
                return
            path = Path(file_name)

        self._repository.save(self._project, path)
        self._is_dirty = False
        self._update_window_title()
        self.statusBar().showMessage("Project saved", 1500)

    def _open_project(self) -> None:
        if not self._confirm_discard_changes():
            return

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open project",
            "",
            "Hymn Studio Project (*.hymn)",
        )
        if not file_name:
            return

        try:
            self._project = self._repository.load(Path(file_name))
            self._timeline = Timeline(self._project.timestamps)
            if self._project.image_folder is not None:
                self._slides = self._slide_loader.load_folder(self._project.image_folder)
                self._current_slide_index = -1
                self._slide_list.clear()
                for slide in self._slides:
                    self._slide_list.addItem(slide.name)
                self._show_slide(0)
            if self._project.audio_path is not None:
                self._audio.load(self._project.audio_path)
                self._time_slider.setEnabled(True)
            self._refresh_properties()
            self._is_dirty = False
            self._update_window_title()
        except (OSError, ValueError) as error:
            self._show_error(str(error))

    def _export_mp4(self) -> None:
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Export MP4",
            "Hymn.mp4",
            "MP4 Video (*.mp4)",
        )
        if not file_name:
            return

        output_path = Path(file_name)
        if output_path.suffix.lower() != ".mp4":
            output_path = output_path.with_suffix(".mp4")

        try:
            self.statusBar().showMessage("Exporting MP4...")
            self._exporter.export(self._project, self._slides, output_path)
        except ExportError as error:
            self._show_error(str(error))
            return

        self.statusBar().showMessage("MP4 exported", 3000)

    def _show_slide(self, index: int) -> None:
        if not self._slides:
            self._preview.clear()
            self._current_slide_index = -1
            return

        index = max(0, min(index, len(self._slides) - 1))
        if index == self._current_slide_index:
            return

        slide = self._slides[index]
        self._current_slide_index = index
        self._slide_list.setCurrentRow(index)
        self._preview.set_pixmap(QPixmap(str(slide.path)))

    def _select_slide(self, index: int) -> None:
        if 0 <= index < len(self._slides):
            self._show_slide(index)

    def _sync_with_audio(self) -> None:
        seconds = self._audio.position_seconds
        duration = self._audio.duration_seconds
        self._update_time_label(seconds)
        self._update_duration_label(duration)
        self._update_time_slider(seconds, duration)

        if not self._slides:
            return

        slide_index = min(
            self._timeline.current_slide_index(seconds),
            len(self._slides) - 1,
        )
        self._show_slide(slide_index)

    def _update_time_label(self, seconds: float) -> None:
        self._time_label.setText(self._format_time(seconds))

    def _update_duration_label(self, seconds: float) -> None:
        self._duration_label.setText(self._format_time(seconds))

    def _format_time(self, seconds: float) -> str:
        total_milliseconds = max(0, int(seconds * 1000))
        minutes, remainder = divmod(total_milliseconds, 60_000)
        whole_seconds, milliseconds = divmod(remainder, 1000)
        return f"{minutes:02}:{whole_seconds:02}.{milliseconds:03}"

    def _update_time_slider(self, seconds: float, duration: float) -> None:
        if self._time_slider.isSliderDown():
            return

        self._is_updating_slider = True
        self._time_slider.setRange(0, max(0, int(duration * 1000)))
        self._time_slider.setValue(max(0, int(seconds * 1000)))
        self._is_updating_slider = False

    def _seek_audio(self, milliseconds: int) -> None:
        if self._is_updating_slider:
            return

        seconds = milliseconds / 1000
        self._audio.seek(seconds)
        self._update_time_label(seconds)

    def _refresh_properties(self) -> None:
        image_folder = self._project.image_folder or "-"
        audio = self._project.audio_path or "-"
        self._properties.setText(
            f"Project: {self._project.name}\n"
            f"Images: {image_folder}\n"
            f"Audio: {audio}\n"
            f"Transitions: {len(self._project.timestamps)}\n"
            f"Resolution: {self._project.video.width}x{self._project.video.height}\n"
            f"FPS: {self._project.video.fps}"
        )

    def _mark_dirty(self) -> None:
        if self._is_dirty:
            return

        self._is_dirty = True
        self._update_window_title()

    def _update_window_title(self) -> None:
        marker = "*" if self._is_dirty else ""
        project_name = self._project.name
        if self._project.project_path is not None:
            project_name = self._project.project_path.stem

        self.setWindowTitle(f"{marker}{project_name} - Hymn Studio")

    def _confirm_discard_changes(self) -> bool:
        if not self._is_dirty:
            return True

        result = QMessageBox.question(
            self,
            "Unsaved changes",
            "Discard unsaved project changes?",
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return result == QMessageBox.StandardButton.Discard

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, "Hymn Studio", message)
