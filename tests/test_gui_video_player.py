# FILE: tests/test_gui_video_player.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for M-GUI-VIDEOPLAYER — VideoPlayerWidget
#   SCOPE: Smoke tests for widget creation, signals, utility methods
#   DEPENDS: pytest, PySide6 (offscreen), QtMultimedia
#   LINKS: M-GUI-VIDEOPLAYER
#   ROLE: TEST
#   MAP_MODE: NONE
# END_MODULE_CONTRACT

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

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


@pytest.mark.skipif(not pyside_available, reason="PySide6 not installed")
class TestVideoPlayerWidget:
    # START_CONTRACT: TestVideoPlayerWidget
    #   PURPOSE: Smoke tests for VideoPlayerWidget
    #   LINKS: M-GUI-VIDEOPLAYER
    # END_CONTRACT: TestVideoPlayerWidget

    def test_creates_without_error(self) -> None:
        _ensure_app()
        from video2pptx.gui.video_player import VideoPlayerWidget
        widget = VideoPlayerWidget()
        assert widget._video_item is not None
        assert widget._view is not None
        assert widget._play_btn is not None
        assert widget._stop_btn is not None
        assert widget._time_label is not None
        assert widget._seek_slider is not None
        assert widget._volume_slider is not None
        widget.deleteLater()

    def test_load_video_missing_does_not_crash(self) -> None:
        _ensure_app()
        from video2pptx.gui.video_player import VideoPlayerWidget
        widget = VideoPlayerWidget()
        widget.load_video("/nonexistent/video.mp4")  # should not crash
        widget.deleteLater()

    def test_play_pause_toggle(self) -> None:
        _ensure_app()
        from video2pptx.gui.video_player import VideoPlayerWidget
        widget = VideoPlayerWidget()

        with patch.object(widget._player, "play") as mock_play:
            widget._on_play_pause()  # not playing → play
            mock_play.assert_called_once()
        widget.deleteLater()

    def test_stop_resets_time(self) -> None:
        _ensure_app()
        from video2pptx.gui.video_player import VideoPlayerWidget
        widget = VideoPlayerWidget()

        with patch.object(widget._player, "stop"):
            widget.stop()
            assert widget._time_label.text() == "00:00 / 00:00"
        widget.deleteLater()

    def test_volume_slider_updates_audio(self) -> None:
        _ensure_app()
        from video2pptx.gui.video_player import VideoPlayerWidget
        widget = VideoPlayerWidget()

        with patch.object(widget._audio_output, "setVolume") as mock_vol:
            widget._volume_slider.setValue(75)
            # The signal triggers _on_volume_changed
            mock_vol.assert_called_with(0.75)
        widget.deleteLater()

    def test_position_changed_signal(self) -> None:
        _ensure_app()
        from video2pptx.gui.video_player import VideoPlayerWidget
        widget = VideoPlayerWidget()

        mock_handler = MagicMock()
        widget.positionChanged.connect(mock_handler)
        widget._on_position_changed(15000)  # 15 seconds
        mock_handler.assert_called_once_with(15.0)
        widget.deleteLater()

    def test_duration_changed_signal(self) -> None:
        _ensure_app()
        from video2pptx.gui.video_player import VideoPlayerWidget
        widget = VideoPlayerWidget()

        mock_handler = MagicMock()
        widget.durationChanged.connect(mock_handler)
        widget._on_duration_changed(120000)  # 120 seconds
        mock_handler.assert_called_once_with(120.0)
        widget.deleteLater()

    def test_fmt_time(self) -> None:
        _ensure_app()
        from video2pptx.gui.video_player import VideoPlayerWidget
        assert VideoPlayerWidget._fmt_time(0) == "00:00"
        assert VideoPlayerWidget._fmt_time(65) == "01:05"
        assert VideoPlayerWidget._fmt_time(3661) == "61:01"

    def test_set_subtitle_text_shows(self) -> None:
        _ensure_app()
        from video2pptx.gui.video_player import VideoPlayerWidget
        widget = VideoPlayerWidget()
        widget.set_subtitle_text("Hello subtitles")
        assert widget._subtitle_item.toPlainText() == "Hello subtitles"
        assert widget._subtitle_item.isVisible()
        widget.deleteLater()

    def test_set_subtitle_text_none_hides(self) -> None:
        _ensure_app()
        from video2pptx.gui.video_player import VideoPlayerWidget
        widget = VideoPlayerWidget()
        widget.set_subtitle_text("Hello")
        widget.set_subtitle_text(None)
        assert widget._subtitle_item.toPlainText() == ""
        assert not widget._subtitle_item.isVisible()
        widget.deleteLater()

    def test_set_subtitle_text_empty_hides(self) -> None:
        _ensure_app()
        from video2pptx.gui.video_player import VideoPlayerWidget
        widget = VideoPlayerWidget()
        widget.set_subtitle_text("")
        assert not widget._subtitle_item.isVisible()
        widget.deleteLater()

    def test_clear_video_resets_state(self) -> None:
        _ensure_app()
        from video2pptx.gui.video_player import VideoPlayerWidget
        widget = VideoPlayerWidget()

        from PySide6.QtCore import QUrl
        with patch.object(widget._player, "setSource") as mock_set:
            widget.clear_video()
            mock_set.assert_called_once_with(QUrl())

        assert widget._time_label.text() == "00:00 / 00:00"
        widget.deleteLater()
