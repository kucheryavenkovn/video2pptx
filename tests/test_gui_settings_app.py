# FILE: tests/test_gui_settings_app.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for M-GUI-SETTINGS-APP — AppSettingsDialog
#   SCOPE: Smoke tests for dialog creation, tab presence, field population, save
#   DEPENDS: pytest, PySide6 (offscreen), M-GUI-APPCONFIG
#   LINKS: M-GUI-SETTINGS-APP
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
class TestAppSettingsDialog:
    # START_CONTRACT: TestAppSettingsDialog
    #   PURPOSE: Smoke tests for AppSettingsDialog
    #   LINKS: M-GUI-SETTINGS-APP
    # END_CONTRACT: TestAppSettingsDialog

    @pytest.fixture
    def app_config(self):
        from video_slide_md.gui.app_config import AppConfigModel
        return AppConfigModel()

    def test_dialog_creates_without_error(self, app_config) -> None:
        _ensure_app()
        from video_slide_md.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)
        assert dlg.windowTitle() == "App Settings"
        dlg.close()

    def test_has_four_tabs(self, app_config) -> None:
        _ensure_app()
        from PySide6.QtWidgets import QTabWidget
        from video_slide_md.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)
        tab_widget = dlg.findChild(QTabWidget)
        assert tab_widget is not None
        assert tab_widget.count() == 4
        dlg.close()

    def test_loads_config_values(self, app_config) -> None:
        _ensure_app()
        app_config.snap_mode = "diff_only"
        app_config.snap_flat_threshold = 0.1

        from video_slide_md.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)

        assert dlg._snap_mode_combo.currentData() == "diff_only"
        assert dlg._snap_threshold_spin.value() == 0.1
        dlg.close()

    def test_accept_saves_config(self, app_config) -> None:
        _ensure_app()
        from video_slide_md.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)

        idx = dlg._snap_mode_combo.findData("fallback_analyze")
        dlg._snap_mode_combo.setCurrentIndex(idx)
        dlg._snap_threshold_spin.setValue(0.08)

        with patch("video_slide_md.gui.settings_app.save_app_config") as mock_save:
            dlg._on_accept()
            mock_save.assert_called_once()

        assert app_config.snap_mode == "fallback_analyze"
        assert app_config.snap_flat_threshold == 0.08

    def test_cancel_does_not_save(self, app_config) -> None:
        _ensure_app()
        from video_slide_md.gui.settings_app import AppSettingsDialog
        original_backend = app_config.backend

        dlg = AppSettingsDialog(app_config)
        idx = dlg._backend_combo.findData("opencv")
        if idx >= 0:
            dlg._backend_combo.setCurrentIndex(idx)

        with patch("video_slide_md.gui.settings_app.save_app_config") as mock_save:
            dlg.reject()
            mock_save.assert_not_called()

        assert app_config.backend == original_backend
        dlg.close()
