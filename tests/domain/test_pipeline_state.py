# FILE: tests/domain/test_pipeline_state.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for PipelineState state machine, transitions, invalidation, and legacy adapter.
#   SCOPE: StageStatus transitions, downstream invalidation, retry, force, from/to legacy, round-trip.
#   DEPENDS: pytest, video2pptx.domain
#   LINKS: V-M-DOMAIN-STATE, M-DOMAIN-STATE
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import pytest

from video2pptx.domain import (
    IllegalStateTransition,
    PipelineState,
    StageStatus,
)


class TestPipelineTransitions:
    def test_initial_all_not_started(self):
        ps = PipelineState()
        for stage in ("preview", "detect", "align", "notes", "auto"):
            assert ps.status(stage) == StageStatus.NOT_STARTED

    def test_start_from_not_started(self):
        ps = PipelineState()
        ps.start("detect", operation_id="abc")
        assert ps.status("detect") == StageStatus.RUNNING
        assert ps.get("detect").operation_id == "abc"

    def test_succeed_from_running(self):
        ps = PipelineState()
        ps.start("detect")
        ps.succeed("detect")
        assert ps.status("detect") == StageStatus.SUCCEEDED

    def test_fail_from_running(self):
        ps = PipelineState()
        ps.start("detect")
        ps.fail("detect", error={"msg": "oops"})
        assert ps.status("detect") == StageStatus.FAILED
        assert ps.get("detect").error is not None

    def test_cancel_from_running(self):
        ps = PipelineState()
        ps.start("detect")
        ps.cancel("detect")
        assert ps.status("detect") == StageStatus.CANCELLED

    def test_skip_from_not_started(self):
        ps = PipelineState()
        ps.skip("align", reason="no subs")
        assert ps.status("align") == StageStatus.SKIPPED

    def test_retry_from_failed(self):
        ps = PipelineState()
        ps.start("detect")
        ps.fail("detect")
        ps.start("detect")
        assert ps.status("detect") == StageStatus.RUNNING

    def test_retry_from_stale(self):
        ps = PipelineState()
        ps.start("detect")
        ps.succeed("detect")
        ps.start("align")
        ps.succeed("align")
        ps.invalidate_from("detect")
        assert ps.status("align") == StageStatus.STALE
        ps.start("align")
        assert ps.status("align") == StageStatus.RUNNING

    def test_illegal_not_started_to_succeeded(self):
        ps = PipelineState()
        with pytest.raises(IllegalStateTransition):
            ps.succeed("detect")

    def test_succeeded_to_running_is_valid_for_rerun(self):
        ps = PipelineState()
        ps.start("detect")
        ps.succeed("detect")
        ps.start("detect")
        assert ps.status("detect") is StageStatus.RUNNING

    def test_illegal_failed_to_succeeded(self):
        ps = PipelineState()
        ps.start("detect")
        ps.fail("detect")
        with pytest.raises(IllegalStateTransition):
            ps.succeed("detect")


class TestDownstreamInvalidation:
    def test_detect_invalidates_align_notes_exports(self):
        ps = PipelineState()
        ps.start("detect")
        ps.succeed("detect")
        ps.start("align")
        ps.succeed("align")
        invalidated = ps.invalidate_from("detect")
        assert "align" in invalidated
        assert ps.status("align") == StageStatus.STALE

    def test_align_invalidates_notes_not_detect(self):
        ps = PipelineState()
        ps.start("detect")
        ps.succeed("detect")
        ps.start("align")
        ps.succeed("align")
        ps.start("notes")
        ps.succeed("notes")
        invalidated = ps.invalidate_from("align")
        assert "notes" in invalidated
        assert ps.status("detect") == StageStatus.SUCCEEDED

    def test_preview_does_not_invalidate(self):
        ps = PipelineState()
        ps.start("preview")
        ps.succeed("preview")
        ps.start("detect")
        ps.succeed("detect")
        invalidated = ps.invalidate_from("preview")
        assert invalidated == []
        assert ps.status("detect") == StageStatus.SUCCEEDED


class TestCanRun:
    def test_not_started_can_run(self):
        ps = PipelineState()
        assert ps.can_run("detect") is True

    def test_running_cannot_run(self):
        ps = PipelineState()
        ps.start("detect")
        assert ps.can_run("detect") is False

    def test_succeeded_cannot_run(self):
        ps = PipelineState()
        ps.start("detect")
        ps.succeed("detect")
        assert ps.can_run("detect") is False

    def test_failed_can_retry(self):
        ps = PipelineState()
        ps.start("detect")
        ps.fail("detect")
        assert ps.can_run("detect") is True


class TestLegacyAdapter:
    def test_from_legacy_all_false(self):
        ps = PipelineState.from_legacy_booleans()
        for stage in ("detect", "notes", "llm"):
            assert ps.status(stage) == StageStatus.NOT_STARTED

    def test_from_legacy_detect_done(self):
        ps = PipelineState.from_legacy_booleans(detect_done=True)
        assert ps.status("detect") == StageStatus.SUCCEEDED
        assert ps.status("notes") == StageStatus.NOT_STARTED

    def test_to_legacy_booleans(self):
        ps = PipelineState()
        ps.start("detect")
        ps.succeed("detect")
        flags = ps.to_legacy_booleans()
        assert flags["detect_done"] is True
        assert flags["notes_done"] is False

    def test_round_trip_legacy(self):
        ps = PipelineState.from_legacy_booleans(
            detect_done=True,
            align_done=True,
            notes_done=True,
            md_exported=True,
            pptx_exported=True,
        )
        flags = ps.to_legacy_booleans()
        assert flags["detect_done"] is True
        assert flags["align_done"] is True
        assert flags["notes_done"] is True
        assert flags["md_exported"] is True
        assert flags["pptx_exported"] is True


class TestSerialization:
    def test_round_trip(self):
        ps = PipelineState()
        ps.start("detect", operation_id="op123")
        ps.succeed("detect")
        ps.start("align")
        data = ps.to_dict()
        restored = PipelineState.from_dict(data)
        assert restored.status("detect") == StageStatus.SUCCEEDED
        assert restored.status("align") == StageStatus.RUNNING
