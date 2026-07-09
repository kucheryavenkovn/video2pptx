# FILE: tests/test_segmenter.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for slide segment builder
#   SCOPE: Segment building, representative timestamp, short segment merging
#   DEPENDS: pytest, video2pptx.segmenter
#   LINKS: V-M-SEGMENTER
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import pytest

from video2pptx.models import FrameFeatures
from video2pptx.segmenter import (
    build_segments,
    choose_representative_timestamp,
)
from video2pptx.slide_detector import ChangeEvent


def make_change(timestamp: float) -> ChangeEvent:
    return ChangeEvent(
        timestamp=timestamp,
        score=0.5,
        features=FrameFeatures(timestamp=timestamp),
    )


class TestChooseRepresentativeTimestamp:
    def test_long_slide_uses_80_percent(self):
        ts = choose_representative_timestamp(0.0, 10.0)
        assert ts == pytest.approx(8.0)

    def test_short_slide_uses_50_percent(self):
        ts = choose_representative_timestamp(0.0, 4.0)
        assert ts == pytest.approx(2.0)

    def test_exactly_6_seconds_uses_80(self):
        ts = choose_representative_timestamp(0.0, 6.0)
        assert ts == pytest.approx(4.8)

    def test_rep_not_exceeding_end(self):
        ts = choose_representative_timestamp(0.0, 0.5)
        assert ts < 0.5

    def test_offset_slide(self):
        ts = choose_representative_timestamp(10.0, 20.0)
        assert ts == pytest.approx(18.0)


class TestBuildSegments:
    def test_no_changes_single_segment(self):
        segs = build_segments([], video_duration=100.0)
        assert len(segs) == 1
        assert segs[0].start == 0.0
        assert segs[0].end == 100.0

    def test_one_change_two_segments(self):
        changes = [make_change(30.0)]
        segs = build_segments(changes, video_duration=100.0, min_slide_duration=5.0)
        assert len(segs) == 2
        assert segs[0].start == 0.0
        assert segs[0].end == 30.0
        assert segs[1].start == 30.0
        assert segs[1].end == 100.0

    def test_segments_have_increasing_indices(self):
        changes = [make_change(20.0), make_change(50.0), make_change(80.0)]
        segs = build_segments(changes, video_duration=100.0)
        indices = [s.index for s in segs]
        assert indices == [1, 2, 3, 4]

    def test_short_segment_skipped(self):
        changes = [make_change(1.0)]  # 1s segment < 3s min
        segs = build_segments(changes, video_duration=100.0, min_slide_duration=3.0)
        assert len(segs) == 1  # first segment (0-1s) removed, second (1-100) kept
        assert segs[0].start == 1.0

    def test_short_first_segment_and_good_second(self):
        changes = [make_change(0.5)]  # 0.5s < 3s
        segs = build_segments(changes, video_duration=100.0, min_slide_duration=3.0)
        assert len(segs) == 1
        assert segs[0].start == 0.5

    def test_representative_timestamp_in_segment(self):
        changes = [make_change(50.0)]
        segs = build_segments(changes, video_duration=100.0)
        assert segs[0].representative_timestamp < segs[0].end
        assert segs[0].representative_timestamp >= segs[0].start

    def test_confidence_default(self):
        segs = build_segments([], video_duration=10.0)
        assert segs[0].confidence == 0.9

    def test_min_slide_duration_short_segment_removed(self):
        changes = [make_change(2.0)]
        segs = build_segments(changes, video_duration=100.0, min_slide_duration=5.0)
        assert len(segs) == 1
        assert segs[0].start == 2.0
