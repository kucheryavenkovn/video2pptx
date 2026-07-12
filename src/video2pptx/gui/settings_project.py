# FILE: src/video2pptx/gui/settings_project.py
# VERSION: 0.3.0
# START_MODULE_CONTRACT
#   PURPOSE: Project Settings QDialog — form-only detection parameters (ROI, thresholds, fps, dedupe).
#            Does NOT persist. Emits settingsChanged signal with DetectionConfig for caller to save.
#   SCOPE: QDialog with form fields initialized from DetectionConfig. Return updated settings via signal.
#   DEPENDS: PySide6, M-DOMAIN-PROJECT, M-GUI-ROI-SELECTOR
#   LINKS: M-GUI-SETTINGS-PROJECT, V-REF-DETECTION-INPUT
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ProjectSettingsDialog - form-only QDialog returns canonical DetectionConfig
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.3.0 - Remove legacy persistence; use canonical DetectionConfig only
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
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from video2pptx.domain.project import DetectionConfig
from video2pptx.gui.roi_selector import RoiSelectorDialog


class ProjectSettingsDialog(QDialog):
    # START_CONTRACT: ProjectSettingsDialog
    #   PURPOSE: Form-only QDialog for detection settings. Returns updated DetectionConfig.
    #   INPUTS: { config: DetectionConfig, parent: QWidget, frame_grabber: Callable }
    #   OUTPUTS: Signal: settingsChanged(DetectionConfig)
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
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_values()

    # START_BLOCK_SETUP_UI
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

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
        self._min_stable_spin.setRange(0.5, 30.0)
        self._min_stable_spin.setSingleStep(0.5)
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

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # END_BLOCK_SETUP_UI

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

        updated = DetectionConfig(
            sample_fps=self._fps_spin.value(),
            decoder_backend=self._backend_combo.currentText(),
            slide_roi=raw_roi or "auto",
            ignore_rois=ignore_rois,
            threshold=threshold,
            min_slide_duration=self._min_dur_spin.value(),
            min_stable_duration=self._min_stable_spin.value(),
            dedupe_enabled=self._dedupe_check.isChecked(),
        )
        self._result_config = updated
        logger.info(
            "[GUI-SettingsProject][_on_accept] Settings updated | "
            f"threshold={updated.threshold} fps={updated.sample_fps} "
            f"backend={updated.decoder_backend}"
        )
        self.accept()

    @property
    def result_config(self) -> DetectionConfig | None:
        """Return updated DetectionConfig if dialog was accepted, else None."""
        return self._result_config
    # END_BLOCK_ON_ACCEPT
