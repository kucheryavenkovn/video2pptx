# FILE: src/video_slide_md/gui/__init__.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: GUI package for video-slide-md desktop application
#   SCOPE: Package marker — exports MainWindow, SettingsDialog, TimelineWidget
#   DEPENDS: PySide6
#   LINKS: M-GUI-MAIN, M-GUI-TIMELINE, M-GUI-SETTINGS, M-GUI-WORKER
#   ROLE: BARREL
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   MainWindow - main application window
#   SettingsDialog - settings dialog with tabs
#   TimelineWidget, TimelinePanel, SubtitlePanel - timeline components
#   DetectWorker, NotesWorker, LlmWorker - background workers
# END_MODULE_MAP

from video_slide_md.gui.main_window import MainWindow
from video_slide_md.gui.settings_dialog import SettingsDialog
from video_slide_md.gui.timeline_widget import TimelineWidget, TimelinePanel, SubtitlePanel
from video_slide_md.gui.workers import DetectWorker, NotesWorker, LlmWorker

__all__ = [
    "MainWindow",
    "SettingsDialog",
    "TimelineWidget",
    "TimelinePanel",
    "SubtitlePanel",
    "DetectWorker",
    "NotesWorker",
    "LlmWorker",
]
