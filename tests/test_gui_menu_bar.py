# FILE: tests/test_gui_menu_bar.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for M-GUI-MENUBAR — MenuBarWidget
#   SCOPE: Verify actions exist, have shortcuts, and emit correct signals
#   DEPENDS: pytest, PySide6 (offscreen)
#   LINKS: M-GUI-MENUBAR
#   ROLE: TEST
#   MAP_MODE: NONE
# END_MODULE_CONTRACT

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

pyside_available = False
try:
    from PySide6.QtWidgets import QApplication, QMainWindow  # noqa: F401
    pyside_available = True
except ImportError:
    pass


def _ensure_app() -> None:
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        QApplication(sys.argv)


@pytest.mark.skipif(not pyside_available, reason="PySide6 not installed")
class TestMenuBarWidget:
    # START_CONTRACT: TestMenuBarWidget
    #   PURPOSE: Verify MenuBarWidget creates all actions and signals
    #   LINKS: M-GUI-MENUBAR
    # END_CONTRACT: TestMenuBarWidget

    def _make(self):
        from video_slide_md.gui.menu_bar import MenuBarWidget
        window = QMainWindow()
        mb = MenuBarWidget(window)
        window.setMenuBar(mb)
        return mb, window

    def test_creates_without_error(self) -> None:
        _ensure_app()
        mb, window = self._make()
        assert mb.act_new_project is not None
        assert mb.act_open_project is not None
        assert mb.act_close_project is not None
        assert mb.act_save_project is not None
        assert mb.act_import_srt is not None
        assert mb.act_exit is not None
        assert mb.act_project_settings is not None
        assert mb.act_app_settings is not None
        window.deleteLater()
        mb.deleteLater()

    def test_shortcuts_assigned(self) -> None:
        _ensure_app()
        mb, window = self._make()
        assert mb.act_new_project.shortcut().toString() == "Ctrl+N"
        assert mb.act_open_project.shortcut().toString() == "Ctrl+O"
        assert mb.act_close_project.shortcut().toString() == "Ctrl+W"
        assert mb.act_save_project.shortcut().toString() == "Ctrl+S"
        assert mb.act_import_srt.shortcut().toString() == "Ctrl+I"
        assert mb.act_exit.shortcut().toString() == "Ctrl+Q"
        assert mb.act_project_settings.shortcut().toString() == "Ctrl+,"
        window.deleteLater()
        mb.deleteLater()

    def test_new_project_signal_emitted(self) -> None:
        _ensure_app()
        mb, window = self._make()
        handler = MagicMock()
        mb.act_new_project.triggered.connect(handler)
        mb.act_new_project.triggered.emit()
        handler.assert_called_once()
        window.deleteLater()
        mb.deleteLater()

    def test_open_project_signal_emitted(self) -> None:
        _ensure_app()
        mb, window = self._make()
        handler = MagicMock()
        mb.act_open_project.triggered.connect(handler)
        mb.act_open_project.triggered.emit()
        handler.assert_called_once()
        window.deleteLater()
        mb.deleteLater()

    def test_close_project_signal_emitted(self) -> None:
        _ensure_app()
        mb, window = self._make()
        handler = MagicMock()
        mb.act_close_project.triggered.connect(handler)
        mb.act_close_project.triggered.emit()
        handler.assert_called_once()
        window.deleteLater()
        mb.deleteLater()

    def test_save_project_signal_emitted(self) -> None:
        _ensure_app()
        mb, window = self._make()
        handler = MagicMock()
        mb.act_save_project.triggered.connect(handler)
        mb.act_save_project.triggered.emit()
        handler.assert_called_once()
        window.deleteLater()
        mb.deleteLater()

    def test_import_srt_signal_emitted(self) -> None:
        _ensure_app()
        mb, window = self._make()
        handler = MagicMock()
        mb.act_import_srt.triggered.connect(handler)
        mb.act_import_srt.triggered.emit()
        handler.assert_called_once()
        window.deleteLater()
        mb.deleteLater()

    def test_exit_signal_emitted(self) -> None:
        _ensure_app()
        mb, window = self._make()
        handler = MagicMock()
        mb.act_exit.triggered.connect(handler)
        mb.act_exit.triggered.emit()
        handler.assert_called_once()
        window.deleteLater()
        mb.deleteLater()

    def test_project_settings_signal_emitted(self) -> None:
        _ensure_app()
        mb, window = self._make()
        handler = MagicMock()
        mb.act_project_settings.triggered.connect(handler)
        mb.act_project_settings.triggered.emit()
        handler.assert_called_once()
        window.deleteLater()
        mb.deleteLater()

    def test_app_settings_signal_emitted(self) -> None:
        _ensure_app()
        mb, window = self._make()
        handler = MagicMock()
        mb.act_app_settings.triggered.connect(handler)
        mb.act_app_settings.triggered.emit()
        handler.assert_called_once()
        window.deleteLater()
        mb.deleteLater()
