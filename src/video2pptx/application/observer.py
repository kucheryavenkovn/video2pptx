# FILE: src/video2pptx/application/observer.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Progress observer protocol for application services.
#   SCOPE: ProgressObserver Protocol, NullProgressObserver
#   DEPENDS: video2pptx.application.dto
#   LINKS: M-APP-COMMON, V-REF-APP-SERVICES
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ProgressObserver - Protocol with on_progress(percent, message)
#   NullProgressObserver - no-op default implementation
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add progress observer protocol and null implementation
# END_CHANGE_SUMMARY

from __future__ import annotations

from typing import Protocol

from video2pptx.application.dto import ProgressUpdate


class ProgressObserver(Protocol):
    """Protocol for receiving progress updates from a running service."""

    def on_progress(self, update: ProgressUpdate) -> None:
        ...


class NullProgressObserver:
    """No-op observer that silently discards all progress updates."""

    def on_progress(self, update: ProgressUpdate) -> None:
        pass
