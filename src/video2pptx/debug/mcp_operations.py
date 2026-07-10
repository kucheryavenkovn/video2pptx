# FILE: src/video2pptx/debug/mcp_operations.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Wire OperationRegistry into MCP — write tools create op, run app_service in OpRunnerThread, return operation_id.
#            Lifecycle tools: health, get_capabilities, get_operation, wait_operation, cancel_operation, list_operations.
#   SCOPE: OpRunnerThread, submit(), lifecycle functions, health/capabilities
#   DEPENDS: M-OPERATION-REGISTRY, M-APP-SERVICE, M-STRUCTURED-ERRORS, M-CONFIRM-POLICY
#   LINKS: M-MCP-OPERATIONS
#   ROLE: INTEGRATION
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   OpRunnerThread - background thread running app_service commands with op status updates
#   OperationRunner - single-dispatch: runs one operation via app_service
#   submit - create op + enqueue; return operation_id
#   get_operation_status - wrapper around registry.get
#   wait_operation - poll registry with timeout
#   cancel_operation - mark op cancelled, signal runner
#   health - MCP health + version
# END_MODULE_MAP

from __future__ import annotations

import time
from pathlib import Path
from queue import Queue
from threading import Event, Thread
from typing import Any

from loguru import logger

from video2pptx.debug.confirm import require_confirm
from video2pptx.debug.errors import OperationError
from video2pptx.debug.operation_registry import OperationRegistry, TERMINAL_STATUSES


_OP_QUEUE: Queue[tuple[str, dict[str, Any], str]] = Queue()
_CANCEL_EVENT = Event()
_REGISTRY = OperationRegistry()


def get_registry() -> OperationRegistry:
    return _REGISTRY


def clear_registry() -> None:
    _REGISTRY.clear()
    while not _OP_QUEUE.empty():
        try:
            _OP_QUEUE.get_nowait()
        except Exception:
            break
    logger.info("[McpOps] Registry and queue cleared")


def submit(tool: str, args: dict[str, Any] | None = None, trace_id: str = "") -> dict[str, Any]:
    op = _REGISTRY.create(tool, args or {})
    if trace_id:
        op.trace_id = trace_id
    _OP_QUEUE.put((op.operation_id, tool, args or {}))
    logger.info(f"[McpOps] Submitted | op_id={op.operation_id} tool={tool}")
    return {
        "operation_id": op.operation_id,
        "tool": tool,
        "status": "queued",
    }


def health(version: str = "0.6.0", backend: str = "auto") -> dict[str, Any]:
    return {
        "status": "ok",
        "version": version,
        "backend": backend,
        "operations_pending": _OP_QUEUE.qsize(),
    }


def get_capabilities() -> dict[str, Any]:
    return {
        "protocol_version": "2024-11-05",
        "server_info": {"name": "video2pptx", "version": "0.6.0"},
        "features": {
            "operation_lifecycle": True,
            "confirm_policy": True,
            "structured_errors": True,
            "atomic_writes": True,
        },
    }


def get_operation(operation_id: str) -> dict[str, Any] | None:
    op = _REGISTRY.get(operation_id)
    if op is None:
        return None
    return op.to_dict()


def list_operations(limit: int = 20) -> list[dict[str, Any]]:
    return [op.to_dict() for op in _REGISTRY.list_operations(limit=limit)]


def wait_operation(operation_id: str, timeout: float = 120.0, poll_interval: float = 0.1) -> dict[str, Any] | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        op = _REGISTRY.get(operation_id)
        if op is None:
            return None
        if op.status in TERMINAL_STATUSES:
            return op.to_dict()
        time.sleep(poll_interval)
    op = _REGISTRY.get(operation_id)
    return op.to_dict() if op else None


def cancel_operation(operation_id: str, confirm: bool = False) -> dict[str, Any]:
    require_confirm("cancel_operation", {"confirm": confirm})
    op = _REGISTRY.cancel(operation_id)
    if op is None:
        return {"error": f"operation not found: {operation_id}"}
    _CANCEL_EVENT.set()
    logger.info(f"[McpOps] Cancelled | op_id={operation_id}")
    return op.to_dict()


class OperationRunner:
    """Runs a single operation by dispatching to app_service based on tool name."""

    def __init__(self, app_service_module: object = None) -> None:
        self._app_service = app_service_module

    def run(self, operation_id: str, tool: str, args: dict[str, Any]) -> None:
        try:
            _REGISTRY.update(operation_id, status="running", progress=0)
            result = self._dispatch(tool, args)
            _REGISTRY.update(operation_id, status="succeeded", progress=100, result=result)
        except OperationError as oe:
            _REGISTRY.update(operation_id, status="failed", error=oe.to_dict())
        except Exception as exc:
            err = OperationError.from_exception(exc, stage=tool, trace_id=operation_id)
            _REGISTRY.update(operation_id, status="failed", error=err.to_dict())

    def _dispatch(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Subclass must implement _dispatch")


class OpRunnerThread(Thread):
    """Background thread that drains the operation queue and runs them via OperationRunner."""

    def __init__(self, runner: OperationRunner | None = None, daemon: bool = True) -> None:
        super().__init__(daemon=daemon, name="OpRunnerThread")
        self._runner = runner
        self._stopped = Event()

    def stop(self) -> None:
        self._stopped.set()
        _CANCEL_EVENT.set()

    def run(self) -> None:
        logger.info("[McpOps] OpRunnerThread started")
        while not self._stopped.is_set():
            try:
                op_id, tool, args = _OP_QUEUE.get(timeout=0.5)
            except Exception:
                continue
            if _CANCEL_EVENT.is_set():
                _REGISTRY.update(op_id, status="cancelled")
                _CANCEL_EVENT.clear()
                logger.info(f"[McpOps] Op cancelled during dequeue | op_id={op_id}")
                continue
            try:
                if self._runner:
                    self._runner.run(op_id, tool, args)
            except Exception as exc:
                err = OperationError.from_exception(exc, stage=tool, trace_id=op_id)
                _REGISTRY.update(op_id, status="failed", error=err.to_dict())
        logger.info("[McpOps] OpRunnerThread stopped")
