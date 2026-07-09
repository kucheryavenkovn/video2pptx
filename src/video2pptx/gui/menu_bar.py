# FILE: src/video2pptx/gui/menu_bar.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: QMenuBar with File and Edit menus for the desktop GUI
#   SCOPE: File (New/Open/Close/Save/Import SRT/Exit) and Edit (Project Settings/App Settings)
#   DEPENDS: PySide6, M-GUI-SETTINGS-PROJECT, M-GUI-SETTINGS-APP
#   LINKS: M-GUI-MENUBAR
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   MenuBarWidget - QMenuBar with File and Edit menus; all actions emit signals
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

from loguru import logger
from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QMenuBar


class MenuBarWidget(QMenuBar):
    # START_CONTRACT: MenuBarWidget
    #   PURPOSE: Build File and Edit menus on the given QMainWindow, emit signals per action
    #   INPUTS: { parent: QMainWindow }
    #   OUTPUTS: signals: new_project, open_project, close_project, save_project, import_srt, exit_app,
    #                      project_settings, app_settings, open_recent_project
    #   SIDE_EFFECTS: connects actions to signals; does NOT install itself (caller adds to layout)
    #   LINKS: M-GUI-MENUBAR
    # END_CONTRACT: MenuBarWidget

    open_recent_project = Signal(str)

    def __init__(self, parent: QMainWindow | None = None) -> None:
        super().__init__(parent)
        self._parent = parent
        self._recent_actions: list[QAction] = []
        self._build_file_menu()
        self._build_edit_menu()

    def set_recent_projects(self, paths: list[str]) -> None:
        for act in self._recent_actions:
            self._recent_menu.removeAction(act)
        self._recent_actions.clear()
        if not paths:
            self._recent_menu.setEnabled(False)
            return
        self._recent_menu.setEnabled(True)
        for p in paths:
            act = QAction(Path(p).name, self)
            act.setToolTip(str(p))
            act.setData(p)
            act.triggered.connect(lambda checked=False, path=p: self.open_recent_project.emit(path))
            self._recent_menu.addAction(act)
            self._recent_actions.append(act)

    # START_BLOCK_FILE_MENU
    def _build_file_menu(self) -> None:
        file_menu = self.addMenu("&File")

        self.act_new_project = QAction("&New Project...", self)
        self.act_new_project.setShortcut("Ctrl+N")
        file_menu.addAction(self.act_new_project)

        self.act_open_project = QAction("&Open Project...", self)
        self.act_open_project.setShortcut("Ctrl+O")
        file_menu.addAction(self.act_open_project)

        self.act_close_project = QAction("&Close Project", self)
        self.act_close_project.setShortcut("Ctrl+W")
        file_menu.addAction(self.act_close_project)

        self.act_save_project = QAction("&Save Project", self)
        self.act_save_project.setShortcut("Ctrl+S")
        file_menu.addAction(self.act_save_project)

        file_menu.addSeparator()

        self._recent_menu = file_menu.addMenu("&Recent Projects")
        self._recent_menu.setEnabled(False)

        file_menu.addSeparator()

        self.act_import_video = QAction("Import &Video...", self)
        self.act_import_video.setShortcut("Ctrl+V")
        file_menu.addAction(self.act_import_video)

        self.act_import_srt = QAction("Import &Subtitles...", self)
        self.act_import_srt.setShortcut("Ctrl+I")
        file_menu.addAction(self.act_import_srt)

        file_menu.addSeparator()

        self.act_process_notes = QAction("Process &Notes...", self)
        file_menu.addAction(self.act_process_notes)

        # Export submenu
        export_menu = file_menu.addMenu("&Export")
        self.act_export_md = QAction("&Markdown (Marp)...", self)
        export_menu.addAction(self.act_export_md)
        self.act_export_pptx = QAction("&PPTX...", self)
        export_menu.addAction(self.act_export_pptx)

        file_menu.addSeparator()

        self.act_exit = QAction("E&xit", self)
        self.act_exit.setShortcut("Ctrl+Q")
        file_menu.addAction(self.act_exit)

        logger.debug("[GUI-MenuBar][_build_file_menu] File menu built")
    # END_BLOCK_FILE_MENU

    # START_BLOCK_EDIT_MENU
    def _build_edit_menu(self) -> None:
        edit_menu = self.addMenu("&Edit")

        self.act_project_settings = QAction("&Project Settings...", self)
        self.act_project_settings.setShortcut("Ctrl+,")
        edit_menu.addAction(self.act_project_settings)

        self.act_app_settings = QAction("&App Settings...", self)
        edit_menu.addAction(self.act_app_settings)

        logger.debug("[GUI-MenuBar][_build_edit_menu] Edit menu built")
    # END_BLOCK_EDIT_MENU
