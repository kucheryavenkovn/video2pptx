# FILE: src/video2pptx/infrastructure/persistence/mapper.py
# VERSION: 2.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Map strict ProjectDocumentV2 to and from the domain Project without business side effects.
#   SCOPE: ProjectMapper with to_domain, to_document, transitional legacy bridge, and derived slides export
#   DEPENDS: video2pptx.domain, persistence.dto, persistence.migrations, legacy models during transition
#   LINKS: M-PERSIST-DTO, M-PERSIST-MIGRATIONS, M-FILE-REPO
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ProjectMapper - side-effect-free mapper between canonical DTO and domain aggregate
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v2.0.0 - Map canonical V2 DTO without lifecycle transitions; retain transitional legacy bridge
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path
from typing import Any

from video2pptx.domain.artifacts import ArtifactRef
from video2pptx.domain.pipeline_state import PIPELINE_STAGES, PipelineState
from video2pptx.domain.project import Project
from video2pptx.infrastructure.persistence.dto import (
    ArtifactDocument,
    PipelineDocument,
    ProjectDocumentV2,
    ScoreDocument,
    SlideDocument,
    StageStateDocument,
)
from video2pptx.infrastructure.persistence.migrations import migrate_v1_to_v2


class ProjectMapper:
    """Side-effect-free mapping between canonical persistence and domain state."""

    # START_CONTRACT: to_domain
    #   PURPOSE: Rehydrate Project from ProjectDocumentV2 without business transitions or invalidation.
    #   INPUTS: { document: ProjectDocumentV2, project_root: str|Path }
    #   OUTPUTS: { Project - complete aggregate state with runtime output_dir }
    #   SIDE_EFFECTS: none
    #   LINKS: M-PERSIST-DTO, M-DOMAIN-PROJECT
    # END_CONTRACT: to_domain
    @staticmethod
    def to_domain(
        document: ProjectDocumentV2,
        project_root: str | Path,
    ) -> Project:
        """Rehydrate an aggregate without invoking business mutation methods."""
        root = Path(project_root)
        slide_data = [
            {
                "uid": slide.uid,
                "index": slide.index,
                "start": slide.start,
                "end": slide.end,
                "image": slide.image or "",
                "representative_timestamp": slide.representative_timestamp,
                "transcript": slide.transcript,
                "notes": slide.notes,
                "llm_description": slide.llm_description,
                "confidence": slide.confidence,
                "manual": slide.manual,
                **slide.extra,
            }
            for slide in document.slides
        ]
        project = Project.from_slides_dict(
            slide_data,
            name=document.name,
            video_path=document.video_path,
            subtitle_path=document.subtitle_path or "",
            output_dir=str(root),
        )
        project.pipeline = PipelineState.from_dict(
            {
                stage: document.pipeline.stages[stage].model_dump(mode="json")
                for stage in PIPELINE_STAGES
            }
        )
        project.score_timestamps = list(document.scores.timestamps)
        project.score_values = list(document.scores.values)
        project.artifacts = {
            name: ArtifactRef.parse(path)
            for name, path in document.artifacts.items.items()
        }
        project.extensions = dict(document.extensions)
        return project

    # START_CONTRACT: to_document
    #   PURPOSE: Project complete aggregate state into strict ProjectDocumentV2.
    #   INPUTS: { project: Project, revision: str }
    #   OUTPUTS: { ProjectDocumentV2 }
    #   SIDE_EFFECTS: none
    #   LINKS: M-PERSIST-DTO, M-DOMAIN-PROJECT
    # END_CONTRACT: to_document
    @staticmethod
    def to_document(
        project: Project,
        revision: str,
    ) -> ProjectDocumentV2:
        """Project the complete aggregate state into a strict canonical document."""
        slides = [
            SlideDocument(
                uid=view.slide_id.value,
                index=view.index,
                start=view.interval.start,
                end=view.interval.end,
                image=str(view.image) if view.image else None,
                representative_timestamp=view.representative_timestamp,
                transcript=view.transcript,
                notes=view.notes,
                llm_description=view.llm_description,
                confidence=view.confidence,
                manual=view.manual,
                extra=dict(view.extra),
            )
            for view in project.slides
        ]
        pipeline = PipelineDocument(
            stages={
                stage: StageStateDocument(
                    status=project.pipeline.get(stage).status,
                    operation_id=project.pipeline.get(stage).operation_id,
                    started_at=project.pipeline.get(stage).started_at,
                    finished_at=project.pipeline.get(stage).finished_at,
                    error=project.pipeline.get(stage).error,
                )
                for stage in PIPELINE_STAGES
            }
        )
        return ProjectDocumentV2(
            revision=revision,
            name=project.name,
            video_path=project.video_path,
            subtitle_path=project.subtitle_path or None,
            slides=slides,
            pipeline=pipeline,
            scores=ScoreDocument(
                timestamps=list(project.score_timestamps),
                values=list(project.score_values),
            ),
            artifacts=ArtifactDocument(
                items={name: ref.as_posix() for name, ref in project.artifacts.items()}
            ),
            extensions=dict(project.extensions),
        )

    # START_CONTRACT: from_legacy_project
    #   PURPOSE: Bridge legacy Pydantic project data through deterministic V2 migration.
    #   INPUTS: { legacy_project: Any, project_root: str|Path }
    #   OUTPUTS: { Project - rehydrated aggregate }
    #   SIDE_EFFECTS: none
    #   LINKS: M-PERSIST-MIGRATIONS, M-FILE-REPO
    # END_CONTRACT: from_legacy_project
    @staticmethod
    def from_legacy_project(
        legacy_project: Any,
        project_root: str | Path,
    ) -> Project:
        """Transitional bridge used by FileProjectRepository until Checkpoint 5.0C."""
        if hasattr(legacy_project, "model_dump"):
            data = legacy_project.model_dump(mode="json")
        else:
            data = dict(legacy_project)
        document = migrate_v1_to_v2(data, project_root)
        return ProjectMapper.to_domain(document, project_root)

    @staticmethod
    def to_legacy_project(
        project: Project,
        legacy_project: Any | None = None,
    ) -> Any:
        """Update or create a legacy Pydantic Project from the domain aggregate.

        Preserves fields the domain doesn't model yet (detection config, etc).
        """
        from video2pptx.project_manager import Project as LegacyProject
        from video2pptx.project_manager import ProjectState

        if legacy_project is not None:
            lp = legacy_project
        else:
            lp = LegacyProject(
                name=project.name,
                video=project.video_path,
                subtitles=project.subtitle_path,
                output_dir=project.output_dir,
            )

        lp.name = project.name
        lp.video = project.video_path
        lp.subtitles = project.subtitle_path
        lp.score_timestamps = list(project.score_timestamps)
        lp.score_values = list(project.score_values)

        legacy_flags = project.pipeline.to_legacy_booleans()
        if lp.state is None:
            lp.state = ProjectState()
        lp.state.preview_done = legacy_flags["preview_done"]
        lp.state.detect_done = legacy_flags["detect_done"]
        lp.state.align_done = legacy_flags["align_done"]
        lp.state.notes_done = legacy_flags["notes_done"]
        lp.state.llm_done = legacy_flags["llm_done"]
        lp.state.md_exported = legacy_flags["md_exported"]
        lp.state.pptx_exported = legacy_flags["pptx_exported"]
        lp.state.auto_done = legacy_flags["auto_done"]

        from video2pptx.models import SlideSegment

        lp.slides = [
            SlideSegment(
                uid=view.slide_id.value,
                index=view.index,
                start=view.interval.start,
                end=view.interval.end,
                duration=view.interval.duration,
                image=str(view.image) if view.image else "",
                representative_timestamp=view.representative_timestamp,
                transcript=view.transcript,
                llm_description=view.llm_description,
                confidence=view.confidence,
                manual=view.manual,
            )
            for view in project.slides
        ]

        return lp

    @staticmethod
    def to_slides_document(project: Project) -> dict[str, Any]:
        """Export slides as a slides.json-compatible dict for derived artifact generation."""
        slides_data = project.to_slides_dict()
        return {
            "schema_version": "1.0",
            "video": {
                "path": project.video_path,
                "duration": 0,
                "fps": 0,
                "width": 0,
                "height": 0,
            },
            "slides": slides_data,
            "score_timestamps": list(project.score_timestamps),
            "score_values": list(project.score_values),
        }
