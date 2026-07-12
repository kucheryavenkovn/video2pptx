# FILE: src/video2pptx/gui/__init__.py
# VERSION: 0.4.0
# START_MODULE_CONTRACT
#   PURPOSE: GUI package for video2pptx desktop application
#   SCOPE: Package marker — exports MainWindow, SettingsDialog
#   DEPENDS: PySide6
#   LINKS: M-GUI-MAIN, M-GUI-TIMELINE3
#   ROLE: BARREL
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT

from video2pptx.gui.main_window import MainWindow
from video2pptx.gui.settings_dialog import SettingsDialog

__all__ = [
    "MainWindow",
    "SettingsDialog",
]
