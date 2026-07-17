# FILE: tests/infra/test_mapper.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Verify side-effect-free canonical DTO and Project aggregate mapping.
#   SCOPE: Rehydration, complete pipeline, artifacts, extensions, slide extras, and runtime root.
#   DEPENDS: pytest, video2pptx.domain, video2pptx.infrastructure.persistence
#   LINKS: M-PERSIST-DTO, M-PERSIST-MIGRATIONS, V-M-REF-PERSISTENCE-STABILIZATION
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add canonical mapper round-trip and no-side-effect tests
# END_CHANGE_SUMMARY

from __future__ import annotations

from datetime import datetime, timezone

from video2pptx.domain.pipeline_state import PIPELINE_STAGES, StageStatus
from video2pptx.domain.project import Project
from video2pptx.infrastructure.persistence.dto import (
    ArtifactDocument,
    PipelineDocument,
    ProjectDocumentV2,
    ScoreDocument,
    SlideDocument,
    StageStateDocument,
)
from video2pptx.infrastructure.persistence.mapper import ProjectMapper


def _document() -> ProjectDocumentV2:
    statuses = list(StageStatus)
    now = datetime(2026, 7, 11, 14, 0, tzinfo=timezone.utc)
    return ProjectDocumentV2(
        revision="mapper-revision",
        name="Mapper project",
        video_path="D:/media/video.mp4",
        subtitle_path="D:/media/subtitles.srt",
        slides=[
            SlideDocument(
                uid="legacy-short-id",
                index=1,
                start=0.0,
                end=5.0,
                image="slides/slide_001.png",
                representative_timestamp=2.5,
                transcript="raw",
                notes="clean",
                extra={"source": "legacy"},
            )
        ],
        pipeline=PipelineDocument(
            stages={
                stage: StageStateDocument(
                    status=statuses[index % len(statuses)],
                    operation_id=f"op-{stage}",
                    started_at=now,
                    finished_at=now,
                    error={"message": stage} if stage == "notes" else None,
                )
                for index, stage in enumerate(PIPELINE_STAGES)
            }
        ),
        scores=ScoreDocument(timestamps=[0.0, 1.0], values=[0.2, 0.4]),
        artifacts=ArtifactDocument(items={"markdown": "deck.md"}),
        extensions={"legacy": {"backend": "auto"}},
    )


class TestCanonicalMapper:
    def test_rehydration_does_not_call_business_replacement(self, tmp_path, monkeypatch):
        def fail_if_called(*args, **kwargs):
            raise AssertionError("replace_detected_slides must not run during rehydration")

        monkeypatch.setattr(Project, "replace_detected_slides", fail_if_called)

        project = ProjectMapper.to_domain(_document(), tmp_path)

        assert project.slide_count == 1
        assert project.get_slide("legacy-short-id") is not None

    def test_round_trip_preserves_complete_pipeline_and_metadata(self, tmp_path):
        source = _document()

        project = ProjectMapper.to_domain(source, tmp_path)
        restored = ProjectMapper.to_document(project, source.revision)

        assert restored == source
        for stage in PIPELINE_STAGES:
            assert restored.pipeline.stages[stage] == source.pipeline.stages[stage]
        assert restored.pipeline.stages["notes"].error == {"message": "notes"}

    def test_project_root_is_runtime_context_not_canonical_data(self, tmp_path):
        project = ProjectMapper.to_domain(_document(), tmp_path)
        restored = ProjectMapper.to_document(project, "new-revision")

        assert project.output_dir == str(tmp_path)
        assert "output_dir" not in restored.model_dump()
        assert restored.revision == "new-revision"

    def test_artifacts_extensions_scores_and_slide_extra_survive(self, tmp_path):
        project = ProjectMapper.to_domain(_document(), tmp_path)

        assert project.artifacts["markdown"].as_posix() == "deck.md"
        assert project.extensions == {"legacy": {"backend": "auto"}}
        assert project.score_timestamps == [0.0, 1.0]
        assert project.score_values == [0.2, 0.4]
        assert dict(project.slides[0].extra) == {"source": "legacy"}

        restored = ProjectMapper.to_document(project, "revision-2")
        assert restored.slides[0].extra == {"source": "legacy"}
