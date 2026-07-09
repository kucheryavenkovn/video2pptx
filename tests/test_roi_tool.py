# FILE: tests/test_roi_tool.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for ROI tool — CLI registration, frame seeking, coordinate format
#   SCOPE: Verify roi_tool_main frame selection, CLI help, and coordinate output format. GUI interaction (select_roi) is excluded from automated tests.
#   DEPENDS: pytest, typer.testing, video2pptx.roi_tool, video2pptx.cli
#   LINKS: V-M-ROI-TOOL
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from video2pptx.cli import app

FIXTURES = Path(__file__).parent / "fixtures"

runner = CliRunner()


class TestRoiTool:
    def test_cli_help(self):
        """roi-tool command should appear in help."""
        result = runner.invoke(app, ["roi-tool", "--help"])
        assert result.exit_code == 0
        assert "roi-tool" in result.output

    def test_cli_missing_video(self):
        """roi-tool with missing video should exit with error."""
        result = runner.invoke(app, [
            "roi-tool",
            str(FIXTURES / "nonexistent.mp4"),
        ])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()
