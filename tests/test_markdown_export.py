# FILE: tests/test_markdown_export.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for Marp Markdown export
#   SCOPE: Markdown generation, slide rendering, time formatting
#   DEPENDS: pytest, video2pptx.markdown_export
#   LINKS: V-M-MD-EXPORT, M-MD-EXPORT
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT



from video2pptx.markdown_export import export_to_markdown, render_slide
from video2pptx.models import SlidesDocument, SlideSegment, VideoInfo
from video2pptx.paths import format_time


def make_seg(index: int, start: float, end: float, image: str = "", transcript: str = "") -> SlideSegment:
    return SlideSegment(
        index=index,
        start=start,
        end=end,
        duration=end - start,
        representative_timestamp=(start + end) / 2,
        image=image,
        transcript=transcript,
        confidence=0.9,
    )


class TestFmtTime:
    def test_seconds_only(self):
        assert format_time(65.0) == "1:05"

    def test_minutes(self):
        assert format_time(3661.0) == "1:01:01"

    def test_zero(self):
        assert format_time(0.0) == "0:00"


class TestRenderSlide:
    def test_basic_slide(self):
        seg = make_seg(1, 0.0, 10.0)
        lines = render_slide(seg, base_dir="slides")
        assert any("0:00" in line for line in lines)

    def test_slide_with_image(self):
        seg = make_seg(1, 0.0, 10.0, image="slide_001.png")
        lines = render_slide(seg, base_dir="slides")
        img_lines = [line for line in lines if "slide_001.png" in line]
        assert len(img_lines) >= 1

    def test_slide_with_transcript(self):
        seg = make_seg(1, 0.0, 10.0, transcript="Hello world")
        lines = render_slide(seg, base_dir="slides")
        assert any("Hello world" in line for line in lines)

    def test_slide_with_warnings(self):
        seg = make_seg(1, 0.0, 10.0)
        seg.warnings = ["Low confidence"]
        lines = render_slide(seg, base_dir="slides")
        assert any("Low confidence" in line for line in lines)

    def test_slide_no_image(self):
        seg = make_seg(1, 0.0, 10.0)
        lines = render_slide(seg, base_dir="slides")
        img_lines = [line for line in lines if "![" in line]
        assert len(img_lines) == 0

    def test_no_timecodes(self):
        seg = make_seg(1, 0.0, 10.0)
        lines = render_slide(seg, base_dir="slides", include_timecodes=False)
        assert not any("0:00" in line for line in lines)

    def test_transcript_comment_location(self):
        seg = make_seg(1, 0.0, 10.0, transcript="Hello world")
        lines = render_slide(seg, base_dir="slides", transcript_location="comment")
        assert any("<!-- Hello world -->" in line for line in lines)

    def test_transcript_none_location(self):
        seg = make_seg(1, 0.0, 10.0, transcript="Hello world")
        lines = render_slide(seg, base_dir="slides", transcript_location="none")
        assert not any("Hello world" in line for line in lines)

    def test_image_as_background(self):
        seg = make_seg(1, 0.0, 10.0, image="slide_001.png")
        lines = render_slide(seg, base_dir="slides", image_as_background=True)
        assert any("![bg]" in line for line in lines)

    def test_image_not_background(self):
        seg = make_seg(1, 0.0, 10.0, image="slide_001.png")
        lines = render_slide(seg, base_dir="slides", image_as_background=False)
        assert any("![Slide 1]" in line for line in lines)

    def test_double_path_bug_fixed(self):
        seg = make_seg(1, 0.0, 10.0, image="slides/slide_001.png")
        lines = render_slide(seg, base_dir="out", image_as_background=True)
        img_line = [ln for ln in lines if "slide_001.png" in ln][0]
        assert "slides/slides/slide_001.png" not in img_line
        assert "slides/slide_001.png" in img_line


class TestExportToMarkdown:
    def test_basic_export(self, tmp_path):
        doc = SlidesDocument(
            video=VideoInfo(path="test.mp4", duration=30.0, width=1920, height=1080, fps=30.0),
            slides=[
                make_seg(1, 0.0, 10.0, "s1.png"),
                make_seg(2, 10.0, 20.0, "s2.png"),
            ],
        )
        out = tmp_path / "deck.md"
        result = export_to_markdown(doc, out)

        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "marp: true" in content
        assert "s1.png" in content
        assert "s2.png" in content

    def test_custom_title(self, tmp_path):
        doc = SlidesDocument(
            video=VideoInfo(path="test.mp4", duration=10.0, width=1920, height=1080, fps=30.0),
            slides=[make_seg(1, 0.0, 10.0)],
        )
        out = tmp_path / "deck.md"
        export_to_markdown(doc, out, title="My Talk")
        content = out.read_text(encoding="utf-8")
        assert "My Talk" in content

    def test_empty_document(self, tmp_path):
        doc = SlidesDocument(
            video=VideoInfo(path="test.mp4", duration=0.0, width=1920, height=1080, fps=30.0),
            slides=[],
        )
        out = tmp_path / "deck.md"
        result = export_to_markdown(doc, out)
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "marp: true" in content
