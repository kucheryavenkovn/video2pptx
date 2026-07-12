# FILE: src/video2pptx/adapters/cli/renderer.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Render ServiceResult to console or JSON.
#   SCOPE: render_service_result
#   DEPENDS: video2pptx.application.dto, rich.console
#   LINKS: M-CLI-ADAPTER
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   render_service_result - human or JSON rendering of ServiceResult
# END_MODULE_MAP

from __future__ import annotations

import json

from rich.console import Console
from rich.markup import escape

from video2pptx.application.dto import ServiceResult


def render_service_result(
    result: ServiceResult,
    console: Console,
    *,
    json_output: bool = False,
) -> None:
    if json_output:
        console.print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return

    if result.success:
        stage_tag = escape(f"[{result.stage}]")
        parts = [f"[green]SUCCESS[/green] {stage_tag}"]
        if result.data:
            for key, value in result.data.items():
                if isinstance(value, (list, dict)):
                    continue
                parts.append(f"  {key}: {value}")
        if result.revision:
            parts.append(f"  revision: {result.revision}")
        if result.warnings:
            for w in result.warnings:
                parts.append(f"  [yellow]warning: {w}[/yellow]")
        console.print("\n".join(parts))
    else:
        console.print(f"[red]FAILED[/red] [{result.stage}]: {result.error or 'Unknown error'}")
