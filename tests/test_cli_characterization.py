# FILE: tests/test_cli_characterization.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Freeze the public pre-Step-7 CLI surface and explicit semantic migration boundary.
#   SCOPE: Command names, positional arguments, options, usage codes, and missing-file behavior.
#   DEPENDS: typer.testing, video2pptx.cli
#   LINKS: M-CLI-ADAPTER, V-M-REF-CLI-ADAPTER
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   EXPECTED_COMMANDS - public CLI commands present before Step 7 migration
#   HELP_CASES - command-specific arguments and options retained or deliberately migrated
#   test_* - characterization assertions for Typer transport behavior
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Freeze CLI surface before Phase 16 Step 7 implementation
# END_CHANGE_SUMMARY

from __future__ import annotations

import pytest
from typer.main import get_command
from typer.testing import CliRunner

from video2pptx.cli import app

runner = CliRunner()


def _declared_tokens(arguments: list[str]) -> set[str]:
    command = get_command(app)
    for name in arguments[:-1]:
        assert hasattr(command, "commands")
        command = command.commands[name]
    tokens: set[str] = set()
    for parameter in command.params:
        tokens.add(parameter.name.upper())
        tokens.update(getattr(parameter, "opts", ()))
        tokens.update(getattr(parameter, "secondary_opts", ()))
    return tokens

EXPECTED_COMMANDS = (
    "detect",
    "detect-slides",
    "notes",
    "roi-tool",
    "export-md",
    "export-pptx",
    "debug",
    "llm-process",
    "project",
    "gui",
    "preview",
    "align",
    "validate",
    "auto",
)

HELP_CASES = (
    (["detect", "--help"], ("VIDEO", "--subtitles", "--out", "--sample-fps", "--dedupe")),
    (["detect-slides", "--help"], ("VIDEO", "--out", "--slide-roi", "--ignore-roi")),
    (["notes", "--help"], ("SLIDES_JSON", "--subtitles", "--notes-mode")),
    (["roi-tool", "--help"], ("VIDEO", "--frame-ts")),
    (["export-md", "--help"], ("SLIDES_JSON", "--image-as-bg", "--transcript-location", "--timecodes")),
    (["export-pptx", "--help"], ("SLIDES_JSON", "--notes-mode")),
    (["debug", "--help"], ("SLIDES_JSON", "--out")),
    (["llm-process", "--help"], ("SLIDES_JSON", "--model", "--base-url")),
    (["project", "create", "--help"], ("VIDEO", "PROJECT_DIR", "--subtitles", "--name")),
    (["project", "open", "--help"], ("PROJECT_DIR",)),
    (["project", "info", "--help"], ("PROJECT_DIR",)),
    (["gui", "--help"], ()),
    (["preview", "--help"], ("PROJECT_DIR", "--sample-fps", "--slide-roi")),
    (["align", "--help"], ("PROJECT_DIR", "--subtitles", "--dry-run")),
    (["validate", "--help"], ("PROJECT_DIR",)),
    (["auto", "--help"], ("PROJECT_DIR", "--mode", "--notes-mode")),
)


def test_root_help_freezes_public_commands() -> None:
    result = runner.invoke(app, ["--help"], env={"COLUMNS": "240"}, terminal_width=240)
    assert result.exit_code == 0
    for command in EXPECTED_COMMANDS:
        assert command in result.stdout


@pytest.mark.parametrize(("arguments", "tokens"), HELP_CASES)
def test_command_help_freezes_arguments_and_options(arguments, tokens) -> None:
    result = runner.invoke(app, arguments, env={"COLUMNS": "240"}, terminal_width=240)
    assert result.exit_code == 0, result.output
    declared = _declared_tokens(arguments)
    for token in tokens:
        assert token in declared


def test_no_command_is_usage_error() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 2
    assert "Missing command" in result.output


@pytest.mark.parametrize(
    "arguments",
    (
        ["detect"],
        ["detect", "video.mp4", "--sample-fps", "not-a-number"],
        ["export-md"],
        ["project", "open"],
        ["detect", "video.mp4", "--unknown-option"],
    ),
)
def test_invalid_invocations_are_usage_errors(arguments) -> None:
    result = runner.invoke(app, arguments)
    assert result.exit_code == 2


@pytest.mark.parametrize(
    "arguments",
    (
        ["detect", "missing-video.mp4"],
        ["detect-slides", "missing-video.mp4"],
        ["notes", "missing-slides.json"],
        ["export-md", "missing-slides.json"],
        ["export-pptx", "missing-slides.json"],
        ["debug", "missing-slides.json"],
        ["llm-process", "missing-slides.json"],
        ["project", "open", "missing-project"],
        ["project", "info", "missing-project"],
    ),
)
def test_missing_inputs_return_legacy_precondition_code(arguments) -> None:
    result = runner.invoke(app, arguments)
    assert result.exit_code == 1
    assert "Traceback" not in result.output


def test_detect_semantic_migration_is_explicit() -> None:
    """Step 7 intentionally changes detect from all-in-one VIDEO mode to CV-only PROJECT_DIR."""
    declared = _declared_tokens(["detect", "--help"])
    assert "VIDEO" in declared
    assert "--export-md" in declared
    assert "--llm" in declared


def test_console_entry_point_shows_new_commands() -> None:
    """Verify the console entry point (video2pptx.cli:run) exposes all Phase 16 Step 7 commands."""
    result = runner.invoke(app, ["--help"], env={"COLUMNS": "240"}, terminal_width=240)
    assert result.exit_code == 0
    output = result.stdout
    for cmd in EXPECTED_COMMANDS:
        assert cmd in output, f"Command '{cmd}' not found in entry point --help output"
    # Verify new Step 7 commands are present
    for cmd in ("preview", "align", "validate", "auto"):
        assert cmd in output, f"Step 7 command '{cmd}' not found in entry point --help"
    # Verify old legacy commands still present
    for cmd in ("detect-slides", "roi-tool", "debug", "llm-process", "gui"):
        assert cmd in output, f"Legacy command '{cmd}' missing from entry point"
