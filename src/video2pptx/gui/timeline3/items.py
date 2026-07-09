# FILE: src/video2pptx/gui/timeline3/items.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: QGraphicsItem subclasses for multi-track timeline: SlideBlockItem, MarkerItem, PlayheadItem, TimeRulerItem, SubtitleTrackItem
#   SCOPE: Item classes with paint, bounding rect, interaction handling
#   DEPENDS: PySide6
#   LINKS: M-GUI-TIMELINE3
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QTextOption
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem


class SlideBlockItem(QGraphicsRectItem):
    # START_CONTRACT: SlideBlockItem
    #   PURPOSE: Green block representing a detected slide interval on the timeline
    #   INPUTS: { x, y, w, h, slide_index: int, image_path: str }
    #   OUTPUTS: double-click → open_image signal
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-TIMELINE3
    # END_CONTRACT: SlideBlockItem

    def __init__(
        self,
        x: float, y: float, w: float, h: float,
        slide_index: int,
        image_path: str = "",
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(x, y, w, h, parent)
        self._slide_index = slide_index
        self._image_path = image_path
        self.setBrush(QBrush(QColor("#4caf50")))
        self.setPen(QPen(QColor("#388e3c"), 1))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

    def slide_index(self) -> int:
        return self._slide_index

    def image_path(self) -> str:
        return self._image_path


class MarkerItem(QGraphicsRectItem):
    # START_CONTRACT: MarkerItem
    #   PURPOSE: Blue draggable marker on the timeline
    #   INPUTS: { x, y, w, h, original_ts: float, snapped_ts: float }
    #   OUTPUTS: drag → marker_moved(old_ts, new_ts)
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-TIMELINE3
    # END_CONTRACT: MarkerItem

    marker_moved = Signal(float, float)  # old_ts, new_ts

    def __init__(
        self,
        x: float, y: float, w: float, h: float,
        original_ts: float,
        snapped_ts: float,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(x, y, w, h, parent)
        self._original_ts = original_ts
        self._snapped_ts = snapped_ts
        self.setBrush(QBrush(QColor("#2196f3")))
        self.setPen(QPen(QColor("#1565c0"), 1))
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def original_ts(self) -> float:
        return self._original_ts

    def snapped_ts(self) -> float:
        return self._snapped_ts


class PlayheadItem(QGraphicsRectItem):
    # START_CONTRACT: PlayheadItem
    #   PURPOSE: Red vertical line showing current playback position
    #   INPUTS: { scene_height: float }
    #   OUTPUTS: none (visual only)
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-TIMELINE3
    # END_CONTRACT: PlayheadItem

    def __init__(self, scene_height: float, parent: QGraphicsItem | None = None) -> None:
        super().__init__(0, 0, 3, scene_height, parent)
        self.setBrush(QBrush(QColor("#ff1744")))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setZValue(10)

    def set_position(self, x: float) -> None:
        self.setPos(x - 1.5, 0)


class SubtitleTrackItem(QGraphicsTextItem):
    # START_CONTRACT: SubtitleTrackItem
    #   PURPOSE: Subtitle text block on the subtitle track with word wrap
    #   INPUTS: { text: str, start_ts: float, end_ts: float, px_per_sec: float }
    #   OUTPUTS: none (visual only)
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-TIMELINE3
    # END_CONTRACT: SubtitleTrackItem

    def __init__(
        self,
        text: str,
        start_ts: float,
        end_ts: float,
        px_per_sec: float,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)
        self._start_ts = start_ts
        self._end_ts = end_ts
        self.setPlainText(text)

        font = QFont()
        font.setPointSize(9)
        self.setFont(font)
        self.setDefaultTextColor(QColor("#e0e0e0"))

        opt = self.document().defaultTextOption()
        opt.setWrapMode(QTextOption.WrapMode.WordWrap)
        opt.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.document().setDefaultTextOption(opt)

        dur = max(end_ts - start_ts, 0.5)
        tw = min(dur * px_per_sec, 400)
        self.setTextWidth(max(tw, 40))

    def start_ts(self) -> float:
        return self._start_ts

    def end_ts(self) -> float:
        return self._end_ts


class TimeRulerItem(QGraphicsRectItem):
    # START_CONTRACT: TimeRulerItem
    #   PURPOSE: Top ruler with tick marks and time labels
    #   INPUTS: { width: float, height: float, duration: float, px_per_sec: float }
    #   OUTPUTS: none (visual only)
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-TIMELINE3
    # END_CONTRACT: TimeRulerItem

    RULER_HEIGHT = 28

    def __init__(self, width: float, px_per_sec: float, parent: QGraphicsItem | None = None) -> None:
        super().__init__(0, 0, width, self.RULER_HEIGHT, parent)
        self._px_per_sec = px_per_sec
        self.setBrush(QBrush(QColor("#1e1e1e")))
        self.setPen(QPen(QColor("#333"), 1))
        self.setZValue(5)

    def set_px_per_sec(self, px_per_sec: float) -> None:
        self._px_per_sec = px_per_sec

    def paint(self, painter: QPainter, option, widget=None) -> None:
        super().paint(painter, option, widget)
        r = self.rect()
        painter.setPen(QPen(QColor("#666"), 1))

        # Dynamic tick interval based on zoom
        px_5s = self._px_per_sec * 5
        if px_5s < 20:
            tick_interval = 30.0
        elif px_5s < 50:
            tick_interval = 10.0
        elif px_5s < 120:
            tick_interval = 5.0
        else:
            tick_interval = 1.0

        t = 0.0
        while t * self._px_per_sec < r.width():
            x = t * self._px_per_sec
            is_major = abs(t % max(tick_interval, 1.0)) < 0.01
            th = 12 if is_major else 6
            painter.drawLine(int(x), int(r.height() - th), int(x), int(r.height()))

            if is_major:
                painter.setPen(QPen(QColor("#aaa")))
                m = int(t // 60)
                s = int(t % 60)
                label = f"{m}:{s:02d}"
                painter.drawText(int(x) - 20, 0, 40, int(r.height()) - th - 2, Qt.AlignmentFlag.AlignCenter, label)
                painter.setPen(QPen(QColor("#666"), 1))
            t += tick_interval / 5.0  # sub-ticks
