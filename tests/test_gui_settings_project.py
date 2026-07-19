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

    def test_quality_presets_map_to_max_side(self, config) -> None:
        _ensure_app()
        from video2pptx.analysis_quality import AnalysisQualityPreset, PRESET_UI_LABELS
        from video2pptx.gui.settings_project import ProjectSettingsDialog

        dlg = ProjectSettingsDialog(config)
        # Fast
        dlg._quality_combo.setCurrentIndex(0)
        dlg._on_accept()
        assert dlg.result_config is not None
        assert dlg.result_config.analysis_max_side == 480

        dlg2 = ProjectSettingsDialog(config)
        dlg2._quality_combo.setCurrentIndex(1)  # Detailed
        dlg2._on_accept()
        assert dlg2.result_config.analysis_max_side == 720

        dlg3 = ProjectSettingsDialog(config)
        dlg3._quality_combo.setCurrentIndex(2)  # Native
        dlg3._on_accept()
        assert dlg3.result_config.analysis_max_side is None

        dlg4 = ProjectSettingsDialog(config)
        dlg4._quality_combo.setCurrentIndex(3)  # Custom
        dlg4._custom_spin.setValue(640)
        dlg4._on_accept()
        assert dlg4.result_config.analysis_max_side == 640

        labels = [dlg._quality_combo.itemText(i) for i in range(dlg._quality_combo.count())]
        joined = " ".join(labels)
        assert "480p" not in joined and "720p" not in joined
        assert PRESET_UI_LABELS[AnalysisQualityPreset.FAST] in labels

    def test_loads_custom_when_non_preset_value(self, config) -> None:
        _ensure_app()
        from video2pptx.analysis_quality import AnalysisQualityPreset
        from video2pptx.gui.settings_project import ProjectSettingsDialog

        config.analysis_max_side = 640
        dlg = ProjectSettingsDialog(config)
        assert dlg._current_preset() is AnalysisQualityPreset.CUSTOM
        assert dlg._custom_spin.value() == 640
        assert dlg._custom_spin.isEnabled()

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
