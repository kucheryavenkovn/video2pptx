# FILE: src/video_slide_md/gui/main_window.py
# VERSION: 0.2.0
# START_MODULE_CONTRACT
#   PURPOSE: Main GUI window — QMainWindow with menu bar, video player, subtitle overlay, timeline, project lifecycle, detection
#   SCOPE: Integrate MenuBarWidget, VideoPlayerWidget, SubtitleOverlayWidget, TimelineV2Widget, SettingsProjectDialog, SettingsAppDialog, MarkerManager
#   DEPENDS: PySide6, M-PROJECT, M-GUI-MENUBAR, M-GUI-VIDEOPLAYER, M-GUI-SUBTITLE-OVERLAY, M-GUI-TIMELINE-V2, M-GUI-SETTINGS-PROJECT, M-GUI-SETTINGS-APP, M-GUI-SMART-SNAP, M-GUI-MARKER-MANAGER, M-GUI-WORKER
#   LINKS: M-GUI-MAIN
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   MainWindow - QMainWindow subclass with full integration
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
    QSizePolicy,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from video_slide_md.backends import BACKENDS
from video_slide_md.project_manager import Project, create_project, load_slides_into_project, open_project, save_project, update_project_state


class MainWindow(QMainWindow):
    # START_CONTRACT: MainWindow
    #   PURPOSE: Main application window integrating all GUI modules for slide detection workflow
    #   INPUTS: none (creates empty window)
    #   OUTPUTS: none (Qt event loop)
    #   SIDE_EFFECTS: creates GUI window, starts event loop, connects all subcomponents
    #   LINKS: M-GUI-MAIN
    # END_CONTRACT: MainWindow

    project_changed = Signal(object)  # Project

    def __init__(self) -> None:
        super().__init__()
        self._project: Project | None = None
        self._marker_manager = None
        self._app_config = None
        self._setup_ui()
        self._connect_menu_signals()

    # START_BLOCK_SETUP_UI
    def _setup_ui(self) -> None:
        self.setWindowTitle("video-slide-md")
        self.resize(1200, 800)

        # --- Menu bar ---
        from video_slide_md.gui.menu_bar import MenuBarWidget
        self._menu_bar = MenuBarWidget(self)
        self.setMenuBar(self._menu_bar)

        # --- Toolbar ---
        toolbar = QToolBar("Project")
        self.addToolBar(toolbar)
        new_btn = toolbar.addAction("New Project")
        new_btn.triggered.connect(self._on_new_project)
        open_btn = toolbar.addAction("Open Project")
        open_btn.triggered.connect(self._on_open_project)

        # --- Central widget ---
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)

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
        main_layout.addLayout(info_row)

        # Splitter: top = video + overlay, bottom = timeline
        self._splitter = QSplitter(Qt.Orientation.Vertical)

        # --- Video + subtitle overlay container ---
        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)

        from video_slide_md.gui.video_player import VideoPlayerWidget
        from video_slide_md.gui.subtitle_overlay import SubtitleOverlayWidget
        self._video_player = VideoPlayerWidget()
        self._subtitle_overlay = SubtitleOverlayWidget()
        self._video_player.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._subtitle_overlay.setParent(self._video_player)
        self._subtitle_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        video_layout.addWidget(self._video_player, stretch=1)

        self._timeline_placeholder = QLabel("No slides detected yet")
        self._timeline_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        video_layout.addWidget(self._timeline_placeholder)
        self._timeline_placeholder.hide()

        # --- Timeline V2 ---
        from video_slide_md.gui.timeline_v2 import TimelineV2Widget
        self._timeline = TimelineV2Widget()
        self._timeline.hide()

        self._splitter.addWidget(video_container)
        self._splitter.addWidget(self._timeline)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 1)
        main_layout.addWidget(self._splitter, stretch=1)

        # Status bar
        self.statusBar().showMessage("Ready")
        self._show_backend_info()

        # Connect video position → subtitle overlay
        self._video_player.positionChanged.connect(self._on_video_position_changed)

        # Connect timeline signals
        self._timeline.marker_added.connect(self._on_timeline_marker_added)
        self._timeline.marker_deleted.connect(self._on_timeline_marker_deleted)

    def _connect_menu_signals(self) -> None:
        mb = self._menu_bar
        mb.act_new_project.triggered.connect(self._on_new_project)
        mb.act_open_project.triggered.connect(self._on_open_project)
        mb.act_close_project.triggered.connect(self._on_close_project)
        mb.act_save_project.triggered.connect(self._on_save_project)
        mb.act_import_srt.triggered.connect(self._on_import_srt)
        mb.act_exit.triggered.connect(self.close)
        mb.act_project_settings.triggered.connect(self._on_project_settings)
        mb.act_app_settings.triggered.connect(self._on_app_settings)

    # END_BLOCK_SETUP_UI

    # START_BLOCK_VIDEO_SUBTITLE_SYNC
    def _on_video_position_changed(self, seconds: float) -> None:
        self._subtitle_overlay.sync_to_position(seconds)

    def _resize_subtitle_overlay(self) -> None:
        if self._video_player.videoWidget():
            self._subtitle_overlay.setGeometry(self._video_player.videoWidget().geometry())
    # END_BLOCK_VIDEO_SUBTITLE_SYNC

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

    def _on_close_project(self) -> None:
        if self._project is None:
            return
        self._video_player.clear_video()
        self._subtitle_overlay.clear_subtitles()
        self._project = None
        self._video_label.setText("Video: —")
        self._subs_label.setText("Subtitles: —")
        self._detect_btn.setEnabled(False)
        self._timeline.hide()
        self._timeline.set_slides([])
        self._timeline.set_markers([])
        self._timeline_placeholder.hide()
        self.setWindowTitle("video-slide-md")
        self.statusBar().showMessage("Project closed")

    def _on_save_project(self) -> None:
        if self._project is None:
            return
        try:
            save_project(self._project)
            self.statusBar().showMessage("Project saved")
            logger.info("[GUI-Main][_on_save_project] Project saved | name={}", self._project.name)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save project: {e}")

    def _on_import_srt(self) -> None:
        if self._project is None:
            return
        subs_path, _ = QFileDialog.getOpenFileName(
            self, "Import Subtitles", "", "Subtitle Files (*.srt *.vtt);;All Files (*)"
        )
        if not subs_path:
            return
        try:
            import shutil
            dst = Path(self._project.project_dir) / Path(subs_path).name
            shutil.copy2(subs_path, dst)
            self._project.subtitles = str(dst)
            from video_slide_md.project_manager import save_project
            save_project(self._project)
            self._subs_label.setText(f"Subtitles: {dst.name}")
            self._subtitle_overlay.load_subtitles(str(dst))
            self.statusBar().showMessage(f"Subtitles imported: {dst.name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import subtitles: {e}")

    def _set_project(self, proj: Project) -> None:
        self._project = proj
        self._video_label.setText(f"Video: {Path(proj.video).name}")
        self._subs_label.setText(f"Subtitles: {Path(proj.subtitles).name}" if proj.subtitles else "Subtitles: —")
        self._detect_btn.setEnabled(True)
        self.setWindowTitle(f"video-slide-md — {proj.name}")

        # Init marker manager ref
        from video_slide_md.gui import marker_manager as mm
        self._marker_manager = mm

        # Init app config (lazy)
        from video_slide_md.gui.app_config import load_app_config
        self._app_config = load_app_config()

        # Load video
        self._video_player.load_video(proj.video)
        if proj.subtitles:
            self._subtitle_overlay.load_subtitles(proj.subtitles)

        # Load slides into timeline
        if proj.slides:
            self._timeline.set_slides(proj.slides)
            self._timeline.set_video_duration(proj.video_duration or 0)
            self._timeline.set_markers(proj.markers)
            self._timeline.set_project(proj)
            self._timeline.show()
        else:
            self._timeline_placeholder.show()

        self.project_changed.emit(proj)
        logger.info("[GUI-Main][_set_project] Project loaded | name={}", proj.name)
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
            load_slides_into_project(self._project)
            # Reload slides into timeline
            if self._project.slides:
                self._timeline.set_slides(self._project.slides)
                self._timeline.set_video_duration(self._project.video_duration or 0)
                self._timeline.set_project(self._project)
                self._timeline.show()
                self._timeline_placeholder.hide()

        def on_error(msg: str) -> None:
            self.statusBar().showMessage(f"Detection failed: {msg}")
            QMessageBox.critical(self, "Detection Error", msg)

        worker = DetectWorker(project=self._project)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.run()
    # END_BLOCK_DETECT

    # START_BLOCK_SETTINGS_MENU
    def _on_project_settings(self) -> None:
        if self._project is None:
            QMessageBox.information(self, "Project Settings", "Open a project first")
            return
        from video_slide_md.gui.settings_project import SettingsProjectDialog
        dlg = SettingsProjectDialog(self._project, self)
        if dlg.exec():
            logger.info("[GUI-Main][_on_project_settings] Project settings updated")
            self.statusBar().showMessage("Project settings updated")

    def _on_app_settings(self) -> None:
        from video_slide_md.gui.settings_app import SettingsAppDialog
        dlg = SettingsAppDialog(self._app_config, self)
        if dlg.exec():
            logger.info("[GUI-Main][_on_app_settings] App settings updated")
            self.statusBar().showMessage("App settings updated")
    # END_BLOCK_SETTINGS_MENU

    # START_BLOCK_TIMELINE_MARKERS
    def _on_timeline_marker_added(self, ts: float) -> None:
        if self._marker_manager is None or self._project is None:
            return

        marker = self._marker_manager.add_marker(self._project, ts)
        if marker:
            self._timeline.set_markers(self._project.markers)
            self.statusBar().showMessage(f"Marker added at {ts:.1f}s")
        else:
            self.statusBar().showMessage(f"Failed to snap marker at {ts:.1f}s")

    def _on_timeline_marker_deleted(self, original_ts: float) -> None:
        if self._marker_manager is None or self._project is None:
            return

        self._marker_manager.delete_marker(self._project, original_ts)
        self._timeline.set_markers(self._project.markers)
        self.statusBar().showMessage(f"Marker deleted at {original_ts:.1f}s")
    # END_BLOCK_TIMELINE_MARKERS

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
