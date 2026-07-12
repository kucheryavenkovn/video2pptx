# FILE: tests/test_cli_characterization.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Freeze the public pre-Step-7 CLI surface and explicit semantic migration boundary.
#   SCOPE: Command names, positional arguments, options, usage codes, and missing-file behavior.
#   DEPENDS: typer.testing, video2pptx.cli
#   LINKS: M-CLI-ADAPTER, V-REF-CLI-ADAPTER
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
from typer.testing import CliRunner

from video2pptx.cli import app

runner = CliRunner()

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
)


def test_root_help_freezes_public_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in EXPECTED_COMMANDS:
        assert command in result.stdout


@pytest.mark.parametrize(("arguments", "tokens"), HELP_CASES)
def test_command_help_freezes_arguments_and_options(arguments, tokens) -> None:
    result = runner.invoke(app, arguments)
    assert result.exit_code == 0, result.output
    for token in tokens:
        assert token in result.stdout


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
    legacy_help = runner.invoke(app, ["detect", "--help"])
    assert "VIDEO" in legacy_help.stdout
    assert "--export-md" in legacy_help.stdout
    assert "--llm" in legacy_help.stdout
