# FILE: tests/test_operation_registry.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for MCP Operation Registry lifecycle
#   SCOPE: create, update, get, wait, cancel, list operations
#   DEPENDS: pytest, video2pptx.debug.operation_registry
#   LINKS: V-M-OPERATION-REGISTRY, M-OPERATION-REGISTRY
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT


from video2pptx.debug.operation_registry import OperationRegistry


class TestOperationRegistry:
    def test_create(self):
        reg = OperationRegistry()
        op = reg.create("detect", {"video": "test.mp4"})
        assert op.operation_id is not None
        assert op.tool == "detect"
        assert op.status == "queued"

    def test_update_to_running(self):
        reg = OperationRegistry()
        op = reg.create("detect")
        updated = reg.update(op.operation_id, status="running", progress=10)
        assert updated.status == "running"
        assert updated.progress == 10
        assert updated.started_at is not None

    def test_update_to_succeeded(self):
        reg = OperationRegistry()
        op = reg.create("detect")
        reg.update(op.operation_id, status="running")
        reg.update(op.operation_id, status="succeeded", result={"slides": 5})
        final = reg.get(op.operation_id)
        assert final.status == "succeeded"
        assert final.finished_at is not None
        assert final.result["slides"] == 5

    def test_update_to_failed(self):
        reg = OperationRegistry()
        op = reg.create("detect")
        reg.update(op.operation_id, status="failed", error="Video not found")
        final = reg.get(op.operation_id)
        assert final.status == "failed"
        assert "Video not found" in final.error

    def test_cancel(self):
        reg = OperationRegistry()
        op = reg.create("detect")
        reg.update(op.operation_id, status="running")
        cancelled = reg.cancel(op.operation_id)
        assert cancelled.status == "cancelled"

    def test_cancel_already_terminal(self):
        reg = OperationRegistry()
        op = reg.create("detect")
        reg.update(op.operation_id, status="succeeded")
        result = reg.cancel(op.operation_id)
        assert result.status == "succeeded"

    def test_wait_success(self):
        reg = OperationRegistry()
        op = reg.create("detect")
        reg.update(op.operation_id, status="running")
        reg.update(op.operation_id, status="succeeded")
        result = reg.wait(op.operation_id, timeout=1.0)
        assert result is not None
        assert result.status == "succeeded"

    def test_wait_timeout(self):
        reg = OperationRegistry()
        op = reg.create("detect")
        result = reg.wait(op.operation_id, timeout=0.2, poll_interval=0.05)
        assert result is not None
        assert result.status == "queued"

    def test_list_operations(self):
        reg = OperationRegistry()
        for i in range(5):
            reg.create(f"tool_{i}")
        ops = reg.list_operations(limit=3)
        assert len(ops) == 3

    def test_invalid_status(self):
        reg = OperationRegistry()
        op = reg.create("detect")
        try:
            reg.update(op.operation_id, status="invalid")
            raise AssertionError("Should have raised")  # noqa: B011
        except ValueError:
            pass

    def test_get_nonexistent(self):
        reg = OperationRegistry()
        assert reg.get("nonexistent") is None

    def test_clear(self):
        reg = OperationRegistry()
        reg.create("detect")
        reg.create("export")
        reg.clear()
        assert len(reg.list_operations()) == 0

    def test_to_dict(self):
        reg = OperationRegistry()
        op = reg.create("detect", {"path": "x"})
        d = op.to_dict()
        assert d["operation_id"] == op.operation_id
        assert d["tool"] == "detect"
        assert d["status"] == "queued"
        assert d["arguments"]["path"] == "x"
