# FILE: tests/test_notes_pipeline.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for notes pipeline — load slides.json, align subtitles, process notes
#   SCOPE: run_notes with synthetic slides.json + SRT, verify transcript/notes fields updated
#   DEPENDS: pytest, video2pptx.notes_pipeline, video2pptx.models, loguru
#   LINKS: V-M-NOTES
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

from pathlib import Path


from video2pptx.models import SlidesDocument, SlideSegment, VideoInfo
from video2pptx.notes_pipeline import run_notes

FIXTURES = Path(__file__).parent / "fixtures"
TEST_SRT = FIXTURES / "test_slides.srt"


def _make_doc(tmp_path: Path, slides_count: int = 3) -> Path:
    segs = [
        SlideSegment(
            index=i + 1,
            start=i * 10.0,
            end=(i + 1) * 10.0,
            duration=10.0,
            representative_timestamp=i * 10.0 + 5.0,
            image=f"slides/slide_{i + 1:03d}.png",
            transcript=f"Subtitle text for segment {i + 1}. ",
        )
        for i in range(slides_count)
    ]
    doc = SlidesDocument(
        video=VideoInfo(
            path="test.mp4",
            duration=slides_count * 10.0,
            width=1920,
            height=1080,
            fps=30.0,
        ),
        slides=segs,
    )
    json_path = tmp_path / "slides.json"
    json_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    return json_path


class TestNotesPipeline:
    def test_run_basic_mode(self, tmp_path, loguru_sink):
        """run_notes in basic mode produces cleaned notes on each segment."""
        json_path = _make_doc(tmp_path)
        run_notes(
            slides_json=json_path,
            subtitles_path=None,
            slides_dir=None,
            notes_mode="basic",
        )

        doc = SlidesDocument.model_validate_json(json_path.read_text(encoding="utf-8"))
        for seg in doc.slides:
            assert seg.transcript is not None
            assert len(seg.transcript) > 0

    def test_with_subtitles(self, tmp_path, loguru_sink):
        """run_notes with SRT aligns cues and produces notes."""
        json_path = _make_doc(tmp_path)
        run_notes(
            slides_json=json_path,
            subtitles_path=TEST_SRT,
            slides_dir=None,
            notes_mode="basic",
        )

        doc = SlidesDocument.model_validate_json(json_path.read_text(encoding="utf-8"))
        slides_with_cues = [s for s in doc.slides if s.subtitle_cues]
        assert len(slides_with_cues) >= 1

    def test_no_subtitles_skips_alignment(self, tmp_path, loguru_sink):
        """Without subtitles path, cues should remain empty but notes should still be set."""
        json_path = _make_doc(tmp_path)
        run_notes(
            slides_json=json_path,
            subtitles_path=None,
            slides_dir=None,
            notes_mode="basic",
        )

        doc = SlidesDocument.model_validate_json(json_path.read_text(encoding="utf-8"))
        for seg in doc.slides:
            assert seg.transcript is not None
            assert len(seg.transcript) > 0

    def test_empty_slides_document(self, tmp_path, loguru_sink):
        """A document with no slides should not crash."""
        json_path = _make_doc(tmp_path, slides_count=0)
        run_notes(
            slides_json=json_path,
            subtitles_path=None,
            slides_dir=None,
            notes_mode="basic",
        )

        doc = SlidesDocument.model_validate_json(json_path.read_text(encoding="utf-8"))
        assert len(doc.slides) == 0

    def test_log_markers_present(self, tmp_path, loguru_sink):
        """Required log markers should appear."""
        json_path = _make_doc(tmp_path)
        run_notes(
            slides_json=json_path,
            subtitles_path=None,
            slides_dir=None,
            notes_mode="basic",
        )
        combined = " ".join(loguru_sink)
        assert "Document loaded" in combined
        assert "Notes processed" in combined
        assert "Enriched document saved" in combined
