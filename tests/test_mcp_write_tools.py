# FILE: tests/test_mcp_write_tools.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for MCP write tools — tool defs, dispatch, schema validation
#   SCOPE: get_write_tool_defs, dispatch_write confirm, is_sync_tool
#   DEPENDS: pytest, video2pptx.debug.mcp_write_tools
#   LINKS: V-M-MCP-WRITE-TOOLS
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import pytest

from video2pptx.debug.mcp_write_tools import (
    dispatch_write,
    get_write_tool_defs,
    is_sync_tool,
)


class TestMcpWriteTools:
    def test_get_defs_returns_list(self):
        defs = get_write_tool_defs()
        assert len(defs) >= 20
        names = [d["name"] for d in defs]
        assert "project_create" in names
        assert "detect" in names
        assert "auto_align" in names
        assert "slide_add" in names
        assert "app_shutdown" in names

    def test_each_def_has_schema(self):
        for d in get_write_tool_defs():
            assert "inputSchema" in d
            assert d["inputSchema"]["type"] == "object"

    def test_dispatch_write_returns_operation(self):
        result = dispatch_write("project_create", {"path": "/tmp/test"}, trace_id="test123")
        assert "operation_id" in result
        assert result["status"] == "queued"
        assert result["tool"] == "project_create"

    def test_dispatch_write_rejects_missing_confirm(self):
        with pytest.raises(Exception, match="detect"):
            dispatch_write("detect", {})
        with pytest.raises(Exception, match="detect"):
            dispatch_write("detect", {"confirm": False})

    def test_dispatch_write_accepts_confirm(self):
        result = dispatch_write("detect", {"confirm": True, "video": "test.mp4"})
        assert result["status"] == "queued"

    def test_is_sync_tool_classification(self):
        assert is_sync_tool("get_project") is True
        assert is_sync_tool("health") is True
        assert is_sync_tool("detect") is False
        assert is_sync_tool("slide_add") is False

    def test_non_destructive_no_confirm_needed(self):
        result = dispatch_write("project_create", {"path": "/tmp/test"})
        assert result["status"] == "queued"
