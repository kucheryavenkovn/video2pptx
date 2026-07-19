# FILE: tests/test_streaming_representatives.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Phase 21 Wave 7 — streaming Pass2 complexity and peak live frames
#   ROLE: TEST
#   LINKS: M-DETECT-SLIDES, Phase-21
# END_MODULE_CONTRACT

from __future__ import annotations

import numpy as np

from video2pptx.models import SlideSegment
from video2pptx.roi import SlideRegion
from video2pptx.streaming_representatives import stream_representatives_and_dedupe


def _seg(i: int, start: float, end: float) -> SlideSegment:
    return SlideSegment(
        index=i,
        start=start,
        end=end,
        duration=end - start,
        representative_timestamp=(start + end) / 2,
        confidence=0.9,
    )


def test_streaming_is_linear_not_frames_times_targets(tmp_path):
    """comparisons should be O(frames + targets), not frames×targets."""
    n_frames = 1000
    n_targets = 100
    frames = (
        type("VF", (), {"timestamp": i * 0.5, "image": np.zeros((8, 8, 3), dtype=np.uint8)})()
        for i in range(n_frames)
    )
    # Targets evenly spaced in the 0..500s range of frames
    segments = [
        _seg(i + 1, float(i * 5), float(i * 5 + 4))
        for i in range(n_targets)
    ]
    # representative timestamps = mid of each → 2.0, 7.0, ... within 0.5 steps
    result = stream_representatives_and_dedupe(
        frames=frames,
        segments=segments,
        slide_region=SlideRegion(roi=None),
        slides_dir=tmp_path / "slides",
        sample_tolerance=0.3,
        dedupe_enabled=False,
    )
    # frames×targets would be ~100_000; linear upper bound ~ frames + few * targets
    assert result.comparisons < n_frames * 5 + n_targets * 5
    assert result.comparisons < n_frames * n_targets // 10
    assert result.peak_live_fullres_frames <= 2
    assert result.screenshots_written == result.captured_count or result.screenshots_written >= 1


def test_peak_live_fullres_frames_at_most_two(tmp_path):
    frames = [
        type("VF", (), {"timestamp": float(t), "image": np.full((4, 4, 3), t % 255, dtype=np.uint8)})()
        for t in range(0, 20)
    ]
    segments = [_seg(1, 0, 5), _seg(2, 5, 10), _seg(3, 10, 15)]
    result = stream_representatives_and_dedupe(
        frames=iter(frames),
        segments=segments,
        slide_region=SlideRegion(roi=None),
        slides_dir=tmp_path / "slides",
        sample_tolerance=0.6,
        dedupe_enabled=True,
    )
    assert result.peak_live_fullres_frames <= 2
    # Sequential filenames
    names = sorted(p.name for p in (tmp_path / "slides").glob("slide_*.png"))
    for i, name in enumerate(names, start=1):
        assert name == f"slide_{i:03d}.png"


def test_stop_after_last_target(tmp_path):
    decoded = {"n": 0}

    def gen():
        for t in range(0, 100):
            decoded["n"] += 1
            yield type(
                "VF",
                (),
                {"timestamp": float(t), "image": np.zeros((2, 2, 3), dtype=np.uint8)},
            )()

    segments = [_seg(1, 0, 2), _seg(2, 3, 5)]  # reps at 1.0 and 4.0
    result = stream_representatives_and_dedupe(
        frames=gen(),
        segments=segments,
        slide_region=SlideRegion(roi=None),
        slides_dir=tmp_path / "slides",
        sample_tolerance=0.6,
        dedupe_enabled=False,
    )
    assert result.decoded_frames < 50  # must not read whole 100
    assert result.captured_count >= 1
