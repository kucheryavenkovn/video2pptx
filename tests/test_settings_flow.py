# FILE: tests/test_settings_flow.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Phase 20 correction — run_project_settings_flow workflow evidence
#   LINKS: V-M-ANALYSIS-QUALITY, Phase-20
#   ROLE: TEST
# END_MODULE_CONTRACT

from __future__ import annotations

from video2pptx.domain.pipeline_state import StageStatus
from video2pptx.domain.project import DetectionConfig, Project
from video2pptx.gui.settings_project import run_project_settings_flow


def _cfg(ams: int | None = 480) -> DetectionConfig:
    return DetectionConfig(
        sample_fps=2.0,
        decoder_backend="auto",
        slide_roi="auto",
        threshold="auto",
        min_slide_duration=2.0,
        min_stable_duration=2.0,
        dedupe_enabled=True,
        analysis_max_side=ams,
    )


def _succeed(p: Project, *stages: str) -> None:
    for s in stages:
        p.pipeline.start(s)
        p.pipeline.succeed(s)


class TestRunProjectSettingsFlow:
    def test_dialog_cancel_no_apply_no_save(self):
        p = Project.create_new(name="a")
        saves: list[bool] = []
        statuses: list[str] = []

        run_project_settings_flow(
            parent=None,  # type: ignore[arg-type]
            project=p,
            save_fn=lambda: saves.append(True) or True,
            status_fn=statuses.append,
            prompt_fn=lambda *a, **k: None,
        )
        assert saves == []
        assert p.detection.analysis_max_side == 480
        assert statuses == []

    def test_warning_cancel_no_apply(self):
        p = Project.create_new(name="b")
        _succeed(p, "detect", "align")
        saves: list[bool] = []
        new = _cfg(720)

        run_project_settings_flow(
            parent=None,  # type: ignore[arg-type]
            project=p,
            save_fn=lambda: saves.append(True) or True,
            status_fn=lambda m: None,
            prompt_fn=lambda *a, **k: new,
            confirm_fn=lambda title, text: False,
        )
        assert saves == []
        assert p.detection.analysis_max_side == 480
        assert p.pipeline.get("detect").status == StageStatus.SUCCEEDED
        assert p.pipeline.get("align").status == StageStatus.SUCCEEDED

    def test_warning_ok_apply_and_save_once(self):
        p = Project.create_new(name="c")
        stages = ("detect", "align", "notes", "llm", "markdown_export", "pptx_export", "auto")
        _succeed(p, *stages)
        saves: list[bool] = []
        statuses: list[str] = []
        new = _cfg(720)

        run_project_settings_flow(
            parent=None,  # type: ignore[arg-type]
            project=p,
            save_fn=lambda: saves.append(True) or True,
            status_fn=statuses.append,
            prompt_fn=lambda *a, **k: new,
            confirm_fn=lambda title, text: True,
        )
        assert saves == [True]
        assert statuses == ["Project settings updated"]
        assert p.detection.analysis_max_side == 720
        assert p.pipeline.get("detect").status == StageStatus.STALE
        for s in ("align", "notes", "llm", "markdown_export", "pptx_export", "auto"):
            assert p.pipeline.get(s).status == StageStatus.STALE

    def test_change_before_detect_no_warning(self):
        p = Project.create_new(name="d")
        confirms: list[bool] = []
        saves: list[bool] = []
        new = _cfg(720)

        run_project_settings_flow(
            parent=None,  # type: ignore[arg-type]
            project=p,
            save_fn=lambda: saves.append(True) or True,
            status_fn=lambda m: None,
            prompt_fn=lambda *a, **k: new,
            confirm_fn=lambda t, x: confirms.append(True) or True,
        )
        assert confirms == []
        assert saves == [True]
        assert p.detection.analysis_max_side == 720

    def test_noop_no_save(self):
        p = Project.create_new(name="e")
        _succeed(p, "detect", "align")
        saves: list[bool] = []
        statuses: list[str] = []
        same = _cfg(480)

        run_project_settings_flow(
            parent=None,  # type: ignore[arg-type]
            project=p,
            save_fn=lambda: saves.append(True) or True,
            status_fn=statuses.append,
            prompt_fn=lambda *a, **k: same,
            confirm_fn=lambda t, x: True,
        )
        assert saves == []
        assert statuses == ["Project settings unchanged"]
        assert p.pipeline.get("detect").status == StageStatus.SUCCEEDED

    def test_save_failure_reloads_and_no_false_success(self):
        p = Project.create_new(name="f")
        p.detection.analysis_max_side = 480
        reloads: list[bool] = []
        statuses: list[str] = []
        new = _cfg(720)

        def _reload() -> bool:
            # Simulate disk still has 480
            p.detection.analysis_max_side = 480
            reloads.append(True)
            return True

        run_project_settings_flow(
            parent=None,  # type: ignore[arg-type]
            project=p,
            save_fn=lambda: False,
            status_fn=statuses.append,
            prompt_fn=lambda *a, **k: new,
            reload_fn=_reload,
        )
        assert reloads == [True]
        assert p.detection.analysis_max_side == 480
        assert statuses == ["Failed to save project settings"]
        assert "updated" not in " ".join(statuses).lower() or "Failed" in statuses[0]
