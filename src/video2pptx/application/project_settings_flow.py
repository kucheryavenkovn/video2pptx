# FILE: src/video2pptx/application/project_settings_flow.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Qt-free project settings apply/rollback workflow (Phase 20 + Phase 21 Wave 4)
#   SCOPE: run_project_settings_flow, snapshots, confirm helpers — no PySide6 imports
#   DEPENDS: video2pptx.domain, video2pptx.analysis_quality
#   LINKS: M-ANALYSIS-QUALITY, Phase-20, Phase-21
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   SettingsApplyResult - optional result dataclass for callers
#   should_confirm_analysis_quality_change - re-detect confirm gate
#   snapshot_detection_config - deep-ish DetectionConfig copy
#   restore_detection_and_pipeline - local rollback helper
#   run_project_settings_flow - dialog-agnostic apply/save/rollback workflow
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Extracted from gui/settings_project.py for pure tests on Python 3.14
# END_CHANGE_SUMMARY

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from video2pptx.analysis_quality import ANALYSIS_QUALITY_CHANGE_WARNING
from video2pptx.domain.pipeline_state import PipelineState, StageStatus
from video2pptx.domain.project import DetectionConfig


@dataclass(frozen=True, slots=True)
class SettingsApplyResult:
    """Outcome of run_project_settings_flow for optional structured callers."""

    applied: bool
    saved: bool
    message: str = ""


def should_confirm_analysis_quality_change(
    old: DetectionConfig,
    new: DetectionConfig,
    detect_succeeded: bool,
) -> bool:
    """True when user must confirm re-detect due to analysis_max_side change after detect."""
    return detect_succeeded and old.analysis_max_side != new.analysis_max_side


def snapshot_detection_config(cfg: DetectionConfig) -> DetectionConfig:
    """Deep-ish copy of DetectionConfig for local rollback."""
    return DetectionConfig(
        sample_fps=cfg.sample_fps,
        decoder_backend=cfg.decoder_backend,
        slide_roi=cfg.slide_roi,
        ignore_rois=list(cfg.ignore_rois),
        threshold=cfg.threshold,
        min_slide_duration=cfg.min_slide_duration,
        min_stable_duration=cfg.min_stable_duration,
        dedupe_enabled=cfg.dedupe_enabled,
        analysis_max_side=cfg.analysis_max_side,
    )


def restore_detection_and_pipeline(
    project: object,
    old_detection: DetectionConfig,
    old_pipeline_dict: dict,
) -> None:
    """Restore detection config and pipeline from snapshots (mutable refs replaced)."""
    project.detection = snapshot_detection_config(old_detection)
    project.pipeline = PipelineState.from_dict(old_pipeline_dict)


def run_project_settings_flow(
    parent: object | None,
    project: object,
    save_fn: Callable[[], bool],
    status_fn: Callable[[str], None],
    frame_grabber: Callable[[], object] | None = None,
    reload_fn: Callable[[], bool] | None = None,
    confirm_fn: Callable[[str, str], bool] | None = None,
    prompt_fn: Callable[..., DetectionConfig | None] | None = None,
) -> SettingsApplyResult:
    """Full Project Settings workflow without Qt imports.

    *project* is domain Project (duck-typed: .detection, .pipeline, .apply_detection_config).
    *save_fn* must return True only when persistence succeeded.
    On save failure: try *reload_fn*; if missing/failed restore local snapshot.

    *prompt_fn* is required for headless/unit use. GUI adapter supplies a Qt dialog
    prompt when calling from settings_project.
    """
    if prompt_fn is None:
        raise ValueError(
            "prompt_fn is required in Qt-free project_settings_flow; "
            "GUI callers should inject prompt_detection_settings via the Qt adapter"
        )

    new_config = prompt_fn(parent, project.detection, frame_grabber)
    if new_config is None:
        return SettingsApplyResult(applied=False, saved=False, message="")

    detect_ok = project.pipeline.get("detect").status == StageStatus.SUCCEEDED
    if should_confirm_analysis_quality_change(project.detection, new_config, detect_ok):
        # GUI adapter always injects confirm_fn (QMessageBox). Pure tests may omit it
        # to mean "caller already accepted the change" (prompt-only harness).
        if confirm_fn is not None and not confirm_fn(
            "Качество анализа", ANALYSIS_QUALITY_CHANGE_WARNING
        ):
            return SettingsApplyResult(applied=False, saved=False, message="cancelled")

    old_detection = snapshot_detection_config(project.detection)
    old_pipeline_dict = project.pipeline.to_dict()

    if not project.apply_detection_config(new_config):
        status_fn("Project settings unchanged")
        return SettingsApplyResult(applied=False, saved=False, message="Project settings unchanged")
    if save_fn():
        status_fn("Project settings updated")
        return SettingsApplyResult(applied=True, saved=True, message="Project settings updated")

    # Save failed — restore disk or local snapshot (never leave memory/disk divergence).
    reloaded = False
    if reload_fn is not None:
        reloaded = bool(reload_fn())
    if reloaded:
        status_fn("Failed to save project settings; persisted state restored")
        return SettingsApplyResult(
            applied=True,
            saved=False,
            message="Failed to save project settings; persisted state restored",
        )
    restore_detection_and_pipeline(project, old_detection, old_pipeline_dict)
    status_fn("Failed to save project settings; local changes rolled back")
    return SettingsApplyResult(
        applied=False,
        saved=False,
        message="Failed to save project settings; local changes rolled back",
    )
