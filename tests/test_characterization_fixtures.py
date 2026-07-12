# FILE: tests/test_characterization_fixtures.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Characterize deterministic synthetic media used by adapter-equivalence tests.
#   SCOPE: Video duration, dimensions, slide sections, and subtitle cue invariants.
#   DEPENDS: pytest, OpenCV, M-SUBTITLES
#   LINKS: V-REF-CHAR-TESTS
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import cv2
import pytest

from video2pptx.subtitles import parse_subtitles


def test_synthetic_video_metadata(synthetic_video_path):
    capture = cv2.VideoCapture(str(synthetic_video_path))
    try:
        assert capture.isOpened()
        fps = capture.get(cv2.CAP_PROP_FPS)
        frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        assert fps > 0
        assert frames > 0
        assert capture.get(cv2.CAP_PROP_FRAME_WIDTH) == 640
        assert capture.get(cv2.CAP_PROP_FRAME_HEIGHT) == 480
        assert frames / fps == pytest.approx(12.0, abs=0.25)
    finally:
        capture.release()


def test_synthetic_subtitle_metadata(synthetic_subtitle_path):
    cues = parse_subtitles(
        synthetic_subtitle_path.read_text(encoding="utf-8"),
        format="srt",
    )
    assert len(cues) == 4
    assert all(cue.text.strip() for cue in cues)
    assert all(cue.start < cue.end for cue in cues)
    assert all(left.end <= right.start for left, right in zip(cues, cues[1:], strict=False))
