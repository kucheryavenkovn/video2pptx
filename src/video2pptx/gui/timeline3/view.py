# FILE: src/video2pptx/gui/timeline3/view.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: TimelineView — QGraphicsView subclass with wheel zoom, middle-click pan, playhead, and track item management
#   SCOPE: Creates QGraphicsScene, manages all timeline items, handles zoom/pan, emits seek_requested
#   DEPENDS: PySide6, M-MODELS, items
#   LINKS: M-GUI-TIMELINE3
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT

from __future__ import annotations

from math import isnan

from loguru import logger
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QWheelEvent
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsView, QMenu

from video2pptx.gui.timeline3.items import (
    MarkerItem,
    PlayheadItem,
    SlideBlockItem,
    SubtitleTrackItem,
    TimeRulerItem,
)
from video2pptx.models import SlideSegment


class TimelineView(QGraphicsView):
    # START_CONTRACT: TimelineView
    #   PURPOSE: QGraphicsView with zoom/pan, manages scene items for all tracks
    #   INPUTS: data via set_* methods, user wheel/mouse events
    #   OUTPUTS: signals: seek_requested(float), marker_added(float), marker_deleted(float), open_image(str)
    #   SIDE_EFFECTS: creates QGraphicsScene, all timeline items
    #   LINKS: M-GUI-TIMELINE3
    # END_CONTRACT: TimelineView

    seek_requested = Signal(float)
    marker_added = Signal(float)
    marker_deleted = Signal(float)
    open_image = Signal(str)

    TRACK_Y = {  # vertical layout
        "ruler": 0,
        "slides": 30,
        "markers": 56,
        "subtitles": 80,
        "waveform": 130,
    }
    TRACK_H = {
        "slides": 24,
        "markers": 20,
        "subtitles": 44,
        "waveform": 44,
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._px_per_sec = 50.0
        self._duration = 0.0
        self._slides: list[SlideSegment] = []
        self._markers: list[dict] = []
        self._subtitles: list = []
        self._score_ts: list[float] = []
        self._score_vals: list[float] = []
        self._project = None

        self._ruler_item: TimeRulerItem | None = None
        self._playhead: PlayheadItem | None = None
        self._waveform_path: QGraphicsItem | None = None
        self._slide_items: list[SlideBlockItem] = []
        self._marker_items: list[MarkerItem] = []
        self._subtitle_items: list[SubtitleTrackItem] = []

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setStyleSheet("background-color: #1e1e1e; border: none;")
        self.setMouseTracking(True)

        self._is_panning = False
        self._pan_start = None

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
        self._slides = slides
        self._markers = markers
        self._duration = duration
        self._subtitles = subtitles or []
        self._score_ts = score_timestamps or []
        self._score_vals = score_values or []

        self._rebuild_scene()

    def set_position(self, seconds: float) -> None:
        if self._playhead is not None:
            self._playhead.set_position(seconds * self._px_per_sec)

    def set_px_per_sec(self, px_per_sec: float) -> None:
        self._px_per_sec = max(5.0, min(500.0, px_per_sec))
        self._rebuild_scene()
    # END_BLOCK_DATA

    # START_BLOCK_REBUILD
    def _rebuild_scene(self) -> None:
        self._scene.clear()
        self._slide_items = []
        self._marker_items = []
        self._subtitle_items = []
        self._waveform_path = None
        self._ruler_item = None
        self._playhead = None

        dur = self._duration
        subtitles = self._subtitles
        score_ts = self._score_ts
        score_vals = self._score_vals
        scene_w = max(dur * self._px_per_sec, self.width())
        scene_h = self._compute_scene_height()

        if dur <= 0:
            self._scene.setSceneRect(0, 0, scene_w, scene_h)
            return

        # Background bands
        self._scene.addRect(0, 0, scene_w, scene_h, pen=None, brush=QBrush(QColor("#1e1e1e")))

        # Track backgrounds
        track_colors = {
            "slides": "#262626",
            "markers": "#242424",
            "subtitles": "#222222",
            "waveform": "#202020",
        }
        for name, y in self.TRACK_Y.items():
            if name in track_colors:
                h = self.TRACK_H.get(name, 24)
                color = QColor(track_colors[name])
                self._scene.addRect(0, y, scene_w, h, pen=None, brush=QBrush(color))

        # Time ruler
        self._ruler_item = TimeRulerItem(scene_w, self._px_per_sec)
        self._scene.addItem(self._ruler_item)

        # Slide blocks
        y_slides = self.TRACK_Y["slides"]
        h_slides = self.TRACK_H["slides"]
        for slide in self._slides:
            x1 = slide.start * self._px_per_sec
            x2 = slide.end * self._px_per_sec
            w = max(x2 - x1, 4)
            item = SlideBlockItem(x1, y_slides, w, h_slides, slide.index, slide.image or "")
            self._slide_items.append(item)
            self._scene.addItem(item)

        # Markers
        y_markers = self.TRACK_Y["markers"]
        h_markers = self.TRACK_H["markers"]
        for marker in self._markers:
            snapped = marker.get("snapped_ts", marker.get("original_ts", 0))
            mx = snapped * self._px_per_sec
            item = MarkerItem(
                mx - 3, y_markers, 6, h_markers,
                float(marker.get("original_ts", 0)),
                float(snapped),
            )
            self._marker_items.append(item)
            self._scene.addItem(item)

        # Subtitles
        y_subs = self.TRACK_Y["subtitles"]
        if subtitles:
            for sub in subtitles:
                if isinstance(sub, dict):
                    start = float(sub.get("start", 0)) / 1000.0
                    end = float(sub.get("end", 0)) / 1000.0
                    text = str(sub.get("text", ""))
                else:
                    start = float(getattr(sub, "start", 0)) / 1000.0
                    end = float(getattr(sub, "end", 0)) / 1000.0
                    text = str(getattr(sub, "text", ""))
                sx = start * self._px_per_sec
                item = SubtitleTrackItem(text, start, end, self._px_per_sec)
                item.setPos(sx, y_subs)
                self._subtitle_items.append(item)
                self._scene.addItem(item)

        # Waveform
        if score_ts and score_vals:
            path = self._build_waveform_path(score_ts, score_vals)
            if path is not None:
                self._scene.addItem(path)

        # Playhead
        self._playhead = PlayheadItem(scene_h)
        self._scene.addItem(self._playhead)

        self._scene.setSceneRect(0, 0, scene_w, scene_h)
    # END_BLOCK_REBUILD

    # START_BLOCK_WAVEFORM
    def _build_waveform_path(self, timestamps: list[float], values: list[float]) -> QGraphicsItem | None:
        from PySide6.QtGui import QPainterPath

        if not timestamps or not values:
            return None

        y = self.TRACK_Y["waveform"]
        h = self.TRACK_H["waveform"]
        max_val = max((v for v in values if not isnan(v)), default=1.0)
        if max_val <= 0:
            max_val = 1.0

        path = QPainterPath()
        first = True
        for ts, sc in zip(timestamps, values):
            if isnan(sc):
                continue
            sx = ts * self._px_per_sec
            sy = y + h - (sc / max_val) * h
            if first:
                path.moveTo(sx, sy)
                first = False
            else:
                path.lineTo(sx, sy)

        if not path.isEmpty():
            # Fill area below
            last_ts = timestamps[-1]
            path.lineTo(last_ts * self._px_per_sec, y + h)
            path.lineTo(timestamps[0] * self._px_per_sec, y + h)
            path.closeSubpath()

            from PySide6.QtWidgets import QGraphicsPathItem
            item = QGraphicsPathItem(path)
            item.setBrush(QBrush(QColor(0, 150, 200, 40)))
            item.setPen(QPen(QColor(0, 180, 220), 1))
            return item

        return None
    # END_BLOCK_WAVEFORM

    # START_BLOCK_ZOOM_PAN
    def wheelEvent(self, event: QWheelEvent | None) -> None:  # noqa: N802
        if event is None:
            super().wheelEvent(event)
            return

        delta = event.angleDelta().y()
        if delta == 0:
            return

        factor = 1.15 if delta > 0 else 1.0 / 1.15
        new_px = self._px_per_sec * factor
        new_px = max(5.0, min(500.0, new_px))

        if abs(new_px - self._px_per_sec) < 0.5:
            return

        self._px_per_sec = new_px
        self._rebuild_scene()
        event.accept()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        # Left click on empty area → seek
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if item is None or item == self._scene:
                scene_pos = self.mapToScene(event.pos())
                ts = scene_pos.x() / self._px_per_sec if self._px_per_sec > 0 else 0
                ts = max(0, min(ts, self._duration))
                self.seek_requested.emit(ts)
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._is_panning and self._pan_start is not None:
            dx = event.pos().x() - self._pan_start.x()
            dy = event.pos().y() - self._pan_start.y()
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - dx
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - dy
            )
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.MiddleButton and self._is_panning:
            self._is_panning = False
            self._pan_start = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        item = self.itemAt(event.pos())
        if item is not None:
            marker_item = None
            p = item
            while p is not None:
                if isinstance(p, MarkerItem):
                    marker_item = p
                    break
                p = p.parentItem()

            if marker_item is not None:
                menu = QMenu(self)
                ts = marker_item.original_ts()
                menu.addAction("Delete Marker", lambda: self._delete_marker(ts))
                menu.addAction("Snap Again", lambda: self._resnap_marker(ts))
                menu.exec(event.screenPos())
                return

            # Check for slide
            slide_item = None
            p = item
            while p is not None:
                if isinstance(p, SlideBlockItem):
                    slide_item = p
                    break
                p = p.parentItem()

            if slide_item is not None:
                menu = QMenu(self)
                menu.addAction("Open Image", lambda: self._open_slide_image(slide_item))
                menu.exec(event.screenPos())
                return

        # Click on empty → add marker
        scene_pos = self.mapToScene(event.pos())
        ts = scene_pos.x() / self._px_per_sec if self._px_per_sec > 0 else 0
        ts = max(0, min(ts, self._duration))
        menu = QMenu(self)
        menu.addAction(f"Add Marker at {self._fmt_time(ts)}", lambda: self._add_marker(ts))
        menu.exec(event.screenPos())
    # END_BLOCK_ZOOM_PAN

    # START_BLOCK_ACTIONS
    def _add_marker(self, ts: float) -> None:
        self.marker_added.emit(ts)
        logger.info(f"[Timeline3][_add_marker] ts={ts:.3f}")

    def _delete_marker(self, ts: float) -> None:
        self.marker_deleted.emit(ts)
        logger.info(f"[Timeline3][_delete_marker] ts={ts:.3f}")

    def _resnap_marker(self, ts: float) -> None:
        self.marker_added.emit(ts)
        logger.info(f"[Timeline3][_resnap_marker] ts={ts:.3f}")

    def _open_slide_image(self, slide: SlideBlockItem) -> None:
        path = slide.image_path()
        if path:
            self.open_image.emit(path)
    # END_BLOCK_ACTIONS

    # START_BLOCK_HELPERS
    def _compute_scene_height(self) -> float:
        h = self.TRACK_Y["waveform"] + self.TRACK_H["waveform"] + 10
        return max(h, 200)

    def scene_width(self) -> float:
        return self._scene.sceneRect().width()

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        if seconds <= 0:
            return "0:00"
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}:{s:02d}"
    # END_BLOCK_HELPERS
