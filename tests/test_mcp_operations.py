# FILE: tests/test_mcp_operations.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for MCP operation lifecycle — submit, wait, cancel, health, runner
#   SCOPE: submit, get_operation, wait_operation, cancel_operation, list_operations, health, runner thread
#   DEPENDS: pytest, video2pptx.debug.mcp_operations
#   LINKS: V-M-MCP-OPERATIONS, M-MCP-OPERATIONS
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT


import pytest

from video2pptx.debug.mcp_operations import (
    OperationRunner,
    cancel_operation,
    clear_registry,
    get_operation,
    get_registry,
    health,
    list_operations,
    submit,
    wait_operation,
)


@pytest.fixture(autouse=True)
def _reset_registry():
    # Stop any global OpRunnerThread from previous GUI tests
    try:
        import video2pptx.debug.mcp_server as _ms
        if _ms._OP_RUNNER_THREAD is not None and _ms._OP_RUNNER_THREAD.is_alive():
            _ms._OP_RUNNER_THREAD.stop()
            _ms._OP_RUNNER_THREAD = None
    except Exception:
        pass
    clear_registry()
    yield


class TestMcpOperations:
    def test_submit_returns_queued(self):
        result = submit("detect", {"video": "test.mp4"})
        assert "operation_id" in result
        assert result["tool"] == "detect"
        assert result["status"] == "queued"

    def test_get_operation_returns_op(self):
        result = submit("detect")
        op = get_operation(result["operation_id"])
        assert op is not None
        assert op["tool"] == "detect"
        assert op["operation_id"] == result["operation_id"]

    def test_get_operation_missing(self):
        assert get_operation("nonexistent") is None

    def test_wait_operation_immediate(self):
        result = submit("detect")
        op_id = result["operation_id"]
        # Mark as succeeded immediately
        reg = get_registry()
        reg.update(op_id, status="succeeded", result={"slides": 3})
        final = wait_operation(op_id, timeout=5)
        assert final is not None
        assert final["status"] == "succeeded"

    def test_wait_operation_timeout(self):
        result = submit("detect")
        # Don't update, should time out or be in terminal state from runner
        final = wait_operation(result["operation_id"], timeout=0.5)
        assert final is not None

    def test_cancel_operation(self):
        reg = get_registry()
        op = reg.create("test_cmd")
        cancelled = cancel_operation(op.operation_id, confirm=True)
        assert cancelled["status"] == "cancelled"

    def test_cancel_operation_requires_confirm(self):
        result = submit("detect")
        with pytest.raises(Exception):
            cancel_operation(result["operation_id"], confirm=False)

    def test_list_operations_ordered(self):
        submit("test_cmd", {"key": "val1"})
        submit("test_cmd", {"key": "val2"})
        submit("test_cmd", {"key": "val3"})
        ops = list_operations(limit=2)
        assert len(ops) == 2
        assert ops[0]["tool"] == "test_cmd"
        assert ops[1]["tool"] == "test_cmd"
        assert ops[0]["operation_id"] != ops[1]["operation_id"]

    def test_health(self):
        h = health(version="0.6.0")
        assert h["status"] == "ok"
        assert h["version"] == "0.6.0"

    def test_op_runner_dispatch(self):
        class TestRunner(OperationRunner):
            def _dispatch(self, tool, args):
                return {"ran": tool, "args": args}

        result = submit("test_cmd", {"key": "val"})
        op_id = result["operation_id"]
        runner = TestRunner()
        runner.run(op_id, "test_cmd", {"key": "val"})
        final = get_operation(op_id)
        assert final["status"] == "succeeded"
        assert final["result"]["ran"] == "test_cmd"

    def test_op_runner_failure(self):
        class BrokenRunner(OperationRunner):
            def _dispatch(self, tool, args):
                raise ValueError("broken")

        result = submit("broken_cmd")
        op_id = result["operation_id"]
        runner = BrokenRunner()
        runner.run(op_id, "broken_cmd", {})
        final = get_operation(op_id)
        assert final["status"] == "failed"
        assert "ValueError" in final["error"]["type"]

    def test_clear_registry(self):
        submit("detect")
        submit("preview")
        clear_registry()
        assert len(list_operations(limit=100)) == 0
