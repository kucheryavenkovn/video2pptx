# FILE: src/video2pptx/adapters/cli/observer.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Rich Console progress observer for CLI commands.
#   SCOPE: RichOperationObserver — prints deterministic progress in TTY and non-TTY environments
#   DEPENDS: video2pptx.application.dto, rich.console
#   LINKS: M-CLI-ADAPTER
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   RichOperationObserver - ProgressObserver that prints via Rich Console
# END_MODULE_MAP

from __future__ import annotations

from rich.console import Console
from rich.markup import escape

from video2pptx.application.dto import ProgressUpdate


class RichOperationObserver:
    """ProgressObserver that prints deterministic progress lines via Rich Console.

    Uses ``console.print()`` unconditionally (no live progress bar) so output
    is deterministic and testable.  In non-TTY environments (e.g. test runner
    with ``record=True``, ``force_terminal=False``) no ANSI escape sequences
    will be emitted.
    """

    def __init__(self, console: Console, *, stage: str = "") -> None:
        self._console = console
        self._stage = stage

    @property
    def stage(self) -> str:
        return self._stage

    def on_progress(self, update: ProgressUpdate) -> None:
        tag = self._stage or update.message.split(" ")[0] if update.message else ""
        percent = update.percent
        msg = update.message

        line = escape(f"[{tag}] ") + f"{percent}% {msg}" if tag else f"{percent}% {msg}"
        self._console.print(line, highlight=False)
