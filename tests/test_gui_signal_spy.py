# FILE: tests/test_gui_signal_spy.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for SignalSpy.watch/watch_all
#   SCOPE: Signal discovery, single signal watch, watch_all
#   DEPENDS: video2pptx.gui.signal_spy, video2pptx.timeline_model, pytest
#   LINKS: V-M-GUI-SIGNAL-SPY
# END_MODULE_CONTRACT

from __future__ import annotations

from video2pptx.gui.signal_spy import SignalSpy
from video2pptx.timeline_model import Timeline


class TestSignalSpy:
    def test_watch_single_signal(self) -> None:
        timeline = Timeline()
        SignalSpy.watch(timeline, "trackAdded")

    def test_watch_all_timeline(self) -> None:
        timeline = Timeline()
        SignalSpy.watch_all(timeline)

    def test_watch_nonexistent_signal(self, caplog) -> None:
        timeline = Timeline()
        SignalSpy.watch(timeline, "no_such_signal")

    def test_watch_all_on_track(self) -> None:
        timeline = Timeline()
        track = timeline.create_track("slides")
        SignalSpy.watch_all(track)
