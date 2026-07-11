# FILE: src/video2pptx/application/services/notes_service.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Canonical basic/LLM notes use case preserving raw cues and forbidding silent LLM fallback.
#   SCOPE: NotesService.execute
#   DEPENDS: video2pptx.application.base, video2pptx.application.dto, video2pptx.application.errors,
#            video2pptx.application.ports.notes_processor, video2pptx.domain
#   LINKS: M-APP-NOTES, V-APP-NOTES, V-REF-APP-SERVICES
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   NotesService - loads project, computes notes, updates transcripts, saves with revision
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add revision-safe notes service
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

from loguru import logger

from video2pptx.application.base import ServiceContext
from video2pptx.application.dto import ServiceResult
from video2pptx.application.errors import StageFailureError
from video2pptx.application.ports.notes_processor import NotesProcessorPort


class NotesService:
    """Canonical notes use case — enrich transcripts and save with revision."""

    def __init__(
        self,
        processor: NotesProcessorPort,
        context: ServiceContext,
    ) -> None:
        self._processor = processor
        self._ctx = context

    def execute(
        self,
        project_location: Path,
        *,
        subtitles_path: str = "",
        mode: str = "basic",
    ) -> ServiceResult:
        repo = self._ctx.repository
        if repo is None:
            return ServiceResult.fail("notes", "Repository not configured")

        try:
            loaded = repo.load(Path(project_location))
            self._ctx.check_cancelled("notes")

            project = loaded.project
            subs = subtitles_path or project.subtitle_path
            if not subs:
                return ServiceResult.fail(
                    "notes",
                    "Subtitles required for notes processing",
                )

            project.pipeline.start("notes")
            self._ctx.report_progress(20, "Processing notes")

            slides_data = project.to_slides_dict()
            output = self._processor.process(
                slides_data,
                subs,
                mode=mode,
            )
            self._ctx.check_cancelled("notes")
            self._ctx.report_progress(70, "Notes computed")

            for slide in project._slides:
                uid = str(slide.slide_id)
                if uid in output.notes_by_uid:
                    slide.notes = output.notes_by_uid[uid]
                if uid in output.llm_descriptions_by_uid:
                    slide.llm_description = output.llm_descriptions_by_uid[uid]

            project.pipeline.succeed("notes")

            save_result = repo.save(
                project,
                loaded.location,
                expected_revision=loaded.revision,
            )
            self._ctx.report_progress(100, "Notes saved")

            logger.info(
                f"[NotesService] Notes done | mode={mode} slides={project.slide_count} "
                f"revision={save_result.revision}"
            )

            return ServiceResult.ok(
                "notes",
                data={
                    "mode": mode,
                    "slides_count": project.slide_count,
                    "raw_cues_preserved": output.raw_cues_preserved,
                },
                revision=save_result.revision,
                warnings=tuple(save_result.warnings),
            )
        except Exception as exc:
            logger.error(f"[NotesService] Failed | error={exc}")
            raise StageFailureError("notes", str(exc), cause=exc) from exc
