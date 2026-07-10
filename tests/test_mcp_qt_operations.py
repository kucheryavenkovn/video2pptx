# FILE: tests/test_mcp_qt_operations.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Regression tests for Qt-affine MCP operation lifecycle and argument binding.
#   SCOPE: project_create operation ID, terminal status, project name/path, structured failure.
#   DEPENDS: pytest, M-DEBUG-MCP, M-PROJECT-MODEL, M-OPERATION-REGISTRY
#   LINKS: V-REF-CHAR-TESTS, E2E-002
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import json

from video2pptx.debug.mcp_operations import clear_registry, get_operation
from video2pptx.debug.mcp_server import _handle_rpc, mcp_process_queue
from video2pptx.project_model import ProjectModel


def _result_data(response: dict) -> dict:
    return json.loads(response["content"][0]["text"])


def test_project_create_has_operation_lifecycle_and_preserves_name(tmp_path):
    clear_registry()
    model = ProjectModel()

    response = _handle_rpc(
        "tools/call",
        {
            "name": "project_create",
            "arguments": {"path": str(tmp_path), "name": "characterized"},
        },
        model,
        model.timeline,
    )
    queued = _result_data(response)
    assert queued["status"] == "queued"
    assert queued["operation_id"]

    mcp_process_queue(model)

    completed = get_operation(queued["operation_id"])
    assert completed["status"] == "succeeded"
    assert model.project_data is not None
    assert model.project_data.name == "characterized"
    assert model.project_path == str(tmp_path / "characterized")
    assert (tmp_path / "characterized" / "project.json").is_file()
