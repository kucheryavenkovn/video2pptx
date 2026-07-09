# FILE: tests/test_models.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for Pydantic data models
#   SCOPE: VideoInfo, Roi, SubtitleCue, FrameFeatures, SlideSegment, SlidesDocument serialization and validation
#   DEPENDS: pytest, pydantic, video2pptx.models
#   LINKS: V-M-MODELS
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import logging

import pytest
from pydantic import ValidationError

from video2pptx.models import (
    FrameFeatures,
    Roi,
    SlideSegment,
    SlidesDocument,
    SubtitleCue,
    VideoInfo,
)

logger = logging.getLogger(__name__)


class TestVideoInfo:
    # START_BLOCK_TEST_VIDEO_INFO
    def test_valid_video_info(self):
        vi = VideoInfo(path="video.mp4", duration=100.0, width=1920, height=1080, fps=30.0)
        assert vi.path == "video.mp4"
        assert vi.duration == 100.0
        assert vi.width == 1920
        assert vi.height == 1080
        assert vi.fps == 30.0

    def test_invalid_negative_duration(self):
        with pytest.raises(ValidationError):
            VideoInfo(path="v.mp4", duration=-1.0, width=1920, height=1080, fps=30.0)

    def test_serialization_roundtrip(self):
        vi = VideoInfo(path="v.mp4", duration=50.0, width=640, height=480, fps=24.0)
        data = vi.model_dump()
        restored = VideoInfo.model_validate(data)
        assert restored == vi
    # END_BLOCK_TEST_VIDEO_INFO


class TestRoi:
    # START_BLOCK_TEST_ROI
    def test_valid_roi(self):
        r = Roi(x1=100, y1=50, x2=1800, y2=1000)
        assert r.x1 == 100
        assert r.y1 == 50
        assert r.x2 == 1800
        assert r.y2 == 1000

    def test_roi_properties(self):
        r = Roi(x1=100, y1=50, x2=1800, y2=1000)
        assert r.width == 1700
        assert r.height == 950

    def test_as_tuple(self):
        r = Roi(x1=0, y1=0, x2=100, y2=200)
        assert r.as_tuple() == (0, 0, 100, 200)

    def test_negative_coordinates_rejected(self):
        with pytest.raises(ValidationError):
            Roi(x1=-1, y1=0, x2=100, y2=100)
    # END_BLOCK_TEST_ROI


class TestSubtitleCue:
    # START_BLOCK_TEST_SUBTITLE_CUE
    def test_valid_cue(self):
        cue = SubtitleCue(start=10.5, end=15.3, text="Hello world")
        assert cue.start == 10.5
        assert cue.end == 15.3
        assert cue.text == "Hello world"

    def test_negative_start_rejected(self):
        with pytest.raises(ValidationError):
            SubtitleCue(start=-1.0, end=5.0, text="bad")

    def test_serialization_roundtrip(self):
        cue = SubtitleCue(start=1.0, end=2.0, text="test")
        data = cue.model_dump()
        restored = SubtitleCue.model_validate(data)
        assert restored == cue
    # END_BLOCK_TEST_SUBTITLE_CUE


class TestFrameFeatures:
    # START_BLOCK_TEST_FRAME_FEATURES
    def test_defaults(self):
        ff = FrameFeatures(timestamp=0.0)
        assert ff.timestamp == 0.0
        assert ff.phash == ""
        assert ff.dhash == ""
        assert ff.hist == []
        assert ff.gray_mean == 0.0

    def test_valid_features(self):
        ff = FrameFeatures(
            timestamp=12.5,
            phash="abc123",
            dhash="def456",
            hist=[0.1, 0.2, 0.3],
            gray_mean=127.5,
        )
        assert ff.phash == "abc123"
        assert ff.dhash == "def456"
        assert len(ff.hist) == 3
        assert ff.gray_mean == 127.5

    def test_negative_timestamp_rejected(self):
        with pytest.raises(ValidationError):
            FrameFeatures(timestamp=-1.0)
    # END_BLOCK_TEST_FRAME_FEATURES


class TestSlideSegment:
    # START_BLOCK_TEST_SLIDE_SEGMENT
    def test_valid_segment(self):
        seg = SlideSegment(index=1, start=0.0, end=42.5, duration=42.5, representative_timestamp=35.0)
        assert seg.index == 1
        assert seg.start == 0.0
        assert seg.end == 42.5
        assert seg.duration == 42.5
        assert seg.representative_timestamp == 35.0
        assert seg.transcript == ""
        assert seg.confidence == 1.0
        assert seg.warnings == []

    def test_with_cues(self):
        cues = [SubtitleCue(start=5.0, end=10.0, text="part one")]
        seg = SlideSegment(
            index=2,
            start=0.0,
            end=20.0,
            duration=20.0,
            representative_timestamp=15.0,
            subtitle_cues=cues,
            transcript="part one",
            confidence=0.95,
        )
        assert len(seg.subtitle_cues) == 1
        assert seg.confidence == 0.95
        assert seg.transcript == "part one"

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            SlideSegment(index=1, start=0, end=10, duration=10, representative_timestamp=5, confidence=1.5)

    def test_index_must_be_positive(self):
        with pytest.raises(ValidationError):
            SlideSegment(index=0, start=0, end=10, duration=10, representative_timestamp=5)
    # END_BLOCK_TEST_SLIDE_SEGMENT


class TestSlidesDocument:
    # START_BLOCK_TEST_SLIDES_DOCUMENT
    def test_minimal_document(self):
        vi = VideoInfo(path="v.mp4", duration=10.0, width=640, height=480, fps=30.0)
        doc = SlidesDocument(video=vi)
        assert doc.schema_version == "1.0"
        assert len(doc.slides) == 0
        assert doc.config == {}
        assert doc.debug == {}

    def test_full_document(self):
        vi = VideoInfo(path="v.mp4", duration=100.0, width=1920, height=1080, fps=30.0)
        seg = SlideSegment(index=1, start=0.0, end=50.0, duration=50.0, representative_timestamp=40.0)
        doc = SlidesDocument(
            video=vi,
            slides=[seg],
            config={"sample_fps": 2, "threshold": "auto"},
            debug={"diff_scores_csv": "debug/scores.csv"},
        )
        assert len(doc.slides) == 1
        assert doc.config["sample_fps"] == 2

    def test_json_roundtrip(self):
        vi = VideoInfo(path="v.mp4", duration=100.0, width=1920, height=1080, fps=30.0)
        seg = SlideSegment(index=1, start=0.0, end=50.0, duration=50.0, representative_timestamp=40.0)
        doc = SlidesDocument(video=vi, slides=[seg])
        raw = doc.model_dump_json()
        restored = SlidesDocument.model_validate_json(raw)
        assert restored.video.duration == 100.0
        assert restored.slides[0].index == 1
        assert restored.slides[0].representative_timestamp == 40.0

    def test_json_schema_validation(self, loguru_sink):
        data = {
            "schema_version": "1.0",
            "video": {"path": "v.mp4", "duration": -1, "width": 640, "height": 480, "fps": 30},
            "slides": [],
            "config": {},
            "debug": {},
        }
        with pytest.raises(ValidationError):
            SlidesDocument.model_validate(data)
    # END_BLOCK_TEST_SLIDES_DOCUMENT
