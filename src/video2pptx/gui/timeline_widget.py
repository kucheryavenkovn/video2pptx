# FILE: src/video2pptx/gui/timeline_widget.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Custom timeline widget — QPainter-drawn time axis with colored slide blocks, click selection, subtitle panel
#   SCOPE: TimelineWidget renders slide intervals, emits selected_slide_changed signal, SubtitlePanel shows text
#   DEPENDS: PySide6, M-MODELS
#   LINKS: M-GUI-TIMELINE
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   TimelineWidget - custom QWidget with painted timeline and click interaction
# END_MODULE_MAP

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from video2pptx.models import SlideSegment


class TimelineWidget(QWidget):
    # START_CONTRACT: TimelineWidget
    #   PURPOSE: Custom widget that renders slide intervals as colored blocks on a time axis
    #   INPUTS: { slides: list[SlideSegment], video_duration: float }
    #   OUTPUTS: signal selected_slide_changed(int)
    #   SIDE_EFFECTS: paints on QPainter
    #   LINKS: M-GUI-TIMELINE
    # END_CONTRACT: TimelineWidget

    selected_slide_changed = Signal(int)

    def __init__(self, slides: list[SlideSegment], video_duration: float, parent=None) -> None:
        super().__init__(parent)
        self._slides = slides
        self._duration = video_duration
        self._selected: int | None = None
        self.setMinimumHeight(80)
        self.setMouseTracking(True)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor(240, 240, 240))

        if not self._slides or self._duration <= 0:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No slides")
            painter.end()
            return

        # Draw blocks
        block_h = h - 20
        for seg in self._slides:
            x1 = int((seg.start / self._duration) * w)
            x2 = int((seg.end / self._duration) * w)
            rect_ = (x1, 10, max(x2 - x1, 2), block_h)

            color = QColor(100, 150, 255) if seg.index == self._selected else QColor(70, 130, 220)
            painter.fillRect(*rect_, color)
            painter.setPen(QPen(Qt.GlobalColor.white, 1))
            painter.drawText(*rect_, Qt.AlignmentFlag.AlignCenter, str(seg.index))

        painter.end()

    def mousePressEvent(self, event) -> None:
        if not self._slides or self._duration <= 0:
            return

        x = event.position().x()
        w = self.width()
        for seg in self._slides:
            x1 = int((seg.start / self._duration) * w)
            x2 = int((seg.end / self._duration) * w)
            if x1 <= x <= x2:
                self._selected = seg.index
                self.selected_slide_changed.emit(seg.index)
                self.update()
                break

    def slide_count(self) -> int:
        return len(self._slides)

    def select_slide(self, index: int) -> None:
        if 0 <= index < len(self._slides):
            self._selected = self._slides[index].index
            self.selected_slide_changed.emit(self._slides[index].index)
            self.update()


class TimelinePanel(QWidget):
    # START_CONTRACT: TimelinePanel
    #   PURPOSE: Splitter layout with TimelineWidget (left) and SubtitlePanel (right)
    #   INPUTS: { slides: list[SlideSegment], video_duration: float }
    #   OUTPUTS: none
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-TIMELINE
    # END_CONTRACT: TimelinePanel

    def __init__(self, slides: list[SlideSegment], video_duration: float, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._timeline = TimelineWidget(slides, video_duration)
        self._subtitle_panel = SubtitlePanel(slides)

        splitter.addWidget(self._timeline)
        splitter.addWidget(self._subtitle_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        self._timeline.selected_slide_changed.connect(self._subtitle_panel.show_slide)

    def timeline(self) -> TimelineWidget:
        return self._timeline


class SubtitlePanel(QWidget):
    # START_CONTRACT: SubtitlePanel
    #   PURPOSE: Right panel showing subtitle text for a selected slide
    #   INPUTS: { slides: list[SlideSegment] }
    #   OUTPUTS: none
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-TIMELINE
    # END_CONTRACT: SubtitlePanel

    def __init__(self, slides: list[SlideSegment], parent=None) -> None:
        super().__init__(parent)
        self._slides = slides
        layout = QVBoxLayout(self)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        layout.addWidget(self._text_edit)

    def show_slide(self, index: int) -> None:
        for seg in self._slides:
            if seg.index == index:
                text = f"Slide {seg.index}  ({seg.start:.1f}s – {seg.end:.1f}s)\n\n"
                text += seg.transcript if seg.transcript else "(no transcript)"
                if seg.notes:
                    text += f"\n\nNotes:\n{seg.notes}"
                self._text_edit.setPlainText(text)
                break
