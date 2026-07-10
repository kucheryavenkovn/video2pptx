# FILE: src/video2pptx/debug/operation_registry.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Operation lifecycle registry for MCP async operations — tracks queued/running/succeeded/failed/cancelled
#   SCOPE: create, update, get, wait, cancel, list operations with timestamps and progress
#   DEPENDS: threading, uuid, time
#   LINKS: M-OPERATION-REGISTRY
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   OperationRegistry - singleton registry for tracking async MCP operations
#   Operation - dataclass for a single operation lifecycle
# END_MODULE_MAP

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

VALID_STATUSES = {"queued", "running", "succeeded", "failed", "cancelled"}
TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}


@dataclass
class Operation:
    operation_id: str
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    status: str = "queued"
    queued_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    progress: int = 0
    stage: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])

    def to_dict(self) -> dict[str, Any]:
        d = {
            "operation_id": self.operation_id,
            "tool": self.tool,
            "arguments": self.arguments,
            "status": self.status,
            "queued_at": self.queued_at,
            "progress": self.progress,
            "stage": self.stage,
            "trace_id": self.trace_id,
        }
        if self.started_at:
            d["started_at"] = self.started_at
        if self.finished_at:
            d["finished_at"] = self.finished_at
        if self.result:
            d["result"] = self.result
        if self.error:
            d["error"] = self.error
        return d


class OperationRegistry:
    def __init__(self) -> None:
        self._operations: dict[str, Operation] = {}
        self._lock = threading.Lock()

    def create(self, tool: str, arguments: dict[str, Any] | None = None) -> Operation:
        op_id = uuid.uuid4().hex[:12]
        op = Operation(
            operation_id=op_id,
            tool=tool,
            arguments=arguments or {},
        )
        with self._lock:
            self._operations[op_id] = op
        logger.info(f"[OperationRegistry] Created | id={op_id} tool={tool}")
        return op

    def update(
        self,
        operation_id: str,
        status: str | None = None,
        progress: int | None = None,
        stage: str | None = None,
        result: dict | None = None,
        error: str | None = None,
    ) -> Operation | None:
        with self._lock:
            op = self._operations.get(operation_id)
            if op is None:
                return None
            if status is not None:
                if status not in VALID_STATUSES:
                    raise ValueError(f"Invalid status: {status}")
                op.status = status
                if status == "running" and op.started_at is None:
                    op.started_at = time.time()
                if status in TERMINAL_STATUSES:
                    op.finished_at = time.time()
            if progress is not None:
                op.progress = progress
            if stage is not None:
                op.stage = stage
            if result is not None:
                op.result = result
            if error is not None:
                op.error = error
            return op

    def get(self, operation_id: str) -> Operation | None:
        with self._lock:
            return self._operations.get(operation_id)

    def list_operations(self, limit: int = 20) -> list[Operation]:
        with self._lock:
            ops = sorted(
                self._operations.values(),
                key=lambda o: o.queued_at,
                reverse=True,
            )
            return ops[:limit]

    def wait(self, operation_id: str, timeout: float = 120.0, poll_interval: float = 0.1) -> Operation | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            op = self.get(operation_id)
            if op is None:
                return None
            if op.status in TERMINAL_STATUSES:
                return op
            time.sleep(poll_interval)
        return self.get(operation_id)

    def cancel(self, operation_id: str) -> Operation | None:
        op = self.get(operation_id)
        if op is None:
            return None
        if op.status in TERMINAL_STATUSES:
            return op
        return self.update(operation_id, status="cancelled")

    def clear(self) -> None:
        with self._lock:
            self._operations.clear()
