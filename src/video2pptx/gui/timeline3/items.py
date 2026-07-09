# FILE: src/video2pptx/gui/timeline3/items.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: QGraphicsItem subclasses for multi-track timeline: SlideBlockItem, SubtitleBlockItem, PlayheadItem, TimeRulerItem
#   SCOPE: Item classes with paint, bounding rect, interaction handling
#   DEPENDS: PySide6
#   LINKS: M-GUI-TIMELINE3
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY
#   v0.1.1 - SlideBlockItem.mouseReleaseEvent: update _start_sec/_end_sec after move/resize
# END_CHANGE_SUMMARY

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem


class SlideBlockItem(QGraphicsRectItem):
    # START_CONTRACT: SlideBlockItem
    #   PURPOSE: Green block — draggable (Alt+drag moves), resizable edges, left-click for image
    #   INPUTS: { x, y, w, h, slide_index, start_sec, end_sec, image_path, on_moved, on_resized }
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-TIMELINE3
    # END_CONTRACT: SlideBlockItem

    RESIZE_MARGIN = 6.0

    def __init__(
        self,
        x: float, y: float, w: float, h: float,
        slide_index: int,
        start_sec: float,
        end_sec: float,
        image_path: str = "",
        is_manual: bool = False,
        on_moved: Callable[[int, float, float], None] | None = None,
        on_resized: Callable[[int, float, float], None] | None = None,
        on_clicked: Callable[[str, int], None] | None = None,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(x, y, w, h, parent)
        self._slide_index = slide_index
        self._start_sec = start_sec
        self._end_sec = end_sec
        self._image_path = image_path
        self._is_manual = is_manual
        self._on_moved = on_moved
        self._on_resized = on_resized
        self._on_clicked = on_clicked
        self._drag_mode: str | None = None
        self._drag_start_scene_x: float = 0.0
        self._drag_start_item_x: float = 0.0
        self._drag_start_rect: tuple[float, float, float, float] = (0, 0, 0, 0)
        if self._is_manual:
            self.setBrush(QBrush(QColor("#ff9800")))
            self.setPen(QPen(QColor("#e65100"), 1))
        else:
            self.setBrush(QBrush(QColor("#4caf50")))
            self.setPen(QPen(QColor("#388e3c"), 1))
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self._locked_y: float = y
    # END_BLOCK_CONSTRUCTOR

    def slide_index(self) -> int:
        return self._slide_index

    def image_path(self) -> str:
        return self._image_path

    def start_sec(self) -> float:
        return self._start_sec

    def end_sec(self) -> float:
        return self._end_sec

    # START_BLOCK_INTERACTION
    def mousePressEvent(self, event) -> None:  # noqa: N802
        from PySide6.QtWidgets import QApplication
        modifiers = QApplication.keyboardModifiers()
        pos_x_in_rect = event.pos().x() - self.rect().x()
        w = self.rect().width()

        if modifiers & Qt.KeyboardModifier.AltModifier:
            self._drag_mode = "move"
            self._drag_start_item_x = self.pos().x() + self.rect().x()
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.update()
            super().mousePressEvent(event)
            return

        if pos_x_in_rect <= self.RESIZE_MARGIN:
            self._drag_mode = "resize_left"
            r = self.rect()
            self._drag_start_rect = (r.x(), r.y(), r.width(), r.height())
            self._drag_start_scene_x = event.scenePos().x()
            event.accept()
            return

        if pos_x_in_rect >= w - self.RESIZE_MARGIN:
            self._drag_mode = "resize_right"
            r = self.rect()
            self._drag_start_rect = (r.x(), r.y(), r.width(), r.height())
            self._drag_start_scene_x = event.scenePos().x()
            event.accept()
            return

        # Regular click on body → open image in player
        if self._on_clicked:
            self._on_clicked(self._image_path, self._slide_index)
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_mode == "resize_left":
            total_dx = event.scenePos().x() - self._drag_start_scene_x
            sx, sy, sw, sh = self._drag_start_rect
            new_w = max(4.0, sw - total_dx)
            new_x = sx + (sw - new_w)
            self.setRect(new_x, sy, new_w, sh)
            event.accept()
            return

        if self._drag_mode == "resize_right":
            total_dx = event.scenePos().x() - self._drag_start_scene_x
            sx, sy, sw, sh = self._drag_start_rect
            new_w = max(4.0, sw + total_dx)
            self.setRect(sx, sy, new_w, sh)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._drag_mode == "move":
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            new_x = self.pos().x() + self.rect().x()
            if abs(new_x - self._drag_start_item_x) > 0.5 and self.scene() is not None:
                views = self.scene().views()
                if views:
                    px = getattr(views[0], '_px_per_sec', 50.0)
                    new_start = max(0.0, new_x / px if px > 0 else 0.0)
                    new_end = max(new_start + 1.0, (new_x + self.rect().width()) / px if px > 0 else 0.0)
                    self._start_sec = new_start
                    self._end_sec = new_end
                    if self._on_moved:
                        self._on_moved(self._slide_index, new_start, new_end)

        elif self._drag_mode in ("resize_left", "resize_right") and self.scene() is not None:
            views = self.scene().views()
            if views:
                px = getattr(views[0], '_px_per_sec', 50.0)
                rx = self.rect().x()
                rw = self.rect().width()
                new_start = max(0.0, rx / px if px > 0 else 0.0)
                new_end = max(new_start + 1.0, (rx + rw) / px if px > 0 else 0.0)
                self._start_sec = new_start
                self._end_sec = new_end
                if self._on_resized:
                    self._on_resized(self._slide_index, new_start, new_end)

        self._drag_mode = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().mouseReleaseEvent(event)
    # END_BLOCK_INTERACTION

    def itemChange(self, change, value):  # noqa: N802
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self._drag_mode == "move":
            value.setY(0)  # lock vertical movement
        return super().itemChange(change, value)

    # START_BLOCK_HOVER
    def hoverMoveEvent(self, event) -> None:  # noqa: N802
        from PySide6.QtWidgets import QApplication
        modifiers = QApplication.keyboardModifiers()
        pos_x_in_rect = event.pos().x() - self.rect().x()
        w = self.rect().width()

        if modifiers & Qt.KeyboardModifier.AltModifier:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif pos_x_in_rect <= self.RESIZE_MARGIN or pos_x_in_rect >= w - self.RESIZE_MARGIN:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().hoverMoveEvent(event)
    # END_BLOCK_HOVER


class SubtitleBlockItem(QGraphicsRectItem):
    # START_CONTRACT: SubtitleBlockItem
    #   PURPOSE: Orange subtitle interval block — click to seek, Alt+drag to move (Y-locked)
    #   INPUTS: { x, y, w, h, start_sec, end_sec, text, on_clicked }
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-TIMELINE3
    # END_CONTRACT: SubtitleBlockItem

    def __init__(
        self,
        x: float, y: float, w: float, h: float,
        start_sec: float,
        end_sec: float,
        text: str,
        on_clicked: Callable[[float], None] | None = None,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(x, y, max(w, 4), h, parent)
        self._start_sec = start_sec
        self._end_sec = end_sec
        self._on_clicked = on_clicked
        self.setBrush(QBrush(QColor(255, 152, 0, 140)))
        self.setPen(QPen(QColor(255, 152, 0), 1))
        self.setToolTip(f"[{self._fmt_time(start_sec)}–{self._fmt_time(end_sec)}] {text}")
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def start_sec(self) -> float:
        return self._start_sec

    def end_sec(self) -> float:
        return self._end_sec

    def mousePressEvent(self, event) -> None:  # noqa: N802
        from PySide6.QtWidgets import QApplication
        modifiers = QApplication.keyboardModifiers()
        if modifiers & Qt.KeyboardModifier.AltModifier:
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            super().mousePressEvent(event)
            return
        if self._on_clicked:
            self._on_clicked(self._start_sec)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable:
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):  # noqa: N802
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            value.setY(0)
        return super().itemChange(change, value)

    def hoverMoveEvent(self, event) -> None:  # noqa: N802
        from PySide6.QtWidgets import QApplication
        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.AltModifier:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().hoverMoveEvent(event)

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"


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
