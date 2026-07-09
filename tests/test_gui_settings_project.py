# FILE: tests/test_gui_settings_project.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for M-GUI-SETTINGS-PROJECT — ProjectSettingsDialog
#   SCOPE: Smoke tests for dialog creation, field population, save/cancel
#   DEPENDS: pytest, PySide6 (offscreen), M-PROJECT
#   LINKS: M-GUI-SETTINGS-PROJECT
#   ROLE: TEST
#   MAP_MODE: NONE
# END_MODULE_CONTRACT

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

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
class TestProjectSettingsDialog:
    # START_CONTRACT: TestProjectSettingsDialog
    #   PURPOSE: Smoke tests for ProjectSettingsDialog
    #   LINKS: M-GUI-SETTINGS-PROJECT
    # END_CONTRACT: TestProjectSettingsDialog

    @pytest.fixture
    def project(self, tmp_path: Path):
        from video_slide_md.project_manager import Project, save_project
        proj = Project(
            name="test",
            video=str(tmp_path / "test.mp4"),
            output_dir=str(tmp_path),
        )
        save_project(proj, tmp_path)
        return proj

    def test_dialog_creates_without_error(self, project) -> None:
        _ensure_app()
        from video_slide_md.gui.settings_project import ProjectSettingsDialog
        dlg = ProjectSettingsDialog(project)
        assert dlg.windowTitle() == "Project Settings"
        dlg.close()

    def test_loads_project_values(self, project) -> None:
        _ensure_app()
        project.detection.slide_roi = "100,100,800,600"
        project.video_config.sample_fps = 5.0
        project.detection.min_slide_duration = 7.0
        project.detection.dedupe_enabled = False

        from video_slide_md.gui.settings_project import ProjectSettingsDialog
        dlg = ProjectSettingsDialog(project)

        roi_text = dlg._roi_edit.text()
        assert "100" in roi_text
        assert dlg._fps_spin.value() == 5.0
        assert dlg._min_dur_spin.value() == 7.0
        assert dlg._dedupe_check.isChecked() is False
        dlg.close()

    def test_accept_saves_to_project(self, project, tmp_path) -> None:
        _ensure_app()
        from video_slide_md.gui.settings_project import ProjectSettingsDialog
        dlg = ProjectSettingsDialog(project)
        dlg._roi_edit.setText("200,200,900,700")
        dlg._threshold_edit.setText("0.15")
        dlg._fps_spin.setValue(3.0)

        dlg._on_accept()

        assert project.detection.slide_roi == "200,200,900,700"
        assert project.detection.threshold == 0.15
        assert project.video_config.sample_fps == 3.0

        # Verify persisted
        from video_slide_md.project_manager import Project as ProjModel
        loaded = ProjModel.model_validate_json(
            (tmp_path / "project.json").read_text(encoding="utf-8")
        )
        assert loaded.detection.slide_roi == "200,200,900,700"

    def test_cancel_does_not_save(self, project) -> None:
        _ensure_app()
        from video_slide_md.gui.settings_project import ProjectSettingsDialog
        dlg = ProjectSettingsDialog(project)
        dlg._roi_edit.setText("300,300,600,400")

        with patch.object(dlg, "accept") as mock_accept:
            dlg.reject()
            mock_accept.assert_not_called()

        assert project.detection.slide_roi != "300,300,600,400"
        dlg.close()
