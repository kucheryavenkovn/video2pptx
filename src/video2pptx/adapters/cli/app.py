# FILE: src/video2pptx/adapters/cli/app.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Typer CLI commands routing to Application Services.
#   SCOPE: preview, detect, align, notes, export-md, export-pptx, validate, auto
#   DEPENDS: video2pptx.bootstrap, video2pptx.adapters.cli.*, rich, typer
#   LINKS: M-CLI-ADAPTER
#   ROLE: ENTRY_POINT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   build_app - create configured Typer app with project-based pipeline commands
#   _run_service - execute a service call with error handling
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add project-based pipeline commands calling Application Services
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from video2pptx.adapters.cli.context import CliContext
from video2pptx.adapters.cli.errors import render_cli_error
from video2pptx.adapters.cli.exit_codes import CliExitCode
from video2pptx.adapters.cli.renderer import render_service_result
from video2pptx.bootstrap import ApplicationServices

_service_attr_map: dict[str, str] = {
    "preview": "preview_service",
    "detect": "detection_service",
    "align": "alignment_service",
    "notes": "notes_service",
    "export-md": "export_service",
    "export-pptx": "export_service",
    "validate": "validation_service",
    "auto": "auto_service",
}


def _run_service(
    services: ApplicationServices,
    console: Console,
    project_dir: Path,
    command: str,
    **kwargs: Any,
) -> int:
    attr = _service_attr_map.get(command, f"{command}_service")
    try:
        service = getattr(services, attr)
        result = service.execute(project_dir, **kwargs)
        render_service_result(result, console)
        # AutoService always returns success=True; check data.success for actual pipeline status
        pipeline_ok = result.data.get("success", True) if command == "auto" else result.success
        return CliExitCode.SUCCESS if pipeline_ok else CliExitCode.GENERAL_APPLICATION_ERROR
    except Exception as exc:
        return render_cli_error(exc, console, project=str(project_dir), stage=command)


def _make_code(exit_code: CliExitCode) -> int:
    return int(exit_code)


def build_app() -> typer.Typer:
    app = typer.Typer(name="video2pptx")
    project_app = typer.Typer(name="project", help="Manage projects - create, open, info")
    app.add_typer(project_app, name="project")

    @app.callback(invoke_without_command=True)
    def main_callback(
        ctx: typer.Context,
        debug: bool = typer.Option(False, "--debug", help="Enable debug output"),
        json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
    ) -> None:
        ctx.obj = CliContext(
            console=Console(),
            debug=debug,
            json_output=json_output,
        )
        if ctx.invoked_subcommand is None:
            console = Console()
            console.print(ctx.get_help())

    @app.command()
    def preview(
        ctx: typer.Context,
        project_dir: str = typer.Argument(..., help="Project directory"),
        sample_fps: float = typer.Option(2.0, "--sample-fps"),
        slide_roi: str = typer.Option("auto", "--slide-roi"),
        threshold: float = typer.Option(0.95, "--threshold"),
        min_stable_duration: float = typer.Option(2.0, "--min-stable-duration"),
    ) -> None:
        """Preview diff scores without creating slides."""
        cli_ctx: CliContext = ctx.obj
        services = ApplicationServices()
        raise typer.Exit(
            code=_make_code(
                _run_service(
                    services, cli_ctx.console, Path(project_dir), "preview",
                    video_path="", sample_fps=sample_fps, slide_roi=slide_roi,
                    ignore_rois=[], threshold=threshold,
                    min_stable_duration=min_stable_duration,
                )
            )
        )

    @app.command()
    def detect(
        ctx: typer.Context,
        project_dir: str = typer.Argument(..., help="Project directory"),
        sample_fps: float = typer.Option(2.0, "--sample-fps"),
        slide_roi: str = typer.Option("auto", "--slide-roi"),
        threshold: float = typer.Option(0.95, "--threshold"),
        min_stable_duration: float = typer.Option(2.0, "--min-stable-duration"),
        min_slide_duration: float = typer.Option(2.0, "--min-slide-duration"),
        dedupe: bool = typer.Option(True, "--dedupe/--no-dedupe"),
    ) -> None:
        """Detect slides in a project (CV only)."""
        cli_ctx: CliContext = ctx.obj
        services = ApplicationServices()
        raise typer.Exit(
            code=_make_code(
                _run_service(
                    services, cli_ctx.console, Path(project_dir), "detect",
                    video_path="", sample_fps=sample_fps, slide_roi=slide_roi,
                    ignore_rois=[], threshold=threshold,
                    min_stable_duration=min_stable_duration,
                    min_slide_duration=min_slide_duration,
                    dedupe_enabled=dedupe,
                )
            )
        )

    @app.command()
    def align(
        ctx: typer.Context,
        project_dir: str = typer.Argument(..., help="Project directory"),
        subtitles: str = typer.Option("", "--subtitles", help="Path to SRT/VTT file"),
        dry_run: bool = typer.Option(False, "--dry-run", help="Show alignment plan without applying"),
    ) -> None:
        """Align slide intervals to subtitle timestamps."""
        cli_ctx: CliContext = ctx.obj
        services = ApplicationServices()
        raise typer.Exit(
            code=_make_code(
                _run_service(
                    services, cli_ctx.console, Path(project_dir), "align",
                    subtitles_path=subtitles, dry_run=dry_run,
                )
            )
        )

    @app.command()
    def notes(
        ctx: typer.Context,
        project_dir: str = typer.Argument(..., help="Project directory"),
        subtitles: str = typer.Option("", "--subtitles", help="Path to SRT/VTT file"),
        mode: str = typer.Option("basic", "--mode", help="Notes mode: basic or llm"),
    ) -> None:
        """Process notes and transcripts for slides."""
        cli_ctx: CliContext = ctx.obj
        services = ApplicationServices()
        raise typer.Exit(
            code=_make_code(
                _run_service(
                    services, cli_ctx.console, Path(project_dir), "notes",
                    subtitles_path=subtitles, mode=mode,
                )
            )
        )

    @app.command(name="export-md")
    def export_md(
        ctx: typer.Context,
        project_dir: str = typer.Argument(..., help="Project directory"),
        output: str = typer.Option("", "--out", "-o", help="Output path"),
        overwrite: bool = typer.Option(True, "--overwrite/--no-overwrite"),
    ) -> None:
        """Export project to Marp Markdown."""
        cli_ctx: CliContext = ctx.obj
        services = ApplicationServices()
        raise typer.Exit(
            code=_make_code(
                _run_service(
                    services, cli_ctx.console, Path(project_dir), "export-md",
                    output_path=output, format="markdown", overwrite=overwrite,
                )
            )
        )

    @app.command(name="export-pptx")
    def export_pptx(
        ctx: typer.Context,
        project_dir: str = typer.Argument(..., help="Project directory"),
        output: str = typer.Option("", "--out", "-o", help="Output path"),
        overwrite: bool = typer.Option(True, "--overwrite/--no-overwrite"),
    ) -> None:
        """Export project to PPTX."""
        cli_ctx: CliContext = ctx.obj
        services = ApplicationServices()
        raise typer.Exit(
            code=_make_code(
                _run_service(
                    services, cli_ctx.console, Path(project_dir), "export-pptx",
                    output_path=output, format="pptx", overwrite=overwrite,
                )
            )
        )

    @app.command()
    def validate(
        ctx: typer.Context,
        project_dir: str = typer.Argument(..., help="Project directory"),
    ) -> None:
        """Validate project storage and aggregate."""
        cli_ctx: CliContext = ctx.obj
        services = ApplicationServices()
        raise typer.Exit(
            code=_make_code(
                _run_service(
                    services, cli_ctx.console, Path(project_dir), "validate",
                )
            )
        )

    @app.command()
    def gui() -> None:
        """Launch the desktop GUI."""
        import sys

        from PySide6.QtWidgets import QApplication

        from video2pptx.gui.main_window import MainWindow
        qapp = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(qapp.exec())

    @app.command()
    def auto(
        ctx: typer.Context,
        project_dir: str = typer.Argument(..., help="Project directory"),
        mode: str = typer.Option("full", "--mode", help="Mode: full, resume, or force"),
        video_path: str = typer.Option("", "--video-path", help="Video file path"),
        subtitles: str = typer.Option("", "--subtitles", help="Path to SRT/VTT file"),
        sample_fps: float = typer.Option(2.0, "--sample-fps"),
        slide_roi: str = typer.Option("auto", "--slide-roi"),
        threshold: float = typer.Option(0.95, "--threshold"),
        notes_mode: str = typer.Option("basic", "--notes-mode"),
        export_format: str = typer.Option("markdown", "--export-format"),
    ) -> None:
        """Run full pipeline: detect -> align -> notes -> export."""
        cli_ctx: CliContext = ctx.obj
        services = ApplicationServices()
        raise typer.Exit(
            code=_make_code(
                _run_service(
                    services, cli_ctx.console, Path(project_dir), "auto",
                    mode=mode, video_path=video_path, subtitles_path=subtitles,
                    sample_fps=sample_fps, slide_roi=slide_roi,
                    ignore_rois=[], threshold=threshold,
                    min_stable_duration=2.0, min_slide_duration=2.0,
                    dedupe_enabled=True, notes_mode=notes_mode,
                    export_format=export_format, export_output_path="",
                    dry_run=False,
                )
            )
        )

    @project_app.command(name="create")
    def project_create(
        ctx: typer.Context,
        project_dir: str = typer.Argument(..., help="Output project directory"),
        name: str = typer.Option("Untitled", "--name", "-n", help="Project name"),
        video: str = typer.Option("", "--video", help="Path to video file"),
        subtitles: str = typer.Option("", "--subtitles", help="Path to SRT/VTT file"),
    ) -> None:
        """Create a new project."""
        cli_ctx: CliContext = ctx.obj
        services = ApplicationServices()
        location = Path(project_dir)
        try:
            from video2pptx.domain.project import Project
            project = Project(name=name, output_dir=str(location))
            services.repository.create(location, project)
            if video:
                loaded = services.repository.load(location)
                loaded.project.import_video(Path(video))
                services.repository.save(loaded.project, location, expected_revision=loaded.revision)
            cli_ctx.console.print(f"[green]✓[/green] Project created: {location.resolve()}")
        except Exception as e:
            render_cli_error(e, cli_ctx.console, stage="project_create")
            raise typer.Exit(code=1) from None

    @project_app.command(name="open")
    def project_open(
        ctx: typer.Context,
        project_dir: str = typer.Argument(..., help="Path to project directory"),
    ) -> None:
        """Open and display project info."""
        cli_ctx: CliContext = ctx.obj
        services = ApplicationServices()
        try:
            loaded = services.repository.load(Path(project_dir))
            proj = loaded.project
            table = Table(title=f"Project: {proj.name}")
            table.add_column("Key", style="cyan")
            table.add_column("Value")
            table.add_row("Name", proj.name)
            table.add_row("Output dir", proj.output_dir)
            table.add_row("Video", str(proj.video) if proj.video else "(none)")
            table.add_row("Subtitles", str(proj.subtitles) if proj.subtitles else "(none)")
            table.add_row("Slides", str(len(proj.slides)))
            cli_ctx.console.print(table)
        except Exception as e:
            render_cli_error(e, cli_ctx.console, stage="project_open")
            raise typer.Exit(code=1) from None

    @project_app.command(name="info")
    def project_info(
        ctx: typer.Context,
        project_dir: str = typer.Argument(..., help="Path to project directory"),
    ) -> None:
        """Quick project status."""
        cli_ctx: CliContext = ctx.obj
        services = ApplicationServices()
        try:
            loaded = services.repository.load(Path(project_dir))
            proj = loaded.project
            cli_ctx.console.print(f"Project: [bold]{proj.name}[/bold] | "
                  f"Slides: {len(proj.slides)} | "
                  f"Detect: {'done' if proj.state.detect_done else 'pending'}")
        except Exception as e:
            render_cli_error(e, cli_ctx.console, stage="project_info")
            raise typer.Exit(code=1) from None

    return app


app = build_app()


def run() -> None:
    """Console_scripts entry point."""
    app()
