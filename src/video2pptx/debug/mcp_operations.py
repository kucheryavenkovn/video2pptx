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
from threading import Event, Lock, Thread
from typing import Any

from loguru import logger

from video2pptx.debug.confirm import require_confirm
from video2pptx.debug.errors import OperationError
from video2pptx.debug.operation_registry import TERMINAL_STATUSES, OperationRegistry

_OP_QUEUE: Queue[tuple[str, dict[str, Any], str]] = Queue()
_CANCEL_EVENT = Event()
_REGISTRY = OperationRegistry()
_COMPLETED_OPS: list[str] = []
_COMPLETED_OPS_LOCK = Lock()
_SYNC_REQUIRED: set[str] = set()
_SYNCHRONIZED_OPS: set[str] = set()


def record_completed(operation_id: str) -> None:
    with _COMPLETED_OPS_LOCK:
        _COMPLETED_OPS.append(operation_id)


def drain_completed_ops() -> list[str]:
    with _COMPLETED_OPS_LOCK:
        result = list(_COMPLETED_OPS)
        _COMPLETED_OPS.clear()
    return result


def require_completion_sync(operation_id: str) -> None:
    with _COMPLETED_OPS_LOCK:
        _SYNC_REQUIRED.add(operation_id)


def mark_completion_synchronized(operation_id: str) -> None:
    with _COMPLETED_OPS_LOCK:
        _SYNCHRONIZED_OPS.add(operation_id)


def get_registry() -> OperationRegistry:
    return _REGISTRY


def clear_registry() -> None:
    _REGISTRY.clear()
    with _COMPLETED_OPS_LOCK:
        _COMPLETED_OPS.clear()
        _SYNC_REQUIRED.clear()
        _SYNCHRONIZED_OPS.clear()
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
            with _COMPLETED_OPS_LOCK:
                awaiting_sync = (
                    operation_id in _SYNC_REQUIRED
                    and operation_id not in _SYNCHRONIZED_OPS
                )
            if awaiting_sync:
                time.sleep(poll_interval)
                continue
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
            if self._requires_completion_sync():
                require_completion_sync(operation_id)
                record_completed(operation_id)
            _REGISTRY.update(operation_id, status="succeeded", progress=100, result=result)
        except OperationError as oe:
            _REGISTRY.update(operation_id, status="failed", error=oe.to_dict())
        except Exception as exc:
            err = OperationError.from_exception(exc, stage=tool, trace_id=operation_id)
            _REGISTRY.update(operation_id, status="failed", error=err.to_dict())
        finally:
            if not self._requires_completion_sync():
                record_completed(operation_id)

    def _dispatch(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Subclass must implement _dispatch")

    def _requires_completion_sync(self) -> bool:
        return False


class AppServiceRunner(OperationRunner):
    """Concrete runner that delegates to app_service.execute_command with project context."""

    def __init__(self, project_model=None) -> None:
        super().__init__()
        self._project_model = project_model

    def _requires_completion_sync(self) -> bool:
        return self._project_model is not None

    def _dispatch(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        from video2pptx.app_service import execute_command

        project = getattr(self._project_model, "project_data", None) if self._project_model else None
        raw_project_path = (
            getattr(self._project_model, "project_path", None)
            if self._project_model
            else None
        )
        project_path = Path(raw_project_path) if raw_project_path else None

        if project is None:
            raise RuntimeError(f"No open project for tool: {tool}")

        video_path = getattr(project, "video", None)
        out_dir = project_path if project_path else Path.cwd()
        cfg = getattr(project, "detection", None)

        base_kwargs = {
            "video_path": str(video_path) if video_path else "",
            "out_dir": str(out_dir),
            "slides_json": str(out_dir / "slides.json") if out_dir else "",
            "subtitles_path": getattr(project, "subtitles", None),
        }

        if cfg:
            from video2pptx.config import AppConfig
            base_kwargs["cfg"] = AppConfig(
                detection=cfg,
                llm=getattr(project, "llm", None),
                video=getattr(project, "video_config", None),
            )

        full_kwargs = {**base_kwargs, **args}
        command = {"quick_preview": "preview"}.get(tool, tool)
        result = execute_command(command, **full_kwargs)
        if result.get("success") is False:
            raise OperationError(
                type="ApplicationCommandError",
                message=result.get("error", f"Command failed: {command}"),
                stage=result.get("stage", command),
                recoverable=True,
            )
        self._persist_project_result(project_path, tool, result)
        return result

    @staticmethod
    def _persist_project_result(
        project_path: Path | None,
        tool: str,
        result: dict[str, Any],
    ) -> None:
        """Compatibility bridge until Phase-16 repository services own persistence."""
        if project_path is None:
            return
        from video2pptx.project_manager import (
            load_slides_into_project,
            open_project,
            save_project,
        )

        project = open_project(project_path)
        if tool == "quick_preview":
            project.score_timestamps = list(result.get("score_timestamps", []))
            project.score_values = list(result.get("score_values", []))
            project.state.preview_done = True
        elif tool == "detect":
            project.slides_json = "slides.json"
            load_slides_into_project(project, force=True)
            project.state.detect_done = True
            project.state.detect_stale = False
            project.state.mark_stale_downstream("detect")
        elif tool == "auto_align":
            load_slides_into_project(project, force=True)
            project.state.align_done = True
            project.state.align_stale = False
            project.state.mark_stale_downstream("align")
        elif tool == "export_md":
            project.state.md_exported = True
            project.state.md_stale = False
        elif tool == "export_pptx":
            project.state.pptx_exported = True
            project.state.pptx_stale = False
        save_project(project, project_path)


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
