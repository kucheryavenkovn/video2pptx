# FILE: src/video2pptx/application/cancellation.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Cooperative cancellation token for application services.
#   SCOPE: CancellationToken
#   DEPENDS: video2pptx.application.errors
#   LINKS: M-APP-COMMON, V-REF-APP-SERVICES
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   CancellationToken - thread-safe flag that services check between steps
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add cooperative cancellation token
# END_CHANGE_SUMMARY

from __future__ import annotations

import threading

from video2pptx.application.errors import CancellationError


class CancellationToken:
    """Thread-safe cooperative cancellation flag.

    Services call ``check(stage)`` between steps.  When ``trigger()``
    has been called from another thread, the next ``check`` raises
    :class:`CancellationError`.
    """

    def __init__(self) -> None:
        self._cancelled = threading.Event()

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    def trigger(self) -> None:
        self._cancelled.set()

    def check(self, stage: str = "") -> None:
        if self._cancelled.is_set():
            raise CancellationError(stage=stage)

    def reset(self) -> None:
        self._cancelled.clear()
