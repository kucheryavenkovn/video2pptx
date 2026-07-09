# FILE: tests/test_cli_e2e.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: End-to-end tests for the full pipeline via CLI
#   SCOPE: Run detect command on synthetic video, verify slides.json and artifacts
#   DEPENDS: pytest, typer.testing, video2pptx.cli
#   LINKS: V-M-CLI-E2E
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from pathlib import Path

from typer.testing import CliRunner

from video2pptx.cli import app

FIXTURES = Path(__file__).parent / "fixtures"
TEST_VIDEO = FIXTURES / "test_slides.mp4"
TEST_SRT = FIXTURES / "test_slides.srt"

runner = CliRunner()


class TestDetectE2E:
    def test_detect_basic(self, tmp_path):
        """Run detect on synthetic video, verify slides.json."""
        result = runner.invoke(app, [
            "detect",
            str(TEST_VIDEO),
            "--out", str(tmp_path),
        ])
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        slides_json = tmp_path / "slides.json"
        assert slides_json.is_file()

        import json
        doc = json.loads(slides_json.read_text(encoding="utf-8"))
        assert "video" in doc
        assert "slides" in doc
        assert len(doc["slides"]) >= 1

        slides_dir = tmp_path / "slides"
        assert slides_dir.is_dir()

    def test_detect_with_subtitles(self, tmp_path):
        """Run detect with SRT, verify subtitles aligned."""
        result = runner.invoke(app, [
            "detect",
            str(TEST_VIDEO),
            "--subtitles", str(TEST_SRT),
            "--out", str(tmp_path),
        ])
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        slides_json = tmp_path / "slides.json"
        assert slides_json.is_file()

        import json
        doc = json.loads(slides_json.read_text(encoding="utf-8"))
        slides = doc["slides"]
        assert len(slides) >= 1
        # At least one slide should have transcript text
        transcripts = [s.get("transcript", "") for s in slides]
        assert any(t for t in transcripts), "No transcript found in any slide"

    def test_detect_with_export_md(self, tmp_path):
        """Run detect with --export-md, verify deck.md."""
        result = runner.invoke(app, [
            "detect",
            str(TEST_VIDEO),
            "--subtitles", str(TEST_SRT),
            "--out", str(tmp_path),
            "--export-md",
        ])
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        deck_md = tmp_path / "deck.md"
        assert deck_md.is_file()
        content = deck_md.read_text(encoding="utf-8")
        assert "marp: true" in content

    def test_detect_with_debug(self, tmp_path):
        """Run detect with --debug, verify debug artifacts."""
        result = runner.invoke(app, [
            "detect",
            str(TEST_VIDEO),
            "--out", str(tmp_path),
            "--debug",
        ])
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        debug_dir = tmp_path / "debug"
        assert debug_dir.is_dir()

        report = debug_dir / "debug_report.txt"
        assert report.is_file()
        assert "Total segments" in report.read_text(encoding="utf-8")

    def test_detect_missing_video(self, tmp_path):
        """Verify error on missing video."""
        result = runner.invoke(app, [
            "detect",
            "/nonexistent/video.mp4",
            "--out", str(tmp_path),
        ])
        assert result.exit_code == 1

    def test_export_md_command(self, tmp_path):
        """Run detect then export-md on the slides.json."""
        # First detect
        runner.invoke(app, [
            "detect",
            str(TEST_VIDEO),
            "--out", str(tmp_path),
        ])
        slides_json = tmp_path / "slides.json"
        assert slides_json.is_file()

        # Then export-md
        result = runner.invoke(app, [
            "export-md",
            str(slides_json),
            "--out", str(tmp_path / "deck.md"),
        ])
        assert result.exit_code == 0

        deck = tmp_path / "deck.md"
        assert deck.is_file()
        assert "marp: true" in deck.read_text(encoding="utf-8")

    def test_debug_command(self, tmp_path):
        """Run detect then debug on the slides.json."""
        runner.invoke(app, [
            "detect",
            str(TEST_VIDEO),
            "--out", str(tmp_path),
        ])
        slides_json = tmp_path / "slides.json"
        assert slides_json.is_file()

        result = runner.invoke(app, [
            "debug",
            str(slides_json),
            "--out", str(tmp_path / "debug"),
        ])
        assert result.exit_code == 0

        report = tmp_path / "debug" / "debug_report.txt"
        assert report.is_file()
