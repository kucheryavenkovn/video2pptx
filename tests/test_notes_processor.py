# FILE: tests/test_notes_processor.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for notes_processor module
#   SCOPE: Verify basic cleanup (join, punctuate, dedupe) and process_notes dispatch
#   DEPENDS: pytest, notes_processor, models
#   LINKS: M-NOTES-PROCESSOR, V-M-NOTES-PROCESSOR
#   ROLE: TEST
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT

from __future__ import annotations


from video2pptx.models import SlideSegment, SubtitleCue
from video2pptx.notes_processor import (
    SYSTEM_PROMPT_REPHRASE,
    LLM_REQUEST_TEMPLATE,
    process_notes,
    _basic_cleanup,
    _build_raw_text,
)


class TestBuildRawText:
    def test_with_cues(self):
        seg = SlideSegment(
            index=1, start=0.0, end=10.0, duration=10.0, representative_timestamp=5.0,
            subtitle_cues=[
                SubtitleCue(start=0.0, end=3.0, text="Hello"),
                SubtitleCue(start=3.5, end=6.0, text="world"),
            ],
        )
        assert _build_raw_text(seg) == "Hello world"

    def test_transcript_fallback(self):
        seg = SlideSegment(
            index=1, start=0.0, end=5.0, duration=5.0, representative_timestamp=2.5,
            transcript="Fallback text",
        )
        assert _build_raw_text(seg) == "Fallback text"

    def test_empty_segment(self):
        seg = SlideSegment(index=1, start=0.0, end=5.0, duration=5.0, representative_timestamp=2.5)
        assert _build_raw_text(seg) == ""


class TestBasicCleanup:
    def test_empty_string(self):
        assert _basic_cleanup("") == ""

    def test_none_empty(self):
        assert _basic_cleanup("   ") == ""

    def test_join_fragments(self):
        raw = "привет мир как дела"
        result = _basic_cleanup(raw)
        assert "привет мир как дела" in result.lower()

    def test_fix_punctuation_spacing(self):
        raw = "hello ,world"
        result = _basic_cleanup(raw)
        assert "hello" in result.lower()
        assert "world" in result.lower()
        assert " ," not in result

    def test_remove_leading_punctuation(self):
        raw = ",.hello"
        result = _basic_cleanup(raw)
        assert result.startswith("Hello") or result.startswith("hello")

    def test_capitalize_sentences(self):
        raw = "hello. world test."
        result = _basic_cleanup(raw)
        assert result == "Hello. World test."

    def test_deduplicate_repeated_words(self):
        raw = "the the quick brown fox"
        result = _basic_cleanup(raw)
        assert "the the" not in result

    def test_collapse_whitespace(self):
        raw = "hello    world\n\n\ntest"
        result = _basic_cleanup(raw)
        assert "  " not in result

    def test_space_before_punctuation(self):
        raw = "hello , world ."
        result = _basic_cleanup(raw)
        assert " ," not in result

    def test_merge_orphan_lines(self):
        raw = "Longer line of text here\nAnd"
        result = _basic_cleanup(raw)
        assert "And" in result


class TestProcessNotes:
    def test_basic_mode_with_cues(self):
        seg = SlideSegment(
            index=1, start=0.0, end=10.0, duration=10.0, representative_timestamp=5.0,
            subtitle_cues=[
                SubtitleCue(start=0.0, end=3.0, text="hello there"),
                SubtitleCue(start=3.5, end=6.0, text="how are you"),
            ],
        )
        result = process_notes(seg, mode="basic")
        assert "hello there" in result.lower()
        assert "how are you" in result.lower()

    def test_basic_mode_no_cues(self):
        seg = SlideSegment(
            index=1, start=0.0, end=5.0, duration=5.0, representative_timestamp=2.5,
            transcript="some raw transcript",
        )
        result = process_notes(seg, mode="basic")
        assert "some raw transcript" in result.lower()

    def test_basic_mode_empty_segment(self):
        seg = SlideSegment(index=1, start=0.0, end=5.0, duration=5.0, representative_timestamp=2.5)
        result = process_notes(seg, mode="basic")
        assert result == ""

    def test_basic_mode_default(self):
        seg = SlideSegment(
            index=1, start=0.0, end=5.0, duration=5.0, representative_timestamp=2.5,
            transcript="default mode test",
        )
        result = process_notes(seg)
        assert "default mode test" in result.lower()

    def test_prompt_templates_exist(self):
        assert len(SYSTEM_PROMPT_REPHRASE) > 50
        assert "{text}" in LLM_REQUEST_TEMPLATE
        assert "{start}" in LLM_REQUEST_TEMPLATE
        assert "{end}" in LLM_REQUEST_TEMPLATE
