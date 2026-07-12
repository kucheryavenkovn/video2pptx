# FILE: src/video2pptx/adapters/cli/errors.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Classify application/domain/infrastructure exceptions into CliExitCode and render them.
#   SCOPE: classify_error, render_cli_error
#   DEPENDS: video2pptx.adapters.cli.exit_codes, video2pptx.application.errors,
#            video2pptx.domain.errors, video2pptx.infrastructure.persistence.errors,
#            rich.console, typing
#   LINKS: M-CLI-ADAPTER
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   classify_error - map an exception to (CliExitCode, category_label)
#   render_cli_error - print formatted error and return exit code
# END_MODULE_MAP

from __future__ import annotations

from rich.console import Console
from rich.markup import escape

from video2pptx.adapters.cli.exit_codes import CliExitCode
from video2pptx.application.errors import CancellationError, StageFailureError
from video2pptx.domain.errors import DomainError, ValidationError
from video2pptx.infrastructure.persistence.errors import (
    ProjectAlreadyExists,
    ProjectAtomicWriteError,
    ProjectDocumentCorrupted,
    ProjectNotFound,
    ProjectRevisionConflict,
    ProjectSchemaUnsupported,
)


def classify_error(error: Exception) -> tuple[CliExitCode, str]:
    if isinstance(error, CancellationError):
        return CliExitCode.CANCELLED, "CANCELLED"

    if isinstance(error, ProjectRevisionConflict):
        return CliExitCode.PERSISTENCE_CONFLICT, "PERSISTENCE_CONFLICT"

    if isinstance(error, ProjectAlreadyExists):
        return CliExitCode.PRECONDITION_ERROR, "PRECONDITION_ERROR"

    if isinstance(error, (ProjectNotFound, ProjectDocumentCorrupted, ProjectSchemaUnsupported)):
        return CliExitCode.PRECONDITION_ERROR, "PRECONDITION_ERROR"

    if isinstance(error, ProjectAtomicWriteError):
        return CliExitCode.EXTERNAL_ADAPTER_ERROR, "EXTERNAL_ADAPTER_ERROR"

    if isinstance(error, StageFailureError):
        return CliExitCode.GENERAL_APPLICATION_ERROR, "STAGE_FAILURE"

    if isinstance(error, ValidationError):
        return CliExitCode.VALIDATION_ERROR, "VALIDATION_ERROR"

    if isinstance(error, DomainError):
        return CliExitCode.VALIDATION_ERROR, "DOMAIN_ERROR"

    if isinstance(error, (ValueError, FileNotFoundError)):
        return CliExitCode.CLI_USAGE_ERROR, "CLI_USAGE_ERROR"

    if isinstance(error, KeyboardInterrupt):
        return CliExitCode.CANCELLED, "CANCELLED"

    return CliExitCode.GENERAL_APPLICATION_ERROR, "UNEXPECTED"


def render_cli_error(
    error: Exception,
    console: Console,
    *,
    debug: bool = False,
    project: str | None = None,
    stage: str | None = None,
) -> CliExitCode:
    code, category = classify_error(error)

    prefix_parts: list[str] = []
    if project:
        prefix_parts.append(f"[{project}]")
    if stage:
        prefix_parts.append(f"[{stage}]")
    prefix = escape(" ".join(prefix_parts))
    if prefix:
        prefix += " "

    message = escape(str(error) or type(error).__name__)
    console.print(f"[red]Error[/red] {prefix}{message}", highlight=False)

    if debug:
        import traceback
        console.print("[dim]Traceback:[/dim]")
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        console.print(f"[dim]{tb.rstrip()}[/dim]")

    if isinstance(error, ProjectNotFound):
        path = error.path or ""
        if path:
            console.print(f"[yellow]Project not found: {path}[/yellow]")
        console.print("[yellow]Create the project first with: video2pptx project create VIDEO DIR[/yellow]")

    if isinstance(error, ProjectRevisionConflict):
        console.print("[yellow]The project was modified elsewhere. Reload and try again.[/yellow]")

    if isinstance(error, ProjectAlreadyExists):
        path = error.path or ""
        if path:
            console.print(f"[yellow]Directory already contains a project: {path}[/yellow]")
        console.print("[yellow]Use a different directory or remove the existing project.[/yellow]")

    return code
