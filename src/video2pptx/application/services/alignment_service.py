# FILE: src/video2pptx/application/services/alignment_service.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Canonical dry-run/apply alignment use case using full-plan validation and atomic aggregate application.
#   SCOPE: AlignmentService.execute
#   DEPENDS: video2pptx.application.base, video2pptx.application.dto, video2pptx.application.errors,
#            video2pptx.application.ports.alignment, video2pptx.domain
#   LINKS: M-APP-ALIGN, V-APP-ALIGN, V-REF-APP-SERVICES
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   AlignmentService - loads project, computes plan, optionally applies, saves with revision
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add revision-safe alignment service with dry-run support
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

from loguru import logger

from video2pptx.application.base import ServiceContext
from video2pptx.application.dto import ServiceResult
from video2pptx.application.errors import StageFailureError
from video2pptx.application.ports.alignment import AlignmentPort
from video2pptx.domain.time import TimeInterval


class AlignmentService:
    """Canonical alignment use case — dry-run or apply with revision-safe persistence."""

    def __init__(
        self,
        aligner: AlignmentPort,
        context: ServiceContext,
    ) -> None:
        self._aligner = aligner
        self._ctx = context

    def execute(
        self,
        project_location: Path,
        subtitles_path: str,
        *,
        dry_run: bool = False,
        max_shift_sec: float = 3.0,
        include_manual: bool = False,
    ) -> ServiceResult:
        repo = self._ctx.repository
        if repo is None:
            return ServiceResult.fail("align", "Repository not configured")

        try:
            loaded = repo.load(Path(project_location))
            self._ctx.check_cancelled("align")

            project = loaded.project
            if not project.subtitle_path and not subtitles_path:
                return ServiceResult.fail(
                    "align",
                    "Subtitles required for alignment",
                )

            intervals = [
                (view.interval.start, view.interval.end)
                for view in project.slides
            ]
            video_duration = max(
                (view.interval.end for view in project.slides),
                default=0.0,
            )

            self._ctx.report_progress(20, "Computing alignment plan")
            plan = self._aligner.compute_plan(
                intervals,
                subtitles_path or project.subtitle_path or "",
                max_shift_sec=max_shift_sec,
                include_manual=include_manual,
                video_duration=video_duration,
            )
            self._ctx.check_cancelled("align")

            if dry_run:
                self._ctx.report_progress(100, "Dry-run complete")
                return ServiceResult.ok(
                    "align",
                    data={
                        "dry_run": True,
                        "boundaries_total": plan.boundaries_total,
                        "boundaries_moved": plan.boundaries_moved,
                        "avg_shift": plan.avg_shift,
                        "max_shift": plan.max_shift,
                        "report": plan.report,
                    },
                )

            project.pipeline.start("align")
            self._ctx.report_progress(60, "Applying alignment")

            for slide_view, (new_start, new_end) in zip(
                project.slides,
                plan.aligned_intervals,
                strict=False,
            ):
                slide = project._require_slide(slide_view.slide_id)
                slide.interval = TimeInterval(new_start, new_end)
                if not new_start <= slide.representative_timestamp <= new_end:
                    slide.representative_timestamp = (new_start + new_end) / 2

            project._reindex()
            project.pipeline.succeed("align")

            save_result = repo.save(
                project,
                loaded.location,
                expected_revision=loaded.revision,
            )
            self._ctx.report_progress(100, "Alignment saved")

            logger.info(
                f"[AlignmentService] Alignment done | moved={plan.boundaries_moved} "
                f"dry_run={dry_run} revision={save_result.revision}"
            )

            return ServiceResult.ok(
                "align",
                data={
                    "dry_run": False,
                    "boundaries_total": plan.boundaries_total,
                    "boundaries_moved": plan.boundaries_moved,
                    "avg_shift": plan.avg_shift,
                    "max_shift": plan.max_shift,
                    "report": plan.report,
                },
                revision=save_result.revision,
                warnings=tuple(save_result.warnings),
            )
        except Exception as exc:
            logger.error(f"[AlignmentService] Failed | error={exc}")
            raise StageFailureError("align", str(exc), cause=exc) from exc
