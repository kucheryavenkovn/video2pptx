# FILE: src/video2pptx/adapters/cli/__init__.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Barrel export for CLI adapter types and helpers.
#   SCOPE: Re-export CliContext, CliExitCode, RichOperationObserver, render_cli_error, render_service_result
#   DEPENDS: video2pptx.adapters.cli.context, video2pptx.adapters.cli.exit_codes,
#            video2pptx.adapters.cli.errors, video2pptx.adapters.cli.renderer,
#            video2pptx.adapters.cli.observer
#   LINKS: M-CLI-ADAPTER
#   ROLE: BARREL
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   CliExitCode - numeric exit codes for CLI commands
#   CliContext - shared CLI runtime context
#   RichOperationObserver - progress observer with Rich Console
#   render_cli_error - classify and render an exception to exit code + console
#   render_service_result - render ServiceResult to console or JSON
# END_MODULE_MAP

from video2pptx.adapters.cli.context import CliContext
from video2pptx.adapters.cli.errors import render_cli_error
from video2pptx.adapters.cli.exit_codes import CliExitCode
from video2pptx.adapters.cli.observer import RichOperationObserver
from video2pptx.adapters.cli.renderer import render_service_result

__all__ = [
    "CliContext",
    "CliExitCode",
    "RichOperationObserver",
    "render_cli_error",
    "render_service_result",
]
