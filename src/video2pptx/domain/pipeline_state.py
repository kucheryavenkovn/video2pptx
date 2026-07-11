# FILE: src/video2pptx/domain/pipeline_state.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Pipeline stage state machine with transitions, invalidation, and legacy compatibility.
#   SCOPE: StageStatus, StageState, PipelineState, transition validation, downstream invalidation
#   DEPENDS: video2pptx.domain.errors
#   LINKS: M-DOMAIN-VALUE, M-DOMAIN-STATE
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   StageStatus - enum: NOT_STARTED, RUNNING, SUCCEEDED, FAILED, CANCELLED, STALE, SKIPPED
#   StageState - dataclass: per-stage status, operation metadata, timestamps, error
#   PipelineState - collection of StageState with transition enforcement and downstream invalidation
#   PIPELINE_STAGES - ordered tuple of all known pipeline stage names
#   DOWNSTREAM - mapping of stage -> tuple of downstream stages that become stale
#   VALID_TRANSITIONS - mapping of (from_status, to_status) -> bool
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Allow SUCCEEDED to RUNNING transition for stage re-runs
# END_CHANGE_SUMMARY

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from video2pptx.domain.errors import IllegalStateTransition


class StageStatus(str, Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STALE = "stale"
    SKIPPED = "skipped"


PIPELINE_STAGES: tuple[str, ...] = (
    "preview",
    "detect",
    "align",
    "notes",
    "llm",
    "markdown_export",
    "pptx_export",
    "auto",
)

DOWNSTREAM: dict[str, tuple[str, ...]] = {
    "preview": (),
    "detect": ("align", "notes", "llm", "markdown_export", "pptx_export", "auto"),
    "align": ("notes", "llm", "markdown_export", "pptx_export", "auto"),
    "notes": ("llm", "markdown_export", "pptx_export", "auto"),
    "llm": ("markdown_export", "pptx_export", "auto"),
    "markdown_export": (),
    "pptx_export": (),
    "auto": (),
}

VALID_TRANSITIONS: dict[tuple[StageStatus, StageStatus], bool] = {
    (StageStatus.NOT_STARTED, StageStatus.RUNNING): True,
    (StageStatus.NOT_STARTED, StageStatus.SKIPPED): True,
    (StageStatus.RUNNING, StageStatus.SUCCEEDED): True,
    (StageStatus.RUNNING, StageStatus.FAILED): True,
    (StageStatus.RUNNING, StageStatus.CANCELLED): True,
    (StageStatus.SUCCEEDED, StageStatus.STALE): True,
    (StageStatus.SUCCEEDED, StageStatus.RUNNING): True,
    (StageStatus.FAILED, StageStatus.RUNNING): True,
    (StageStatus.STALE, StageStatus.RUNNING): True,
    (StageStatus.CANCELLED, StageStatus.RUNNING): True,
    (StageStatus.SKIPPED, StageStatus.RUNNING): True,
}


@dataclass
class StageState:
    status: StageStatus = StageStatus.NOT_STARTED
    operation_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "operation_id": self.operation_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StageState:
        status_raw = data.get("status", "not_started")
        try:
            status = StageStatus(status_raw)
        except ValueError:
            status = StageStatus.NOT_STARTED
        started = data.get("started_at")
        finished = data.get("finished_at")
        return cls(
            status=status,
            operation_id=data.get("operation_id"),
            started_at=datetime.fromisoformat(started) if started else None,
            finished_at=datetime.fromisoformat(finished) if finished else None,
            error=data.get("error"),
        )


class PipelineState:
    """Mutable collection of per-stage state with transition enforcement.

    This is NOT frozen because pipeline transitions are inherently stateful.
    However the value objects within each StageState are copied on transition.
    """

    def __init__(self) -> None:
        self._stages: dict[str, StageState] = {
            stage: StageState() for stage in PIPELINE_STAGES
        }

    def get(self, stage: str) -> StageState:
        if stage not in self._stages:
            raise KeyError(f"Unknown pipeline stage: {stage}")
        return self._stages[stage]

    def status(self, stage: str) -> StageStatus:
        return self.get(stage).status

    def start(
        self,
        stage: str,
        operation_id: str | None = None,
    ) -> None:
        self._transition(stage, StageStatus.RUNNING)
        s = self._stages[stage]
        s.operation_id = operation_id
        s.started_at = datetime.now(timezone.utc)
        s.finished_at = None
        s.error = None

    def succeed(self, stage: str) -> None:
        self._transition(stage, StageStatus.SUCCEEDED)
        s = self._stages[stage]
        s.finished_at = datetime.now(timezone.utc)

    def fail(self, stage: str, error: dict[str, Any] | None = None) -> None:
        self._transition(stage, StageStatus.FAILED)
        s = self._stages[stage]
        s.finished_at = datetime.now(timezone.utc)
        s.error = error

    def cancel(self, stage: str) -> None:
        self._transition(stage, StageStatus.CANCELLED)
        s = self._stages[stage]
        s.finished_at = datetime.now(timezone.utc)

    def skip(self, stage: str, reason: str | None = None) -> None:
        self._transition(stage, StageStatus.SKIPPED)

    def invalidate_from(self, stage: str) -> list[str]:
        """Mark all downstream stages as STALE. Returns list of invalidated stage names."""
        if stage not in self._stages:
            raise KeyError(f"Unknown pipeline stage: {stage}")
        invalidated: list[str] = []
        for downstream in DOWNSTREAM.get(stage, ()):
            ds = self._stages[downstream]
            if ds.status == StageStatus.SUCCEEDED:
                ds.status = StageStatus.STALE
                invalidated.append(downstream)
        return invalidated

    def can_run(self, stage: str) -> bool:
        s = self.get(stage)
        return s.status in (
            StageStatus.NOT_STARTED,
            StageStatus.FAILED,
            StageStatus.STALE,
            StageStatus.CANCELLED,
            StageStatus.SKIPPED,
        )

    def _transition(self, stage: str, target: StageStatus) -> None:
        s = self.get(stage)
        current = s.status
        if current == target:
            return
        key = (current, target)
        if not VALID_TRANSITIONS.get(key, False):
            raise IllegalStateTransition(
                f"Cannot transition {stage} from {current.value} to {target.value}"
            )
        s.status = target

    def to_dict(self) -> dict[str, Any]:
        return {
            stage: self._stages[stage].to_dict()
            for stage in PIPELINE_STAGES
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineState:
        ps = cls()
        for stage in PIPELINE_STAGES:
            if stage in data:
                ps._stages[stage] = StageState.from_dict(data[stage])
        return ps

    @classmethod
    def from_legacy_booleans(
        cls,
        detect_done: bool = False,
        notes_done: bool = False,
        llm_done: bool = False,
        preview_done: bool = False,
        align_done: bool = False,
        md_exported: bool = False,
        pptx_exported: bool = False,
        auto_done: bool = False,
    ) -> PipelineState:
        """Construct a PipelineState from legacy boolean flags."""
        ps = cls()
        if preview_done:
            ps._stages["preview"].status = StageStatus.SUCCEEDED
        if detect_done:
            ps._stages["detect"].status = StageStatus.SUCCEEDED
        if align_done:
            ps._stages["align"].status = StageStatus.SUCCEEDED
        if notes_done:
            ps._stages["notes"].status = StageStatus.SUCCEEDED
        if llm_done:
            ps._stages["llm"].status = StageStatus.SUCCEEDED
        if md_exported:
            ps._stages["markdown_export"].status = StageStatus.SUCCEEDED
        if pptx_exported:
            ps._stages["pptx_export"].status = StageStatus.SUCCEEDED
        if auto_done:
            ps._stages["auto"].status = StageStatus.SUCCEEDED
        return ps

    def to_legacy_booleans(self) -> dict[str, bool]:
        """Derive legacy boolean flags from the current state machine."""
        return {
            "preview_done": self._stages["preview"].status == StageStatus.SUCCEEDED,
            "detect_done": self._stages["detect"].status == StageStatus.SUCCEEDED,
            "align_done": self._stages["align"].status == StageStatus.SUCCEEDED,
            "notes_done": self._stages["notes"].status == StageStatus.SUCCEEDED,
            "llm_done": self._stages["llm"].status == StageStatus.SUCCEEDED,
            "md_exported": self._stages["markdown_export"].status == StageStatus.SUCCEEDED,
            "pptx_exported": self._stages["pptx_export"].status == StageStatus.SUCCEEDED,
            "auto_done": self._stages["auto"].status == StageStatus.SUCCEEDED,
        }
