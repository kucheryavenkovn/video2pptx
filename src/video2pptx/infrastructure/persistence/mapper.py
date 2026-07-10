# FILE: src/video2pptx/infrastructure/persistence/mapper.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Map between legacy Pydantic Project/SlideSegment and domain Project/Slide.
#   SCOPE: ProjectMapper with to_domain, to_legacy_project, to_legacy_slides_document
#   DEPENDS: video2pptx.domain, video2pptx.models, video2pptx.project_manager
#   LINKS: M-PORT-REPO
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ProjectMapper - bidirectional mapper between legacy Pydantic models and domain aggregate
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Initial mapper with legacy UID migration and pipeline state bridge
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path
from typing import Any

from video2pptx.domain.artifacts import ArtifactRef, migrate_legacy_artifact
from video2pptx.domain.identifiers import SlideId
from video2pptx.domain.pipeline_state import PipelineState
from video2pptx.domain.project import Project
from video2pptx.domain.slide import Slide
from video2pptx.domain.time import TimeInterval


class ProjectMapper:
    """Bidirectional mapper between legacy persistence models and domain aggregate."""

    @staticmethod
    def to_domain(
        legacy_project: Any,
        project_root: str | Path,
    ) -> Project:
        """Convert a legacy Pydantic Project to a domain Project aggregate.

        Assigns UIDs to slides that lack them.
        Migrates artifact paths to ArtifactRef.
        Maps legacy boolean pipeline flags to PipelineState.
        """
        root = Path(project_root)
        project = Project(
            name=getattr(legacy_project, "name", "Untitled"),
            video_path=getattr(legacy_project, "video", ""),
            subtitle_path=getattr(legacy_project, "subtitles", ""),
            output_dir=getattr(legacy_project, "output_dir", str(root)),
        )

        state = getattr(legacy_project, "state", None)
        if state is not None:
            project.pipeline = PipelineState.from_legacy_booleans(
                preview_done=getattr(state, "preview_done", False),
                detect_done=getattr(state, "detect_done", False),
                align_done=getattr(state, "align_done", False),
                notes_done=getattr(state, "notes_done", False),
                llm_done=getattr(state, "llm_done", False),
                md_exported=getattr(state, "md_exported", False),
                pptx_exported=getattr(state, "pptx_exported", False),
                auto_done=getattr(state, "auto_done", False),
            )

        project.score_timestamps = list(getattr(legacy_project, "score_timestamps", []))
        project.score_values = list(getattr(legacy_project, "score_values", []))

        legacy_slides = getattr(legacy_project, "slides", [])
        domain_slides: list[Slide] = []
        for legacy_slide in legacy_slides:
            uid_value = getattr(legacy_slide, "uid", "") or ""
            if not uid_value.strip():
                uid_value = SlideId.new().value
            start = float(getattr(legacy_slide, "start", 0.0))
            end = float(getattr(legacy_slide, "end", start + 1.0))
            interval = TimeInterval(start, end)
            rep_ts = float(getattr(legacy_slide, "representative_timestamp", 0.0))
            if not start <= rep_ts <= end:
                rep_ts = (start + end) / 2

            image_raw = getattr(legacy_slide, "image", "") or ""
            image: ArtifactRef | None = None
            if image_raw:
                try:
                    image = ArtifactRef.parse(image_raw)
                except Exception:
                    try:
                        image = migrate_legacy_artifact(image_raw, root)
                    except Exception:
                        image = None

            domain_slides.append(
                Slide(
                    slide_id=SlideId.parse(uid_value),
                    interval=interval,
                    index=int(getattr(legacy_slide, "index", 0)),
                    image=image,
                    representative_timestamp=rep_ts,
                    transcript=getattr(legacy_slide, "transcript", ""),
                    notes="",
                    llm_description=getattr(legacy_slide, "llm_description", None),
                    confidence=float(getattr(legacy_slide, "confidence", 1.0)),
                    manual=bool(getattr(legacy_slide, "manual", False)),
                )
            )

        if domain_slides:
            project.replace_detected_slides(domain_slides)

        return project

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
