# FILE: src/video2pptx/infrastructure/persistence/mapper.py
# VERSION: 2.3.0
# START_MODULE_CONTRACT
#   PURPOSE: Map strict ProjectDocumentV2 to and from the domain Project without business side effects.
#   SCOPE: ProjectMapper with to_domain, to_document, and derived slides export
#   DEPENDS: video2pptx.domain, persistence.dto
#   LINKS: M-PERSIST-DTO, M-PERSIST-MIGRATIONS, M-FILE-REPO
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ProjectMapper - side-effect-free mapper between canonical DTO and domain aggregate
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v2.3.0 - Emit legacy-valid sentinel video dimensions in derived slides documents
#   v2.2.0 - Stamp derived slides documents with canonical source revision
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

    # START_CONTRACT: to_slides_document
    #   PURPOSE: Generate revision-linked slides.json compatibility data from canonical aggregate state.
    #   INPUTS: { project: Project, source_revision: str }
    #   OUTPUTS: { dict[str, Any] - derived compatibility document }
    #   SIDE_EFFECTS: none
    #   LINKS: M-FILE-REPO
    # END_CONTRACT: to_slides_document
    @staticmethod
    def to_slides_document(
        project: Project,
        source_revision: str,
    ) -> dict[str, Any]:
        """Export slides as a slides.json-compatible dict for derived artifact generation."""
        slides_data = project.to_slides_dict()
        return {
            "schema_version": "1.0",
            "source_revision": source_revision,
            "video": {
                "path": project.video_path,
                "duration": 0,
                "fps": 0,
                "width": 1,
                "height": 1,
            },
            "slides": slides_data,
            "score_timestamps": list(project.score_timestamps),
            "score_values": list(project.score_values),
        }
