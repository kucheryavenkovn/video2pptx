# FILE: src/video2pptx/gui/timeline3/widget.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: TimelineWidget — top-level container for TimelineView, TrackHeaderPanel, HScrollBar, ZoomControls
#   SCOPE: QWidget that wraps TimelineView with headers and controls. Main interface used by MainWindow.
#   DEPENDS: PySide6, view, items
#   LINKS: M-GUI-TIMELINE3
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from video2pptx.gui.timeline3.view import TimelineView
from video2pptx.models import SlideSegment


class TrackHeaderPanel(QWidget):
    # START_CONTRACT: TrackHeaderPanel
    #   PURPOSE: Left-side labels for each timeline track
    #   INPUTS: none
    #   OUTPUTS: none (visual only)
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-TIMELINE3
    # END_CONTRACT: TrackHeaderPanel

    TRACK_NAMES = [
        ("subtitles", "Subtitles"),
        ("slides", "Slides"),
        ("markers", "Markers"),
        ("waveform", "Score"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(80)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        # Spacer for ruler area
        layout.addSpacing(28)

        from video2pptx.gui.timeline3.view import TimelineView
        heights = {
            "subtitles": TimelineView.TRACK_H_SUBS,
            "slides": TimelineView.TRACK_H_SLIDES,
            "markers": TimelineView.TRACK_H_MARKERS,
            "waveform": TimelineView.TRACK_H_WAVEFORM,
        }
        for key, name in self.TRACK_NAMES:
            h = heights.get(key, 24)
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            lbl.setStyleSheet("color: #888; font-size: 10px; padding-left: 4px;")
            lbl.setFixedHeight(h)
            layout.addWidget(lbl)

        layout.addStretch()


class TimelineWidget(QWidget):
    # START_CONTRACT: TimelineWidget
    #   PURPOSE: Top-level container — TimelineView + TrackHeaderPanel + HScrollBar + Zoom slider
    #   INPUTS: data via set_* methods
    #   OUTPUTS: signals: seek_requested(float), marker_added(float), marker_deleted(float), open_image(str)
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-TIMELINE3
    # END_CONTRACT: TimelineWidget

    seek_requested = Signal(float)
    open_image = Signal(str, int)  # path, slide_index
    add_manual_slide = Signal(float)  # timestamp
    slide_moved = Signal(int, float, float)  # index, new_start, new_end
    slide_resized = Signal(int, float, float)  # index, new_start, new_end
    open_subtitle_editor = Signal(int)  # slide_index

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    # START_BLOCK_SETUP_UI
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # View row: headers + timeline view
        view_row = QHBoxLayout()
        view_row.setContentsMargins(0, 0, 0, 0)
        view_row.setSpacing(0)

        self._headers = TrackHeaderPanel(self)
        view_row.addWidget(self._headers)

        self._view = TimelineView(self)
        view_row.addWidget(self._view, stretch=1)

        layout.addLayout(view_row, stretch=1)

        # Bottom controls row
        controls = QHBoxLayout()
        controls.setContentsMargins(4, 0, 4, 0)

        btn_fit = QPushButton("Fit")
        btn_fit.setToolTip("Zoom to fit entire video")
        btn_fit.setFixedWidth(40)
        btn_fit.clicked.connect(self._on_zoom_fit)
        controls.addWidget(btn_fit)

        btn_out = QPushButton("–")
        btn_out.setToolTip("Zoom out")
        btn_out.setFixedWidth(30)
        btn_out.clicked.connect(self._on_zoom_out)
        controls.addWidget(btn_out)

        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(10, 100)    # 10% - 1000%
        self._zoom_slider.setValue(50)          # 50 px/sec at 50%
        self._zoom_slider.setFixedWidth(120)
        self._zoom_slider.setToolTip("Zoom level")
        controls.addWidget(self._zoom_slider)

        btn_in = QPushButton("+")
        btn_in.setToolTip("Zoom in")
        btn_in.setFixedWidth(30)
        btn_in.clicked.connect(self._on_zoom_in)
        controls.addWidget(btn_in)

        self._zoom_label = QLabel("50 px/s")
        self._zoom_label.setFixedWidth(60)
        self._zoom_label.setStyleSheet("color: #888;")
        controls.addWidget(self._zoom_label)

        controls.addStretch()

        layout.addLayout(controls)
    # END_BLOCK_SETUP_UI

    # START_BLOCK_SIGNALS
    def _connect_signals(self) -> None:
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider)
        self._view.seek_requested.connect(self.seek_requested)
        self._view.open_image.connect(self.open_image)
        self._view.add_manual_slide.connect(self.add_manual_slide)
        self._view.slide_moved.connect(self.slide_moved)
        self._view.slide_resized.connect(self.slide_resized)
        self._view.open_subtitle_editor.connect(self.open_subtitle_editor)
    # END_BLOCK_SIGNALS

    # START_BLOCK_DATA
    def set_data(
        self,
        slides: list[SlideSegment],
        markers: list[dict],
        subtitles: list | None = None,
        score_timestamps: list[float] | None = None,
        score_values: list[float] | None = None,
        duration: float = 0.0,
    ) -> None:
        self._view.set_data(slides, markers, subtitles, score_timestamps, score_values, duration)
        if duration > 0:
            self._on_zoom_fit()

    def set_slides(self, slides: list[SlideSegment]) -> None:
        self._view._slides = slides
        self._view._rebuild_scene()

    def set_markers(self, markers: list[dict]) -> None:
        self._view._markers = markers
        self._view._rebuild_scene()

    def set_video_duration(self, duration: float) -> None:
        self._view._duration = duration
        self._view._rebuild_scene()

    def set_subtitles(self, subs) -> None:
        events = []
        if subs is not None:
            for ev in subs.events:
                events.append({"start": ev.start, "end": ev.end, "text": ev.plaintext})
        self._view._subtitles = events
        self._view._rebuild_scene()

    def set_scores(self, timestamps: list[float], values: list[float]) -> None:
        self._view._score_ts = timestamps
        self._view._score_vals = values
        self._view._rebuild_scene()

    def clear_scores(self) -> None:
        self._view._score_ts = []
        self._view._score_vals = []
        self._view._rebuild_scene()

    def set_position(self, seconds: float) -> None:
        self._view.set_position(seconds)

    def set_project(self, project) -> None:
        self._view._project = project
        if hasattr(project, 'output_dir'):
            self._view._project_dir = str(project.output_dir)

    # START_BLOCK_ZOOM
    def zoom_fit(self) -> None:
        self._on_zoom_fit()

    def _on_zoom_fit(self) -> None:
        dur = self._view._duration
        if dur <= 0:
            return
        view_w = self._view.viewport().width()
        px_per_sec = view_w / dur if dur > 0 and view_w > 0 else 50
        px_per_sec = max(1.0, px_per_sec)
        self._set_px_per_sec(px_per_sec)

    def _on_zoom_in(self) -> None:
        self._adjust_zoom(1.3)

    def _on_zoom_out(self) -> None:
        self._adjust_zoom(1.0 / 1.3)

    def _on_zoom_slider(self, value: int) -> None:
        # slider 10-100 → px_per_sec 5-500
        px = 5.0 + (value - 10) * (495.0 / 90.0)
        self._view.set_px_per_sec(px)
        self._zoom_label.setText(f"{px:.0f} px/s")

    def _set_px_per_sec(self, px: float) -> None:
        self._view.set_px_per_sec(px)
        sv = int(10 + (px - 5) * 90.0 / 495.0)
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(max(10, min(100, sv)))
        self._zoom_slider.blockSignals(False)
        self._zoom_label.setText(f"{px:.0f} px/s")

    def _adjust_zoom(self, factor: float) -> None:
        new_px = self._view._px_per_sec * factor
        self._set_px_per_sec(max(5.0, min(500.0, new_px)))
    # END_BLOCK_ZOOM
