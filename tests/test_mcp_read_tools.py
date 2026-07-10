# FILE: tests/test_mcp_read_tools.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for MCP read tools — get_app_state, get_project, get_timeline, list_artifacts
#   SCOPE: Read tool output shapes, edge cases (no project, no timeline)
#   DEPENDS: pytest, video2pptx.debug.mcp_read_tools
#   LINKS: V-M-MCP-READ-TOOLS
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from pathlib import Path

import pytest

from video2pptx.debug.mcp_read_tools import (
    get_app_state,
    get_project,
    get_timeline,
    get_slide,
    get_subtitle_clip,
    list_artifacts,
)


class TestMcpReadTools:
    def test_get_app_state_no_project(self):
        state = get_app_state()
        assert state["has_project"] is False

    def test_get_app_state_with_path(self):
        class FakeModel:
            project_path = Path("/fake/path")

        state = get_app_state(FakeModel())
        assert state["has_project"] is True
        assert state["project_path"] == str(Path("/fake/path"))

    def test_get_project_none(self):
        assert get_project(None) == {"error": "no project"}

    def test_get_timeline_none(self):
        tl = get_timeline(None)
        assert tl["duration"] == 0

    def test_get_slide_no_timeline(self):
        assert get_slide(None) is None

    def test_get_subtitle_clip_no_timeline(self):
        assert get_subtitle_clip(None) is None

    def test_list_artifacts_none(self):
        assert list_artifacts(None) == []

    def test_list_artifacts_non_existent(self):
        assert list_artifacts("/nonexistent/path") == []

    def test_list_artifacts_directory(self, tmp_path: Path):
        (tmp_path / "file1.json").write_text("{}", encoding="utf-8")
        (tmp_path / "file2.txt").write_text("hello", encoding="utf-8")
        arts = list_artifacts(tmp_path)
        assert len(arts) == 2
        assert arts[0]["name"] == "file1.json"
        assert arts[1]["name"] == "file2.txt"
        assert arts[1]["size_bytes"] == 5
