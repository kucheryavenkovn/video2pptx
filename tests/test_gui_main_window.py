# FILE: tests/test_gui_main_window.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for M-GUI-MAIN (updated) — MainWindow with full integration
#   SCOPE: Smoke tests for component creation and basic signal routing
#   DEPENDS: pytest, PySide6 (offscreen), M-PROJECT, all GUI modules
#   LINKS: M-GUI-MAIN
#   ROLE: TEST
#   MAP_MODE: NONE
# END_MODULE_CONTRACT

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pyside_available = False
try:
    from PySide6.QtWidgets import QApplication  # noqa: F401
    pyside_available = True
except ImportError:
    pass


def _ensure_app() -> None:
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        QApplication(sys.argv)


@pytest.mark.skipif(not pyside_available, reason="PySide6 not installed")
class TestMainWindow:
    # START_CONTRACT: TestMainWindow
    #   PURPOSE: Smoke tests for updated MainWindow (Phase-11 integration)
    #   LINKS: M-GUI-MAIN
    # END_CONTRACT: TestMainWindow

    def test_creates_without_error(self) -> None:
        _ensure_app()
        from video_slide_md.gui.main_window import MainWindow
        w = MainWindow()
        assert w._project is None
        assert w._menu_bar is not None
        assert w._video_player is not None
        assert w._subtitle_overlay is not None
        assert w._timeline is not None
        assert w._detect_btn is not None
        w.deleteLater()

    def test_window_title_default(self) -> None:
        _ensure_app()
        from video_slide_md.gui.main_window import MainWindow
        w = MainWindow()
        assert "video-slide-md" in w.windowTitle()
        w.deleteLater()

    def test_info_labels_default(self) -> None:
        _ensure_app()
        from video_slide_md.gui.main_window import MainWindow
        w = MainWindow()
        assert "—" in w._video_label.text()
        assert "—" in w._subs_label.text()
        w.deleteLater()

    def test_detect_button_disabled_without_project(self) -> None:
        _ensure_app()
        from video_slide_md.gui.main_window import MainWindow
        w = MainWindow()
        assert w._detect_btn.isEnabled() is False
        w.deleteLater()

    def test_set_project_updates_ui(self, tmp_path: Path) -> None:
        _ensure_app()
        from video_slide_md.gui.main_window import MainWindow

        proj_dir = tmp_path / "testproj"
        proj_dir.mkdir()
        video_path = proj_dir / "test.mp4"
        video_path.write_text("fake video")

        from video_slide_md.project_manager import Project
        proj = Project(name="test", video=str(video_path), output_dir=str(proj_dir))

        w = MainWindow()
        w._set_project(proj)
        assert w._project is not None
        assert w._project.name == "test"
        assert w._detect_btn.isEnabled()
        assert "test" in w.windowTitle()
        assert "test.mp4" in w._video_label.text()
        w.deleteLater()

    def test_video_position_syncs_subtitles(self, tmp_path: Path) -> None:
        _ensure_app()
        from video_slide_md.gui.main_window import MainWindow
        w = MainWindow()
        with patch.object(w._subtitle_overlay, "sync_to_position") as mock:
            w._on_video_position_changed(10.5)
            mock.assert_called_once_with(10.5)
        w.deleteLater()

    def test_project_changed_signal_emitted(self, tmp_path: Path) -> None:
        _ensure_app()
        from video_slide_md.gui.main_window import MainWindow
        from video_slide_md.project_manager import Project

        proj_dir = tmp_path / "testproj"
        proj_dir.mkdir()
        video_path = proj_dir / "test.mp4"
        video_path.write_text("fake video")

        proj = Project(name="test", video=str(video_path), output_dir=str(proj_dir))

        w = MainWindow()
        handler = MagicMock()
        w.project_changed.connect(handler)
        w._set_project(proj)
        handler.assert_called_once()
        w.deleteLater()

    def test_menu_bar_actions_present(self) -> None:
        _ensure_app()
        from video_slide_md.gui.main_window import MainWindow
        w = MainWindow()
        mb = w._menu_bar
        assert mb.act_new_project is not None
        assert mb.act_open_project is not None
        assert mb.act_close_project is not None
        assert mb.act_save_project is not None
        assert mb.act_import_srt is not None
        assert mb.act_exit is not None
        assert mb.act_project_settings is not None
        assert mb.act_app_settings is not None
        w.deleteLater()

    def test_timeline_hidden_initially(self) -> None:
        _ensure_app()
        from video_slide_md.gui.main_window import MainWindow
        w = MainWindow()
        assert w._timeline.isHidden()
        w.deleteLater()
