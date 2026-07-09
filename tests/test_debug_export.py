# FILE: tests/test_debug_export.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for debug export artifacts
#   SCOPE: CSV export, text report, contact sheet
#   DEPENDS: pytest, video2pptx.debug_export
#   LINKS: V-M-DEBUG-EXPORT
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT


import numpy as np

from video2pptx.debug_export import (
    export_contact_sheet,
    export_debug_csv,
    export_debug_report,
)
from video2pptx.models import SlideSegment


def make_seg(index: int, start: float, end: float) -> SlideSegment:
    return SlideSegment(
        index=index,
        start=start,
        end=end,
        duration=end - start,
        representative_timestamp=(start + end) / 2,
        image=f"slide_{index:03d}.png",
        transcript=f"Transcript for slide {index}",
        confidence=0.9,
    )


class TestExportDebugCsv:
    def test_writes_csv(self, tmp_path):
        out = tmp_path / "debug" / "scores.csv"
        export_debug_csv(
            scores=[0.1, 0.2, 0.3],
            timestamps=[1.0, 2.0, 3.0],
            output_path=out,
        )
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "timestamp,score" in content
        assert "1.000,0.100000" in content

    def test_empty_lists(self, tmp_path):
        out = tmp_path / "scores.csv"
        export_debug_csv(scores=[], timestamps=[], output_path=out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "timestamp,score" in content  # header only

    def test_creates_parent_dir(self, tmp_path):
        out = tmp_path / "a" / "b" / "c" / "scores.csv"
        export_debug_csv(scores=[0.5], timestamps=[1.0], output_path=out)
        assert out.exists()


class TestExportDebugReport:
    def test_writes_report(self, tmp_path):
        segs = [make_seg(1, 0.0, 10.0), make_seg(2, 10.0, 20.0)]
        out = tmp_path / "report.txt"
        export_debug_report(segs, "test.mp4", out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "test.mp4" in content
        assert "Slide #1" in content
        assert "Slide #2" in content
        assert "Transcript for slide" in content

    def test_empty_segments(self, tmp_path):
        out = tmp_path / "report.txt"
        export_debug_report([], "test.mp4", out)
        content = out.read_text(encoding="utf-8")
        assert "Total segments: 0" in content


class TestExportContactSheet:
    def test_skips_without_pil(self, tmp_path):
        segs = [make_seg(1, 0.0, 10.0)]
        frames = {5.0: np.full((100, 100, 3), 128, dtype=np.uint8)}
        out = tmp_path / "contact.jpg"
        result = export_contact_sheet(segs, frames, out)
        # With PIL available, should create a file
        if _pil_available():
            assert out.exists()
        else:
            assert not out.exists() or result == out


def _pil_available() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False
