# FILE: tests/test_cli_adapter_core.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Module-local tests for CLI adapter infra (exit_codes, errors, observer, context, renderer).
#   SCOPE: CliExitCode values, error classification, render_cli_error output, RichOperationObserver
#          deterministic output, CliContext cancellation, render_service_result JSON/human modes.
#   DEPENDS: video2pptx.adapters.cli, video2pptx.application.errors, video2pptx.domain.errors,
#            video2pptx.infrastructure.persistence.errors, rich.console, pytest
#   LINKS: M-CLI-ADAPTER, V-REF-CLI-ADAPTER
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ExitCodeTests - exact numeric values and misspell-test
#   ErrorClassificationTests - each error type maps to correct code + label
#   RenderCliErrorTests - human readable output, debug traceback, known hints
#   ObserverTests - no ANSI in record mode, format smoke
#   ContextTests - cancellation triggers
#   RenderServiceResultTests - human and JSON formatting
# END_MODULE_MAP

from __future__ import annotations

import json

import pytest
from rich.console import Console

from video2pptx.adapters.cli import (
    CliContext,
    CliExitCode,
    RichOperationObserver,
    render_cli_error,
    render_service_result,
)
from video2pptx.adapters.cli import errors as cli_errors
from video2pptx.application.dto import ServiceResult
from video2pptx.application.errors import CancellationError, StageFailureError
from video2pptx.domain.errors import (
    DuplicateSlideId,
    ValidationError,
)
from video2pptx.infrastructure.persistence.errors import (
    ProjectAlreadyExists,
    ProjectAtomicWriteError,
    ProjectDocumentCorrupted,
    ProjectNotFound,
    ProjectRevisionConflict,
)

# =========================================================================
# ExitCodeTests
# =========================================================================


class TestExitCodeValues:
    def test_success_is_zero(self) -> None:
        assert CliExitCode.SUCCESS == 0

    def test_general_application_error_is_one(self) -> None:
        assert CliExitCode.GENERAL_APPLICATION_ERROR == 1

    def test_cli_usage_error_is_two(self) -> None:
        assert CliExitCode.CLI_USAGE_ERROR == 2

    def test_precondition_error_is_three(self) -> None:
        assert CliExitCode.PRECONDITION_ERROR == 3

    def test_validation_error_is_four(self) -> None:
        assert CliExitCode.VALIDATION_ERROR == 4

    def test_persistence_conflict_is_five(self) -> None:
        assert CliExitCode.PERSISTENCE_CONFLICT == 5

    def test_external_adapter_error_is_six(self) -> None:
        assert CliExitCode.EXTERNAL_ADAPTER_ERROR == 6

    def test_cancelled_is_seven(self) -> None:
        assert CliExitCode.CANCELLED == 7

    def test_no_unknown_codes_beyond_seven(self) -> None:
        known = len(CliExitCode)
        assert known == 8, f"Expected 8 codes, got {known}"


# =========================================================================
# ErrorClassificationTests
# =========================================================================


class TestClassifyError:
    def test_cancellation_error(self) -> None:
        code, label = cli_errors.classify_error(CancellationError(stage="test"))
        assert code == CliExitCode.CANCELLED
        assert label == "CANCELLED"

    def test_keyboard_interrupt(self) -> None:
        code, label = cli_errors.classify_error(KeyboardInterrupt())
        assert code == CliExitCode.CANCELLED
        assert label == "CANCELLED"

    def test_revision_conflict(self) -> None:
        code, label = cli_errors.classify_error(ProjectRevisionConflict("conflict"))
        assert code == CliExitCode.PERSISTENCE_CONFLICT
        assert label == "PERSISTENCE_CONFLICT"

    def test_project_already_exists(self) -> None:
        code, label = cli_errors.classify_error(ProjectAlreadyExists("exists"))
        assert code == CliExitCode.PRECONDITION_ERROR
        assert label == "PRECONDITION_ERROR"

    def test_project_not_found(self) -> None:
        code, label = cli_errors.classify_error(ProjectNotFound("missing"))
        assert code == CliExitCode.PRECONDITION_ERROR
        assert label == "PRECONDITION_ERROR"

    def test_project_document_corrupted(self) -> None:
        code, label = cli_errors.classify_error(ProjectDocumentCorrupted("corrupt"))
        assert code == CliExitCode.PRECONDITION_ERROR

    def test_project_atomic_write_error(self) -> None:
        code, label = cli_errors.classify_error(ProjectAtomicWriteError("io"))
        assert code == CliExitCode.EXTERNAL_ADAPTER_ERROR
        assert label == "EXTERNAL_ADAPTER_ERROR"

    def test_stage_failure(self) -> None:
        code, label = cli_errors.classify_error(StageFailureError("detect", "failed"))
        assert code == CliExitCode.GENERAL_APPLICATION_ERROR
        assert label == "STAGE_FAILURE"

    def test_validation_error_domain(self) -> None:
        code, label = cli_errors.classify_error(ValidationError("bad value"))
        assert code == CliExitCode.VALIDATION_ERROR
        assert label == "VALIDATION_ERROR"

    def test_generic_domain_error(self) -> None:
        code, label = cli_errors.classify_error(DuplicateSlideId("dup"))
        assert code == CliExitCode.VALIDATION_ERROR
        assert label == "DOMAIN_ERROR"

    def test_value_error(self) -> None:
        code, label = cli_errors.classify_error(ValueError("bad arg"))
        assert code == CliExitCode.CLI_USAGE_ERROR
        assert label == "CLI_USAGE_ERROR"

    def test_file_not_found(self) -> None:
        code, label = cli_errors.classify_error(FileNotFoundError("missing"))
        assert code == CliExitCode.CLI_USAGE_ERROR
        assert label == "CLI_USAGE_ERROR"

    def test_unexpected_exception(self) -> None:
        code, label = cli_errors.classify_error(RuntimeError("unexpected"))
        assert code == CliExitCode.GENERAL_APPLICATION_ERROR
        assert label == "UNEXPECTED"


# =========================================================================
# RenderCliErrorTests
# =========================================================================


def _make_console() -> Console:
    return Console(record=True, force_terminal=False, width=120)


class TestRenderCliError:
    def test_simple_error_output(self) -> None:
        console = _make_console()
        code = render_cli_error(ValueError("bad"), console)
        assert code == CliExitCode.CLI_USAGE_ERROR
        output = console.export_text()
        assert "Error" in output
        assert "bad" in output

    def test_cancellation_output(self) -> None:
        console = _make_console()
        code = render_cli_error(CancellationError(stage="detect"), console)
        assert code == CliExitCode.CANCELLED
        output = console.export_text()
        assert "Error" in output
        assert "cancelled" in output.lower()

    def test_project_not_found_hint(self) -> None:
        console = _make_console()
        err = ProjectNotFound("project not found", path="/tmp/missing")
        code = render_cli_error(err, console)
        assert code == CliExitCode.PRECONDITION_ERROR
        output = console.export_text()
        assert "project create" in output.lower()

    def test_revision_conflict_hint(self) -> None:
        console = _make_console()
        err = ProjectRevisionConflict("conflict")
        code = render_cli_error(err, console)
        assert code == CliExitCode.PERSISTENCE_CONFLICT
        output = console.export_text()
        assert "modified elsewhere" in output.lower()

    def test_debug_traceback(self) -> None:
        console = _make_console()
        try:
            raise ValueError("deep")
        except ValueError as exc:
            code = render_cli_error(exc, console, debug=True)
        assert code == CliExitCode.CLI_USAGE_ERROR
        output = console.export_text()
        assert "Traceback" in output

    def test_project_stage_prefix(self) -> None:
        console = _make_console()
        err = StageFailureError("detect", "no frames")
        code = render_cli_error(err, console, project="myproject", stage="detect")
        assert code == CliExitCode.GENERAL_APPLICATION_ERROR
        output = console.export_text()
        assert "myproject" in output
        assert "detect" in output

    def test_keyboard_interrupt(self) -> None:
        console = _make_console()
        code = render_cli_error(KeyboardInterrupt(), console)
        assert code == CliExitCode.CANCELLED


# =========================================================================
# ObserverTests
# =========================================================================


class TestRichOperationObserver:
    def test_no_ansi_in_record_mode(self) -> None:
        console = Console(record=True, force_terminal=False, width=120)
        observer = RichOperationObserver(console, stage="detect")
        from video2pptx.application.dto import ProgressUpdate

        observer.on_progress(ProgressUpdate(percent=50, message="Processing"))
        output = console.export_text()
        assert "[" in output
        # No ANSI escape sequences
        assert "\x1b[" not in output

    def test_format_smoke(self) -> None:
        console = Console(record=True, force_terminal=False, width=120)
        observer = RichOperationObserver(console, stage="detect")
        from video2pptx.application.dto import ProgressUpdate

        observer.on_progress(ProgressUpdate(percent=10, message="Starting"))
        observer.on_progress(ProgressUpdate(percent=100, message="Done"))
        output = console.export_text()
        assert "[detect]" in output
        assert "10%" in output
        assert "Starting" in output
        assert "100%" in output
        assert "Done" in output

    def test_empty_stage_uses_message_prefix(self) -> None:
        console = Console(record=True, force_terminal=False, width=120)
        observer = RichOperationObserver(console)
        from video2pptx.application.dto import ProgressUpdate

        observer.on_progress(ProgressUpdate(percent=0, message="preview starting"))
        output = console.export_text()
        assert "0%" in output

    def test_stage_property(self) -> None:
        observer = RichOperationObserver(Console(), stage="align")
        assert observer.stage == "align"


# =========================================================================
# ContextTests
# =========================================================================


class TestCliContext:
    def test_cancellation_not_triggered_by_default(self) -> None:
        ctx = CliContext()
        assert not ctx.cancellation.is_cancelled

    def test_handle_interrupt_triggers_cancellation(self) -> None:
        ctx = CliContext()
        ctx.handle_interrupt()
        assert ctx.cancellation.is_cancelled

    def test_cancellation_check_raises_after_interrupt(self) -> None:
        ctx = CliContext()
        from video2pptx.application.errors import CancellationError

        ctx.handle_interrupt()
        with pytest.raises(CancellationError):
            ctx.cancellation.check("test")

    def test_default_debug_and_json(self) -> None:
        ctx = CliContext()
        assert not ctx.debug
        assert not ctx.json_output

    def test_services_none_by_default(self) -> None:
        ctx = CliContext()
        assert ctx.services is None


# =========================================================================
# RenderServiceResultTests
# =========================================================================


class TestRenderServiceResult:
    def test_success_human(self) -> None:
        console = Console(record=True, force_terminal=False, width=120)
        result = ServiceResult.ok("detect", data={"slides_count": 5, "video_duration": 120.0})
        render_service_result(result, console)
        output = console.export_text()
        assert "SUCCESS" in output
        assert "detect" in output
        assert "slides_count: 5" in output

    def test_success_with_revision(self) -> None:
        console = Console(record=True, force_terminal=False, width=120)
        result = ServiceResult.ok("detect", revision="abc123")
        render_service_result(result, console)
        output = console.export_text()
        assert "revision: abc123" in output

    def test_success_with_warnings(self) -> None:
        console = Console(record=True, force_terminal=False, width=120)
        result = ServiceResult.ok("detect", warnings=("low fps",))
        render_service_result(result, console)
        output = console.export_text()
        assert "warning: low fps" in output.lower()

    def test_failure_human(self) -> None:
        console = Console(record=True, force_terminal=False, width=120)
        result = ServiceResult.fail("detect", "Video file not found")
        render_service_result(result, console)
        output = console.export_text()
        assert "FAILED" in output
        assert "Video file not found" in output

    def test_json_output(self) -> None:
        console = Console(record=True, force_terminal=False, width=120)
        result = ServiceResult.ok("detect", data={"slides_count": 3})
        render_service_result(result, console, json_output=True)
        output = console.export_text()
        parsed = json.loads(output)
        assert parsed["success"] is True
        assert parsed["stage"] == "detect"
        assert parsed["slides_count"] == 3

    def test_json_failure(self) -> None:
        console = Console(record=True, force_terminal=False, width=120)
        result = ServiceResult.fail("detect", "bad file")
        render_service_result(result, console, json_output=True)
        output = console.export_text()
        parsed = json.loads(output)
        assert parsed["success"] is False
        assert parsed["error"] == "bad file"
