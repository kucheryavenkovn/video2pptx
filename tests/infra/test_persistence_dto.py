# FILE: tests/infra/test_persistence_dto.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Verify strict schema 2.0 canonical persistence DTO behavior.
#   SCOPE: Full pipeline round-trip, canonical field rejection, portable artifacts, slide and score invariants.
#   DEPENDS: pytest, pydantic, video2pptx.infrastructure.persistence.dto
#   LINKS: M-PERSIST-DTO, V-PERSIST-DTO, V-REF-PERSISTENCE-STABILIZATION
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add schema 2.0 DTO contract tests
# END_CHANGE_SUMMARY

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from video2pptx.domain.pipeline_state import PIPELINE_STAGES, StageStatus
from video2pptx.infrastructure.persistence.dto import (
    ArtifactDocument,
    PipelineDocument,
    ProjectDocumentV2,
    ScoreDocument,
    SlideDocument,
    StageStateDocument,
)


def _pipeline() -> PipelineDocument:
    statuses = (
        StageStatus.NOT_STARTED,
        StageStatus.RUNNING,
        StageStatus.SUCCEEDED,
        StageStatus.FAILED,
        StageStatus.CANCELLED,
        StageStatus.STALE,
        StageStatus.SKIPPED,
        StageStatus.SUCCEEDED,
    )
    now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
    return PipelineDocument(
        stages={
            stage: StageStateDocument(
                status=status,
                operation_id=f"op-{stage}",
                started_at=now,
                finished_at=now,
                error={"type": "example", "stage": stage} if status is StageStatus.FAILED else None,
            )
            for stage, status in zip(PIPELINE_STAGES, statuses, strict=True)
        }
    )


def _document() -> ProjectDocumentV2:
    return ProjectDocumentV2(
        revision="revision-1",
        name="DTO project",
        video_path="D:/media/lecture.mp4",
        subtitle_path="D:/media/lecture.srt",
        slides=[
            SlideDocument(
                uid="legacy-uid-12",
                index=1,
                start=0.0,
                end=5.0,
                image="slides/slide_001.png",
                representative_timestamp=2.5,
                transcript="raw",
                notes="clean",
                confidence=0.9,
            )
        ],
        pipeline=_pipeline(),
        scores=ScoreDocument(timestamps=[0.0, 1.0], values=[0.1, 0.2]),
        artifacts=ArtifactDocument(items={"markdown": "deck.md", "pptx": "deck.pptx"}),
        extensions={"legacy": {"backend": "auto"}},
    )


class TestProjectDocumentV2:
    def test_json_round_trip_preserves_complete_pipeline(self):
        document = _document()

        restored = ProjectDocumentV2.model_validate_json(document.model_dump_json())

        assert restored == document
        assert restored.pipeline.stages["notes"].status is StageStatus.FAILED
        assert restored.pipeline.stages["notes"].operation_id == "op-notes"
        assert restored.pipeline.stages["notes"].error == {
            "type": "example",
            "stage": "notes",
        }
        assert restored.pipeline.stages["llm"].status is StageStatus.CANCELLED
        assert restored.pipeline.stages["markdown_export"].status is StageStatus.STALE
        assert restored.pipeline.stages["pptx_export"].status is StageStatus.SKIPPED

    def test_output_dir_is_rejected_as_unknown_canonical_field(self):
        data = _document().model_dump()
        data["output_dir"] = "D:/non-portable/project"

        with pytest.raises(ValidationError, match="output_dir"):
            ProjectDocumentV2.model_validate(data)

    def test_unknown_field_must_be_inside_extensions(self):
        data = _document().model_dump()
        data["backend"] = "auto"

        with pytest.raises(ValidationError, match="backend"):
            ProjectDocumentV2.model_validate(data)

    def test_legacy_slide_id_is_preserved(self):
        restored = ProjectDocumentV2.model_validate_json(_document().model_dump_json())

        assert restored.slides[0].uid == "legacy-uid-12"

    def test_duplicate_slide_ids_rejected(self):
        data = _document().model_dump()
        duplicate = dict(data["slides"][0])
        duplicate["index"] = 2
        duplicate["start"] = 5.0
        duplicate["end"] = 10.0
        duplicate["representative_timestamp"] = 7.5
        data["slides"].append(duplicate)

        with pytest.raises(ValidationError, match="UIDs must be unique"):
            ProjectDocumentV2.model_validate(data)


class TestNestedDocuments:
    def test_pipeline_requires_all_canonical_stages(self):
        stages = _pipeline().stages
        stages.pop("auto")

        with pytest.raises(ValidationError, match="missing=.*auto"):
            PipelineDocument(stages=stages)

    def test_absolute_generated_artifact_rejected(self):
        with pytest.raises(ValidationError, match="absolute"):
            ArtifactDocument(items={"markdown": "D:/project/deck.md"})

    def test_score_arrays_must_have_equal_lengths(self):
        with pytest.raises(ValidationError, match="equal lengths"):
            ScoreDocument(timestamps=[0.0], values=[])

    def test_slide_interval_and_representative_timestamp_validated(self):
        with pytest.raises(ValidationError, match="greater than start"):
            SlideDocument(
                uid="s1",
                index=1,
                start=5.0,
                end=5.0,
                representative_timestamp=5.0,
            )
