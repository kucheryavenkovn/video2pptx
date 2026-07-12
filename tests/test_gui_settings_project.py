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
    #   PURPOSE: Smoke tests for ProjectSettingsDialog using canonical DetectionConfig
    #   LINKS: M-GUI-SETTINGS-PROJECT
    # END_CONTRACT: TestProjectSettingsDialog

    @pytest.fixture
    def config(self):
        from video2pptx.domain.project import DetectionConfig
        return DetectionConfig(
            sample_fps=2.0, decoder_backend="auto",
            slide_roi="auto", threshold="auto",
            min_slide_duration=2.0, min_stable_duration=2.0,
            dedupe_enabled=True,
        )

    def test_dialog_creates_without_error(self, config) -> None:
        _ensure_app()
        from video2pptx.gui.settings_project import ProjectSettingsDialog
        dlg = ProjectSettingsDialog(config)
        assert dlg.windowTitle() == "Project Settings"
        dlg.close()

    def test_loads_project_values(self, config) -> None:
        _ensure_app()
        config.slide_roi = "100,100,800,600"
        config.sample_fps = 5.0
        config.min_slide_duration = 7.0
        config.dedupe_enabled = False

        from video2pptx.gui.settings_project import ProjectSettingsDialog
        dlg = ProjectSettingsDialog(config)

        assert "100" in dlg._roi_edit.text()
        assert dlg._fps_spin.value() == 5.0
        assert dlg._min_dur_spin.value() == 7.0
        assert dlg._dedupe_check.isChecked() is False
        dlg.close()

    def test_accept_returns_updated_config(self, config) -> None:
        _ensure_app()
        from video2pptx.gui.settings_project import ProjectSettingsDialog
        dlg = ProjectSettingsDialog(config)
        dlg._roi_edit.setText("200,200,900,700")
        dlg._threshold_edit.setText("0.15")
        dlg._fps_spin.setValue(3.0)

        dlg._on_accept()

        result = dlg.result_config
        assert result is not None
        assert result.slide_roi == "200,200,900,700"
        assert result.threshold == 0.15
        assert result.sample_fps == 3.0

    def test_cancel_does_not_return_config(self, config) -> None:
        _ensure_app()
        from video2pptx.gui.settings_project import ProjectSettingsDialog
        dlg = ProjectSettingsDialog(config)
        dlg._roi_edit.setText("300,300,600,400")

        with patch.object(dlg, "accept") as mock_accept:
            dlg.reject()
            mock_accept.assert_not_called()

        assert dlg.result_config is None
        dlg.close()
