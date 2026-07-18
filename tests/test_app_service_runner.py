# FILE: tests/test_app_service_runner.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Regression tests for MCP AppServiceRunner dispatch through McpServiceAdapter.
#   SCOPE: Command mapping, path passthrough, failure propagation (persistence tested in Phase 16 unit tests).
#   DEPENDS: pytest, M-MCP-OPERATIONS, M-MCP-ADAPTER
#   LINKS: V-M-REF-CHAR-TESTS, M-APP-SERVICE, M-CANONICAL-COMMANDS, M-MCP-OPERATIONS
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   _Model - minimal ProjectModel substitute for runner path tests
#   test_* - MCP adapter and runner dispatch regressions
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Replace _persist_project_result tests with adapter dispatch tests
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

import pytest

from video2pptx.debug.app_service_adapter import McpServiceAdapter
from video2pptx.debug.mcp_operations import AppServiceRunner


class _Model:
    def __init__(self, project_path: Path):
        self.project_data = None
        self.project_path = str(project_path)


def test_unknown_command_returns_error(tmp_path):
    adapter = McpServiceAdapter()
    result = adapter.execute_command("nonexistent", tmp_path)
    assert result["success"] is False
    assert "unknown" in result["error"]


def test_preview_dispatch_passthrough(tmp_path):
    adapter = McpServiceAdapter()
    result = adapter.execute_command("preview", tmp_path, video_path="")
    # Result format matches ServiceResult.to_dict()
    assert "success" in result
    assert result["stage"] == "preview"


def test_auto_align_command_maps_correctly(tmp_path):
    adapter = McpServiceAdapter()
    result = adapter.execute_command(
        "auto_align", tmp_path,
        subtitles_path="", dry_run=True,
    )
    assert "success" in result
    # Without a real project the call fails, but the command is not 'unknown'
    assert result.get("stage", "") == "auto_align"


def test_export_md_dispatch(tmp_path):
    adapter = McpServiceAdapter()
    result = adapter.execute_command("export_md", tmp_path)
    assert "success" in result


def test_export_pptx_dispatch(tmp_path):
    adapter = McpServiceAdapter()
    result = adapter.execute_command("export_pptx", tmp_path)
    assert "success" in result


def test_process_notes_dispatch(tmp_path):
    adapter = McpServiceAdapter()
    result = adapter.execute_command("process_notes", tmp_path, subtitles_path="")
    assert "success" in result


def test_auto_dispatch(tmp_path):
    adapter = McpServiceAdapter()
    result = adapter.execute_command("auto", tmp_path, video_path="", subtitles_path="")
    assert "success" in result


def test_runner_dispatch_rejects_missing_project(tmp_path):
    runner = AppServiceRunner(project_model=None)
    with pytest.raises(RuntimeError, match="No open project"):
        runner._dispatch("detect", {})


def test_runner_dispatch_nonexistent_project_raises_operation_error(tmp_path):
    from video2pptx.debug.errors import OperationError
    model = _Model(project_path=tmp_path / "nonexistent")
    runner = AppServiceRunner(project_model=model)
    with pytest.raises(OperationError):
        runner._dispatch("detect", {})
