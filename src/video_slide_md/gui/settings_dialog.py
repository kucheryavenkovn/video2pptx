# FILE: src/video_slide_md/gui/settings_dialog.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Settings dialog with tabs for LLM prompt, GPU/Backend, and Detection configuration
#   SCOPE: QDialog with QTabWidget, save/load settings from project
#   DEPENDS: PySide6, M-PROJECT, M-CONFIG, M-BACKENDS
#   LINKS: M-GUI-SETTINGS
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   SettingsDialog - QDialog with project settings tabs
# END_MODULE_MAP

from __future__ import annotations

from loguru import logger
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from video_slide_md.backends import BACKENDS
from video_slide_md.config import DetectionConfig, LlmConfig
from video_slide_md.project_manager import Project, save_project
from video_slide_md.notes_processor import SYSTEM_PROMPT_REPHRASE


class SettingsDialog(QDialog):
    # START_CONTRACT: SettingsDialog
    #   PURPOSE: Settings dialog with tabs for LLM, GPU/Backend, Detection
    #   INPUTS: { project: Project }
    #   OUTPUTS: emits settings_changed signal, saves to project.json
    #   SIDE_EFFECTS: writes to project.json on save
    #   LINKS: M-GUI-SETTINGS
    # END_CONTRACT: SettingsDialog

    settings_changed = Signal()

    def __init__(self, project: Project, parent=None) -> None:
        super().__init__(parent)
        self._project = project
        self.setWindowTitle("Settings")
        self.resize(600, 500)
        self._setup_ui()

    # START_BLOCK_SETUP_UI
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # LLM Tab
        llm_tab = self._build_llm_tab()
        tabs.addTab(llm_tab, "LLM")

        # GPU/Backend Tab
        backend_tab = self._build_backend_tab()
        tabs.addTab(backend_tab, "GPU/Backend")

        # Detection Tab
        detect_tab = self._build_detection_tab()
        tabs.addTab(detect_tab, "Detection")

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    # END_BLOCK_SETUP_UI

    # START_BLOCK_LLM_TAB
    def _build_llm_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form = QFormLayout()

        self._model_edit = QLineEdit(self._project.llm.model)
        form.addRow("Model:", self._model_edit)

        self._base_url_edit = QLineEdit(self._project.llm.base_url)
        form.addRow("Base URL:", self._base_url_edit)

        self._prompt_edit = QPlainTextEdit()
        self._prompt_edit.setPlainText(SYSTEM_PROMPT_REPHRASE)
        form.addRow("System Prompt:", self._prompt_edit)

        layout.addLayout(form)
        layout.addStretch()
        return tab

    # END_BLOCK_LLM_TAB

    # START_BLOCK_BACKEND_TAB
    def _build_backend_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group = QGroupBox("Available Backends")
        group_layout = QVBoxLayout(group)

        self._backend_buttons: dict[str, QRadioButton] = {}
        for name, info in BACKENDS.items():
            status = "✓" if info["available"] else "✗"
            btn = QRadioButton(f"{name} [{status}]")
            btn.setEnabled(info["available"])
            if name == "opencv":
                btn.setChecked(True)
            self._backend_buttons[name] = btn
            group_layout.addWidget(btn)

        group_layout.addStretch()
        layout.addWidget(group)
        layout.addStretch()
        return tab

    # END_BLOCK_BACKEND_TAB

    # START_BLOCK_DETECTION_TAB
    def _build_detection_tab(self) -> QWidget:
        tab = QWidget()
        layout = QFormLayout(tab)

        self._threshold_edit = QLineEdit(str(self._project.detection.threshold))
        layout.addRow("Threshold:", self._threshold_edit)

        self._min_slide_edit = QLineEdit(str(self._project.detection.min_slide_duration))
        layout.addRow("Min Slide Duration:", self._min_slide_edit)

        self._min_stable_edit = QLineEdit(str(self._project.detection.min_stable_duration))
        layout.addRow("Min Stable Duration:", self._min_stable_edit)

        return tab

    # END_BLOCK_DETECTION_TAB

    # START_BLOCK_SAVE
    def save(self) -> None:
        self._project.llm.model = self._model_edit.text()
        self._project.llm.base_url = self._base_url_edit.text()

        try:
            self._project.detection.threshold = float(self._threshold_edit.text())
        except ValueError:
            self._project.detection.threshold = self._threshold_edit.text()

        try:
            self._project.detection.min_slide_duration = float(self._min_slide_edit.text())
        except ValueError:
            pass

        try:
            self._project.detection.min_stable_duration = float(self._min_stable_edit.text())
        except ValueError:
            pass

        save_project(self._project)
        self.settings_changed.emit()
        self.accept()
        logger.info("[GUI-Settings][save] Settings saved")
    # END_BLOCK_SAVE
