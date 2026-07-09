# FILE: tests/test_timeline_model.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for timeline_model classes
#   SCOPE: Clip hierarchy, Track operations, Timeline container
#   DEPENDS: video2pptx.timeline_model, pytest
#   LINKS: V-M-TIMELINE-MODEL
# END_MODULE_CONTRACT

from __future__ import annotations

import pytest
from video2pptx.timeline_model import (
    Clip, SlideClip, SubtitleClip, MarkerClip, ScoreClip,
    Track, ScoreTrack, Timeline,
)


class TestClip:
    def test_uid_generated(self) -> None:
        c = Clip(0, 10)
        assert c.uid
        assert len(c.uid) == 8

    def test_duration(self) -> None:
        c = Clip(5, 15)
        assert c.duration == 10

    def test_contains(self) -> None:
        c = Clip(10, 20)
        assert c.contains(10)
        assert c.contains(15)
        assert c.contains(20)
        assert not c.contains(5)

    def test_overlaps(self) -> None:
        a = Clip(0, 10)
        b = Clip(5, 15)
        c = Clip(15, 20)
        assert a.overlaps(b)
        assert b.overlaps(a)
        assert not a.overlaps(c)


class TestSlideClip:
    def test_to_from_segment(self) -> None:
        from video2pptx.models import SlideSegment
        seg = SlideSegment(index=1, start=10.0, end=30.0, duration=20.0, representative_timestamp=15.0, transcript="Hello")
        clip = SlideClip.from_segment(seg)
        assert clip.index == 1
        assert clip.start_sec == 10.0
        assert clip.transcript == "Hello"
        back = clip.to_segment()
        assert back.index == 1
        assert back.start == 10.0


class TestTrack:
    def test_add_remove_clip(self, qtbot) -> None:
        track = Track("test")
        clip = SlideClip(0, 5)
        track.add_clip(clip)
        assert len(track.clips()) == 1
        assert track.name == "test"
        track.remove_clip(clip.uid)
        assert len(track.clips()) == 0

    def test_sort(self) -> None:
        track = Track("test")
        track.add_clip(SlideClip(10, 15))
        track.add_clip(SlideClip(0, 5))
        track.sort()
        assert track.clips()[0].start_sec == 0


class TestTimeline:
    def test_create_track(self) -> None:
        tl = Timeline()
        track = tl.create_track("slides")
        assert tl.track("slides") is track
        assert "slides" in tl.track_names()

    def test_duration_signal(self, qtbot) -> None:
        tl = Timeline()
        with qtbot.waitSignal(tl.durationChanged, timeout=1000):
            tl.duration = 120.0
        assert tl.duration == 120.0
