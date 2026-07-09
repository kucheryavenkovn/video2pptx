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
#
# START_CHANGE_SUMMARY
#   v0.3.1 - Fix _on_slide_resized duplicate save + missing timeline refresh
#   v0.3.1 - Fix closeEvent not clearing timeline (now calls _on_close_project)
#   v0.3.1 - Fix _on_detect_finished / _on_notes_finished pass force=True to load_slides_into_project
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

import pysubs2
from loguru import logger
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
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
from video2pptx.gui.status_manager import StatusBarManager
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
        self._app_config = load_app_config()
        self._subs: pysubs2.SSAFile | None = None
        self._status = StatusBarManager(self)
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
        add_marker_btn.setToolTip("Add a manual slide at current video position (Ctrl+M)")
        add_marker_btn.triggered.connect(self._on_add_marker_at_position)

        markers_btn = toolbar.addAction("Slides")
        markers_btn.setToolTip("Show slide info")
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
        self._detect_btn.setToolTip("Full detection — pHash + histograms, 3 passes")
        self._detect_btn.setEnabled(False)
        self._detect_btn.clicked.connect(self._on_detect)

        self._quick_detect_btn = QPushButton("Quick Detect")
        self._quick_detect_btn.setToolTip("Fast detection — keyframes only, pixel MAE + screenshots")
        self._quick_detect_btn.setEnabled(False)
        self._quick_detect_btn.clicked.connect(self._on_quick_detect)

        self._export_btn = QPushButton("Export")
        self._export_btn.setToolTip("Export to Markdown or PPTX")
        self._export_btn.setEnabled(False)
        self._export_menu = QMenu(self)
        self._export_menu.addAction("Export &Markdown (Marp)...", self._on_export_md)
        self._export_menu.addAction("Export &PPTX...", self._on_export_pptx)
        self._export_btn.setMenu(self._export_menu)

        self._notes_btn = QPushButton("Process Notes")
        self._notes_btn.setToolTip("Align subtitles + process speaker notes")
        self._notes_btn.setEnabled(False)
        self._notes_btn.clicked.connect(self._on_process_notes)

        self._save_btn = QPushButton("Save")
        self._save_btn.setToolTip("Save project changes")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._on_save_project)

        info_row.addWidget(self._video_label)
        info_row.addWidget(self._subs_label)
        info_row.addWidget(self._backend_label)
        info_row.addStretch()
        info_row.addWidget(self._quick_detect_btn)
        info_row.addWidget(self._detect_btn)
        info_row.addWidget(QLabel("  "))
        info_row.addWidget(self._notes_btn)
        info_row.addWidget(self._export_btn)
        info_row.addWidget(self._save_btn)
        main_layout.addLayout(info_row)

        # Splitter: top = video + overlay, bottom = timeline
        self._splitter = QSplitter(Qt.Orientation.Vertical)
        self._splitter.setChildrenCollapsible(False)

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
        self._splitter.setStretchFactor(1, 2)  # more timeline height
        main_layout.addWidget(self._splitter, stretch=1)

        # Status bar
        self.statusBar().showMessage("Ready")
        self._show_backend_info()

        # Connect video position → subtitle overlay
        self._video_player.positionChanged.connect(self._on_video_position_changed)
        self._video_player.durationChanged.connect(self._on_video_duration_changed)

        # Connect timeline signals
        self._timeline.add_manual_slide.connect(self._on_add_manual_slide)
        self._timeline.set_slide_frame.connect(self._on_set_slide_frame)
        self._timeline.clear_slide_image.connect(self._on_clear_slide_image)
        self._timeline.delete_slide.connect(self._on_delete_slide)
        self._timeline.seek_requested.connect(self._on_seek_to_marker)
        self._timeline.open_image.connect(self._on_open_timeline_image)
        self._timeline.slide_moved.connect(self._on_slide_moved)
        self._timeline.slide_resized.connect(self._on_slide_resized)
        self._timeline.open_subtitle_editor.connect(self._on_open_subtitle_editor)

        # Keyboard shortcuts
        self._shortcut_add_marker = QShortcut(QKeySequence("Ctrl+M"), self)
        self._shortcut_add_marker.activated.connect(self._on_add_marker_at_position)

    def _connect_menu_signals(self) -> None:
        mb = self._menu_bar
        mb.act_new_project.triggered.connect(self._on_new_project)
        mb.act_open_project.triggered.connect(self._on_open_project)
        mb.act_close_project.triggered.connect(self._on_close_project)
        mb.act_save_project.triggered.connect(self._on_save_project)
        mb.act_import_video.triggered.connect(self._on_import_video)
        mb.act_import_srt.triggered.connect(self._on_import_srt)
        mb.act_exit.triggered.connect(self.close)
        mb.act_export_md.triggered.connect(self._on_export_md)
        mb.act_export_pptx.triggered.connect(self._on_export_pptx)
        mb.act_process_notes.triggered.connect(self._on_process_notes)
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
        self._video_player.hide_slide_image()
        self._timeline.set_position(seconds)

    def _on_video_duration_changed(self, seconds: float) -> None:
        if seconds <= 0:
            return
        self._timeline.set_video_duration(seconds)
        if self._project and self._project.slides:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._timeline.zoom_fit)

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
            # Remove invalid path from recent list
            if path in self._app_config.recent_projects:
                self._app_config.recent_projects.remove(path)
                save_app_config(self._app_config)
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
        self._timeline.set_subtitles(None)
        self._project = None
        self._video_label.setText("Video: —")
        self._subs_label.setText("Subtitles: —")
        self._detect_btn.setEnabled(False)
        self._quick_detect_btn.setEnabled(False)
        self._video_label.setText("Video: —")
        self._subs_label.setText("Subtitles: —")
        self._detect_btn.setEnabled(False)
        self._quick_detect_btn.setEnabled(False)
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
            self._detect_btn.setEnabled(True)
            self._quick_detect_btn.setEnabled(True)
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
        self._quick_detect_btn.setEnabled(bool(proj.video))
        has_slides = bool(proj.slides)
        self._export_btn.setEnabled(has_slides)
        has_slides_and_subs = has_slides and bool(proj.subtitles)
        self._notes_btn.setEnabled(has_slides_and_subs)
        self._save_btn.setEnabled(bool(self._project))
        self.setWindowTitle(f"video2pptx — {proj.name}")

        self._app_config = load_app_config()

        # Load slides into timeline
        dur = getattr(proj, "video_duration", 0) or 0
        if proj.slides:
            dur = max(dur, proj.slides[-1].end)
            self._timeline.set_slides(proj.slides)
            self._timeline.set_video_duration(dur)
            self._timeline.set_subtitles(self._subs)
            self._timeline.set_project(proj)
        else:
            self._timeline.set_video_duration(dur)
            self._timeline.set_subtitles(self._subs)
            self._timeline.set_project(proj)
        # Set score waveform from loaded project
        if proj.score_timestamps and proj.score_values:
            self._timeline.set_scores(proj.score_timestamps, proj.score_values)

        self.project_changed.emit(proj)
        logger.info("[GUI-Main][_set_project] Project loaded | name={}", proj.name)

        # Add to recent projects and refresh menu
        if self._current_project_dir:
            self._app_config = add_recent_project(self._current_project_dir, self._app_config)
            save_app_config(self._app_config)
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
        self._on_close_project()
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

        # Warn if slides already exist
        if self._project.slides:
            reply = QMessageBox.question(
                self,
                "Re-detect?",
                f"Project already has {len(self._project.slides)} detected slides.\n"
                "Re-detection will overwrite slides.json and screenshots.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._status.start("Detection")
        logger.info("[GUI-Main][_on_detect] Detect triggered")

        from PySide6.QtCore import QThread
        from video2pptx.gui.workers import DetectWorker

        self._detect_thread = QThread(self)
        self._detect_worker = DetectWorker(project=self._project)
        self._detect_worker.moveToThread(self._detect_thread)
        self._detect_worker.finished.connect(self._on_detect_finished)
        self._detect_worker.error.connect(self._on_detect_error)
        self._detect_worker.progress.connect(self._on_worker_progress_msg)
        self._detect_thread.started.connect(self._detect_worker.run)
        self._detect_thread.start()
    # END_BLOCK_DETECT

    def _on_export_md(self) -> None:
        if not self._project or not self._project.slides_json:
            return
        try:
            from video2pptx.markdown_export import export_to_markdown
            from video2pptx.models import SlidesDocument
            json_path = Path(self._project.output_dir) / self._project.slides_json
            out_path = Path(self._project.output_dir) / "deck.md"
            if out_path.exists():
                r = QMessageBox.question(self, "Overwrite?", f"{out_path} already exists.\nOverwrite?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if r != QMessageBox.StandardButton.Yes:
                    return
            doc = SlidesDocument.model_validate_json(json_path.read_text(encoding="utf-8"))
            export_to_markdown(doc, out_path, slides_dir=str(Path(self._project.output_dir) / "slides"), title=self._project.name)
            self.statusBar().showMessage(f"Markdown exported: {out_path}")
            self._offer_open_file(out_path)
            logger.info("[GUI-Main][_on_export_md] Markdown export complete")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def _on_export_pptx(self) -> None:
        if not self._project or not self._project.slides_json:
            return
        try:
            from video2pptx.pptx_export import export_to_pptx
            from video2pptx.models import SlidesDocument
            json_path = Path(self._project.output_dir) / self._project.slides_json
            out_path = Path(self._project.output_dir) / "deck.pptx"
            if out_path.exists():
                r = QMessageBox.question(self, "Overwrite?", f"{out_path} already exists.\nOverwrite?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if r != QMessageBox.StandardButton.Yes:
                    return
            doc = SlidesDocument.model_validate_json(json_path.read_text(encoding="utf-8"))
            export_to_pptx(doc, out_path, slides_dir=str(Path(self._project.output_dir) / "slides"), title=self._project.name, notes_mode="basic")
            self.statusBar().showMessage(f"PPTX exported: {out_path}")
            self._offer_open_file(out_path)
            logger.info("[GUI-Main][_on_export_pptx] PPTX export complete")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    @staticmethod
    def _offer_open_file(path: Path) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        r = QMessageBox.question(None, "Export complete", f"File saved:\n{path}\n\nOpen?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _on_process_notes(self) -> None:
        if not self._project or not self._project.slides:
            return

        # Check if already processed
        if self._project.state.notes_done:
            r = QMessageBox.question(self, "Re-process?",
                                     "Notes were already processed. Re-run?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes:
                return

        self._status.start("Notes")
        self._notes_btn.setEnabled(False)

        from PySide6.QtCore import QThread
        from video2pptx.gui.workers import NotesWorker

        self._notes_thread = QThread(self)
        self._notes_worker = NotesWorker(project=self._project)
        self._notes_worker.moveToThread(self._notes_thread)
        self._notes_worker.finished.connect(self._on_notes_finished)
        self._notes_worker.error.connect(self._on_notes_error)
        self._notes_worker.progress.connect(self._on_worker_progress_msg)
        self._notes_thread.started.connect(self._notes_worker.run)
        self._notes_thread.start()

    # START_BLOCK_QUICK_DETECT
    def _on_quick_detect(self) -> None:
        if self._project is None or not self._project.video:
            return
        if self._project.slides:
            r = QMessageBox.question(self, "Re-detect?",
                                     f"Project already has {len(self._project.slides)} slides.\n"
                                     "Re-run detection (overwrites screenshots)?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes:
                return

        self._status.start("Quick Detect")
        self._quick_detect_btn.setEnabled(False)
        self._detect_btn.setEnabled(False)
        logger.info("[GUI-Main][_on_quick_detect] Quick detect triggered")

        from PySide6.QtCore import QThread
        from video2pptx.gui.workers import QuickDetectWorker

        self._quick_detect_thread = QThread(self)
        self._quick_detect_worker = QuickDetectWorker(project=self._project)
        self._quick_detect_worker.moveToThread(self._quick_detect_thread)
        self._quick_detect_worker.finished.connect(self._on_detect_finished)
        self._quick_detect_worker.error.connect(self._on_detect_error)
        self._quick_detect_worker.progress.connect(self._on_worker_progress_msg)
        self._quick_detect_thread.started.connect(self._quick_detect_worker.run)
        self._quick_detect_thread.start()
    # END_BLOCK_QUICK_DETECT

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

    # START_BLOCK_MANUAL_SLIDES
    def _on_add_manual_slide(self, ts: float) -> None:
        if self._project is None:
            return
        from video2pptx.models import SlideSegment
        idx = len(self._project.slides) + 1
        new_slide = SlideSegment(
            index=idx,
            start=ts,
            end=ts + 5.0,
            duration=5.0,
            representative_timestamp=ts,
            image="",
            manual=True,
        )
        self._project.slides.append(new_slide)
        self._project.slides.sort(key=lambda s: s.start)
        # Reindex
        for i, s in enumerate(self._project.slides):
            s.index = i + 1
        save_project(self._project)
        self._timeline.set_slides(self._project.slides)
        self._timeline.set_project(self._project)
        self._timeline.zoom_fit()
        self.statusBar().showMessage(f"Manual slide added at {ts:.1f}s")

    def _on_set_slide_frame(self, slide_index: int) -> None:
        pos = slide_index - 1
        if not self._project or pos >= len(self._project.slides):
            return
        slide = self._project.slides[pos]
        pos_sec = self._video_player._player.position() / 1000.0
        try:
            from video2pptx.video_decode import VideoDecoder
            import cv2
            decoder = VideoDecoder(self._project.video, sample_fps=1.0)
            for vf in decoder.iter_frames():
                if vf.timestamp >= pos_sec:
                    img = cv2.cvtColor(vf.image, cv2.COLOR_RGB2BGR)
                    slides_dir = Path(self._project.output_dir) / "slides"
                    slides_dir.mkdir(parents=True, exist_ok=True)
                    fname = f"slide_{slide_index:03d}.png"
                    cv2.imwrite(str(slides_dir / fname), img)
                    slide.image = f"slides/{fname}"
                    save_project(self._project)
                    self._timeline.set_slides(self._project.slides)
                    self.statusBar().showMessage(f"Slide {slide_index} image set from {pos_sec:.1f}s")
                    break
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to capture frame: {e}")

    def _on_clear_slide_image(self, slide_index: int) -> None:
        pos = slide_index - 1
        if not self._project or pos >= len(self._project.slides):
            return
        self._project.slides[pos].image = ""
        save_project(self._project)
        self._timeline.set_slides(self._project.slides)
        self.statusBar().showMessage(f"Slide {slide_index} image cleared")

    def _on_delete_slide(self, slide_index: int) -> None:
        pos = slide_index - 1
        if not self._project or pos >= len(self._project.slides):
            return
        r = QMessageBox.question(self, "Delete Slide?",
                                 f"Delete slide #{slide_index}?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes:
            return
        del self._project.slides[pos]
        for i, s in enumerate(self._project.slides):
            s.index = i + 1
        save_project(self._project)
        self._timeline.set_slides(self._project.slides)
        self._timeline.set_project(self._project)
        self._timeline.zoom_fit()
        self.statusBar().showMessage(f"Slide {slide_index} deleted")

    def _on_add_marker_at_position(self) -> None:
        if self._project is None:
            QMessageBox.information(self, "Add Slide", "Open a project first")
            return
        ts = self._video_player._player.position() / 1000.0
        self._on_add_manual_slide(ts)
    # END_BLOCK_TIMELINE_MARKERS

    def _on_slide_moved(self, index: int, new_start: float, new_end: float) -> None:
        pos = index - 1
        if self._project and 0 <= pos < len(self._project.slides):
            s = self._project.slides[pos]
            s.start = new_start
            s.end = new_end
            s.duration = new_end - new_start
            save_project(self._project)
            self._project.slides.sort(key=lambda s: s.start)
            for i, s in enumerate(self._project.slides):
                s.index = i + 1
            # Defer rebuild to avoid destroying the item during its own event handler
            QTimer.singleShot(0, lambda: self._timeline.set_slides(self._project.slides))
            self.statusBar().showMessage(f"Slide {index} moved: {new_start:.1f}s – {new_end:.1f}s")

    def _on_slide_resized(self, index: int, new_start: float, new_end: float) -> None:
        pos = index - 1
        if self._project and 0 <= pos < len(self._project.slides):
            s = self._project.slides[pos]
            s.start = new_start
            s.end = new_end
            s.duration = new_end - new_start
            save_project(self._project)
            QTimer.singleShot(0, lambda: self._timeline.set_slides(self._project.slides))
            self.statusBar().showMessage(f"Slide {index} resized: {new_start:.1f}s – {new_end:.1f}s")

    def _on_open_subtitle_editor(self, slide_index: int) -> None:
        if not self._project or slide_index >= len(self._project.slides):
            return
        from video2pptx.gui.subtitle_editor import SubtitleEditorDialog

        slide = self._project.slides[slide_index]
        img_path = str(Path(self._project.output_dir) / slide.image) if slide.image else ""

        # Gather raw subtitle cues for this slide interval
        raw_cues: list[str] = []
        if self._subs is not None:
            for ev in self._subs.events:
                if ev.start >= slide.start * 1000 and ev.end <= slide.end * 1000:
                    text = ev.plaintext.strip()
                    if text:
                        raw_cues.append(text)

        dlg = SubtitleEditorDialog(
            slide_index=slide.index,
            start_sec=slide.start,
            end_sec=slide.end,
            image_path=img_path,
            transcript=slide.transcript or "",
            subtitle_cues=raw_cues,
            llm_config=self._project.llm,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            slide.transcript = dlg.transcript()
            desc = dlg.description()
            if desc.strip():
                slide.llm_description = desc.strip()
            save_project(self._project)
            self.statusBar().showMessage(f"Slide {slide_index} saved")

    # START_BLOCK_MARKER_ACTIONS
    def _on_open_marker_panel(self) -> None:
        if self._project is None:
            QMessageBox.information(self, "Markers", "Open a project first")
            return
        self.statusBar().showMessage(f"Slides: {len(self._project.slides)}")

    def _on_seek_to_marker(self, ts: float) -> None:
        player = self._video_player._player
        player.setPosition(int(ts * 1000))
        from PySide6.QtCore import QTimer
        player.play()
        QTimer.singleShot(10, player.pause)
        self.statusBar().showMessage(f"Seeked to {ts:.1f}s")

    def _on_open_timeline_image(self, path: str, slide_index: int = 0) -> None:
        if not path:
            self.statusBar().showMessage(f"Slide #{slide_index}: no image set")
            return
        if self._project:
            full = str(Path(self._project.output_dir) / path)
        else:
            full = path
        label = f"Slide #{slide_index}" if slide_index else ""
        self._video_player.show_slide_image(full, label)
        self.statusBar().showMessage(f"Slide #{slide_index}: {path}")
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

    def _on_worker_progress(self, pct: int) -> None:
        self._status.update(pct)

    def _on_worker_progress_msg(self, pct: int, msg: str) -> None:
        self._status.update(pct, msg)

    def _on_preview_finished(self, ts: list[float], scores: list[float], duration: float) -> None:
        self._quick_detect_thread.quit()

    def _on_detect_finished(self, path: str) -> None:
        self._status.finish(f"Detection complete: {path}")
        update_project_state(self._project, detect_done=True, slides_json=path)
        load_slides_into_project(self._project, force=True)
        # Set score waveform from slides.json
        if self._project.score_timestamps and self._project.score_values:
            self._timeline.set_scores(self._project.score_timestamps, self._project.score_values)
        if self._project.slides:
            dur = max(self._project.slides[-1].end, self._video_player.duration())
            self._timeline.set_slides(self._project.slides)
            self._timeline.set_video_duration(dur)
            self._timeline.set_markers(self._project.markers)
            self._timeline.set_subtitles(self._subs)
            self._timeline.set_project(self._project)
            self._timeline.zoom_fit()
        self._export_btn.setEnabled(bool(self._project.slides))
        self._notes_btn.setEnabled(bool(self._project.slides) and bool(self._project.subtitles))
        self._detect_thread.quit()

    def _on_detect_error(self, msg: str) -> None:
        self._status.finish(f"Detection failed: {msg}")
        QMessageBox.critical(self, "Detection Error", msg)
        self._detect_thread.quit()

    def _on_notes_finished(self, path: str) -> None:
        load_slides_into_project(self._project, force=True)
        self._status.finish(f"Notes processed: {len(self._project.slides)} slides")
        self._notes_btn.setEnabled(True)
        self._notes_thread.quit()

    def _on_notes_error(self, msg: str) -> None:
        self._status.finish(f"Notes failed: {msg}")
        self._notes_btn.setEnabled(True)
        self._notes_thread.quit()
