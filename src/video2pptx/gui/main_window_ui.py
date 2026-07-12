# FILE: src/video2pptx/gui/main_window_ui.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Construct MainWindow widgets and host optional debug/MCP infrastructure.
#   SCOPE: Menu, toolbar, info row, video/timeline layout, signal wiring, debug dock, MCP timer.
#   DEPENDS: PySide6, M-GUI-MAIN, M-GUI-MENUBAR, M-GUI-VIDEOPLAYER, M-GUI-TIMELINE3
#   LINKS: M-GUI-WINDOW-UI, V-REF-GUI-ADAPTER
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   setup_main_window_ui - construct and connect MainWindow widgets
#   connect_main_window_signals - connect controllers, model projection, and menus
#   MainWindowHost - own optional debug dock and MCP server lifecycle
# END_MODULE_MAP

from __future__ import annotations

from loguru import logger
from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


def _show_about(window) -> None:
    from video2pptx.gui.about_dialog import show_about_dialog
    show_about_dialog(window)


def _open_logs() -> None:
    from video2pptx.gui.about_dialog import AboutDialog
    path = AboutDialog._log_dir()
    path.mkdir(parents=True, exist_ok=True)
    QDesktopServices.openUrl(path.as_uri())


def _open_github() -> None:
    from video2pptx.application.identity import application_identity
    QDesktopServices.openUrl(application_identity().repository_url)


def _on_check_updates(window) -> None:
    from video2pptx.gui.update_controller import UpdateController
    ctrl = UpdateController(window)
    ctrl.manual_check(window)


def setup_main_window_ui(window) -> None:
    """Build MainWindow's passive widgets and route their Qt signals."""
    from video2pptx.gui.menu_bar import MenuBarWidget
    from video2pptx.gui.timeline3 import TimelineWidget
    from video2pptx.gui.video_player import VideoPlayerWidget

    window.setWindowTitle("video2pptx")
    window.resize(1200, 800)
    window._menu_bar = MenuBarWidget(window)
    window.setMenuBar(window._menu_bar)
    toolbar = QToolBar("Project")
    window.addToolBar(toolbar)
    actions = (
        ("New Project", "", window._on_new_project),
        ("Open Project", "", window._on_open_project),
        (None, "", None),
        ("Import Video", "", window._on_import_video),
        ("Import Subtitles", "", window._on_import_srt),
        (None, "", None),
        ("Add Marker", "Add a manual slide at current video position (Ctrl+M)", window._on_add_marker_at_position),
        ("Slides", "Show slide info", window._on_open_marker_panel),
    )
    for text, tip, slot in actions:
        if text is None:
            toolbar.addSeparator()
            continue
        action = toolbar.addAction(text)
        action.setToolTip(tip)
        action.triggered.connect(slot)

    central = QWidget()
    window.setCentralWidget(central)
    main_layout = QVBoxLayout(central)
    main_layout.setContentsMargins(4, 4, 4, 4)
    info_row = QHBoxLayout()
    window._video_label = QLabel("Video: —")
    window._subs_label = QLabel("Subtitles: —")
    window._backend_label = QLabel("Backend: auto")

    def button(text, tip, slot):
        result = QPushButton(text)
        result.setToolTip(tip)
        result.setEnabled(False)
        result.clicked.connect(slot)
        return result

    window._btn_detect = button("Detect", "Detect slides via computer vision", window._on_detect)
    window._btn_quick_preview = button("Quick Preview", "Compute diff scores only", window._on_quick_detect)
    window._btn_auto_align = button("Auto Align", "Align boundaries to subtitles", window._on_auto_align)
    window._btn_auto = button("Auto", "Detect, align, notes, export, save", window._on_auto)
    window._btn_process_notes = button("Process Notes", "Process speaker notes", window._on_process_notes)
    window._btn_save = button("Save", "Save project changes", window._on_save_project)
    window._btn_export = QPushButton("Export")
    window._btn_export.setEnabled(False)
    window._export_menu = QMenu(window)
    window._export_menu.addAction("Export &Markdown (Marp)...", window._on_export_md)
    window._export_menu.addAction("Export &PPTX...", window._on_export_pptx)
    window._btn_export.setMenu(window._export_menu)
    window._PIPELINE_BUTTONS = [
        window._btn_quick_preview, window._btn_detect, window._btn_auto_align,
        window._btn_process_notes, window._btn_auto, window._btn_export,
    ]
    for widget in (window._video_label, window._subs_label, window._backend_label):
        info_row.addWidget(widget)
    info_row.addStretch()
    for widget in (
        window._btn_quick_preview, window._btn_detect, window._btn_auto_align,
        window._btn_process_notes, window._btn_auto, window._btn_export, window._btn_save,
    ):
        info_row.addWidget(widget)
    main_layout.addLayout(info_row)

    window._splitter = QSplitter(Qt.Orientation.Vertical)
    window._splitter.setChildrenCollapsible(False)
    video_container = QWidget()
    video_layout = QVBoxLayout(video_container)
    video_layout.setContentsMargins(0, 0, 0, 0)
    window._video_player = VideoPlayerWidget()
    window._video_player.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    video_layout.addWidget(window._video_player, stretch=1)
    window._timeline = TimelineWidget()
    window._splitter.addWidget(video_container)
    window._splitter.addWidget(window._timeline)
    window._splitter.setStretchFactor(0, 3)
    window._splitter.setStretchFactor(1, 2)
    main_layout.addWidget(window._splitter, stretch=1)
    window.statusBar().showMessage("Ready")
    window._show_backend_info()
    window._video_player.positionChanged.connect(window._on_video_position_changed)
    window._video_player.durationChanged.connect(window._on_video_duration_changed)
    timeline_routes = (
        ("add_manual_slide", window._on_add_manual_slide),
        ("set_slide_frame", window._on_set_slide_frame),
        ("clear_slide_image", window._on_clear_slide_image),
        ("delete_slide", window._on_delete_slide),
        ("seek_requested", window._on_seek_to_marker),
        ("open_image", window._on_open_timeline_image),
        ("slide_moved", window._on_slide_moved),
        ("slide_resized", window._on_slide_resized),
        ("open_subtitle_editor", window._on_open_subtitle_editor),
    )
    for signal_name, slot in timeline_routes:
        getattr(window._timeline, signal_name).connect(slot)
    window._shortcut_add_marker = QShortcut(QKeySequence("Ctrl+M"), window)
    window._shortcut_add_marker.activated.connect(window._on_add_marker_at_position)


def connect_main_window_signals(window) -> None:
    """Connect passive UI routing after all widgets and controllers exist."""
    def slides_changed() -> None:
        if window._model.output_dir == window._project_ctrl.project_dir:
            window._project_ctrl.reload(emit=False)
        window._on_model_slides_changed()
        project = window._model.project_data
        window._btn_auto_align.setEnabled(
            bool(project and project.slides and project.subtitles and project.state.detect_done)
        )

    def legacy_project_opened() -> None:
        if not window._syncing_projection and window._model.output_dir:
            window._project_ctrl.open(window._model.output_dir)

    pipeline = window._pipeline_ctrl
    pipeline.progress.connect(window._on_worker_progress_msg)
    pipeline.stageFinished.connect(window._on_pipeline_finished)
    pipeline.error.connect(window._on_pipeline_error)
    pipeline.busyChanged.connect(window._on_busy_changed)
    pipeline.operationRejected.connect(window._on_operation_rejected)
    window._project_ctrl.projectOpened.connect(window._on_project_opened)
    window._project_ctrl.errorOccurred.connect(window._on_project_ctrl_error)
    window._timeline_ctrl.slidesChanged.connect(slides_changed)
    window._timeline_ctrl.errorOccurred.connect(
        lambda message: window._on_project_ctrl_error(message)
    )
    model = window._model
    model.slidesChanged.connect(slides_changed)
    model.projectOpened.connect(legacy_project_opened)
    model.subtitlesChanged.connect(window._on_model_subtitles_changed)
    model.videoChanged.connect(window._on_model_video_changed)
    model.projectClosed.connect(window._reset_ui)
    model.scoresChanged.connect(
        lambda: window._timeline.set_scores(model.score_timestamps, model.score_values)
        if model.score_timestamps and model.score_values
        else window._timeline.clear_scores()
    )
    menu = window._menu_bar
    routes = (
        (menu.act_new_project.triggered, window._on_new_project),
        (menu.act_open_project.triggered, window._on_open_project),
        (menu.act_close_project.triggered, window._on_close_project),
        (menu.act_save_project.triggered, window._on_save_project),
        (menu.act_import_video.triggered, window._on_import_video),
        (menu.act_import_srt.triggered, window._on_import_srt),
        (menu.act_exit.triggered, window.close),
        (menu.act_export_md.triggered, window._on_export_md),
        (menu.act_export_pptx.triggered, window._on_export_pptx),
        (menu.act_process_notes.triggered, window._on_process_notes),
        (menu.act_project_settings.triggered, window._on_project_settings),
        (menu.act_app_settings.triggered, window._on_app_settings),
    )
    for signal, slot in routes:
        signal.connect(slot)
    menu.open_recent_project.connect(window._on_open_recent_project)
    window._refresh_recent_projects()

    # Help menu
    menu.show_about.connect(lambda: _show_about(window))
    menu.open_logs.connect(lambda: _open_logs())
    menu.open_github.connect(lambda: _open_github())
    menu.check_updates.connect(lambda: _on_check_updates(window))


class MainWindowHost(QObject):
    """Own optional debug and MCP infrastructure outside MainWindow adapter logic."""

    def __init__(self, window, model) -> None:
        super().__init__(window)
        self._window = window
        self._model = model
        self.active = False
        self._mcp = None
        self._timer = None

    def start(self) -> None:
        self._setup_debug_dock()
        self._setup_mcp_server()

    def _setup_debug_dock(self) -> None:
        try:
            from video2pptx.gui.debug_dock import DebugDock
            from video2pptx.gui.log_bridge import LogBridge
            dock = DebugDock()
            self._window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
            dock.hide()
            LogBridge.instance().newLog.connect(dock.append_log)
            QShortcut(QKeySequence("Ctrl+D"), self._window).activated.connect(dock.toggleViewAction().trigger)
            self._debug_dock = dock
        except Exception:
            logger.debug("[MainWindowHost][_setup_debug_dock] Debug dock unavailable")

    def _setup_mcp_server(self) -> None:
        try:
            from video2pptx.debug.mcp_server import McpServer
            self._mcp = McpServer(self._model, self._model.timeline, port=9812, main_window=self._window)
            self._mcp.start()
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._process_mcp_queue)
            self._timer.start(50)
        except Exception as exc:
            logger.warning("[MainWindowHost][_setup_mcp_server] MCP unavailable: {}", exc)

    def _process_mcp_queue(self) -> None:
        from video2pptx.debug.mcp_server import mcp_process_queue
        self.active = True
        try:
            mcp_process_queue(self._model, self._window)
        finally:
            self.active = False
