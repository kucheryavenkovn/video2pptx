# FILE: tests/application/test_common.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Verify common application DTOs, errors, cancellation, and service context.
#   SCOPE: ServiceResult, ProgressUpdate, CancellationError, CancellationToken, ServiceContext.
#   DEPENDS: pytest, video2pptx.application
#   LINKS: M-APP-COMMON, V-REF-APP-SERVICES
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add common application layer tests
# END_CHANGE_SUMMARY

from __future__ import annotations

import pytest

from video2pptx.application.base import ServiceContext
from video2pptx.application.cancellation import CancellationToken
from video2pptx.application.dto import ProgressUpdate, ServiceResult
from video2pptx.application.errors import (
    ApplicationError,
    CancellationError,
    StageFailureError,
)
from video2pptx.application.observer import NullProgressObserver


class TestServiceResult:
    def test_ok_factory(self):
        r = ServiceResult.ok("detect", data={"count": 3}, revision="rev-1")
        assert r.success is True
        assert r.stage == "detect"
        assert r.data == {"count": 3}
        assert r.revision == "rev-1"
        assert r.error is None

    def test_fail_factory(self):
        r = ServiceResult.fail("notes", "LLM unavailable")
        assert r.success is False
        assert r.stage == "notes"
        assert r.error == "LLM unavailable"
        assert r.revision is None

    def test_to_dict_round_trip(self):
        r = ServiceResult.ok(
            "align",
            data={"moved": 2},
            revision="rev-2",
            warnings=("stale",),
        )
        d = r.to_dict()
        assert d["success"] is True
        assert d["stage"] == "align"
        assert d["moved"] == 2
        assert d["revision"] == "rev-2"
        assert d["warnings"] == ["stale"]

    def test_frozen(self):
        r = ServiceResult.ok("detect")
        with pytest.raises(Exception):
            r.success = False  # type: ignore[misc]


class TestProgressUpdate:
    def test_valid(self):
        u = ProgressUpdate(percent=50, message="halfway")
        assert u.percent == 50
        assert u.message == "halfway"

    def test_negative_rejected(self):
        with pytest.raises(ValueError):
            ProgressUpdate(percent=-1)

    def test_over_100_rejected(self):
        with pytest.raises(ValueError):
            ProgressUpdate(percent=101)


class TestErrors:
    def test_cancellation_error_carries_stage(self):
        err = CancellationError(stage="detect")
        assert err.stage == "detect"
        assert isinstance(err, ApplicationError)

    def test_stage_failure_error_format(self):
        cause = RuntimeError("boom")
        err = StageFailureError("notes", "pipeline failed", cause=cause)
        assert err.stage == "notes"
        assert err.cause is cause
        assert "[notes]" in str(err)


class TestCancellationToken:
    def test_initial_state_not_cancelled(self):
        token = CancellationToken()
        assert token.is_cancelled is False

    def test_trigger_sets_flag(self):
        token = CancellationToken()
        token.trigger()
        assert token.is_cancelled is True

    def test_check_raises_after_trigger(self):
        token = CancellationToken()
        token.trigger()
        with pytest.raises(CancellationError, match="cancel"):
            token.check("detect")

    def test_check_passes_when_not_triggered(self):
        token = CancellationToken()
        token.check("detect")

    def test_reset_clears_flag(self):
        token = CancellationToken()
        token.trigger()
        token.reset()
        assert token.is_cancelled is False
        token.check("detect")


class TestServiceContext:
    def test_defaults_are_safe(self):
        ctx = ServiceContext()
        assert ctx.repository is None
        ctx.check_cancelled("detect")
        ctx.report_progress(50, "half")

    def test_check_cancelled_raises(self):
        token = CancellationToken()
        token.trigger()
        ctx = ServiceContext(cancellation=token)
        with pytest.raises(CancellationError):
            ctx.check_cancelled("align")

    def test_report_progress_calls_observer(self):
        updates: list[ProgressUpdate] = []

        class Collector:
            def on_progress(self, update: ProgressUpdate) -> None:
                updates.append(update)

        ctx = ServiceContext(observer=Collector())
        ctx.report_progress(25, "quarter")
        assert len(updates) == 1
        assert updates[0].percent == 25
        assert updates[0].message == "quarter"

    def test_null_observer_does_not_raise(self):
        ctx = ServiceContext(observer=NullProgressObserver())
        ctx.report_progress(100, "done")

    def test_repository_passed_through(self):
        class FakeRepo:
            pass

        repo = FakeRepo()
        ctx = ServiceContext(repository=repo)
        assert ctx.repository is repo
