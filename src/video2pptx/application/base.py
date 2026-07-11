# FILE: src/video2pptx/application/base.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Shared service context bundling repository, observer, and cancellation.
#   SCOPE: ServiceContext
#   DEPENDS: video2pptx.application.dto, video2pptx.application.cancellation, video2pptx.application.observer
#   LINKS: M-APP-COMMON, V-REF-APP-SERVICES
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ServiceContext - bundles repository, observer, cancellation for stage services
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add ServiceContext for shared service dependencies
# END_CHANGE_SUMMARY

from __future__ import annotations

from loguru import logger

from video2pptx.application.cancellation import CancellationToken
from video2pptx.application.dto import ProgressUpdate
from video2pptx.application.observer import NullProgressObserver, ProgressObserver


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
