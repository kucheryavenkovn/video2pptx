# FILE: tests/test_subtitles.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for subtitle parsing and alignment
#   SCOPE: SRT/VTT parsing, cue alignment, edge cases
#   DEPENDS: pytest, video_slide_md.subtitles
#   LINKS: V-M-SUBTITLES
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import pytest

from video_slide_md.models import SlideSegment, SubtitleCue
from video_slide_md.subtitles import (
    align_cues_to_segments,
    parse_subtitles,
)


# ---------- Fixtures ----------

SRT_CONTENT = """1
00:00:01,000 --> 00:00:04,000
Hello world

2
00:00:05,000 --> 00:00:08,500
This is a test

3
00:00:10,000 --> 00:00:12,000
Third cue
"""

VTT_CONTENT = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:04.000
Hello from VTT

00:00:05.000 --> 00:00:08.500
VTT second cue
"""

VTT_NO_HEADER = """WEBVTT

00:00:01.000 --> 00:00:04.000
Direct cue
"""


# ---------- Parsing Tests ----------

class TestParseSubtitles:
    def test_parse_srt(self):
        cues = parse_subtitles(SRT_CONTENT, format="srt")
        assert len(cues) == 3
        assert cues[0].text == "Hello world"
        assert cues[0].start == 1.0
        assert cues[0].end == 4.0

    def test_parse_srt_auto_detect(self):
        cues = parse_subtitles(SRT_CONTENT)
        assert len(cues) == 3

    def test_parse_vtt(self):
        cues = parse_subtitles(VTT_CONTENT, format="vtt")
        assert len(cues) == 2
        assert cues[0].text == "Hello from VTT"

    def test_parse_vtt_auto_detect(self):
        cues = parse_subtitles(VTT_CONTENT)
        assert len(cues) == 2

    def test_vtt_no_header(self):
        cues = parse_subtitles(VTT_NO_HEADER)
        assert len(cues) == 1

    def test_empty_content(self):
        cues = parse_subtitles("")
        assert cues == []

    def test_parse_timestamps_milliseconds(self):
        srt = """1
00:01:30,500 --> 00:01:35,750
Timestamp test
"""
        cues = parse_subtitles(srt)
        assert len(cues) == 1
        assert cues[0].start == 90.5
        assert cues[0].end == 95.75

    def test_multi_line_text_joined(self):
        srt = """1
00:00:01,000 --> 00:00:03,000
Line one
Line two
"""
        cues = parse_subtitles(srt)
        assert len(cues) == 1
        assert cues[0].text == "Line one Line two"

    def test_no_index_srt(self):
        # Some SRT files omit the index line
        srt = """00:00:01,000 --> 00:00:03,000
No index
"""
        cues = parse_subtitles(srt)
        assert len(cues) == 1


# ---------- Alignment Tests ----------

class TestAlignCuesToSegments:
    def test_simple_alignment(self):
        segs = [
            SlideSegment(index=1, start=0.0, end=10.0, duration=10.0, representative_timestamp=5.0, confidence=0.9),
            SlideSegment(index=2, start=10.0, end=20.0, duration=10.0, representative_timestamp=15.0, confidence=0.9),
        ]
        cues = [
            SubtitleCue(start=1.0, end=3.0, text="First"),
            SubtitleCue(start=12.0, end=14.0, text="Second"),
        ]
        result = align_cues_to_segments(segs, cues)
        assert len(result[0].subtitle_cues) == 1
        assert result[0].subtitle_cues[0].text == "First"
        assert result[0].transcript == "First"
        assert len(result[1].subtitle_cues) == 1
        assert result[1].subtitle_cues[0].text == "Second"

    def test_cue_at_boundary_goes_to_left_segment(self):
        segs = [
            SlideSegment(index=1, start=0.0, end=10.0, duration=10.0, representative_timestamp=5.0, confidence=0.9),
            SlideSegment(index=2, start=10.0, end=20.0, duration=10.0, representative_timestamp=15.0, confidence=0.9),
        ]
        cues = [
            SubtitleCue(start=9.5, end=10.5, text="Overlap"),
        ]
        result = align_cues_to_segments(segs, cues)
        # Cue overlaps both segments; assigned to first matching
        assert len(result[0].subtitle_cues) == 1

    def test_multiple_cues_per_segment(self):
        segs = [
            SlideSegment(index=1, start=0.0, end=10.0, duration=10.0, representative_timestamp=5.0, confidence=0.9),
        ]
        cues = [
            SubtitleCue(start=1.0, end=3.0, text="A"),
            SubtitleCue(start=4.0, end=6.0, text="B"),
        ]
        result = align_cues_to_segments(segs, cues)
        assert len(result[0].subtitle_cues) == 2
        assert result[0].transcript == "A B"

    def test_cue_outside_all_segments(self):
        segs = [
            SlideSegment(index=1, start=5.0, end=10.0, duration=5.0, representative_timestamp=7.5, confidence=0.9),
        ]
        cues = [
            SubtitleCue(start=0.0, end=3.0, text="Outside"),
        ]
        result = align_cues_to_segments(segs, cues)
        assert len(result[0].subtitle_cues) == 0

    def test_empty_cues(self):
        segs = [
            SlideSegment(index=1, start=0.0, end=10.0, duration=10.0, representative_timestamp=5.0, confidence=0.9),
        ]
        result = align_cues_to_segments(segs, [])
        assert result[0].transcript == ""

    def test_cues_are_sorted(self):
        segs = [
            SlideSegment(index=1, start=0.0, end=10.0, duration=10.0, representative_timestamp=5.0, confidence=0.9),
        ]
        cues = [
            SubtitleCue(start=5.0, end=7.0, text="B"),
            SubtitleCue(start=1.0, end=3.0, text="A"),
        ]
        result = align_cues_to_segments(segs, cues)
        assert result[0].subtitle_cues[0].text == "A"
