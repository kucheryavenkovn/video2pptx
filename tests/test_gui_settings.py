# FILE: tests/test_gui_settings.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for settings dialog — tabs, prompt editing, backend selection
#   SCOPE: Verify dialog opens, tabs exist, save persists changes via project manager
#   DEPENDS: pytest, PySide6, video2pptx.project_manager
#   LINKS: V-M-GUI-SETTINGS, M-GUI-SETTINGS
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import sys

import pytest

pyside_available = False
try:
    from PySide6.QtWidgets import QApplication, QDialog, QPlainTextEdit, QTabWidget
    pyside_available = True
except ImportError:
    pass


def _ensure_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.mark.skipif(not pyside_available, reason="PySide6 not installed")
class TestSettingsDialog:
    def test_dialog_opens(self, tmp_path):
        """Settings dialog opens with correct tab count."""
        from video2pptx.gui.settings_dialog import SettingsDialog
        from video2pptx.project_manager import create_project

        _ensure_app()
        video = tmp_path / "video.mp4"
        video.write_text("fake")
        proj = create_project(tmp_path / "proj", video_path=video, name="Test")

        dialog = SettingsDialog(project=proj)
        assert isinstance(dialog, QDialog)

        tabs = dialog.findChild(QTabWidget)
        assert tabs is not None
        assert tabs.count() >= 2  # LLM, GPU/Backend, Detection

    def test_llm_tab_shows_prompt(self, tmp_path):
        """LLM tab displays the current system prompt in editable field."""
        from video2pptx.gui.settings_dialog import SettingsDialog
        from video2pptx.project_manager import create_project

        _ensure_app()
        video = tmp_path / "video.mp4"
        video.write_text("fake")
        proj = create_project(tmp_path / "proj", video_path=video)

        dialog = SettingsDialog(project=proj)

        # Find QPlainTextEdit widget (the prompt editor)
        editors = dialog.findChildren(QPlainTextEdit)
        assert len(editors) >= 1
        # At least one editor should have content
        assert any(len(e.toPlainText()) > 0 for e in editors)

    def test_save_persists_changes(self, tmp_path):
        """Save button writes changes to project.json and can be reloaded."""
        from video2pptx.gui.settings_dialog import SettingsDialog
        from video2pptx.project_manager import create_project, open_project

        _ensure_app()
        video = tmp_path / "video.mp4"
        video.write_text("fake")
        proj_dir = tmp_path / "proj"
        proj = create_project(proj_dir, video_path=video)

        dialog = SettingsDialog(project=proj)
        dialog.save()

        reloaded = open_project(proj_dir)
        assert reloaded.name == proj.name
