# FILE: src/video2pptx/gui/settings_project.py
# VERSION: 0.4.0
# START_MODULE_CONTRACT
#   PURPOSE: Project Settings QDialog — form-only detection parameters including analysis quality presets.
#            Does NOT persist. Returns DetectionConfig for caller to apply via domain path.
#   SCOPE: QDialog with form fields from DetectionConfig; analysis quality combo + custom spin
#   DEPENDS: PySide6, M-DOMAIN-PROJECT, M-ANALYSIS-QUALITY, M-GUI-ROI-SELECTOR
#   LINKS: M-GUI-SETTINGS-PROJECT, Phase-20
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ProjectSettingsDialog - form-only QDialog returns canonical DetectionConfig
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.5.0 - Phase 21: Qt adapter; workflow lives in application/project_settings_flow
# END_CHANGE_SUMMARY

from __future__ import annotations

from collections.abc import Callable

from loguru import logger
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from video2pptx.analysis_quality import (
    ANALYSIS_MAX_SIDE_MAX,
    ANALYSIS_MAX_SIDE_MIN,
    FULL_RES_NOTICE,
    PRESET_DESCRIPTIONS,
    PRESET_UI_LABELS,
    AnalysisQualityPreset,
    max_side_from_preset,
    preset_from_max_side,
    validate_custom_max_side,
)
from video2pptx.application.project_settings_flow import (
    SettingsApplyResult,
    restore_detection_and_pipeline,
    should_confirm_analysis_quality_change,
    snapshot_detection_config,
)
from video2pptx.application.project_settings_flow import (
    run_project_settings_flow as _run_project_settings_flow_core,
)
from video2pptx.domain.project import DetectionConfig
from video2pptx.gui.roi_selector import RoiSelectorDialog

# Re-export Qt-free names for backward-compatible imports from this module.
__all__ = [
    "ProjectSettingsDialog",
    "SettingsApplyResult",
    "prompt_detection_settings",
    "restore_detection_and_pipeline",
    "run_project_settings_flow",
    "should_confirm_analysis_quality_change",
    "snapshot_detection_config",
]


class ProjectSettingsDialog(QDialog):
    # START_CONTRACT: ProjectSettingsDialog
    #   PURPOSE: Form-only QDialog for detection settings. Returns updated DetectionConfig.
    #   INPUTS: { config: DetectionConfig, parent: QWidget, frame_grabber: Callable }
    #   OUTPUTS: result_config DetectionConfig after accept
    #   SIDE_EFFECTS: none (caller handles persistence)
    #   LINKS: M-GUI-SETTINGS-PROJECT
    # END_CONTRACT: ProjectSettingsDialog

    def __init__(
        self,
        config: DetectionConfig,
        parent: QWidget | None = None,
        frame_grabber: Callable[[], QPixmap | None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._result_config: DetectionConfig | None = None
        self._frame_grabber = frame_grabber
        self.setWindowTitle("Project Settings")
        self.setMinimumWidth(440)
        self._setup_ui()
        self._load_values()

    # START_BLOCK_SETUP_UI
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # --- Analysis quality (Phase 20) ---
        analysis_group = QGroupBox("Анализ видео")
        analysis_layout = QFormLayout(analysis_group)

        self._quality_combo = QComboBox()
        self._preset_order = [
            AnalysisQualityPreset.FAST,
            AnalysisQualityPreset.DETAILED,
            AnalysisQualityPreset.NATIVE,
            AnalysisQualityPreset.CUSTOM,
        ]
        for preset in self._preset_order:
            # Store enum *value* string — Qt userData can mishandle Enum instances.
            self._quality_combo.addItem(PRESET_UI_LABELS[preset], preset.value)
        self._quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        analysis_layout.addRow("Качество анализа:", self._quality_combo)

        self._quality_desc = QLabel()
        self._quality_desc.setWordWrap(True)
        analysis_layout.addRow(self._quality_desc)

        self._custom_spin = QSpinBox()
        self._custom_spin.setRange(ANALYSIS_MAX_SIDE_MIN, ANALYSIS_MAX_SIDE_MAX)
        self._custom_spin.setSingleStep(16)
        self._custom_spin.setSuffix(" пикселей")
        self._custom_spin.setValue(480)
        analysis_layout.addRow("Максимальная сторона кадра для анализа:", self._custom_spin)

        notice = QLabel(FULL_RES_NOTICE)
        notice.setWordWrap(True)
        notice.setStyleSheet("color: #555;")
        analysis_layout.addRow(notice)

        layout.addWidget(analysis_group)

        # Detection group
        det_group = QGroupBox("Detection")
        det_layout = QFormLayout(det_group)

        self._roi_edit = QLineEdit()
        self._roi_edit.setPlaceholderText("auto, full, or x1,y1,x2,y2")
        det_layout.addRow("Slide ROI:", self._roi_edit)

        self._ignore_roi_edit = QLineEdit()
        self._ignore_roi_edit.setPlaceholderText("x1,y1,x2,y2; x1,y1,x2,y2")

        ignore_row = QHBoxLayout()
        ignore_row.addWidget(self._ignore_roi_edit, stretch=1)
        btn_roi_selector = QPushButton("Select ROI")
        btn_roi_selector.setToolTip("Open visual ROI selector (video frame must be loaded)")
        btn_roi_selector.clicked.connect(self._on_open_roi_selector)
        ignore_row.addWidget(btn_roi_selector)
        det_layout.addRow("Ignore ROIs:", ignore_row)

        self._threshold_edit = QLineEdit()
        self._threshold_edit.setPlaceholderText("auto or 0.0-1.0")
        det_layout.addRow("Threshold:", self._threshold_edit)

        self._fps_spin = QDoubleSpinBox()
        self._fps_spin.setRange(0.1, 30.0)
        self._fps_spin.setSingleStep(0.5)
        det_layout.addRow("Sample FPS:", self._fps_spin)

        self._backend_combo = QComboBox()
        self._backend_combo.addItems(["auto", "opencv", "pyav", "decord"])
        det_layout.addRow("Decoder Backend:", self._backend_combo)

        self._min_dur_spin = QDoubleSpinBox()
        self._min_dur_spin.setRange(0.5, 60.0)
        self._min_dur_spin.setSingleStep(0.5)
        det_layout.addRow("Min Slide Duration (s):", self._min_dur_spin)

        self._min_stable_spin = QDoubleSpinBox()
        # 0.0 = debounce disabled; unit is seconds (not frames)
        self._min_stable_spin.setRange(0.0, 30.0)
        self._min_stable_spin.setSingleStep(0.5)
        self._min_stable_spin.setDecimals(2)
        det_layout.addRow("Min Stable Duration (s):", self._min_stable_spin)

        self._dedupe_check = QCheckBox("Enable deduplication")
        det_layout.addRow(self._dedupe_check)

        # Export group
        export_group = QGroupBox("Export after detection")
        export_layout = QVBoxLayout(export_group)

        self._export_md_check = QCheckBox("Export deck.md (Marp)")
        export_layout.addWidget(self._export_md_check)

        self._export_pptx_check = QCheckBox("Export deck.pptx")
        export_layout.addWidget(self._export_pptx_check)

        layout.addWidget(det_group)
        layout.addWidget(export_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # END_BLOCK_SETUP_UI

    def _current_preset(self) -> AnalysisQualityPreset:
        data = self._quality_combo.currentData()
        if isinstance(data, AnalysisQualityPreset):
            return data
        if isinstance(data, str):
            try:
                return AnalysisQualityPreset(data)
            except ValueError:
                pass
        return AnalysisQualityPreset.FAST

    def _on_quality_changed(self, _index: int = 0) -> None:
        preset = self._current_preset()
        self._quality_desc.setText(PRESET_DESCRIPTIONS[preset])
        is_custom = preset is AnalysisQualityPreset.CUSTOM
        self._custom_spin.setEnabled(is_custom)
        self._custom_spin.setVisible(is_custom)

    # START_BLOCK_ROI_SELECTOR
    def _on_open_roi_selector(self) -> None:
        if self._frame_grabber is None:
            logger.warning("[GUI-SettingsProject][_on_open_roi_selector] No frame grabber provided")
            return

        pixmap = self._frame_grabber()
        if pixmap is None or pixmap.isNull():
            logger.warning("[GUI-SettingsProject][_on_open_roi_selector] No frame available")
            return

        dlg = RoiSelectorDialog(pixmap, self)

        def on_rois_selected(rois: list) -> None:
            csv_parts = [",".join(str(v) for v in r) for r in rois]
            existing = self._ignore_roi_edit.text().strip()
            if existing:
                self._ignore_roi_edit.setText(existing + "; " + "; ".join(csv_parts))
            else:
                self._ignore_roi_edit.setText("; ".join(csv_parts))

        dlg.rois_selected.connect(on_rois_selected)
        dlg.exec()

    # END_BLOCK_ROI_SELECTOR

    # START_BLOCK_LOAD_VALUES
    def _load_values(self) -> None:
        dc = self._config
        self._roi_edit.setText(str(dc.slide_roi))
        self._ignore_roi_edit.setText("; ".join(
            ",".join(str(v) for v in roi) for roi in dc.ignore_rois
        ))
        self._threshold_edit.setText(str(dc.threshold))
        self._fps_spin.setValue(dc.sample_fps)
        self._backend_combo.setCurrentText(dc.decoder_backend)
        self._min_dur_spin.setValue(dc.min_slide_duration)
        self._min_stable_spin.setValue(dc.min_stable_duration)
        self._dedupe_check.setChecked(dc.dedupe_enabled)

        preset = preset_from_max_side(dc.analysis_max_side)
        idx = self._preset_order.index(preset)
        self._quality_combo.setCurrentIndex(idx)
        if preset is AnalysisQualityPreset.CUSTOM and dc.analysis_max_side is not None:
            self._custom_spin.setValue(int(dc.analysis_max_side))
        self._on_quality_changed()
    # END_BLOCK_LOAD_VALUES

    # START_BLOCK_ON_ACCEPT
    def _on_accept(self) -> None:
        raw_roi = self._roi_edit.text().strip()
        raw_ignore = self._ignore_roi_edit.text().strip()
        raw_thresh = self._threshold_edit.text().strip()

        ignore_rois: list[list[int]] = []
        if raw_ignore:
            for p in raw_ignore.split(";"):
                p = p.strip()
                if p:
                    try:
                        vals = [int(x.strip()) for x in p.split(",")]
                        if len(vals) == 4:
                            ignore_rois.append(vals)
                    except ValueError:
                        pass

        threshold: float | str = "auto"
        if raw_thresh:
            try:
                threshold = float(raw_thresh)
            except ValueError:
                threshold = raw_thresh

        try:
            analysis_max_side = max_side_from_preset(
                self._current_preset(),
                custom_value=self._custom_spin.value(),
            )
            if self._current_preset() is AnalysisQualityPreset.CUSTOM:
                validate_custom_max_side(analysis_max_side)
        except ValueError as exc:
            QMessageBox.warning(self, "Качество анализа", str(exc))
            return

        updated = DetectionConfig(
            sample_fps=self._fps_spin.value(),
            decoder_backend=self._backend_combo.currentText(),
            slide_roi=raw_roi or "auto",
            ignore_rois=ignore_rois,
            threshold=threshold,
            min_slide_duration=self._min_dur_spin.value(),
            min_stable_duration=self._min_stable_spin.value(),
            dedupe_enabled=self._dedupe_check.isChecked(),
            analysis_max_side=analysis_max_side,
        )
        self._result_config = updated
        logger.info(
            "[GUI-SettingsProject][_on_accept] Settings updated | "
            f"threshold={updated.threshold} fps={updated.sample_fps} "
            f"backend={updated.decoder_backend} analysis_max_side={updated.analysis_max_side}"
        )
        self.accept()

    @property
    def result_config(self) -> DetectionConfig | None:
        """Return updated DetectionConfig if dialog was accepted, else None."""
        return self._result_config
    # END_BLOCK_ON_ACCEPT


def prompt_detection_settings(
    parent: QWidget | None,
    current: DetectionConfig,
    frame_grabber: Callable[[], QPixmap | None] | None = None,
) -> DetectionConfig | None:
    """Show Project Settings dialog; return new DetectionConfig or None if cancelled."""
    dlg = ProjectSettingsDialog(current, parent, frame_grabber=frame_grabber)
    if not dlg.exec():
        return None
    return dlg.result_config


def run_project_settings_flow(
    parent: QWidget | None,
    project: object,
    save_fn: Callable[[], bool],
    status_fn: Callable[[str], None],
    frame_grabber: Callable[[], QPixmap | None] | None = None,
    reload_fn: Callable[[], bool] | None = None,
    confirm_fn: Callable[[str, str], bool] | None = None,
    prompt_fn: Callable[..., DetectionConfig | None] | None = None,
) -> SettingsApplyResult:
    """Qt adapter: optional QMessageBox confirm, dialog prompt, then Qt-free workflow."""

    def _qt_confirm(title: str, text: str) -> bool:
        reply = QMessageBox.warning(
            parent,
            title,
            text,
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return reply == QMessageBox.StandardButton.Ok

    return _run_project_settings_flow_core(
        parent=parent,
        project=project,
        save_fn=save_fn,
        status_fn=status_fn,
        frame_grabber=frame_grabber,
        reload_fn=reload_fn,
        confirm_fn=confirm_fn if confirm_fn is not None else _qt_confirm,
        prompt_fn=prompt_fn if prompt_fn is not None else prompt_detection_settings,
    )
