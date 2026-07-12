# FILE: src/video2pptx/application/base.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Shared service context and project-bound input resolution for all application services.
#   SCOPE: ServiceContext, resolve_project_input, resolve_project_path, resolve_detection_override, normalize_roi
#   DEPENDS: video2pptx.application.dto, video2pptx.application.cancellation, video2pptx.application.observer,
#            video2pptx.application.errors
#   LINKS: M-APP-COMMON, M-APP-INPUT-RESOLVER, V-REF-DETECTION-INPUT
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ServiceContext - bundles repository, observer, cancellation for stage services
#   resolve_project_input - resolve None/""/whitespace override against project value
#   resolve_project_path - resolve and validate file path from override or project
#   resolve_detection_override - typed detection setting override (None = use project)
#   normalize_roi - normalize None/"" to "auto"
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Add input resolution contract for project-bound operations
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

from loguru import logger

from video2pptx.application.cancellation import CancellationToken
from video2pptx.application.dto import ProgressUpdate
from video2pptx.application.observer import NullProgressObserver, ProgressObserver


# START_CONTRACT: resolve_project_input
#   PURPOSE: Resolve None/""/whitespace override against canonical project value.
#            Raises PreconditionError if both are absent.
#   INPUTS: { override: str|None - command argument, project_value: str|None - canonical field,
#             field: str - display name for error messages }
#   OUTPUTS: str - resolved non-blank value
#   SIDE_EFFECTS: may raise PreconditionError
#   LINKS: M-APP-INPUT-RESOLVER
# END_CONTRACT: resolve_project_input
def resolve_project_input(
    override: str | None,
    project_value: str | None,
    *,
    field: str = "",
) -> str:
    effective = (override or "").strip()
    if not effective:
        effective = (project_value or "").strip()
    if not effective:
        from video2pptx.application.errors import PreconditionError
        raise PreconditionError(
            f"Project has no {field} configured" if field else "Required input is missing"
        )
    return effective


# START_CONTRACT: resolve_project_path
#   PURPOSE: Resolve file path from override or project, exists+is_file validation.
#   INPUTS: { override: str|None, project_value: str|None, field: str }
#   OUTPUTS: Path - validated existing file path
#   SIDE_EFFECTS: raises PreconditionError on missing/directory path
#   LINKS: M-APP-INPUT-RESOLVER
# END_CONTRACT: resolve_project_path
def resolve_project_path(
    override: str | None,
    project_value: str | None,
    *,
    field: str = "video",
) -> Path:
    raw = resolve_project_input(override, project_value, field=field)
    p = Path(raw)
    if p.is_dir():
        from video2pptx.application.errors import PreconditionError
        raise PreconditionError(f"Configured {field} path is not a file: {raw}")
    if not p.exists():
        from video2pptx.application.errors import PreconditionError
        raise PreconditionError(f"Configured {field} path does not exist: {raw}")
    return p


def resolve_detection_override(
    override: float | str | None,
    project_value: float | str,
) -> float | str:
    """Resolve a detection settings override (None → use project value)."""
    if override is not None:
        return override
    return project_value


def normalize_roi(roi: str | None) -> str:
    """Normalize blank ROI to 'auto'."""
    roi = (roi or "").strip()
    return roi if roi else "auto"


class ServiceContext:
    """Shared dependency bundle for application stage services.

    Holds a repository port, progress observer, and cancellation token.
    Services call ``check_cancelled(stage)`` and ``report_progress(percent, message)``
    instead of managing these concerns individually.
    """

    def __init__(
        self,
        repository: object | None = None,
        observer: ProgressObserver | None = None,
        cancellation: CancellationToken | None = None,
    ) -> None:
        self._repository = repository
        self._observer: ProgressObserver = observer or NullProgressObserver()
        self._cancellation = cancellation or CancellationToken()

    @property
    def repository(self) -> object | None:
        return self._repository

    @property
    def cancellation(self) -> CancellationToken:
        return self._cancellation

    def check_cancelled(self, stage: str = "") -> None:
        self._cancellation.check(stage)

    def report_progress(self, percent: int, message: str = "") -> None:
        update = ProgressUpdate(percent=percent, message=message)
        self._observer.on_progress(update)
        logger.debug(f"[ServiceContext] progress | percent={percent} message={message}")
