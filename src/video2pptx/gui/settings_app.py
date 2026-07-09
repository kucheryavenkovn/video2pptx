# FILE: src/video2pptx/gui/settings_app.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: App Settings QDialog — LLM, GPU/Backend, Snap, Default Paths tabs
#   SCOPE: QDialog with QTabWidget. Read/write via M-GUI-APPCONFIG.
#   DEPENDS: PySide6, M-CONFIG, M-GUI-APPCONFIG, M-BACKENDS
#   LINKS: M-GUI-SETTINGS-APP
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   AppSettingsDialog - QDialog with tabs for all app-wide settings
#   ModelListCombo - editable QComboBox that fetches model list on popup
# END_MODULE_MAP

from __future__ import annotations


from loguru import logger
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from video2pptx.backends import BACKENDS, detect_best_backend
from video2pptx.gui.app_config import AppConfigModel, save_app_config


class ModelListCombo(QComboBox):
    # START_CONTRACT: ModelListCombo
    #   PURPOSE: Editable combo that fetches model names from LLM API on popup
    #   INPUTS: { parent: QWidget | None }
    #   OUTPUTS: none
    #   SIDE_EFFECTS: HTTP request when popup opens
    #   LINKS: M-GUI-SETTINGS-APP
    # END_CONTRACT: ModelListCombo

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self._models_url: str = ""
        self._api_token: str = ""

    def set_models_url(self, url: str) -> None:
        self._models_url = url

    def set_api_token(self, token: str) -> None:
        self._api_token = token

    def showPopup(self) -> None:
        self._fetch_and_populate()
        super().showPopup()

    def _fetch_and_populate(self) -> None:
        from video2pptx.config import LlmConfig
        from video2pptx.llm_client import LlmClient

        url = self._models_url.strip()
        if not url:
            return

        cfg = LlmConfig(base_url=url, api_token=self._api_token)
        try:
            client = LlmClient(cfg)
            models = client.fetch_models()
            client.close()
        except Exception:
            models = []

        if not models:
            return

        current_text = self.currentText().strip()
        self.blockSignals(True)
        self.clear()
        for m in models:
            self.addItem(m)
        self.setEditText(current_text if current_text else models[0])
        self.blockSignals(False)


class AppSettingsDialog(QDialog):
    # START_CONTRACT: AppSettingsDialog
    #   PURPOSE: QDialog with QTabWidget for LLM, GPU/Backend, Snap, Default Paths
    #   INPUTS: { app_config: AppConfigModel }
    #   OUTPUTS: none — saves to app-config.yaml on accept
    #   SIDE_EFFECTS: writes app-config.yaml on accept
    #   LINKS: M-GUI-SETTINGS-APP
    # END_CONTRACT: AppSettingsDialog

    def __init__(self, app_config: AppConfigModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._app_config = app_config
        self.setWindowTitle("App Settings")
        self.setMinimumWidth(480)
        self._setup_ui()
        self._load_values()

    # START_BLOCK_SETUP_UI
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._build_llm_tab(), "LLM")
        tabs.addTab(self._build_gpu_tab(), "GPU / Backend")
        tabs.addTab(self._build_snap_tab(), "Snap")
        tabs.addTab(self._build_paths_tab(), "Default Paths")
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    # END_BLOCK_SETUP_UI

    # START_BLOCK_BUILD_LLM_TAB
    def _build_llm_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)

        model_row = QHBoxLayout()
        self._llm_model_combo = ModelListCombo()
        self._llm_model_combo.setMinimumWidth(200)
        self._llm_model_combo.currentTextChanged.connect(self._on_model_text_changed)
        model_row.addWidget(self._llm_model_combo)
        form.addRow("Model:", model_row)

        self._llm_base_url_edit = QLineEdit()
        self._llm_base_url_edit.textChanged.connect(self._on_base_url_changed)
        form.addRow("Base URL:", self._llm_base_url_edit)

        self._llm_models_url_edit = QLineEdit()
        self._llm_models_url_edit.setPlaceholderText("Leave empty to use Base URL /models")
        self._llm_models_url_edit.textChanged.connect(self._sync_model_combo_config)
        form.addRow("Models URL:", self._llm_models_url_edit)

        self._llm_api_token_edit = QLineEdit()
        self._llm_api_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._llm_api_token_edit.textChanged.connect(self._sync_model_combo_config)
        form.addRow("API Token:", self._llm_api_token_edit)

        self._llm_context_spin = QSpinBox()
        self._llm_context_spin.setRange(1024, 256000)
        self._llm_context_spin.setSingleStep(1024)
        form.addRow("Context Window:", self._llm_context_spin)

        self._llm_temperature_spin = QDoubleSpinBox()
        self._llm_temperature_spin.setRange(0.0, 2.0)
        self._llm_temperature_spin.setSingleStep(0.1)
        form.addRow("Temperature:", self._llm_temperature_spin)

        self._llm_max_tokens_spin = QSpinBox()
        self._llm_max_tokens_spin.setRange(64, 128000)
        self._llm_max_tokens_spin.setSingleStep(256)
        form.addRow("Max Tokens:", self._llm_max_tokens_spin)

        self._notes_mode_combo = QComboBox()
        self._notes_mode_combo.addItem("Basic (regex cleanup only)", "basic")
        self._notes_mode_combo.addItem("LLM (vision + rephrase)", "llm")
        form.addRow("Notes Mode:", self._notes_mode_combo)

        # Prompt editors
        self._llm_vision_prompt_edit = QTextEdit()
        self._llm_vision_prompt_edit.setMaximumHeight(80)
        self._llm_vision_prompt_edit.setPlaceholderText("Prompt for slide image vision analysis...")
        form.addRow("Vision Prompt:", self._llm_vision_prompt_edit)

        self._llm_correction_prompt_edit = QTextEdit()
        self._llm_correction_prompt_edit.setMaximumHeight(80)
        self._llm_correction_prompt_edit.setPlaceholderText("Prompt for transcript correction...")
        form.addRow("Correction Prompt:", self._llm_correction_prompt_edit)

        # Test Connection button row
        test_layout = QHBoxLayout()
        self._llm_test_btn = QPushButton("Test Connection")
        self._llm_test_btn.clicked.connect(self._on_test_llm_connection)
        test_layout.addWidget(self._llm_test_btn)
        test_layout.addStretch()
        form.addRow("", test_layout)

        return tab
    # END_BLOCK_BUILD_LLM_TAB

    # START_BLOCK_BUILD_GPU_TAB
    def _build_gpu_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)

        self._backend_combo = QComboBox()
        self._backend_combo.addItem("auto", "auto")
        for name, info in BACKENDS.items():
            label = f"{name} ({'available' if info['available'] else 'not available'})"
            self._backend_combo.addItem(label, name)
        form.addRow("Decoder Backend:", self._backend_combo)

        # Detect Best button
        detect_layout = QHBoxLayout()
        self._detect_backend_btn = QPushButton("Detect Best Backend")
        self._detect_backend_btn.clicked.connect(self._on_detect_best_backend)
        detect_layout.addWidget(self._detect_backend_btn)
        detect_layout.addStretch()
        form.addRow("", detect_layout)

        # CUDA info
        cuda_info = QLabel(self._get_cuda_info())
        cuda_info.setWordWrap(True)
        cuda_info.setStyleSheet("color: #666; font-size: 11px;")
        form.addRow("CUDA:", cuda_info)

        return tab
    # END_BLOCK_BUILD_GPU_TAB

    # START_BLOCK_BUILD_SNAP_TAB
    def _build_snap_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)

        self._snap_mode_combo = QComboBox()
        self._snap_mode_combo.addItem("hybrid", "hybrid")
        self._snap_mode_combo.addItem("diff_only", "diff_only")
        self._snap_mode_combo.addItem("fallback_analyze", "fallback_analyze")
        form.addRow("Snap Mode:", self._snap_mode_combo)

        self._snap_threshold_spin = QDoubleSpinBox()
        self._snap_threshold_spin.setRange(0.001, 1.0)
        self._snap_threshold_spin.setSingleStep(0.005)
        self._snap_threshold_spin.setDecimals(3)
        form.addRow("Flat Threshold:", self._snap_threshold_spin)

        return tab
    # END_BLOCK_BUILD_SNAP_TAB

    # START_BLOCK_BUILD_PATHS_TAB
    def _build_paths_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)

        path_row = QHBoxLayout()
        self._default_dir_edit = QLineEdit()
        self._default_dir_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse_default_dir)
        path_row.addWidget(self._default_dir_edit)
        path_row.addWidget(browse_btn)
        form.addRow("Default Project Dir:", path_row)

        self._restore_check = QCheckBox("Prompt to restore last project on startup")
        form.addRow("", self._restore_check)

        return tab
    # END_BLOCK_BUILD_PATHS_TAB

    # START_BLOCK_LOAD_VALUES
    def _load_values(self) -> None:
        llm = self._app_config.llm
        self._llm_model_combo.setEditText(llm.model)
        self._llm_base_url_edit.setText(llm.base_url)
        self._llm_models_url_edit.setText(llm.models_url)
        self._llm_api_token_edit.setText(llm.api_token)
        self._llm_context_spin.setValue(llm.context_window)
        self._llm_temperature_spin.setValue(llm.temperature)
        self._llm_max_tokens_spin.setValue(llm.max_tokens)
        self._llm_vision_prompt_edit.setPlainText(llm.vision_prompt)
        self._llm_correction_prompt_edit.setPlainText(llm.correction_prompt)

        idx = self._notes_mode_combo.findData(self._app_config.notes_mode)
        if idx >= 0:
            self._notes_mode_combo.setCurrentIndex(idx)

        self._sync_model_combo_config()

        idx = self._backend_combo.findData(self._app_config.backend)
        if idx >= 0:
            self._backend_combo.setCurrentIndex(idx)

        self._snap_mode_combo.setCurrentIndex(
            self._snap_mode_combo.findData(self._app_config.snap_mode)
        )
        self._snap_threshold_spin.setValue(self._app_config.snap_flat_threshold)
        self._default_dir_edit.setText(self._app_config.default_project_dir)
        self._restore_check.setChecked(self._app_config.restore_last_project)
    # END_BLOCK_LOAD_VALUES

    # START_BLOCK_ON_ACCEPT
    def _on_accept(self) -> None:
        llm = self._app_config.llm
        llm.model = self._llm_model_combo.currentText().strip() or llm.model
        llm.base_url = self._llm_base_url_edit.text().strip() or llm.base_url
        llm.models_url = self._llm_models_url_edit.text().strip()
        llm.api_token = self._llm_api_token_edit.text().strip()
        llm.context_window = self._llm_context_spin.value()
        llm.temperature = self._llm_temperature_spin.value()
        llm.max_tokens = self._llm_max_tokens_spin.value()
        llm.vision_prompt = self._llm_vision_prompt_edit.toPlainText().strip()
        llm.correction_prompt = self._llm_correction_prompt_edit.toPlainText().strip()

        self._app_config.notes_mode = self._notes_mode_combo.currentData() or "basic"

        self._app_config.backend = self._backend_combo.currentData()
        self._app_config.snap_mode = self._snap_mode_combo.currentData()
        self._app_config.snap_flat_threshold = self._snap_threshold_spin.value()
        self._app_config.default_project_dir = self._default_dir_edit.text().strip()
        self._app_config.restore_last_project = self._restore_check.isChecked()

        save_app_config(self._app_config)
        logger.info(
            "[GUI-SettingsApp][_on_accept] App settings saved | "
            f"model={llm.model} backend={self._app_config.backend} "
            f"snap_mode={self._app_config.snap_mode}"
        )
        self.accept()
    # END_BLOCK_ON_ACCEPT

    # START_BLOCK_HELPERS
    def _on_browse_default_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select Default Project Directory")
        if directory:
            self._default_dir_edit.setText(directory)

    # START_BLOCK_MODEL_COMBO_SYNC
    def _on_model_text_changed(self, text: str) -> None:
        pass  # keep value accessible via currentText()

    def _on_base_url_changed(self, url: str) -> None:
        if not self._llm_models_url_edit.text().strip():
            self._llm_models_url_edit.setText(f"{url.rstrip('/')}/models")

    def _sync_model_combo_config(self) -> None:
        models_url = self._llm_models_url_edit.text().strip() or f"{self._llm_base_url_edit.text().strip().rstrip('/')}/models"
        self._llm_model_combo.set_models_url(models_url)
        self._llm_model_combo.set_api_token(self._llm_api_token_edit.text().strip())
    # END_BLOCK_MODEL_COMBO_SYNC

    # START_BLOCK_ON_TEST_CONNECTION
    def _on_test_llm_connection(self) -> None:
        from video2pptx.config import LlmConfig

        cfg = LlmConfig(
            base_url=self._llm_base_url_edit.text().strip(),
            api_token=self._llm_api_token_edit.text().strip(),
        )
        self._llm_test_btn.setEnabled(False)
        self._llm_test_btn.setText("Testing...")
        QTimer.singleShot(50, lambda: self._do_test_llm(cfg))

    def _do_test_llm(self, cfg) -> None:
        from video2pptx.llm_client import LlmClient

        try:
            client = LlmClient(cfg)
            ok, msg = client.test_connection()
            client.close()
            if ok:
                QMessageBox.information(self, "Connection OK", msg)
            else:
                QMessageBox.warning(self, "Connection Failed", msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            self._llm_test_btn.setEnabled(True)
            self._llm_test_btn.setText("Test Connection")
    # END_BLOCK_ON_TEST_CONNECTION

    # START_BLOCK_ON_DETECT_BACKEND
    def _on_detect_best_backend(self) -> None:
        best = detect_best_backend()
        idx = self._backend_combo.findData(best)
        if idx >= 0:
            self._backend_combo.setCurrentIndex(idx)
        QMessageBox.information(self, "Detection Complete", f"Best available backend: {best}")
    # END_BLOCK_ON_DETECT_BACKEND

    def _get_cuda_info(self) -> str:
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
                if lines:
                    return "GPU: " + "\n".join(lines)
            return "NVIDIA driver not detected"
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return "NVIDIA driver not detected"
    # END_BLOCK_HELPERS
