# FILE: src/video2pptx/debug/errors.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Typed operation errors for MCP — type/message/stage/recoverable/trace_id/details. Full traceback to log; never swallow exceptions.
#   SCOPE: OperationError dataclass, to_dict(), traceback log capture
#   DEPENDS: none
#   LINKS: M-STRUCTURED-ERRORS
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   OperationError - typed error envelope with type/message/stage/recoverable/trace_id/details
# END_MODULE_MAP

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass
class OperationError(Exception):
    type: str
    message: str
    stage: str = ""
    recoverable: bool = False
    trace_id: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        stage: str = "",
        trace_id: str = "",
        recoverable: bool = True,
    ) -> OperationError:
        tb = traceback.format_exc()
        logger.error(f"[OperationError] {type(exc).__name__}: {exc} | stage={stage} trace_id={trace_id}\n{tb}")
        return cls(
            type=type(exc).__name__,
            message=str(exc),
            stage=stage,
            recoverable=recoverable,
            trace_id=trace_id,
            details={"traceback": tb},
        )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "type": self.type,
            "message": self.message,
        }
        if self.stage:
            d["stage"] = self.stage
        if self.recoverable:
            d["recoverable"] = True
        if self.trace_id:
            d["trace_id"] = self.trace_id
        if self.details:
            d["details"] = self.details
        return d
