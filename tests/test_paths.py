# FILE: tests/test_paths.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for centralized path resolution utilities
#   SCOPE: resolve_artifact_path, resolve_markdown_image_path, format_time
#   DEPENDS: pytest, video2pptx.paths
#   LINKS: V-M-PATHS
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from pathlib import Path

from video2pptx.paths import resolve_artifact_path, resolve_markdown_image_path, format_time


class TestResolveArtifactPath:
    def test_bare_filename(self):
        result = resolve_artifact_path("/proj/out", "slide_001.png")
        assert result == Path("/proj/out/slides/slide_001.png")

    def test_relative_with_slides_prefix(self):
        result = resolve_artifact_path("/proj/out", "slides/slide_001.png")
        assert result == Path("/proj/out/slides/slide_001.png")

    def test_absolute_path(self):
        result = resolve_artifact_path("/proj/out", "/abs/path/slide_001.png")
        assert result == Path("/abs/path/slide_001.png")

    def test_empty_string(self):
        result = resolve_artifact_path("/proj/out", "")
        assert result == Path()

    def test_no_base_dir(self):
        result = resolve_artifact_path(None, "slide_001.png")
        assert result == Path("slides/slide_001.png")

    def test_windows_backslashes(self):
        result = resolve_artifact_path("C:\\proj", "slides\\slide_001.png")
        assert result == Path("C:\\proj") / Path("slides/slide_001.png")


class TestResolveMarkdownImagePath:
    def test_bare_filename(self):
        result = resolve_markdown_image_path("/proj/out", "slide_001.png")
        assert result == "slides/slide_001.png"

    def test_relative_with_slides_prefix(self):
        result = resolve_markdown_image_path("/proj/out", "slides/slide_001.png")
        assert result == "slides/slide_001.png"

    def test_no_double_prefix(self):
        result = resolve_markdown_image_path("/proj/out", "slides/slide_001.png")
        assert "slides/slides/" not in result

    def test_empty_string(self):
        assert resolve_markdown_image_path("/proj/out", "") == ""

    def test_no_base_dir(self):
        result = resolve_markdown_image_path(None, "slide_001.png")
        assert result == "slides/slide_001.png"


class TestFormatTime:
    def test_zero(self):
        assert format_time(0.0) == "0:00"

    def test_seconds(self):
        assert format_time(65.0) == "1:05"

    def test_minutes(self):
        assert format_time(3661.0) == "1:01:01"

    def test_negative_clamped(self):
        assert format_time(-5.0) == "0:00"
