# FILE: src/video2pptx/gui/settings_project.py
# VERSION: 0.2.0
# START_MODULE_CONTRACT
#   PURPOSE: Project Settings QDialog — detection parameters (ROI, thresholds, fps, dedupe)
#   SCOPE: QDialog with form fields. Read/write via project.json. Emit signal on save. "Select ROI" button opens RoiSelectorDialog.
#   DEPENDS: PySide6, M-CONFIG, M-PROJECT, M-GUI-ROI-SELECTOR
#   LINKS: M-GUI-SETTINGS-PROJECT
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ProjectSettingsDialog - QDialog with detection parameter fields + visual ROI selector
# END_MODULE_MAP

from __future__ import annotations

from collections.abc import Callable

from loguru import logger
from PySide6.QtCore import Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
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

from video2pptx.gui.roi_selector import RoiSelectorDialog
from video2pptx.project_manager import Project, save_project


class ProjectSettingsDialog(QDialog):
    # START_CONTRACT: ProjectSettingsDialog
    #   PURPOSE: QDialog with form fields for detection parameters — ROI, thresholds, fps, dedupe
    #   INPUTS: { project: Project }
    #   OUTPUTS: Signal: settings_changed()
    #   SIDE_EFFECTS: writes project.json on accept
    #   LINKS: M-GUI-SETTINGS-PROJECT
    # END_CONTRACT: ProjectSettingsDialog

    settings_changed = Signal()

    def __init__(
        self,
        project: Project,
        parent: QWidget | None = None,
        frame_grabber: Callable[[], QPixmap | None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._project = project
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

        layout.addWidget(det_group)

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
        det = self._project.detection
        vc = self._project.video_config
        self._roi_edit.setText(str(det.slide_roi))
        self._ignore_roi_edit.setText("; ".join(
            ",".join(str(v) for v in roi) for roi in det.ignore_rois
        ))
        self._threshold_edit.setText(str(det.threshold))
        self._fps_spin.setValue(vc.sample_fps)
        self._min_dur_spin.setValue(det.min_slide_duration)
        self._min_stable_spin.setValue(det.min_stable_duration)
        self._dedupe_check.setChecked(det.dedupe_enabled)
    # END_BLOCK_LOAD_VALUES

    # START_BLOCK_ON_ACCEPT
    def _on_accept(self) -> None:
        det = self._project.detection
        vc = self._project.video_config

        det.slide_roi = self._roi_edit.text().strip() or "auto"

        raw = self._ignore_roi_edit.text().strip()
        if raw:
            parts = raw.split(";")
            rois: list[list[int]] = []
            for p in parts:
                p = p.strip()
                if p:
                    try:
                        vals = [int(x.strip()) for x in p.split(",")]
                        if len(vals) == 4:
                            rois.append(vals)
                    except ValueError:
                        pass
            det.ignore_rois = rois
        else:
            det.ignore_rois = []

        thresh = self._threshold_edit.text().strip()
        if thresh:
            try:
                det.threshold = float(thresh)
            except ValueError:
                det.threshold = thresh
        else:
            det.threshold = "auto"

        vc.sample_fps = self._fps_spin.value()
        det.min_slide_duration = self._min_dur_spin.value()
        det.min_stable_duration = self._min_stable_spin.value()
        det.dedupe_enabled = self._dedupe_check.isChecked()

        save_project(self._project)
        logger.info(
            "[GUI-SettingsProject][_on_accept] Project settings saved | "
            f"roi={det.slide_roi} threshold={det.threshold} fps={vc.sample_fps}"
        )
        self.settings_changed.emit()
        self.accept()
    # END_BLOCK_ON_ACCEPT
