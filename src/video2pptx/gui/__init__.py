# FILE: src/video2pptx/gui/__init__.py
# VERSION: 0.3.0
# START_MODULE_CONTRACT
#   PURPOSE: GUI package for video2pptx desktop application
#   SCOPE: Package marker — exports MainWindow, SettingsDialog, TimelineWidget (V3), TimelineV2 legacy
#   DEPENDS: PySide6
#   LINKS: M-GUI-MAIN, M-GUI-TIMELINE, M-GUI-SETTINGS, M-GUI-WORKER, M-GUI-ROI-SELECTOR, M-GUI-MARKER-PANEL, M-GUI-TIMELINE3
#   ROLE: BARREL
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   MainWindow - main application window
#   SettingsDialog - settings dialog with tabs
#   TimelineWidget, TimelinePanel, SubtitlePanel - timeline components (legacy)
#   DetectWorker, NotesWorker, LlmWorker - background workers
# END_MODULE_MAP

from video2pptx.gui.main_window import MainWindow
from video2pptx.gui.settings_dialog import SettingsDialog
from video2pptx.gui.timeline_widget import TimelineWidget as TimelineWidgetV1, TimelinePanel, SubtitlePanel
from video2pptx.gui.workers import DetectWorker, NotesWorker, LlmWorker

__all__ = [
    "MainWindow",
    "SettingsDialog",
    "TimelineWidgetV1",
    "TimelinePanel",
    "SubtitlePanel",
    "DetectWorker",
    "NotesWorker",
    "LlmWorker",
]
