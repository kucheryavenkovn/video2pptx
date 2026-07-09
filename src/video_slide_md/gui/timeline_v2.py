# FILE: src/video_slide_md/gui/timeline_v2.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Enhanced timeline with green (detected) and blue (manual) markers, double-click to open image, right-click context menu
#   SCOPE: QWidget with QPainter time axis, green/blue markers. Click, double-click, right-click interactions.
#   DEPENDS: PySide6, M-MODELS, M-GUI-MARKER-MANAGER
#   LINKS: M-GUI-TIMELINE-V2
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   TimelineV2Widget - custom QWidget with green/blue markers, context menu
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

from loguru import logger
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtCore import QUrl
from PySide6.QtGui import QBrush, QColor, QDesktopServices, QPainter, QPen
from PySide6.QtWidgets import QMenu, QWidget

from video_slide_md.models import SlideSegment
from video_slide_md.project_manager import Project


class TimelineV2Widget(QWidget):
    # START_CONTRACT: TimelineV2Widget
    #   PURPOSE: Custom QWidget drawing a time axis with green (detected) and blue (manual) markers
    #   INPUTS: { slides: list[SlideSegment], markers: list[dict], video_duration: float }
    #   OUTPUTS: signals: open_image(str), marker_added(float), marker_deleted(float)
    #   SIDE_EFFECTS: opens system viewer on double-click, shows context menu on right-click
    #   LINKS: M-GUI-TIMELINE-V2
    # END_CONTRACT: TimelineV2Widget

    open_image = Signal(str)
    marker_added = Signal(float)
    marker_deleted = Signal(float)

    MARKER_HEIGHT = 24
    TRACK_Y = 8

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._slides: list[SlideSegment] = []
        self._markers: list[dict] = []
        self._video_duration: float = 0.0
        self._project = None

        self.setMinimumHeight(60)
        self.setMouseTracking(True)

    # START_BLOCK_DATA
    def set_slides(self, slides: list[SlideSegment]) -> None:
        self._slides = slides
        self.update()

    def set_markers(self, markers: list[dict]) -> None:
        self._markers = markers
        self.update()

    def set_video_duration(self, duration: float) -> None:
        self._video_duration = duration
        self.update()

    def set_project(self, project: Project | None) -> None:
        self._project = project
    # END_BLOCK_DATA

    # START_BLOCK_POSITION
    def _ts_to_x(self, seconds: float) -> float:
        if self._video_duration <= 0:
            return 0
        margin = 40
        w = self.width() - 2 * margin
        return margin + (seconds / self._video_duration) * w

    def _x_to_ts(self, x: float) -> float:
        if self._video_duration <= 0:
            return 0
        margin = 40
        w = self.width() - 2 * margin
        if w <= 0:
            return 0
        return ((x - margin) / w) * self._video_duration
    # END_BLOCK_POSITION

    # START_BLOCK_PAINT
    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._video_duration <= 0:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No video loaded")
            return

        margin = 40
        w = self.width() - 2 * margin
        y = self.TRACK_Y
        h = self.MARKER_HEIGHT

        # Background track
        painter.fillRect(QRectF(margin, y, w, h), QBrush(QColor("#2d2d2d")))

        # Green markers for detected slides
        painter.setBrush(QBrush(QColor("#4caf50")))
        painter.setPen(QPen(QColor("#388e3c"), 1))
        for slide in self._slides:
            x1 = self._ts_to_x(slide.start)
            x2 = self._ts_to_x(slide.end)
            sw = max(x2 - x1, 4)
            painter.drawRect(QRectF(x1, y, sw, h))

        # Blue markers for manual markers
        painter.setBrush(QBrush(QColor("#2196f3")))
        painter.setPen(QPen(QColor("#1565c0"), 1))
        for marker in self._markers:
            snapped = marker.get("snapped_ts", marker.get("original_ts", 0))
            mx = self._ts_to_x(snapped)
            painter.drawRect(QRectF(mx - 2, y, 4, h))

        # Time labels (start, middle, end)
        painter.setPen(QPen(QColor("#aaa")))
        for frac, label in [(0, "0:00"), (0.5, self._fmt_time(self._video_duration / 2)), (1, self._fmt_time(self._video_duration))]:
            tx = margin + frac * w
            painter.drawText(QRectF(tx - 20, y + h + 4, 40, 16), Qt.AlignmentFlag.AlignCenter, label)

        painter.end()
    # END_BLOCK_PAINT

    # START_BLOCK_INTERACTION
    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        x = event.position().x()
        ts = self._x_to_ts(x)

        # Check if double-click on a green marker
        for slide in self._slides:
            if slide.start <= ts <= slide.end:
                image_path = self._resolve_image_path(slide.image)
                if image_path:
                    logger.info(f"[GUI-TimelineV2][double-click] Opening image | path={image_path}")
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(image_path)))
                    self.open_image.emit(str(image_path))
                return

        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        x = event.pos().x()
        ts = self._x_to_ts(x)
        menu = QMenu(self)

        # Check if clicking on existing blue marker
        existing: dict | None = None
        for marker in self._markers:
            snapped = marker.get("snapped_ts", marker.get("original_ts", 0))
            if abs(snapped - ts) < 1.0:
                existing = marker
                break

        if existing:
            menu.addAction("Delete Marker", lambda: self._delete_marker(existing))
            menu.addAction("Snap Again", lambda: self._resnap_marker(existing))
        else:
            menu.addAction(f"Add Marker at {self._fmt_time(ts)}", lambda: self._add_marker(ts))

        menu.exec(event.globalPos())

    def _add_marker(self, ts: float) -> None:
        self.marker_added.emit(ts)
        logger.info(f"[GUI-TimelineV2][_add_marker] Marker requested | ts={ts:.3f}")

    def _delete_marker(self, marker: dict) -> None:
        orig = marker.get("original_ts", 0)
        self.marker_deleted.emit(orig)
        logger.info(f"[GUI-TimelineV2][_delete_marker] Marker delete requested | ts={orig:.3f}")

    def _resnap_marker(self, marker: dict) -> None:
        orig = marker.get("original_ts", 0)
        self.marker_added.emit(orig)  # re-trigger snap
        logger.info(f"[GUI-TimelineV2][_resnap_marker] Marker resnap requested | ts={orig:.3f}")
    # END_BLOCK_INTERACTION

    # START_BLOCK_HELPERS
    def _resolve_image_path(self, relative_path: str) -> Path | None:
        if not relative_path or not self._project:
            return None
        base = Path(self._project.output_dir)
        full = base / relative_path
        if full.is_file():
            return full.resolve()
        return None

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        if seconds <= 0:
            return "0:00"
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}:{s:02d}"
    # END_BLOCK_HELPERS
