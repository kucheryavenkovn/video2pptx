# FILE: tests/test_dedupe.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for duplicate slide segment removal
#   SCOPE: Deduplication of similar segments, edge cases
#   DEPENDS: pytest, numpy, video_slide_md.dedupe
#   LINKS: V-M-DEDUPE
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import numpy as np
import pytest

from video_slide_md.dedupe import deduplicate_segments
from video_slide_md.models import SlideSegment


def make_seg(index: int, start: float, end: float) -> SlideSegment:
    return SlideSegment(
        index=index,
        start=start,
        end=end,
        duration=end - start,
        representative_timestamp=(start + end) / 2,
        confidence=0.9,
    )


class TestDeduplicateSegments:
    def test_empty_segments(self):
        assert deduplicate_segments([], {}) == []

    def test_single_segment_unchanged(self):
        seg = make_seg(1, 0.0, 10.0)
        result = deduplicate_segments([seg], {})
        assert len(result) == 1
        assert result[0] is seg

    def test_reuses_existing_when_no_frame(self):
        segs = [make_seg(1, 0.0, 10.0), make_seg(2, 10.0, 20.0)]
        result = deduplicate_segments(segs, {})
        assert len(result) == 2

    def test_no_duplicates_different_frames(self):
        frames = {
            5.0: np.full((50, 50, 3), 0, dtype=np.uint8),
            15.0: np.full((50, 50, 3), 255, dtype=np.uint8),
        }
        segs = [
            make_seg(1, 0.0, 10.0),
            make_seg(2, 10.0, 20.0),
        ]
        segs[0].representative_timestamp = 5.0
        segs[1].representative_timestamp = 15.0
        result = deduplicate_segments(segs, frames, max_distance=0.02)
        assert len(result) == 2

    def test_duplicates_merged(self):
        frames = {
            5.0: np.full((50, 50, 3), 128, dtype=np.uint8),
            15.0: np.full((50, 50, 3), 128, dtype=np.uint8),
        }
        segs = [
            make_seg(1, 0.0, 10.0),
            make_seg(2, 10.0, 20.0),
        ]
        segs[0].representative_timestamp = 5.0
        segs[1].representative_timestamp = 15.0
        result = deduplicate_segments(segs, frames, max_distance=0.02)
        assert len(result) == 1
        assert result[0].start == 0.0
        assert result[0].end == 20.0

    def test_reindexed_after_merge(self):
        frames = {
            5.0: np.full((50, 50, 3), 0, dtype=np.uint8),
            15.0: np.full((50, 50, 3), 0, dtype=np.uint8),
            25.0: np.full((50, 50, 3), 255, dtype=np.uint8),
        }
        segs = [
            make_seg(1, 0.0, 10.0),
            make_seg(2, 10.0, 20.0),
            make_seg(3, 20.0, 30.0),
        ]
        segs[0].representative_timestamp = 5.0
        segs[1].representative_timestamp = 15.0
        segs[2].representative_timestamp = 25.0
        result = deduplicate_segments(segs, frames, max_distance=0.02)
        assert len(result) == 2
        assert result[0].index == 1
        assert result[1].index == 2

    def test_high_confidence_preserved(self):
        frames = {
            5.0: np.full((50, 50, 3), 0, dtype=np.uint8),
            15.0: np.full((50, 50, 3), 0, dtype=np.uint8),
        }
        segs = [
            make_seg(1, 0.0, 10.0),
            make_seg(2, 10.0, 20.0),
        ]
        segs[0].representative_timestamp = 5.0
        segs[1].representative_timestamp = 15.0
        segs[1].confidence = 0.95
        result = deduplicate_segments(segs, frames, max_distance=0.02)
        assert len(result) == 1
        assert result[0].confidence == 0.95
