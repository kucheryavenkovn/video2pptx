# FILE: src/video2pptx/gui/main_window.py
# VERSION: 0.4.1
# START_MODULE_CONTRACT
#   PURPOSE: Main GUI window — QMainWindow with menu bar, video player, subtitle overlay, always-visible timeline, marker panel, project lifecycle, detection
#   SCOPE: Integrate MenuBarWidget, VideoPlayerWidget, TimelineV2Widget, MarkerPanel, SettingsProjectDialog, SettingsAppDialog, MarkerManager
#   DEPENDS: PySide6, M-PROJECT-MODEL, M-PROJECT, M-GUI-MENUBAR, M-GUI-VIDEOPLAYER, M-GUI-TIMELINE-V2, M-GUI-SETTINGS-PROJECT, M-GUI-SETTINGS-APP, M-GUI-SMART-SNAP, M-GUI-MARKER-MANAGER, M-GUI-MARKER-PANEL, M-GUI-WORKER
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
#   LAST_CHANGE: v0.4.1 - Reset Auto and Auto Align controls when a project closes
#   v0.4.0 - Refactor to use ProjectModel (QObject with signals) instead of Project (Pydantic data bag)
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
from video2pptx.debug.action_registry import mcp_action
from video2pptx.gui.app_config import add_recent_project, load_app_config, save_app_config
from video2pptx.gui.status_manager import StatusBarManager
from video2pptx.project_model import ProjectModel


class MainWindow(QMainWindow):
    # START_CONTRACT: MainWindow
    #   PURPOSE: Main application window integrating all GUI modules for slide detection workflow
    #   INPUTS: none (creates empty window)
    #   OUTPUTS: none (Qt event loop)
    #   SIDE_EFFECTS: creates GUI window, starts event loop, connects all subcomponents
    #   LINKS: M-GUI-MAIN
    # END_CONTRACT: MainWindow

    project_changed = Signal(object)  # Project (legacy, kept for MCP)

    def __init__(self) -> None:
        super().__init__()
        from video2pptx.bootstrap.application import ApplicationServices
        self._app_svcs = ApplicationServices()
        self._model = ProjectModel(self)
        from video2pptx.gui.controllers import (
            PipelineController,
            ProjectController,
            TimelineController,
        )
        self._project_ctrl = ProjectController(services=self._app_svcs, parent=self)
        self._pipeline_ctrl = PipelineController(services=self._app_svcs, parent=self)
        self._timeline_ctrl = TimelineController(services=self._app_svcs, parent=self)
        self._mcp_active: bool = False
        self._subs: pysubs2.SSAFile | None = None
        self._app_config = load_app_config()
        self._status = StatusBarManager(self)
        self._setup_ui()
        self._connect_controller_signals()
        self._connect_model_signals()
        self._connect_menu_signals()
        self._setup_debug_dock()
        self._setup_mcp_server()
        self._try_restore_last_project()

    def _connect_controller_signals(self) -> None:
        pc, pp, tm = self._pipeline_ctrl, self._project_ctrl, self._timeline_ctrl
        pc.progress.connect(self._on_worker_progress_msg)
        pc.stageFinished.connect(self._on_pipeline_finished)
        pc.error.connect(self._on_pipeline_error)
        pp.projectOpened.connect(self._on_project_opened)
        pp.errorOccurred.connect(self._on_project_ctrl_error)
        tm.slidesChanged.connect(self._on_model_slides_changed)
        tm.errorOccurred.connect(lambda m: QMessageBox.critical(self, "Timeline Error", m))

    # START_BLOCK_MODEL_SIGNALS
    def _connect_model_signals(self) -> None:
        m = self._model
        m.slidesChanged.connect(self._on_model_slides_changed)
        m.subtitlesChanged.connect(lambda: (
            self._load_subs_from_model(),
            self._timeline.set_subtitles(self._subs),
            self._subs_label.setText(f"Subtitles: {Path(m.project_data.subtitles).name}" if m.project_data and m.project_data.subtitles else "Subtitles: —"),
        ))
        m.videoChanged.connect(lambda p: (
            self._video_label.setText(f"Video: {Path(p).name}" if p else "Video: —"),
            self._video_player.load_video(p) if p else None,
            setattr(self._btn_detect, 'enabled', bool(p)),
            setattr(self._btn_quick_preview, 'enabled', bool(p)),
        ))
        m.projectClosed.connect(self._reset_ui)
        m.scoresChanged.connect(lambda: (
            self._timeline.set_scores(m.score_timestamps, m.score_values) if m.score_timestamps and m.score_values else self._timeline.clear_scores(),
        ))

    def _on_model_slides_changed(self) -> None:
        proj = self._model.project_data
        if proj and proj.slides:
            self._timeline.set_slides(proj.slides)
            self._timeline.set_video_duration(max(proj.slides[-1].end, self._video_player.duration()))
            self._timeline.set_project(proj)
            self._timeline.zoom_fit()
        has = bool(proj and proj.slides)
        self._btn_export.setEnabled(has)
        self._btn_process_notes.setEnabled(has and bool(proj and proj.subtitles))

    def _reset_ui(self) -> None:
        self._video_player.clear_video()
        self._video_player.set_subtitle_text(None)
        self._subs = None
        self._timeline.set_subtitles(None)
        self._timeline.set_slides([])
        self._timeline.set_markers([])
        self._timeline.clear_scores()
        for lbl, txt in ((self._video_label, "Video: —"), (self._subs_label, "Subtitles: —")):
            lbl.setText(txt)
        for btn in (self._btn_detect, self._btn_quick_preview, self._btn_auto, self._btn_auto_align, self._btn_export, self._btn_process_notes, self._btn_save):
            btn.setEnabled(False)
        self.setWindowTitle("video2pptx")
        self.statusBar().showMessage("Project closed")
    # END_BLOCK_MODEL_SIGNALS

    # START_BLOCK_SETUP_UI
    def _setup_ui(self) -> None:
        self.setWindowTitle("video2pptx")
        self.resize(1200, 800)

        # --- Menu bar ---
        from video2pptx.gui.menu_bar import MenuBarWidget
        self._menu_bar = MenuBarWidget(self)
        self.setMenuBar(self._menu_bar)

        toolbar = QToolBar("Project")
        self.addToolBar(toolbar)
        for text, tip, slot in (
            ("New Project", "", self._on_new_project), ("Open Project", "", self._on_open_project),
            ("---", "", None), ("Import Video", "", self._on_import_video),
            ("Import Subtitles", "", self._on_import_srt), ("---", "", None),
            ("Add Marker", "Add a manual slide at current video position (Ctrl+M)", self._on_add_marker_at_position),
            ("Slides", "Show slide info", self._on_open_marker_panel),
        ):
            if text == "---":
                toolbar.addSeparator()
            else:
                a = toolbar.addAction(text)
                if tip:
                    a.setToolTip(tip)
                if slot:
                    a.triggered.connect(slot)
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
        def _mkbtn(n, tip, slot):
            b = QPushButton(n)
            b.setToolTip(tip)
            b.setEnabled(False)
            b.clicked.connect(slot)
            return b
        self._btn_detect = _mkbtn("Detect", "Detect slides via computer vision — CV only, no align/notes/export", self._on_detect)
        self._btn_quick_preview = _mkbtn("Quick Preview", "Quick preview: compute diff scores only, no slides created", self._on_quick_detect)
        self._btn_auto_align = _mkbtn("Auto Align", "Align visual boundaries to subtitle anchors", self._on_auto_align)
        self._btn_auto = _mkbtn("Auto", "Full pipeline: Detect → Align → Notes → Export → Save", self._on_auto)
        self._btn_process_notes = _mkbtn("Process Notes", "Process subtitles into cleaned speaker notes", self._on_process_notes)
        self._btn_save = _mkbtn("Save", "Save project changes", self._on_save_project)
        self._btn_export = QPushButton("Export")
        self._btn_export.setToolTip("Export to Markdown or PPTX")
        self._btn_export.setEnabled(False)
        self._export_menu = QMenu(self)
        self._export_menu.addAction("Export &Markdown (Marp)...", self._on_export_md)
        self._export_menu.addAction("Export &PPTX...", self._on_export_pptx)
        self._btn_export.setMenu(self._export_menu)

        info_row.addWidget(self._video_label)
        info_row.addWidget(self._subs_label)
        info_row.addWidget(self._backend_label)
        info_row.addStretch()
        info_row.addWidget(self._btn_quick_preview)
        info_row.addWidget(self._btn_detect)
        info_row.addWidget(self._btn_auto_align)
        info_row.addWidget(QLabel("  "))
        info_row.addWidget(self._btn_process_notes)
        info_row.addWidget(self._btn_auto)
        info_row.addWidget(self._btn_export)
        info_row.addWidget(self._btn_save)
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

        tl = self._timeline
        for sig, slot in (
            (tl.add_manual_slide, self._on_add_manual_slide), (tl.set_slide_frame, self._on_set_slide_frame),
            (tl.clear_slide_image, self._on_clear_slide_image), (tl.delete_slide, self._on_delete_slide),
            (tl.seek_requested, self._on_seek_to_marker), (tl.open_image, self._on_open_timeline_image),
            (tl.slide_moved, self._on_slide_moved), (tl.slide_resized, self._on_slide_resized),
            (tl.open_subtitle_editor, self._on_open_subtitle_editor),
        ):
            sig.connect(slot)

        # Keyboard shortcuts
        self._shortcut_add_marker = QShortcut(QKeySequence("Ctrl+M"), self)
        self._shortcut_add_marker.activated.connect(self._on_add_marker_at_position)

    def _setup_debug_dock(self) -> None:
        try:
            from video2pptx.gui.debug_dock import DebugDock
            from video2pptx.gui.log_bridge import LogBridge
            lb = LogBridge.instance()
            self._debug_dock = DebugDock()
            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._debug_dock)
            self._debug_dock.hide()
            lb.newLog.connect(self._debug_dock.append_log)
            QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(self._debug_dock.toggleViewAction().trigger)
        except Exception:
            logger.debug("[GUI-Main][_setup_debug_dock] Debug dock not available")

    def _setup_mcp_server(self) -> None:
        self._mcp = self._mcp_timer = None
        try:
            from video2pptx.debug.action_registry import ActionRegistry
            from video2pptx.debug.mcp_server import McpServer
            self._mcp = McpServer(self._model, self._model.timeline, port=9812, action_registry=ActionRegistry(self), main_window=self)
            self._mcp.start()
            self._mcp_timer = QTimer(self)
            self._mcp_timer.timeout.connect(self._process_mcp_queue)
            self._mcp_timer.start(50)
        except Exception as e:
            logger.warning(f"[GUI-Main][_setup_mcp_server] MCP server not available: {e}")

    def _process_mcp_queue(self) -> None:
        from video2pptx.debug.mcp_server import _ACTION_QUEUE, _CMD_QUEUE, mcp_process_queue
        qc, qa = _CMD_QUEUE.qsize(), _ACTION_QUEUE.qsize()
        if qc or qa:
            logger.debug(f"[GUI-Main][_process_mcp_queue] Processing | cmd_queue={qc} action_queue={qa}")
        self._mcp_active = True
        try:
            mcp_process_queue(self._model)
        finally:
            self._mcp_active = False

    def _confirm(self, title: str, text: str) -> bool:
        return self._mcp_active or QMessageBox.question(self, title, text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def _connect_menu_signals(self) -> None:
        mb = self._menu_bar
        for sig, slot in (
            (mb.act_new_project.triggered, self._on_new_project),
            (mb.act_open_project.triggered, self._on_open_project),
            (mb.act_close_project.triggered, self._on_close_project),
            (mb.act_save_project.triggered, self._on_save_project),
            (mb.act_import_video.triggered, self._on_import_video),
            (mb.act_import_srt.triggered, self._on_import_srt),
            (mb.act_exit.triggered, self.close),
            (mb.act_export_md.triggered, self._on_export_md),
            (mb.act_export_pptx.triggered, self._on_export_pptx),
            (mb.act_process_notes.triggered, self._on_process_notes),
            (mb.act_project_settings.triggered, self._on_project_settings),
            (mb.act_app_settings.triggered, self._on_app_settings),
        ):
            sig.connect(slot)
        mb.open_recent_project.connect(self._on_open_recent_project)
        self._refresh_recent_projects()

    # END_BLOCK_SETUP_UI

    # START_BLOCK_RECENT_PROJECTS
    def _refresh_recent_projects(self) -> None:
        self._app_config = load_app_config()
        self._menu_bar.set_recent_projects(self._app_config.recent_projects)
    # END_BLOCK_RECENT_PROJECTS

    def _on_video_position_changed(self, s: float) -> None:
        self._video_player.set_subtitle_text(self._get_subtitle_at(s))
        self._video_player.hide_slide_image()
        self._timeline.set_position(s)

    def _on_video_duration_changed(self, s: float) -> None:
        if s > 0:
            self._timeline.set_video_duration(s)
            proj = self._model.project_data
            if proj and proj.slides:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(100, self._timeline.zoom_fit)

    def _get_subtitle_at(self, s: float) -> str | None:
        if self._subs is None:
            return None
        ms = int(s * 1000)
        for ev in self._subs.events:
            if ev.start <= ms < ev.end and ev.plaintext.strip():
                return ev.plaintext.strip()
        return None

    def _load_subs_from_model(self) -> None:
        proj = self._model.project_data
        self._subs = None
        if proj and proj.subtitles:
            p = Path(proj.subtitles)
            if p.is_file():
                try:
                    self._subs = pysubs2.load(str(p), encoding="utf-8")
                except Exception:
                    pass

    # START_BLOCK_PROJECT_LIFECYCLE
    def _on_new_project(self) -> None:
        proj_dir = QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if not proj_dir:
            return
        import os
        folder_name = os.path.basename(os.path.normpath(proj_dir))
        parent_dir = str(Path(proj_dir).parent)
        self._project_ctrl.create(parent_dir, folder_name)
        if self._project_ctrl.project_dir:
            self._model.open(self._project_ctrl.project_dir)

    def _on_open_project(self) -> None:
        proj_dir = QFileDialog.getExistingDirectory(self, "Open Project Directory")
        if not proj_dir:
            return
        self._project_ctrl.open(proj_dir)
        if self._project_ctrl.project_dir:
            self._model.open(self._project_ctrl.project_dir)

    def _on_open_recent_project(self, path: str) -> None:
        proj_dir = Path(path).resolve()
        if not proj_dir.is_dir():
            QMessageBox.critical(self, "Error", f"Project directory not found:\n{path}")
            if path in self._app_config.recent_projects:
                self._app_config.recent_projects.remove(path)
                save_app_config(self._app_config)
            self._refresh_recent_projects()
            return
        self._project_ctrl.open(str(proj_dir))
        if self._project_ctrl.project_dir:
            self._model.open(self._project_ctrl.project_dir)

    def _on_project_opened(self) -> None:
        proj = self._model.project_data
        if proj is None:
            return
        self._video_label.setText(f"Video: {Path(proj.video).name}" if proj.video else "Video: —")
        if proj.video:
            self._video_player.load_video(proj.video)
        self._load_subs_from_model()
        self._subs_label.setText(f"Subtitles: {Path(proj.subtitles).name}" if proj.subtitles else "Subtitles: —")
        self._btn_detect.setEnabled(bool(proj.video))
        self._btn_quick_preview.setEnabled(bool(proj.video))
        self._btn_auto.setEnabled(bool(proj.video))
        has_slides = bool(proj.slides)
        self._btn_export.setEnabled(has_slides)
        self._btn_process_notes.setEnabled(has_slides and bool(proj.subtitles))
        self._btn_auto_align.setEnabled(has_slides and bool(proj.subtitles) and getattr(proj.state, 'detect_done', False))
        self._btn_save.setEnabled(True)
        self.setWindowTitle(f"video2pptx — {proj.name}")
        dur = max(getattr(proj, "video_duration", 0) or 0, proj.slides[-1].end if proj.slides else 0)
        if proj.slides:
            self._timeline.set_slides(proj.slides)
        self._timeline.set_video_duration(dur)
        self._timeline.set_subtitles(self._subs)
        self._timeline.set_project(proj)
        if proj.score_timestamps and proj.score_values:
            self._timeline.set_scores(proj.score_timestamps, proj.score_values)
        self.project_changed.emit(proj)
        d = self._model.output_dir or getattr(proj, "project_dir", "")
        if d:
            self._app_config = add_recent_project(d, self._app_config)
            save_app_config(self._app_config)
            self._menu_bar.set_recent_projects(self._app_config.recent_projects)
        logger.info("[GUI-Main][_on_project_opened] Project loaded | name={}", proj.name)

    def _on_close_project(self) -> None:
        if self._model.is_open:
            self._project_ctrl.close()
            self._model.close()

    def _on_save_project(self) -> None:
        self._project_ctrl.save()
        if self._project_ctrl.revision:
            self.statusBar().showMessage("Project saved")

    def _on_import_video(self) -> None:
        if not self._model.is_open:
            return
        p, _ = QFileDialog.getOpenFileName(self, "Import Video", "", "Video Files (*.mp4 *.mkv *.mov *.webm);;All Files (*)")
        if not p:
            return
        try:
            self._model.import_video(p)
            m = self._model.project_data
            if m and m.subtitles:
                self._load_subs_from_model()
                self._subs_label.setText(f"Subtitles: {Path(m.subtitles).name}")
                self._timeline.set_subtitles(self._subs)
            self.statusBar().showMessage(f"Video imported, subs auto-detected: {Path(m.subtitles).name}" if m and m.subtitles else f"Video imported: {Path(p).name}")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_import_srt(self) -> None:
        if not self._model.is_open:
            return
        p, _ = QFileDialog.getOpenFileName(self, "Import Subtitles", "", "Subtitle Files (*.srt *.vtt);;All Files (*)")
        if not p:
            return
        try:
            self._model.load_subtitles(p)
            self.statusBar().showMessage(f"Subtitles imported: {Path(p).name}")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Error", str(e))

    # START_BLOCK_PROJECT_RESTORE
    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        try:
            cfg = load_app_config()
            cfg.last_project_path = self._model.output_dir
            save_app_config(cfg)
        except Exception:
            pass
        self._project_ctrl.close()
        self._model.close()
        super().closeEvent(event)

    def _try_restore_last_project(self) -> None:
        try:
            cfg = load_app_config()
            if cfg.restore_last_project and cfg.last_project_path and (Path(cfg.last_project_path) / "project.json").is_file():
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._do_restore_project(str(cfg.last_project_path)))
        except Exception:
            pass

    def _do_restore_project(self, project_path: str) -> None:
        import os
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            return
        try:
            r = QMessageBox.question(self, "Restore", f"Open previous project?\n\n{Path(project_path).name}", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if r == QMessageBox.StandardButton.Yes:
                self._model.open(project_path)
        except Exception:
            pass
    # END_BLOCK_PROJECT_RESTORE

    # START_BLOCK_PIPELINE
    def _run_pipeline(self, stage: str, **params) -> None:
        proj = self._model.project_data
        if not proj:
            return
        project_dir = self._project_ctrl.project_dir or proj.output_dir
        if not project_dir:
            return
        self._status.start(stage.capitalize())
        getattr(self._pipeline_ctrl, f"run_{stage}")(project_dir, **params)

    def _on_pipeline_finished(self, result) -> None:
        self._status.finish(f"{result.stage.capitalize()} complete")
        self._model.refresh_from_disk()
        if result.stage in ("detect", "preview"):
            proj = self._model.project_data
            if proj:
                self._btn_auto_align.setEnabled(bool(proj.subtitles) and bool(proj.slides))
        if result.stage in ("export",):
            out = result.data.get("output_path", "")
            if out:
                self._offer_open_file(Path(out))

    def _on_pipeline_error(self, msg: str) -> None:
        self._status.finish(f"Pipeline failed: {msg}")
        QMessageBox.critical(self, "Error", msg)

    @mcp_action(name='detect', desc='Run full slide detection')
    def _on_detect(self) -> None:
        proj = self._model.project_data
        if not proj:
            return
        if proj.slides and not self._confirm("Re-detect?", "Overwrite slides.json and screenshots?"):
            return
        self._run_pipeline("detect", video_path=proj.video or "")

    @mcp_action(name='detect_quick', desc='Run quick preview')
    def _on_quick_detect(self) -> None:
        proj = self._model.project_data
        if not proj:
            return
        if proj.slides and not self._confirm("Re-run?", "Overwrite slides?"):
            return
        self._run_pipeline("preview", video_path=proj.video or "")

    @mcp_action(name='notes', desc='Process speaker notes')
    def _on_process_notes(self) -> None:
        proj = self._model.project_data
        if not proj:
            return
        if proj.state.notes_done and not self._confirm("Re-process?", "Notes already processed."):
            return
        self._btn_process_notes.setEnabled(False)
        self._run_pipeline("notes", subtitles_path=proj.subtitles or "")

    def _on_auto_align(self) -> None:
        proj = self._model.project_data
        if not proj:
            return
        self._run_pipeline("align", subtitles_path=proj.subtitles or "")

    def _on_auto(self) -> None:
        proj = self._model.project_data
        if not proj or not proj.video:
            return
        self._run_pipeline("auto", video_path=proj.video, subtitles_path=proj.subtitles or "")

    @mcp_action(name='export_md', desc='Export to Markdown')
    def _on_export_md(self) -> None:
        proj = self._model.project_data
        if not proj:
            return
        out = Path(proj.output_dir) / "deck.md"
        if out.exists() and not self._confirm("Overwrite?", f"{out.name} already exists."):
            return
        self._run_pipeline("export", format="markdown", output_path=str(out))

    @mcp_action(name='export_pptx', desc='Export to PPTX')
    def _on_export_pptx(self) -> None:
        proj = self._model.project_data
        if not proj:
            return
        out = Path(proj.output_dir) / "deck.pptx"
        if out.exists() and not self._confirm("Overwrite?", f"{out.name} already exists."):
            return
        self._run_pipeline("export", format="pptx", output_path=str(out))

    @mcp_action(name='add_marker', desc='Add marker at current position')
    def _on_add_marker_at_position(self) -> None:
        if not self._model.is_open:
            QMessageBox.information(self, "Add Slide", "Open a project first")
            return
        ts = self._video_player._player.position() / 1000.0
        self._on_add_manual_slide(ts)
    # END_BLOCK_PIPELINE

    @staticmethod
    def _offer_open_file(path: Path) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        r = QMessageBox.question(None, "Export complete", f"File saved:\n{path}\n\nOpen?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _on_project_ctrl_error(self, msg: str) -> None:
        QMessageBox.critical(self, "Error", msg)
    # END_BLOCK_PIPELINE_EXPORT

    # START_BLOCK_SETTINGS_MENU
    def _on_project_settings(self) -> None:
        proj = self._model.project_data
        if proj is None:
            QMessageBox.information(self, "Project Settings", "Open a project first")
            return
        from video2pptx.gui.settings_project import ProjectSettingsDialog
        dlg = ProjectSettingsDialog(proj, self, frame_grabber=self._grab_current_frame)
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
    def _project_dir(self):
        return self._project_ctrl.project_dir or (self._model.output_dir if self._model.is_open else None)

    def _with_timeline(self, action: str, *a, msg="", confirm="", **kw):
        d = self._project_dir()
        if not d:
            return
        if confirm and not self._confirm("Confirm", confirm):
            return
        getattr(self._timeline_ctrl, action)(d, *a, **kw)
        self._model.refresh_from_disk()
        self._sync_timeline()
        if msg:
            self.statusBar().showMessage(msg)

    @mcp_action(name='slide_add_ui', desc='Add manual slide at timestamp')
    def _on_add_manual_slide(self, ts: float) -> None:
        self._with_timeline("add_slide", ts, msg=f"Manual slide added at {ts:.1f}s")

    @mcp_action(name='slide_set_frame', desc='Capture frame as slide image')
    def _on_set_slide_frame(self, slide_index: int) -> None:
        d = self._project_dir()
        if not d:
            return
        pos_sec = self._video_player._player.position() / 1000.0
        try:
            import cv2
            proj = self._model.project_data
            if not proj:
                return
            from video2pptx.video_decode import VideoDecoder
            decoder = VideoDecoder(proj.video, sample_fps=1.0)
            for vf in decoder.iter_frames():
                if vf.timestamp >= pos_sec:
                    img = cv2.cvtColor(vf.image, cv2.COLOR_RGB2BGR)
                    (Path(d) / "slides").mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(Path(d) / "slides" / f"slide_{slide_index:03d}.png"), img)
                    self._timeline_ctrl.clear_slide_image(d, slide_index)
                    self._model.refresh_from_disk()
                    self._sync_timeline()
                    self.statusBar().showMessage(f"Slide {slide_index} image set from {pos_sec:.1f}s")
                    break
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to capture frame: {e}")

    @mcp_action(name='slide_clear_image', desc='Clear slide image')
    def _on_clear_slide_image(self, slide_index: int) -> None:
        self._with_timeline("clear_slide_image", slide_index, msg=f"Slide {slide_index} image cleared")

    @mcp_action(name='slide_delete_ui', desc='Delete slide by index')
    def _on_delete_slide(self, slide_index: int) -> None:
        self._with_timeline("delete_slide", slide_index, msg=f"Slide {slide_index} deleted", confirm=f"Delete slide #{slide_index}?")

    @mcp_action(name='slide_moved', desc='Move slide to new start/end')
    def _on_slide_moved(self, index: int, new_start: float, new_end: float) -> None:
        d = self._project_dir()
        if not d:
            return
        self._timeline_ctrl.move_slide(d, index, new_start, new_end)
        self._model.refresh_from_disk()
        QTimer.singleShot(0, self._sync_timeline)
        self.statusBar().showMessage(f"Slide {index} moved: {new_start:.1f}s – {new_end:.1f}s")

    @mcp_action(name='slide_resize', desc='Resize slide interval')
    def _on_slide_resized(self, index: int, new_start: float, new_end: float) -> None:
        d = self._project_dir()
        if not d:
            return
        self._timeline_ctrl.resize_slide(d, index, new_end)
        self._model.refresh_from_disk()
        QTimer.singleShot(0, self._sync_timeline)
        self.statusBar().showMessage(f"Slide {index} resized: {new_start:.1f}s – {new_end:.1f}s")

    @mcp_action(name='edit_subtitles', desc='Open subtitle editor')
    def _on_open_subtitle_editor(self, slide_index: int) -> None:
        proj = self._model.project_data
        if not proj or slide_index >= len(proj.slides):
            return
        from video2pptx.gui.controllers.subtitle_editor_handler import open_subtitle_editor
        if open_subtitle_editor(proj.slides[slide_index], self._subs, self._model.output_dir or "", self):
            self._project_ctrl.save()
            self.statusBar().showMessage(f"Slide {slide_index} saved")
    # END_BLOCK_TIMELINE_MARKERS

    def _sync_timeline(self) -> None:
        proj = self._model.project_data
        if proj:
            if proj.slides:
                self._timeline.set_slides(proj.slides)
                self._timeline.set_project(proj)
            self._timeline.set_subtitles(self._subs)
            self._timeline.zoom_fit()

    @mcp_action(name='seek', desc='Seek video to position')
    def _on_seek_to_marker(self, ts: float) -> None:
        self._video_player._player.pause()
        self._video_player._player.setPosition(int(ts * 1000))
        self.statusBar().showMessage(f"Seeked to {ts:.1f}s")

    @mcp_action(name='slide_show_image', desc='Show slide image')
    def _on_open_timeline_image(self, path: str, slide_index: int = 0) -> None:
        if not path:
            self.statusBar().showMessage(f"Slide #{slide_index}: no image set")
            return
        full = str(Path(self._model.output_dir) / path) if self._model.project_data else path
        self._video_player.show_slide_image(full, f"Slide #{slide_index}" if slide_index else "")
        self.statusBar().showMessage(f"Slide #{slide_index}: {path}")

    @mcp_action(name='marker_panel', desc='Open marker panel')
    def _on_open_marker_panel(self) -> None:
        proj = self._model.project_data
        if not proj:
            QMessageBox.information(self, "Markers", "Open a project first")
            return
        self.statusBar().showMessage(f"Slides: {len(proj.slides)}")

    def _show_backend_info(self) -> None:
        try:
            avail = [n for n, i in BACKENDS.items() if i["available"]]
            self._backend_label.setText(f"Backend: {', '.join(avail) if avail else 'none'}")
        except Exception:
            self._backend_label.setText("Backend: auto")

    def project(self):
        return self._model.project_data

    def _on_worker_progress_msg(self, pct: int, msg: str) -> None:
        self._status.update(pct, msg)
