# FILE: src/video2pptx/adapters/cli/context.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Shared CLI runtime context bundling services, console, cancellation, and flags.
#   SCOPE: CliContext dataclass
#   DEPENDS: video2pptx.application.cancellation, rich.console
#   LINKS: M-CLI-ADAPTER
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   CliContext - services, console, cancellation token, debug, json_output
# END_MODULE_MAP

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rich.console import Console

from video2pptx.application.cancellation import CancellationToken


@dataclass
class CliContext:
    services: Any = None
    console: Console = field(default_factory=Console)
    cancellation: CancellationToken = field(default_factory=CancellationToken)
    debug: bool = False
    json_output: bool = False

    def handle_interrupt(self) -> None:
        """Trigger the cancellation token."""
        self.cancellation.trigger()
