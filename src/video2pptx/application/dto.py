# FILE: src/video2pptx/application/dto.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Structured DTOs for application service results and progress reporting.
#   SCOPE: ServiceResult, ProgressUpdate
#   DEPENDS: none
#   LINKS: M-APP-COMMON, V-REF-APP-SERVICES
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ServiceResult - typed result from a stage service execution
#   ProgressUpdate - percent and message for progress reporting
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add common application DTOs
# END_CHANGE_SUMMARY

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ProgressUpdate:
    percent: int
    message: str = ""

    def __post_init__(self) -> None:
        if not 0 <= self.percent <= 100:
            raise ValueError(f"percent must be 0-100, got {self.percent}")


@dataclass(frozen=True, slots=True)
class ServiceResult:
    success: bool
    stage: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    revision: str | None = None
    warnings: tuple[str, ...] = ()

    @classmethod
    def ok(
        cls,
        stage: str,
        *,
        data: dict[str, Any] | None = None,
        revision: str | None = None,
        warnings: tuple[str, ...] = (),
    ) -> ServiceResult:
        return cls(
            success=True,
            stage=stage,
            data=data or {},
            revision=revision,
            warnings=warnings,
        )

    @classmethod
    def fail(
        cls,
        stage: str,
        error: str,
        *,
        data: dict[str, Any] | None = None,
    ) -> ServiceResult:
        return cls(
            success=False,
            stage=stage,
            error=error,
            data=data or {},
        )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"success": self.success, "stage": self.stage}
        d.update(self.data)
        if self.error:
            d["error"] = self.error
        if self.revision:
            d["revision"] = self.revision
        if self.warnings:
            d["warnings"] = list(self.warnings)
        return d
