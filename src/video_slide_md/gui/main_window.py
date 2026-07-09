# FILE: src/video_slide_md/gui/main_window.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Main GUI window — QMainWindow with project toolbar, video/subtitle selectors, detect button, central splitter
#   SCOPE: Create and show MainWindow, manage project lifecycle, trigger detect/notes/llm via workers
#   DEPENDS: PySide6, M-PROJECT, M-GUI-TIMELINE, M-GUI-SETTINGS, M-GUI-WORKER
#   LINKS: M-GUI-MAIN
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   MainWindow - QMainWindow subclass with project toolbar, file selectors, backend info, detect button
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

from loguru import logger
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from video_slide_md.project_manager import Project, create_project, open_project, update_project_state
from video_slide_md.backends import BACKENDS


class MainWindow(QMainWindow):
    # START_CONTRACT: MainWindow
    #   PURPOSE: Main application window with project management, video/subtitle selectors, backend info, detect button, central area
    #   INPUTS: none (creates empty window)
    #   OUTPUTS: none (Qt event loop)
    #   SIDE_EFFECTS: creates GUI window, starts event loop
    #   LINKS: M-GUI-MAIN
    # END_CONTRACT: MainWindow

    project_changed = Signal(object)  # Project

    def __init__(self) -> None:
        super().__init__()
        self._project: Project | None = None
        self._setup_ui()

    # START_BLOCK_SETUP_UI
    def _setup_ui(self) -> None:
        self.setWindowTitle("video-slide-md")
        self.resize(1200, 800)

        # Toolbar
        toolbar = QToolBar("Project")
        self.addToolBar(toolbar)

        new_btn = toolbar.addAction("New Project")
        new_btn.triggered.connect(self._on_new_project)

        open_btn = toolbar.addAction("Open Project")
        open_btn.triggered.connect(self._on_open_project)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Info row
        info_row = QHBoxLayout()
        self._video_label = QLabel("Video: —")
        self._subs_label = QLabel("Subtitles: —")
        self._backend_label = QLabel("Backend: auto")
        self._detect_btn = QPushButton("Detect")
        self._detect_btn.setEnabled(False)
        self._detect_btn.clicked.connect(self._on_detect)

        info_row.addWidget(self._video_label)
        info_row.addWidget(self._subs_label)
        info_row.addWidget(self._backend_label)
        info_row.addStretch()
        info_row.addWidget(self._detect_btn)
        layout.addLayout(info_row)

        # Timeline placeholder
        self._timeline_placeholder = QLabel("Open a project to begin")
        self._timeline_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._timeline_placeholder, stretch=1)

        # Status bar
        self.statusBar().showMessage("Ready")

        # Detect available backends
        self._show_backend_info()

    # END_BLOCK_SETUP_UI

    # START_BLOCK_PROJECT_LIFECYCLE
    def _on_new_project(self) -> None:
        video_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video", "", "Video Files (*.mp4 *.mkv *.mov *.webm);;All Files (*)"
        )
        if not video_path:
            return

        proj_dir = QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if not proj_dir:
            return

        subs_path, _ = QFileDialog.getOpenFileName(
            self, "Select Subtitles (optional)", "", "Subtitle Files (*.srt *.vtt);;All Files (*)"
        )
        subs_arg = subs_path if subs_path else None

        try:
            proj = create_project(
                project_dir=proj_dir,
                video_path=video_path,
                subtitles_path=subs_arg,
                name=Path(video_path).stem,
            )
            self._set_project(proj)
            self.statusBar().showMessage(f"Project created: {proj.name}")
        except (FileNotFoundError, FileExistsError) as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_open_project(self) -> None:
        proj_dir = QFileDialog.getExistingDirectory(self, "Open Project Directory")
        if not proj_dir:
            return

        try:
            proj = open_project(proj_dir)
            self._set_project(proj)
            self.statusBar().showMessage(f"Project opened: {proj.name}")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Error", str(e))

    def _set_project(self, proj: Project) -> None:
        self._project = proj
        self._video_label.setText(f"Video: {Path(proj.video).name}")
        self._subs_label.setText(f"Subtitles: {Path(proj.subtitles).name}" if proj.subtitles else "Subtitles: —")
        self._detect_btn.setEnabled(True)
        self.project_changed.emit(proj)
        logger.info(f"[GUI-Main][_set_project] Project loaded | name={proj.name}")

    # END_BLOCK_PROJECT_LIFECYCLE

    # START_BLOCK_DETECT
    def _on_detect(self) -> None:
        if self._project is None:
            return
        self.statusBar().showMessage("Detection started...")
        logger.info("[GUI-Main][_on_detect] Detect triggered")

        from video_slide_md.gui.workers import DetectWorker

        def on_finished(path: str) -> None:
            self.statusBar().showMessage(f"Detection complete: {path}")
            update_project_state(self._project, detect_done=True, slides_json=path)

        def on_error(msg: str) -> None:
            self.statusBar().showMessage(f"Detection failed: {msg}")
            QMessageBox.critical(self, "Detection Error", msg)

        worker = DetectWorker(project=self._project)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.run()

    # END_BLOCK_DETECT

    # START_BLOCK_BACKEND_INFO
    def _show_backend_info(self) -> None:
        try:
            available = [name for name, info in BACKENDS.items() if info["available"]]
            text = ", ".join(available) if available else "none"
            self._backend_label.setText(f"Backend: {text}")
        except Exception:
            self._backend_label.setText("Backend: auto")
    # END_BLOCK_BACKEND_INFO

    def project(self) -> Project | None:
        return self._project
