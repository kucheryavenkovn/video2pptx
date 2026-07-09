# FILE: tests/test_gui_timeline.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for timeline widget — rendering, click selection, subtitle panel
#   SCOPE: Verify TimelineWidget paints correct number of blocks, emits signal on click, subtitle panel updates
#   DEPENDS: pytest, PySide6, video_slide_md.models
#   LINKS: V-M-GUI-TIMELINE
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import sys

import pytest

pyside_available = False
try:
    from PySide6.QtWidgets import QApplication, QWidget, QTextEdit
    from PySide6.QtCore import QSignalSpy
    pyside_available = True
except ImportError:
    pass


def _ensure_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.mark.skipif(not pyside_available, reason="PySide6 not installed")
class TestTimelineWidget:
    def test_render_slides(self):
        """Timeline renders correct number of slide blocks matching input."""
        from video_slide_md.models import SlideSegment
        from video_slide_md.gui.timeline_widget import TimelineWidget

        _ensure_app()
        slides = [
            SlideSegment(index=1, start=0.0, end=10.0, duration=10.0, representative_timestamp=5.0),
            SlideSegment(index=2, start=10.0, end=20.0, duration=10.0, representative_timestamp=15.0),
            SlideSegment(index=3, start=20.0, end=30.0, duration=10.0, representative_timestamp=25.0),
        ]

        widget = TimelineWidget(slides=slides, video_duration=30.0)
        assert isinstance(widget, QWidget)
        assert widget.slide_count() == 3

    def test_select_emits_signal(self):
        """select_slide emits selected_slide_changed signal with correct index."""
        from video_slide_md.models import SlideSegment
        from video_slide_md.gui.timeline_widget import TimelineWidget

        _ensure_app()
        slides = [
            SlideSegment(index=1, start=0.0, end=10.0, duration=10.0, representative_timestamp=5.0),
            SlideSegment(index=2, start=10.0, end=20.0, duration=10.0, representative_timestamp=15.0),
        ]
        widget = TimelineWidget(slides=slides, video_duration=20.0)

        spy = QSignalSpy(widget.selected_slide_changed)
        widget.select_slide(1)
        assert len(spy) == 1
        assert spy[0][0] == 1  # emitted index

    def test_subtitle_panel_shows_text(self):
        """Subtitle panel displays correct text for selected segment."""
        from video_slide_md.models import SlideSegment
        from video_slide_md.gui.timeline_widget import TimelineWidget

        _ensure_app()
        slides = [
            SlideSegment(index=1, start=0.0, end=10.0, duration=10.0,
                         representative_timestamp=5.0, transcript="Hello world"),
        ]

        widget = TimelineWidget(slides=slides, video_duration=10.0)
        widget.select_slide(0)

        panel = widget.findChild(QTextEdit)
        assert panel is not None
        assert "Hello world" in panel.toPlainText()

    def test_empty_slides(self):
        """Empty slides list should not crash the widget."""
        from video_slide_md.gui.timeline_widget import TimelineWidget

        _ensure_app()
        widget = TimelineWidget(slides=[], video_duration=0.0)
        assert isinstance(widget, QWidget)
