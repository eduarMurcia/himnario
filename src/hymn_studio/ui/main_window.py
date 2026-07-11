from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeyEvent, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from hymn_studio.audio import AudioPlayer
from hymn_studio.models import HymnProject, Slide
from hymn_studio.project import ProjectRepository
from hymn_studio.services.slides import SlideLoader
from hymn_studio.timeline import Timeline
from hymn_studio.widgets.slide_preview import SlidePreview


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Hymn Studio")
        self.resize(1280, 760)

        self._project = HymnProject()
        self._timeline = Timeline()
        self._slides: list[Slide] = []

        self._repository = ProjectRepository()
        self._slide_loader = SlideLoader()
        self._audio = AudioPlayer()

        self._slide_list = QListWidget()
        self._preview = SlidePreview()
        self._properties = QLabel("No project loaded")
        self._properties.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._time_label = QLabel("00:00.000")

        self._build_actions()
        self._build_layout()
        self.setStatusBar(QStatusBar())

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
        export_button.clicked.connect(self._export_placeholder)

        controls.addWidget(play_button)
        controls.addWidget(next_button)
        controls.addStretch()
        controls.addWidget(self._time_label)
        controls.addWidget(export_button)

        root_layout.addWidget(splitter)
        root_layout.addLayout(controls)
        self.setCentralWidget(root)

    def _open_image_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Open image folder")
        if not folder:
            return

        try:
            self._slides = self._slide_loader.load_folder(Path(folder))
        except ValueError as error:
            self._show_error(str(error))
            return

        self._project.image_folder = Path(folder)
        self._slide_list.clear()
        for slide in self._slides:
            self._slide_list.addItem(slide.name)

        self._show_slide(0)
        self._refresh_properties()

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
        self._refresh_properties()

    def _play_pause(self) -> None:
        self._audio.play_pause()

    def _record_transition(self) -> None:
        if not self._slides:
            return

        seconds = self._audio.position_seconds
        self._timeline.add_transition(seconds)
        self._project.timestamps = self._timeline.timestamps
        next_index = min(len(self._project.timestamps), len(self._slides) - 1)
        self._show_slide(next_index)
        self._time_label.setText(f"{seconds:0.3f}s")
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
        self.statusBar().showMessage("Project saved", 1500)

    def _open_project(self) -> None:
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
                self._slide_list.clear()
                for slide in self._slides:
                    self._slide_list.addItem(slide.name)
                self._show_slide(0)
            if self._project.audio_path is not None:
                self._audio.load(self._project.audio_path)
            self._refresh_properties()
        except (OSError, ValueError) as error:
            self._show_error(str(error))

    def _export_placeholder(self) -> None:
        self._show_error("MP4 export will be implemented in the next focused commit.")

    def _show_slide(self, index: int) -> None:
        if not self._slides:
            self._preview.clear()
            return

        slide = self._slides[index]
        self._slide_list.setCurrentRow(index)
        self._preview.set_pixmap(QPixmap(str(slide.path)))

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

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, "Hymn Studio", message)
