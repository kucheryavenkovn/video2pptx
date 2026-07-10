# FILE: tests/test_auto_align.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for Auto Align algorithm
#   SCOPE: candidate generation, boundary alignment, invariant validation, dry run, idempotency
#   DEPENDS: pytest, video2pptx.auto_align
#   LINKS: V-M-AUTO-ALIGN
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from pathlib import Path

from video2pptx.auto_align import (
    AlignmentReport,
    SubtitleAnchorProvider,
    align_slides_to_subtitles,
    _validate_boundaries,
)
from video2pptx.models import SlideSegment, SubtitleCue


def make_seg(index: int, start: float, end: float, manual: bool = False) -> SlideSegment:
    return SlideSegment(
        index=index,
        start=start,
        end=end,
        duration=end - start,
        representative_timestamp=(start + end) / 2,
        manual=manual,
    )


def make_srt(tmp_path: Path, cues: list[tuple[float, float, str]]) -> Path:
    lines: list[str] = []
    for i, (start, end, text) in enumerate(cues, 1):
        def _fmt(sec: float) -> str:
            h = int(sec // 3600)
            m = int((sec % 3600) // 60)
            s = int(sec % 60)
            ms = int((sec % 1) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        lines.append(str(i))
        lines.append(f"{_fmt(start)} --> {_fmt(end)}")
        lines.append(text)
        lines.append("")
    p = tmp_path / "test.srt"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


class TestSubtitleAnchorProvider:
    def test_generates_anchors(self):
        cues = [
            SubtitleCue(start=0.0, end=3.0, text="a"),
            SubtitleCue(start=5.0, end=8.0, text="b"),
            SubtitleCue(start=10.0, end=12.0, text="c"),
        ]
        provider = SubtitleAnchorProvider(cues)
        anchors = provider.anchors(20.0)
        assert 0.0 in anchors
        assert 5.0 in anchors
        assert 10.0 in anchors

    def test_gap_midpoint(self):
        cues = [
            SubtitleCue(start=0.0, end=3.0, text="a"),
            SubtitleCue(start=7.0, end=10.0, text="b"),
        ]
        provider = SubtitleAnchorProvider(cues)
        anchors = provider.anchors(20.0)
        assert 5.0 in anchors


class TestValidateBoundaries:
    def test_valid_boundaries(self):
        slides = [make_seg(1, 0.0, 10.0), make_seg(2, 10.0, 20.0)]
        errors = _validate_boundaries(slides, 20.0)
        assert len(errors) == 0

    def test_negative_start(self):
        slides = [make_seg(1, 0.0, 0.5)]
        errors = _validate_boundaries(slides, 20.0, min_duration=1.0)
        assert any("duration" in e for e in errors)

    def test_start_ge_end(self):
        slides = [make_seg(1, 10.0, 10.0)]
        errors = _validate_boundaries(slides, 20.0)
        assert any("start >= end" in e for e in errors)


class TestAlignSlidesToSubtitles:
    def test_single_slide_no_boundaries(self, tmp_path):
        srt = make_srt(tmp_path, [(0, 5, "a"), (5, 10, "b")])
        slides = [make_seg(1, 0.0, 30.0)]
        report = align_slides_to_subtitles(slides, srt, video_duration=30.0)
        assert report.boundaries_total == 0

    def test_dry_run_no_modification(self, tmp_path):
        srt = make_srt(tmp_path, [(0, 5, "a"), (6, 12, "b"), (15, 25, "c")])
        slides = [make_seg(1, 0.0, 10.0), make_seg(2, 10.0, 30.0)]
        original_end = slides[0].end
        report = align_slides_to_subtitles(slides, srt, dry_run=True, video_duration=30.0)
        assert slides[0].end == original_end
        assert len(report.details) == 1

    def test_apply_modifies_slides(self, tmp_path):
        srt = make_srt(tmp_path, [(0, 5, "a"), (6, 12, "b"), (15, 25, "c")])
        slides = [make_seg(1, 0.0, 10.0), make_seg(2, 10.0, 30.0)]
        report = align_slides_to_subtitles(slides, srt, dry_run=False, max_shift_sec=3.0, video_duration=30.0)
        assert slides[0].end == slides[1].start
        assert report.boundaries_total == 1

    def test_manual_boundary_skipped(self, tmp_path):
        srt = make_srt(tmp_path, [(0, 5, "a"), (6, 12, "b")])
        slides = [make_seg(1, 0.0, 10.0, manual=True), make_seg(2, 10.0, 30.0, manual=True)]
        report = align_slides_to_subtitles(slides, srt, include_manual=False, video_duration=30.0)
        assert report.boundaries_total == 0

    def test_manual_boundary_included(self, tmp_path):
        srt = make_srt(tmp_path, [(0, 5, "a"), (6, 12, "b")])
        slides = [make_seg(1, 0.0, 10.0, manual=True), make_seg(2, 10.0, 30.0, manual=True)]
        report = align_slides_to_subtitles(slides, srt, include_manual=True, video_duration=30.0)
        assert report.boundaries_total == 1

    def test_idempotency(self, tmp_path):
        srt = make_srt(tmp_path, [(0, 5, "a"), (6, 12, "b"), (15, 25, "c")])
        slides = [make_seg(1, 0.0, 10.0), make_seg(2, 10.0, 30.0)]
        r1 = align_slides_to_subtitles(slides, srt, dry_run=False, max_shift_sec=3.0, video_duration=30.0)
        end_after_first = slides[0].end
        r2 = align_slides_to_subtitles(slides, srt, dry_run=False, max_shift_sec=3.0, video_duration=30.0)
        assert slides[0].end == end_after_first
        assert r2.boundaries_moved == 0 or abs(r2.avg_shift) < 0.1

    def test_max_shift_respected(self, tmp_path):
        srt = make_srt(tmp_path, [(0, 5, "a"), (20, 25, "b")])
        slides = [make_seg(1, 0.0, 10.0), make_seg(2, 10.0, 30.0)]
        report = align_slides_to_subtitles(slides, srt, dry_run=True, max_shift_sec=2.0, video_duration=30.0)
        for detail in report.details:
            assert abs(detail["delta_sec"]) <= 2.01

    def test_report_structure(self, tmp_path):
        srt = make_srt(tmp_path, [(0, 5, "a"), (6, 12, "b"), (15, 25, "c")])
        slides = [make_seg(1, 0.0, 10.0), make_seg(2, 10.0, 20.0), make_seg(3, 20.0, 30.0)]
        report = align_slides_to_subtitles(slides, srt, dry_run=True, video_duration=30.0)
        d = report.to_dict()
        assert "boundaries_total" in d
        assert "boundaries_moved" in d
        assert "details" in d
        assert len(d["details"]) == 2
