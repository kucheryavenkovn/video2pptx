# FILE: tests/test_gui_timeline_v2.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for M-GUI-TIMELINE-V2 — TimelineV2Widget
#   SCOPE: Smoke tests for rendering, signals, marker interaction
#   DEPENDS: pytest, PySide6 (offscreen), M-MODELS
#   LINKS: M-GUI-TIMELINE-V2
#   ROLE: TEST
#   MAP_MODE: NONE
# END_MODULE_CONTRACT

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pyside_available = False
try:
    from PySide6.QtWidgets import QApplication  # noqa: F401
    pyside_available = True
except ImportError:
    pass


def _ensure_app() -> None:
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        QApplication(sys.argv)


def make_slide(index: int, start: float, end: float, image: str = "") -> dict:
    return {
        "index": index,
        "start": start,
        "end": end,
        "duration": end - start,
        "image": image,
        "representative_timestamp": start + (end - start) / 2,
        "transcript": "",
        "subtitle_cues": [],
        "confidence": 1.0,
        "warnings": [],
    }


@pytest.mark.skipif(not pyside_available, reason="PySide6 not installed")
class TestTimelineV2Widget:
    # START_CONTRACT: TestTimelineV2Widget
    #   PURPOSE: Smoke tests for TimelineV2Widget
    #   LINKS: M-GUI-TIMELINE-V2
    # END_CONTRACT: TestTimelineV2Widget

    def test_creates_without_error(self) -> None:
        _ensure_app()
        from video_slide_md.gui.timeline_v2 import TimelineV2Widget
        widget = TimelineV2Widget()
        assert widget._slides == []
        assert widget._markers == []
        widget.deleteLater()

    def test_set_slides_updates_display(self) -> None:
        _ensure_app()
        from video_slide_md.gui.timeline_v2 import TimelineV2Widget
        widget = TimelineV2Widget()
        widget.set_video_duration(100.0)
        slides_data = [make_slide(1, 0.0, 10.0), make_slide(2, 10.0, 30.0)]

        from video_slide_md.models import SlideSegment
        slides = [SlideSegment(**s) for s in slides_data]
        widget.set_slides(slides)
        assert len(widget._slides) == 2
        widget.deleteLater()

    def test_set_markers_updates_display(self) -> None:
        _ensure_app()
        from video_slide_md.gui.timeline_v2 import TimelineV2Widget
        widget = TimelineV2Widget()
        widget.set_video_duration(100.0)
        widget.set_markers([{"original_ts": 25.0, "snapped_ts": 24.0, "snap_mode": "hybrid"}])
        assert len(widget._markers) == 1
        widget.deleteLater()

    def test_marker_added_signal(self) -> None:
        _ensure_app()
        from video_slide_md.gui.timeline_v2 import TimelineV2Widget
        widget = TimelineV2Widget()
        mock_handler = MagicMock()
        widget.marker_added.connect(mock_handler)

        widget._add_marker(15.0)
        mock_handler.assert_called_once_with(15.0)
        widget.deleteLater()

    def test_marker_deleted_signal(self) -> None:
        _ensure_app()
        from video_slide_md.gui.timeline_v2 import TimelineV2Widget
        widget = TimelineV2Widget()
        mock_handler = MagicMock()
        widget.marker_deleted.connect(mock_handler)

        widget._delete_marker({"original_ts": 20.0, "snapped_ts": 19.0})
        mock_handler.assert_called_once_with(20.0)
        widget.deleteLater()

    def test_fmt_time(self) -> None:
        _ensure_app()
        from video_slide_md.gui.timeline_v2 import TimelineV2Widget
        assert TimelineV2Widget._fmt_time(0) == "0:00"
        assert TimelineV2Widget._fmt_time(65) == "1:05"
        assert TimelineV2Widget._fmt_time(3661) == "61:01"

    def test_resolve_image_path_returns_none_without_project(self) -> None:
        _ensure_app()
        from video_slide_md.gui.timeline_v2 import TimelineV2Widget
        widget = TimelineV2Widget()
        result = widget._resolve_image_path("slides/slide_001.png")
        assert result is None
        widget.deleteLater()

    def test_resolve_image_path_with_project(self, tmp_path: Path) -> None:
        _ensure_app()
        from video_slide_md.gui.timeline_v2 import TimelineV2Widget
        from video_slide_md.project_manager import Project

        proj = Project(name="test", video="/tmp/test.mp4", output_dir=str(tmp_path))

        # Create the image file
        img_dir = tmp_path / "slides"
        img_dir.mkdir()
        img_file = img_dir / "slide_001.png"
        img_file.write_text("fake png")

        widget = TimelineV2Widget()
        widget.set_project(proj)
        result = widget._resolve_image_path("slides/slide_001.png")
        assert result is not None
        assert result.exists()
        widget.deleteLater()

    def test_ts_to_x_conversion(self) -> None:
        _ensure_app()
        from video_slide_md.gui.timeline_v2 import TimelineV2Widget
        widget = TimelineV2Widget()
        widget.set_video_duration(100.0)
        widget.resize(500, 60)

        # At ts=0, x should be near margin (40)
        x0 = widget._ts_to_x(0.0)
        assert abs(x0 - 40) < 1

        # At ts=duration, x should be near width - margin
        x_end = widget._ts_to_x(100.0)
        assert abs(x_end - 460) < 1

        # Round-trip
        ts = widget._x_to_ts(widget._ts_to_x(50.0))
        assert abs(ts - 50.0) < 0.1
        widget.deleteLater()
