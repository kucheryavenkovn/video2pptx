# FILE: tests/test_gui_subtitle_overlay.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for M-GUI-SUBTITLE-OVERLAY — SubtitleOverlayWidget
#   SCOPE: Tests for subtitle loading, text retrieval at time, sync, clear
#   DEPENDS: pytest, PySide6 (offscreen), pysubs2
#   LINKS: M-GUI-SUBTITLE-OVERLAY
#   ROLE: TEST
#   MAP_MODE: NONE
# END_MODULE_CONTRACT

from __future__ import annotations

import sys
from pathlib import Path

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


SRT_CONTENT = """\
1
00:00:01,000 --> 00:00:04,000
Hello world

2
00:00:05,000 --> 00:00:08,000
Second subtitle
"""


@pytest.fixture
def srt_file(tmp_path: Path) -> Path:
    path = tmp_path / "test.srt"
    path.write_text(SRT_CONTENT, encoding="utf-8")
    return path


@pytest.mark.skipif(not pyside_available, reason="PySide6 not installed")
class TestSubtitleOverlayWidget:
    # START_CONTRACT: TestSubtitleOverlayWidget
    #   PURPOSE: Verify subtitle overlay widget behavior
    #   LINKS: M-GUI-SUBTITLE-OVERLAY
    # END_CONTRACT: TestSubtitleOverlayWidget

    def test_creates_without_error(self) -> None:
        _ensure_app()
        from video_slide_md.gui.subtitle_overlay import SubtitleOverlayWidget
        widget = SubtitleOverlayWidget()
        assert widget._subs is None
        assert widget.isHidden()
        widget.deleteLater()

    def test_load_subtitles_from_file(self, srt_file: Path) -> None:
        _ensure_app()
        from video_slide_md.gui.subtitle_overlay import SubtitleOverlayWidget
        widget = SubtitleOverlayWidget()
        widget.load_subtitles(srt_file)
        assert widget._subs is not None
        assert len(widget._subs) == 2
        widget.deleteLater()

    def test_load_none_clears(self) -> None:
        _ensure_app()
        from video_slide_md.gui.subtitle_overlay import SubtitleOverlayWidget
        widget = SubtitleOverlayWidget()
        widget.load_subtitles(None)
        assert widget._subs is None
        assert widget.isHidden()
        widget.deleteLater()

    def test_load_missing_file_does_not_crash(self) -> None:
        _ensure_app()
        from video_slide_md.gui.subtitle_overlay import SubtitleOverlayWidget
        widget = SubtitleOverlayWidget()
        widget.load_subtitles("/nonexistent/file.srt")
        assert widget._subs is None
        widget.deleteLater()

    def test_get_text_at_time_returns_correct_cue(self, srt_file: Path) -> None:
        _ensure_app()
        from video_slide_md.gui.subtitle_overlay import SubtitleOverlayWidget
        widget = SubtitleOverlayWidget()
        widget.load_subtitles(srt_file)

        text = widget._get_text_at_time(2.0)
        assert text == "Hello world"

        text = widget._get_text_at_time(6.0)
        assert text == "Second subtitle"
        widget.deleteLater()

    def test_get_text_between_cues_returns_none(self, srt_file: Path) -> None:
        _ensure_app()
        from video_slide_md.gui.subtitle_overlay import SubtitleOverlayWidget
        widget = SubtitleOverlayWidget()
        widget.load_subtitles(srt_file)

        text = widget._get_text_at_time(4.5)
        assert text is None
        widget.deleteLater()

    def test_sync_to_position_shows_text(self, srt_file: Path) -> None:
        _ensure_app()
        from video_slide_md.gui.subtitle_overlay import SubtitleOverlayWidget
        widget = SubtitleOverlayWidget()
        widget.load_subtitles(srt_file)

        widget.sync_to_position(2.0)
        assert widget.text() == "Hello world"
        assert widget.isVisible()
        widget.deleteLater()

    def test_sync_to_position_hides_between_cues(self, srt_file: Path) -> None:
        _ensure_app()
        from video_slide_md.gui.subtitle_overlay import SubtitleOverlayWidget
        widget = SubtitleOverlayWidget()
        widget.load_subtitles(srt_file)

        widget.sync_to_position(4.5)
        assert widget.isHidden()
        widget.deleteLater()

    def test_sync_without_subtitles_hides(self) -> None:
        _ensure_app()
        from video_slide_md.gui.subtitle_overlay import SubtitleOverlayWidget
        widget = SubtitleOverlayWidget()

        widget.sync_to_position(10.0)
        assert widget.isHidden()
        widget.deleteLater()

    def test_clear_subtitles(self, srt_file: Path) -> None:
        _ensure_app()
        from video_slide_md.gui.subtitle_overlay import SubtitleOverlayWidget
        widget = SubtitleOverlayWidget()
        widget.load_subtitles(srt_file)
        assert widget._subs is not None

        widget.clear_subtitles()
        assert widget._subs is None
        assert widget.text() == ""
        assert widget.isHidden()
        widget.deleteLater()
