# FILE: tests/test_cli_adapter_commands.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Module-local tests for CLI adapter Typer commands.
#   SCOPE: Command registration, argument parsing, missing-project handling, exit codes
#   DEPENDS: video2pptx.adapters.cli.app, typer.testing
#   LINKS: M-CLI-ADAPTER, V-REF-CLI-ADAPTER
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   TestCommandRegistration - all 8 commands registered with correct names
#   TestCommandArguments - PROJECT_DIR positional, flags exist
#   TestMissingProject - error handling for non-existent project directory
# END_MODULE_MAP

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from video2pptx.adapters.cli.app import app
from video2pptx.adapters.cli.exit_codes import CliExitCode

runner = CliRunner()

EXPECTED_COMMANDS = (
    "preview",
    "detect",
    "align",
    "notes",
    "export-md",
    "export-pptx",
    "validate",
    "auto",
)

# Commands that accept PROJECT_DIR as first positional argument
PROJECT_DIR_COMMANDS = (
    "preview",
    "detect",
    "align",
    "notes",
    "export-md",
    "export-pptx",
    "validate",
    "auto",
)

# Common flags expected on pipeline commands
COMMON_FLAGS = (
    "debug",
    "json",
)


class TestCommandRegistration:
    def test_root_help_lists_all_commands(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for cmd in EXPECTED_COMMANDS:
            assert cmd in result.stdout

    @pytest.mark.parametrize("command", EXPECTED_COMMANDS)
    def test_command_help_succeeds(self, command: str) -> None:
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0, f"{command} --help failed: {result.output}"

    @pytest.mark.parametrize("command", PROJECT_DIR_COMMANDS)
    def test_command_accepts_project_dir(self, command: str) -> None:
        result = runner.invoke(app, [command, "--help"])
        assert "PROJECT_DIR" in result.stdout or "project" in result.stdout.lower()

    def test_no_command_invokes_callback(self) -> None:
        result = runner.invoke(app, [])
        assert result.exit_code == 0


class TestMissingProject:
    """Commands called with a non-existent project dir should fail gracefully."""

    @pytest.mark.parametrize(
        ("command", "args"),
        [
            ("preview", []),
            ("detect", []),
            ("align", []),
            ("notes", []),
            ("export-md", []),
            ("export-pptx", []),
            ("validate", []),
            ("auto", []),
        ],
    )
    def test_missing_project_dir_returns_nonzero(self, command, args) -> None:
        result = runner.invoke(app, [command, "/tmp/nonexistent_project_xyz", *args])
        # Should exit with non-zero code (project not found)
        assert result.exit_code != 0
        # Should not crash with traceback
        assert "Traceback" not in result.output

    def test_unknown_command_usage_error(self) -> None:
        result = runner.invoke(app, ["nonexistent-command"])
        assert result.exit_code == 2

    def test_detect_without_project_dir_usage_error(self) -> None:
        result = runner.invoke(app, ["detect"])
        assert result.exit_code == 2


class TestExitCodes:
    @pytest.mark.parametrize(
        ("command", "expected_code"),
        [
            ("preview", CliExitCode.PRECONDITION_ERROR),
            ("detect", CliExitCode.PRECONDITION_ERROR),
            ("align", CliExitCode.PRECONDITION_ERROR),
        ],
    )
    def test_missing_project_precondition_error(self, command, expected_code) -> None:
        result = runner.invoke(app, [command, "/tmp/missing_dir_12345"])
        assert result.exit_code == expected_code.value, (
            f"Expected {expected_code.value} ({expected_code.name}), "
            f"got {result.exit_code} for {command}: {result.output[:200]}"
        )

    def test_auto_missing_project_returns_general_error(self) -> None:
        result = runner.invoke(app, ["auto", "/tmp/missing_dir_12345"])
        assert result.exit_code == CliExitCode.GENERAL_APPLICATION_ERROR.value
