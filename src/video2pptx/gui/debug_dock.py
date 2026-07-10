# FILE: src/video2pptx/gui/debug_dock.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: QDockWidget with LogPanel (live logs) + StatePanel (Timeline→Track→Clip tree). Toggle via Ctrl+D.
#   SCOPE: LogPanel: color-coded QPlainTextEdit + level filter combo. StatePanel: QTreeWidget with Refresh btn.
#   DEPENDS: PySide6, M-GUI-LOG-BRIDGE, M-TIMELINE-MODEL, M-PROJECT-MODEL
#   LINKS: M-GUI-DEBUG-DOCK
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   DebugDock - QDockWidget with QTabWidget(LogPanel, StatePanel)
#   LogPanel - QWidget with color-coded log viewer + level filter
#   StatePanel - QWidget with QTreeWidget showing Timeline/Track/Clip
# END_MODULE_MAP

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class LogPanel(QWidget):
    """Live log viewer: color-coded QPlainTextEdit with level filter."""

    LEVEL_COLORS = {
        "DEBUG": "#808080",
        "INFO": "#c8c8c8",
        "WARNING": "#ffc832",
        "ERROR": "#ff5050",
        "CRITICAL": "#ff2828",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._filter = QComboBox()
        self._filter.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self._filter.currentTextChanged.connect(self._on_filter_changed)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.document().setMaximumBlockCount(5000)
        self._text.setStyleSheet("QTextEdit { background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas; font-size: 11px; }")

        layout.addWidget(self._filter)
        layout.addWidget(self._text)

    def append(self, level: str, time_str: str, message: str) -> None:
        if self._filter.currentText() != "ALL" and self._filter.currentText() != level:
            return
        self._text.append(f"[{level:7s}] [{time_str}] {message}")

    def _on_filter_changed(self, _text: str) -> None:
        self._text.clear()


class StatePanel(QWidget):
    """Tree view of Timeline → Track → Clip hierarchy."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._timeline = None
        self._project_model = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self.refresh)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Name", "Value"])
        self._tree.setStyleSheet("QTreeWidget { background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas; font-size: 11px; }")

        layout.addWidget(self._refresh_btn)
        layout.addWidget(self._tree)

    def set_targets(self, project_model, timeline) -> None:
        self._project_model = project_model
        self._timeline = timeline
        self.refresh()

    def refresh(self) -> None:
        self._tree.clear()
        if self._timeline is None:
            return

        root = QTreeWidgetItem(self._tree, ["Timeline", ""])
        dur_item = QTreeWidgetItem(root, ["duration", f"{self._timeline.duration:.1f}s"])
        root.addChild(dur_item)

        for name in self._timeline.track_names():
            track = self._timeline.track(name)
            if track is None:
                continue
            clips = track.clips()
            track_item = QTreeWidgetItem(root, [f'track("{name}")', f"{len(clips)} clips"])
            for clip in clips:
                cls = type(clip).__name__
                label = f"{cls} #{getattr(clip, 'index', '?')}" if cls == "SlideClip" else cls
                val = f"{clip.start_sec:.1f}s – {clip.end_sec:.1f}s"
                clip_item = QTreeWidgetItem(track_item, [label, val])
                track_item.addChild(clip_item)
            root.addChild(track_item)

        if self._project_model and hasattr(self._project_model, "project_data"):
            proj = self._project_model.project_data
            if proj:
                proj_item = QTreeWidgetItem(self._tree, ["Project", proj.name or ""])
                for key in ("video", "subtitles", "output_dir"):
                    val = getattr(proj, key, "") or ""
                    proj_item.addChild(QTreeWidgetItem(proj_item, [key, str(val)[:80]]))

        self._tree.expandAll()


class DebugDock(QDockWidget):
    """QDockWidget with LogPanel + StatePanel tabs. Toggle via Ctrl+D."""

    def __init__(self, project_model=None, timeline=None, parent: QWidget | None = None) -> None:
        super().__init__("Debug", parent)
        self.setObjectName("DebugDock")
        self.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        self._log_panel = LogPanel()
        self._state_panel = StatePanel()

        self._tabs = QTabWidget()
        self._tabs.addTab(self._log_panel, "Logs")
        self._tabs.addTab(self._state_panel, "State")
        self.setWidget(self._tabs)

        if project_model is not None or timeline is not None:
            self._state_panel.set_targets(project_model, timeline)

    def append_log(self, level: str, time_str: str, message: str) -> None:
        self._log_panel.append(level, time_str, message)

    def set_targets(self, project_model, timeline) -> None:
        self._state_panel.set_targets(project_model, timeline)
