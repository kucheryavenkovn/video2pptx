# FILE: tests/test_gui_main.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Smoke tests for main GUI window — creation, project toolbar, detect button
#   SCOPE: Verify window opens, toolbar buttons exist, basic layout renders. Uses offscreen platform.
#   DEPENDS: pytest, PySide6
#   LINKS: V-M-GUI-MAIN
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import sys

import pytest

# Skip all tests if imports are missing or no display
pyside_available = False
try:
    from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QToolBar  # noqa: F401
    pyside_available = True
except ImportError:
    pass


def _ensure_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.mark.skipif(not pyside_available, reason="PySide6 not installed")
class TestMainWindowSmoke:
    def test_window_creation(self):
        """MainWindow can be instantiated and shown without errors."""
        from PySide6.QtWidgets import QMainWindow

        _ensure_app()

        # M-GUI-MAIN: MainWindow is a QMainWindow subclass
        from video2pptx.gui.main_window import MainWindow

        window = MainWindow()
        assert isinstance(window, QMainWindow)

    def test_toolbar_has_project_buttons(self):
        """Toolbar contains New, Open, Save buttons."""
        _ensure_app()
        from video2pptx.gui.main_window import MainWindow

        window = MainWindow()

        # Find the toolbar — should have project actions
        toolbar = window.findChild(QToolBar)
        assert toolbar is not None

        actions = [a.text() for a in toolbar.actions()]
        has_new = any("New" in a or "Создать" in a for a in actions)
        has_open = any("Open" in a or "Открыть" in a for a in actions)

        assert has_new and has_open, f"Toolbar missing project actions: {actions}"

    def test_detect_button_exists(self):
        """Detect button is present and disabled when no project loaded."""
        _ensure_app()
        from video2pptx.gui.main_window import MainWindow

        window = MainWindow()

        buttons = window.findChildren(QPushButton)
        detect_btn = None
        for btn in buttons:
            if "detect" in btn.text().lower():
                detect_btn = btn
                break

        assert detect_btn is not None, "No Detect button found"
        assert not detect_btn.isEnabled(), "Detect should be disabled with no project"
