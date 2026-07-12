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
        from video2pptx.gui.app_config import AppConfigModel
        return AppConfigModel()

    def test_dialog_creates_without_error(self, app_config) -> None:
        _ensure_app()
        from video2pptx.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)
        assert dlg.windowTitle() == "App Settings"
        dlg.close()

    def test_has_four_tabs(self, app_config) -> None:
        _ensure_app()
        from PySide6.QtWidgets import QTabWidget

        from video2pptx.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)
        tab_widget = dlg.findChild(QTabWidget)
        assert tab_widget is not None
        assert tab_widget.count() == 5
        dlg.close()

    def test_loads_config_values(self, app_config) -> None:
        _ensure_app()
        app_config.snap_mode = "diff_only"
        app_config.snap_flat_threshold = 0.1

        from video2pptx.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)

        assert dlg._snap_mode_combo.currentData() == "diff_only"
        assert dlg._snap_threshold_spin.value() == 0.1
        dlg.close()

    def test_accept_saves_config(self, app_config) -> None:
        _ensure_app()
        from video2pptx.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)

        idx = dlg._snap_mode_combo.findData("fallback_analyze")
        dlg._snap_mode_combo.setCurrentIndex(idx)
        dlg._snap_threshold_spin.setValue(0.08)

        with patch("video2pptx.gui.settings_app.save_app_config") as mock_save:
            dlg._on_accept()
            mock_save.assert_called_once()

        assert app_config.snap_mode == "fallback_analyze"
        assert app_config.snap_flat_threshold == 0.08

    def test_cancel_does_not_save(self, app_config) -> None:
        _ensure_app()
        from video2pptx.gui.settings_app import AppSettingsDialog
        original_backend = app_config.backend

        dlg = AppSettingsDialog(app_config)
        idx = dlg._backend_combo.findData("opencv")
        if idx >= 0:
            dlg._backend_combo.setCurrentIndex(idx)

        with patch("video2pptx.gui.settings_app.save_app_config") as mock_save:
            dlg.reject()
            mock_save.assert_not_called()

        assert app_config.backend == original_backend
        dlg.close()

    def test_llm_tab_has_api_token_and_test_button(self, app_config) -> None:
        _ensure_app()
        from video2pptx.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)
        assert hasattr(dlg, "_llm_api_token_edit")
        assert dlg._llm_api_token_edit.echoMode() == dlg._llm_api_token_edit.EchoMode.Password
        assert hasattr(dlg, "_llm_test_btn")
        assert dlg._llm_test_btn.text() == "Test Connection"
        dlg.close()

    def test_gpu_tab_has_detect_backend_button(self, app_config) -> None:
        _ensure_app()
        from video2pptx.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)
        assert hasattr(dlg, "_detect_backend_btn")
        assert dlg._detect_backend_btn.text() == "Detect Best Backend"
        dlg.close()

    def test_accept_saves_api_token(self, app_config) -> None:
        _ensure_app()
        from video2pptx.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)
        dlg._llm_api_token_edit.setText("sk-test-token-123")
        with patch("video2pptx.gui.settings_app.save_app_config"):
            dlg._on_accept()
        assert app_config.llm.api_token == "sk-test-token-123"
        dlg.close()

    def test_paths_tab_has_restore_checkbox(self, app_config) -> None:
        _ensure_app()
        from video2pptx.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)
        assert hasattr(dlg, "_restore_check")
        assert dlg._restore_check.isChecked() is True  # default
        dlg.close()

    def test_accept_saves_restore_checkbox(self, app_config) -> None:
        _ensure_app()
        from video2pptx.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)
        dlg._restore_check.setChecked(False)
        with patch("video2pptx.gui.settings_app.save_app_config"):
            dlg._on_accept()
        assert app_config.restore_last_project is False
        dlg.close()

    def test_restore_checkbox_loads_from_config(self, app_config) -> None:
        _ensure_app()
        app_config.restore_last_project = False
        from video2pptx.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)
        assert dlg._restore_check.isChecked() is False
        dlg.close()

    def test_llm_tab_has_model_combo(self, app_config) -> None:
        _ensure_app()
        from video2pptx.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)
        assert hasattr(dlg, "_llm_model_combo")
        assert dlg._llm_model_combo.isEditable()
        dlg.close()

    def test_llm_tab_has_models_url_field(self, app_config) -> None:
        _ensure_app()
        from video2pptx.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)
        assert hasattr(dlg, "_llm_models_url_edit")
        assert "models" in dlg._llm_models_url_edit.placeholderText().lower()
        dlg.close()

    def test_accept_saves_models_url(self, app_config) -> None:
        _ensure_app()
        from video2pptx.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)
        dlg._llm_models_url_edit.setText("http://custom-host/v1/models")
        with patch("video2pptx.gui.settings_app.save_app_config"):
            dlg._on_accept()
        assert app_config.llm.models_url == "http://custom-host/v1/models"
        dlg.close()

    def test_model_combo_syncs_url_from_config(self, app_config) -> None:
        _ensure_app()
        from video2pptx.gui.settings_app import AppSettingsDialog
        app_config.llm.models_url = "http://custom/v1/models"
        dlg = AppSettingsDialog(app_config)
        assert dlg._llm_models_url_edit.text() == "http://custom/v1/models"
        dlg.close()

    def test_model_combo_fetches_with_models_url(self, app_config) -> None:
        _ensure_app()
        from video2pptx.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(app_config)
        dlg._llm_base_url_edit.clear()
        dlg._llm_models_url_edit.setText("http://test-host/v1/models")
        with patch("video2pptx.llm_client.LlmClient.fetch_models", return_value=["m1", "m2"]):
            dlg._llm_model_combo.showPopup()
            assert dlg._llm_model_combo.count() == 2
            assert dlg._llm_model_combo.itemText(0) == "m1"
        dlg.close()
