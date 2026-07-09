# FILE: src/video2pptx/gui/main_window.py
# VERSION: 0.3.0
# START_MODULE_CONTRACT
#   PURPOSE: Main GUI window — QMainWindow with menu bar, video player, subtitle overlay, always-visible timeline, marker panel, project lifecycle, detection
#   SCOPE: Integrate MenuBarWidget, VideoPlayerWidget, TimelineV2Widget, MarkerPanel, SettingsProjectDialog, SettingsAppDialog, MarkerManager
#   DEPENDS: PySide6, M-PROJECT, M-GUI-MENUBAR, M-GUI-VIDEOPLAYER, M-GUI-TIMELINE-V2, M-GUI-SETTINGS-PROJECT, M-GUI-SETTINGS-APP, M-GUI-SMART-SNAP, M-GUI-MARKER-MANAGER, M-GUI-MARKER-PANEL, M-GUI-WORKER
#   LINKS: M-GUI-MAIN
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   MainWindow - QMainWindow subclass with full integration, always-visible timeline, marker panel
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

import pysubs2
from loguru import logger
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QKeySequence, QPixmap, QShortcut
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

from video2pptx.backends import BACKENDS
from video2pptx.gui.app_config import add_recent_project, load_app_config, save_app_config
from video2pptx.project_manager import Project, create_project, import_video_to_project, import_subtitles_to_project, load_slides_into_project, open_project, save_project, update_project_state


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
        self._current_project_dir: str | None = None
        self._marker_manager = None
        self._app_config = load_app_config()
        self._subs: pysubs2.SSAFile | None = None
        self._setup_ui()
        self._connect_menu_signals()
        self._try_restore_last_project()

    # START_BLOCK_SETUP_UI
    def _setup_ui(self) -> None:
        self.setWindowTitle("video2pptx")
        self.resize(1200, 800)

        # --- Menu bar ---
        from video2pptx.gui.menu_bar import MenuBarWidget
        self._menu_bar = MenuBarWidget(self)
        self.setMenuBar(self._menu_bar)

        # --- Toolbar ---
        toolbar = QToolBar("Project")
        self.addToolBar(toolbar)
        new_btn = toolbar.addAction("New Project")
        new_btn.triggered.connect(self._on_new_project)
        open_btn = toolbar.addAction("Open Project")
        open_btn.triggered.connect(self._on_open_project)
        toolbar.addSeparator()
        import_video_btn = toolbar.addAction("Import Video")
        import_video_btn.triggered.connect(self._on_import_video)
        import_subs_btn = toolbar.addAction("Import Subtitles")
        import_subs_btn.triggered.connect(self._on_import_srt)
        toolbar.addSeparator()
        add_marker_btn = toolbar.addAction("Add Marker")
        add_marker_btn.setToolTip("Add a marker at current video position (Ctrl+M)")
        add_marker_btn.triggered.connect(self._on_add_marker)
        markers_btn = toolbar.addAction("Markers")
        markers_btn.setToolTip("Open marker list")
        markers_btn.triggered.connect(self._on_open_marker_panel)

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
        self._preview_btn = QPushButton("Preview")
        self._preview_btn.setToolTip("Quick preview — show score waveform on timeline (no files written)")
        self._preview_btn.setEnabled(False)
        self._preview_btn.clicked.connect(self._on_preview)

        info_row.addWidget(self._video_label)
        info_row.addWidget(self._subs_label)
        info_row.addWidget(self._backend_label)
        info_row.addStretch()
        info_row.addWidget(self._preview_btn)
        info_row.addWidget(self._detect_btn)
        main_layout.addLayout(info_row)

        # Splitter: top = video + overlay, bottom = timeline
        self._splitter = QSplitter(Qt.Orientation.Vertical)

        # --- Video + subtitle overlay container ---
        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)

        from video2pptx.gui.video_player import VideoPlayerWidget
        self._video_player = VideoPlayerWidget()
        self._video_player.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        video_layout.addWidget(self._video_player, stretch=1)

        # --- Timeline V3 (multi-track, zoom/pan) ---
        from video2pptx.gui.timeline3 import TimelineWidget
        self._timeline = TimelineWidget()

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
        self._timeline.seek_requested.connect(self._on_seek_to_marker)
        self._timeline.open_image.connect(self._on_open_timeline_image)

        # Keyboard shortcuts
        self._shortcut_add_marker = QShortcut(QKeySequence("Ctrl+M"), self)
        self._shortcut_add_marker.activated.connect(self._on_add_marker)

    def _connect_menu_signals(self) -> None:
        mb = self._menu_bar
        mb.act_new_project.triggered.connect(self._on_new_project)
        mb.act_open_project.triggered.connect(self._on_open_project)
        mb.act_close_project.triggered.connect(self._on_close_project)
        mb.act_save_project.triggered.connect(self._on_save_project)
        mb.act_import_video.triggered.connect(self._on_import_video)
        mb.act_import_srt.triggered.connect(self._on_import_srt)
        mb.act_exit.triggered.connect(self.close)
        mb.act_project_settings.triggered.connect(self._on_project_settings)
        mb.act_app_settings.triggered.connect(self._on_app_settings)
        mb.open_recent_project.connect(self._on_open_recent_project)
        self._refresh_recent_projects()

    # END_BLOCK_SETUP_UI

    # START_BLOCK_RECENT_PROJECTS
    def _refresh_recent_projects(self) -> None:
        self._app_config = load_app_config()
        self._menu_bar.set_recent_projects(self._app_config.recent_projects)
    # END_BLOCK_RECENT_PROJECTS

    # START_BLOCK_VIDEO_SUBTITLE_SYNC
    def _on_video_position_changed(self, seconds: float) -> None:
        text = self._get_subtitle_at(seconds)
        self._video_player.set_subtitle_text(text)
        self._timeline.set_position(seconds)

    def _get_subtitle_at(self, seconds: float) -> str | None:
        if self._subs is None:
            return None
        ms = int(seconds * 1000)
        for event in self._subs.events:
            if event.start <= ms < event.end:
                if event.plaintext.strip():
                    return event.plaintext.strip()
        return None

    def _load_subtitles(self, subtitle_path: str | Path | None) -> None:
        if subtitle_path is None:
            self._subs = None
            return
        path = Path(subtitle_path)
        if not path.is_file():
            logger.warning(f"[GUI-Main][_load_subtitles] File not found | path={path}")
            self._subs = None
            return
        try:
            self._subs = pysubs2.load(str(path), encoding="utf-8")
            logger.info(f"[GUI-Main][_load_subtitles] Loaded | path={path} cues={len(self._subs)}")
        except Exception as exc:
            logger.warning(f"[GUI-Main][_load_subtitles] Failed to parse | path={path} error={exc}")
            self._subs = None

    # END_BLOCK_VIDEO_SUBTITLE_SYNC

    # START_BLOCK_PROJECT_LIFECYCLE
    def _on_new_project(self) -> None:
        proj_dir = QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if not proj_dir:
            return

        import os
        folder_name = os.path.basename(os.path.normpath(proj_dir))

        try:
            proj = create_project(project_dir=proj_dir, name=folder_name)
            self._current_project_dir = str(Path(proj_dir).resolve())
            self._set_project(proj)
            self.statusBar().showMessage(f"Project created: {proj.name}")
        except FileExistsError as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_open_project(self) -> None:
        proj_dir = QFileDialog.getExistingDirectory(self, "Open Project Directory")
        if not proj_dir:
            return

        try:
            proj = open_project(proj_dir)
            self._current_project_dir = str(Path(proj_dir).resolve())
            self._set_project(proj)
            self.statusBar().showMessage(f"Project opened: {proj.name}")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_open_recent_project(self, path: str) -> None:
        proj_dir = Path(path).resolve()
        if not proj_dir.is_dir():
            QMessageBox.critical(self, "Error", f"Project directory not found:\n{path}")
            self._app_config = add_recent_project(str(proj_dir), self._app_config)
            self._refresh_recent_projects()
            return
        try:
            proj = open_project(proj_dir)
            self._current_project_dir = str(proj_dir)
            self._set_project(proj)
            self.statusBar().showMessage(f"Project opened: {proj.name}")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_close_project(self) -> None:
        if self._project is None:
            return
        self._video_player.clear_video()
        self._video_player.set_subtitle_text(None)
        self._subs = None
        self._project = None
        self._video_label.setText("Video: —")
        self._subs_label.setText("Subtitles: —")
        self._detect_btn.setEnabled(False)
        self._preview_btn.setEnabled(False)
        self._timeline.set_slides([])
        self._timeline.set_markers([])
        self._timeline.clear_scores()
        self.setWindowTitle("video2pptx")
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

    def _on_import_video(self) -> None:
        if self._project is None:
            return
        video_path, _ = QFileDialog.getOpenFileName(
            self, "Import Video", "", "Video Files (*.mp4 *.mkv *.mov *.webm);;All Files (*)"
        )
        if not video_path:
            return
        try:
            import_video_to_project(self._project, video_path)
            self._video_label.setText(f"Video: {Path(video_path).name}")
            self._video_player.load_video(video_path)
            self.statusBar().showMessage(f"Video imported: {Path(video_path).name}")

            if self._project.subtitles:
                sub_path = Path(self._project.subtitles)
                self._subs_label.setText(f"Subtitles: {sub_path.name}")
                self._load_subtitles(self._project.subtitles)
                self.statusBar().showMessage(f"Video imported, subtitles auto-detected: {sub_path.name}")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_import_srt(self) -> None:
        if self._project is None:
            return
        subs_path, _ = QFileDialog.getOpenFileName(
            self, "Import Subtitles", "", "Subtitle Files (*.srt *.vtt);;All Files (*)"
        )
        if not subs_path:
            return
        try:
            import_subtitles_to_project(self._project, subs_path)
            sub_path = Path(subs_path)
            self._subs_label.setText(f"Subtitles: {sub_path.name}")
            self._load_subtitles(subs_path)
            self.statusBar().showMessage(f"Subtitles imported: {sub_path.name}")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Error", str(e))

    def _set_project(self, proj: Project) -> None:
        self._project = proj

        # Video label
        if proj.video:
            self._video_label.setText(f"Video: {Path(proj.video).name}")
            self._video_player.load_video(proj.video)
        else:
            self._video_label.setText("Video: —")

        # Subtitles label
        self._subs_label.setText(f"Subtitles: {Path(proj.subtitles).name}" if proj.subtitles else "Subtitles: —")
        if proj.subtitles:
            self._load_subtitles(proj.subtitles)

        self._detect_btn.setEnabled(bool(proj.video))
        self._preview_btn.setEnabled(bool(proj.video))
        self.setWindowTitle(f"video2pptx — {proj.name}")

        # Init marker manager ref
        from video2pptx.gui import marker_manager as mm
        self._marker_manager = mm

        self._app_config = load_app_config()

        # Load slides into timeline
        dur = getattr(proj, "video_duration", 0) or 0
        if proj.slides:
            self._timeline.set_slides(proj.slides)
            self._timeline.set_video_duration(dur)
            self._timeline.set_markers(proj.markers)
            self._timeline.set_subtitles(self._subs)
            self._timeline.set_project(proj)
        else:
            self._timeline.set_video_duration(dur)
            self._timeline.set_markers(proj.markers)
            self._timeline.set_subtitles(self._subs)
            self._timeline.set_project(proj)

        self.project_changed.emit(proj)
        logger.info("[GUI-Main][_set_project] Project loaded | name={}", proj.name)

        # Add to recent projects and refresh menu
        if self._current_project_dir:
            self._app_config = add_recent_project(self._current_project_dir, self._app_config)
            self._menu_bar.set_recent_projects(self._app_config.recent_projects)
    # END_BLOCK_PROJECT_LIFECYCLE

    # START_BLOCK_PROJECT_RESTORE
    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._project is not None:
            try:
                cfg = load_app_config()
                cfg.last_project_path = self._project.output_dir
                save_app_config(cfg)
            except Exception:
                pass
        super().closeEvent(event)

    def _try_restore_last_project(self) -> None:
        try:
            cfg = load_app_config()
            if not cfg.restore_last_project:
                return
            if not cfg.last_project_path:
                return
            last_path = Path(cfg.last_project_path)
            if not (last_path / "project.json").is_file():
                return
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._do_restore_project(str(last_path)))
        except Exception:
            pass

    def _do_restore_project(self, project_path: str) -> None:
        try:
            import os
            if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
                return
            reply = QMessageBox.question(
                self,
                "Restore Project",
                f"Open previous project?\n\n{Path(project_path).name}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                proj = open_project(project_path)
                self._set_project(proj)
                self.statusBar().showMessage(f"Restored project: {proj.name}")
        except Exception:
            pass
    # END_BLOCK_PROJECT_RESTORE

    # START_BLOCK_DETECT
    def _on_detect(self) -> None:
        if self._project is None:
            return
        self.statusBar().showMessage("Detection started...")
        logger.info("[GUI-Main][_on_detect] Detect triggered")

        from video2pptx.gui.workers import DetectWorker

        def on_finished(path: str) -> None:
            self.statusBar().showMessage(f"Detection complete: {path}")
            update_project_state(self._project, detect_done=True, slides_json=path)
            load_slides_into_project(self._project)
            # Reload slides into timeline
            if self._project.slides:
                self._timeline.set_slides(self._project.slides)
                self._timeline.set_video_duration(self._project.video_duration or 0)
                self._timeline.set_subtitles(self._subs)
                self._timeline.set_project(self._project)

        def on_error(msg: str) -> None:
            self.statusBar().showMessage(f"Detection failed: {msg}")
            QMessageBox.critical(self, "Detection Error", msg)

        worker = DetectWorker(project=self._project)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.run()
    # END_BLOCK_DETECT

    # START_BLOCK_PREVIEW
    def _on_preview(self) -> None:
        if self._project is None or not self._project.video:
            return
        self.statusBar().showMessage("Preview analysis running...")
        self._preview_btn.setEnabled(False)
        logger.info("[GUI-Main][_on_preview] Preview triggered")

        from PySide6.QtCore import QThread
        from video2pptx.gui.workers import PreviewWorker

        self._preview_thread = QThread(self)
        self._preview_worker = PreviewWorker(video_path=self._project.video)
        self._preview_worker.moveToThread(self._preview_thread)

        def on_finished(ts: list[float], scores: list[float]) -> None:
            self._timeline.set_scores(ts, scores)
            self._timeline.set_video_duration(self._project.video_duration or 0)
            self.statusBar().showMessage(f"Preview complete — {len(scores)} frames")
            self._preview_btn.setEnabled(True)
            self._preview_thread.quit()

        def on_error(msg: str) -> None:
            self.statusBar().showMessage(f"Preview failed: {msg}")
            self._preview_btn.setEnabled(True)
            self._preview_thread.quit()

        self._preview_worker.finished.connect(on_finished)
        self._preview_worker.error.connect(on_error)
        self._preview_thread.started.connect(self._preview_worker.run)
        self._preview_thread.start()
    # END_BLOCK_PREVIEW

    # START_BLOCK_SETTINGS_MENU
    def _on_project_settings(self) -> None:
        if self._project is None:
            QMessageBox.information(self, "Project Settings", "Open a project first")
            return
        from video2pptx.gui.settings_project import ProjectSettingsDialog
        dlg = ProjectSettingsDialog(self._project, self, frame_grabber=self._grab_current_frame)
        if dlg.exec():
            logger.info("[GUI-Main][_on_project_settings] Project settings updated")
            self.statusBar().showMessage("Project settings updated")

    def _grab_current_frame(self) -> QPixmap | None:
        if not hasattr(self, "_video_player") or self._video_player is None:
            return None
        view = self._video_player._view
        if view is None:
            return None
        return view.grab()

    def _on_app_settings(self) -> None:
        from video2pptx.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(self._app_config, self)
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

    # START_BLOCK_MARKER_ACTIONS
    def _on_add_marker(self) -> None:
        if self._project is None:
            QMessageBox.information(self, "Add Marker", "Open a project first")
            return
        ts = self._video_player._player.position() / 1000.0
        self._on_timeline_marker_added(ts)

    def _on_open_marker_panel(self) -> None:
        if self._project is None:
            QMessageBox.information(self, "Markers", "Open a project first")
            return
        from video2pptx.gui.marker_panel import MarkerPanel
        dlg = MarkerPanel(self._project, self)
        dlg.seek_requested.connect(self._on_seek_to_marker)
        dlg.marker_deleted.connect(self._on_timeline_marker_deleted)
        dlg.marker_resnapped.connect(lambda ts: self._timeline.set_markers(self._project.markers))
        dlg.exec()

    def _on_seek_to_marker(self, ts: float) -> None:
        self._video_player._player.setPosition(int(ts * 1000))
        self.statusBar().showMessage(f"Seeked to marker at {ts:.1f}s")

    def _on_open_timeline_image(self, path: str) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        self.statusBar().showMessage(f"Opened: {path}")
    # END_BLOCK_MARKER_ACTIONS

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
