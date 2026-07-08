# FILE: tests/test_cli.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for CLI commands and argument parsing
#   SCOPE: detect, export-md, debug commands, help, error handling
#   DEPENDS: pytest, typer, video_slide_md.cli
#   LINKS: V-M-CLI
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import logging

from typer.testing import CliRunner

from video_slide_md.cli import _build_cli_overrides, app

runner = CliRunner()
logger = logging.getLogger(__name__)


class TestDetectCommand:
    def test_detect_missing_video(self):
        result = runner.invoke(app, ["detect", "/nonexistent/video.mp4"])
        assert result.exit_code == 1

    def test_detect_missing_subtitles(self):
        result = runner.invoke(app, ["detect", __file__, "--subtitles", "/nonexistent/sub.srt"])
        assert result.exit_code == 1

    def test_detect_help(self):
        result = runner.invoke(app, ["detect", "--help"])
        assert result.exit_code == 0
        assert "detect" in result.stdout

    def test_detect_with_valid_file(self, tmp_path):
        video = tmp_path / "video.mp4"
        # Create minimal valid video with OpenCV
        import cv2
        import numpy as np
        fourcc = cv2.VideoWriter.fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(video), fourcc, 10.0, (100, 100))
        for _ in range(5):
            writer.write(np.full((100, 100, 3), 128, dtype=np.uint8))
        writer.release()
        result = runner.invoke(app, ["detect", str(video), "--out", str(tmp_path / "out")])
        assert result.exit_code == 0
        assert (tmp_path / "out" / "slides.json").is_file()


class TestExportMdCommand:
    def test_export_md_missing_json(self):
        result = runner.invoke(app, ["export-md", "/nonexistent/slides.json"])
        assert result.exit_code == 1

    def test_export_md_help(self):
        result = runner.invoke(app, ["export-md", "--help"])
        assert result.exit_code == 0
        assert "export-md" in result.stdout


class TestDebugCommand:
    def test_debug_missing_json(self):
        result = runner.invoke(app, ["debug", "/nonexistent/slides.json"])
        assert result.exit_code == 1


class TestBuildCliOverrides:
    def test_empty_overrides(self):
        result = _build_cli_overrides()
        assert result == {}

    def test_sample_fps(self):
        result = _build_cli_overrides(sample_fps=5.0)
        assert result["video"]["sample_fps"] == 5.0

    def test_decoder_backend(self):
        result = _build_cli_overrides(decoder_backend="opencv")
        assert result["video"]["decoder_backend"] == "opencv"

    def test_slide_roi(self):
        result = _build_cli_overrides(slide_roi="100,50,1800,1000")
        assert result["detection"]["slide_roi"] == "100,50,1800,1000"

    def test_ignore_roi(self):
        result = _build_cli_overrides(ignore_roi=["1450,720,1900,1080"])
        assert result["detection"]["ignore_rois"] == [[1450, 720, 1900, 1080]]

    def test_threshold_float(self):
        result = _build_cli_overrides(threshold="0.5")
        assert result["detection"]["threshold"] == 0.5

    def test_threshold_auto(self):
        result = _build_cli_overrides(threshold="auto")
        assert result["detection"]["threshold"] == "auto"

    def test_min_slide_duration(self):
        result = _build_cli_overrides(min_slide_duration=5.0)
        assert result["detection"]["min_slide_duration"] == 5.0

    def test_dedupe(self):
        result = _build_cli_overrides(dedupe=False)
        assert result["detection"]["dedupe_enabled"] is False

    def test_debug_flag(self):
        result = _build_cli_overrides(debug=True)
        assert result["debug"]["save_sampled_frames"] is True
        assert result["debug"]["save_diff_scores"] is True
