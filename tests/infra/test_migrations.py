# FILE: tests/infra/test_migrations.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Verify deterministic and loss-aware schema 1.0 to 2.0 migration.
#   SCOPE: Stable IDs, pipeline flags, portable artifacts, extensions, and legacy field preservation.
#   DEPENDS: pytest, video2pptx.infrastructure.persistence.migrations
#   LINKS: M-PERSIST-MIGRATIONS, V-PERSIST-MIGRATIONS
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add schema 1.0 to 2.0 migration tests
# END_CHANGE_SUMMARY

from __future__ import annotations

from video2pptx.domain.pipeline_state import StageStatus
from video2pptx.infrastructure.persistence.migrations import migrate_v1_to_v2


def _legacy(project_root) -> dict:
    return {
        "version": "1.0",
        "name": "Legacy lecture",
        "video": "D:/media/lecture.mp4",
        "subtitles": "D:/media/lecture.srt",
        "output_dir": str(project_root),
        "video_config": {"sample_fps": 2.0},
        "detection": {"threshold": 0.2},
        "llm": {"model": "local"},
        "markers": [{"original_ts": 4.0, "snapped_ts": 4.2}],
        "backend": "auto",
        "state": {
            "preview_done": True,
            "detect_done": True,
            "align_done": False,
            "notes_done": True,
            "llm_done": False,
            "md_exported": True,
            "pptx_exported": False,
            "auto_done": False,
        },
        "slides_json": "slides.json",
        "slides": [
            {
                "index": 9,
                "start": 0.0,
                "end": 5.0,
                "representative_timestamp": 2.5,
                "image": "slides/slide_001.png",
                "transcript": "raw",
                "custom_slide_field": "preserve-me",
            },
            {
                "uid": "existing-legacy-id",
                "index": 4,
                "start": 5.0,
                "end": 10.0,
                "representative_timestamp": 7.5,
            },
        ],
        "score_timestamps": [0, 1],
        "score_values": [0.1, 0.2],
    }


class TestMigrationIdentity:
    def test_missing_ids_are_deterministic_and_existing_ids_are_preserved(self, tmp_path):
        first = migrate_v1_to_v2(_legacy(tmp_path), tmp_path)
        second = migrate_v1_to_v2(_legacy(tmp_path), tmp_path)

        assert first.slides[0].uid == second.slides[0].uid
        assert len(first.slides[0].uid) == 32
        assert first.slides[1].uid == "existing-legacy-id"
        assert [slide.index for slide in first.slides] == [1, 2]
        assert first.revision == second.revision

    def test_slide_extension_fields_are_preserved(self, tmp_path):
        document = migrate_v1_to_v2(_legacy(tmp_path), tmp_path)

        assert document.slides[0].extra == {"custom_slide_field": "preserve-me"}


class TestMigrationContent:
    def test_pipeline_flags_map_without_inferred_transitions(self, tmp_path):
        document = migrate_v1_to_v2(_legacy(tmp_path), tmp_path)

        assert document.pipeline.stages["preview"].status is StageStatus.SUCCEEDED
        assert document.pipeline.stages["detect"].status is StageStatus.SUCCEEDED
        assert document.pipeline.stages["align"].status is StageStatus.NOT_STARTED
        assert document.pipeline.stages["notes"].status is StageStatus.SUCCEEDED
        assert document.pipeline.stages["markdown_export"].status is StageStatus.SUCCEEDED
        assert document.pipeline.stages["pptx_export"].status is StageStatus.NOT_STARTED

    def test_unknown_project_fields_are_preserved_under_legacy_extensions(self, tmp_path):
        document = migrate_v1_to_v2(_legacy(tmp_path), tmp_path)
        legacy = document.extensions["legacy"]

        assert legacy["video_config"] == {"sample_fps": 2.0}
        assert legacy["detection"] == {"threshold": 0.2}
        assert legacy["llm"] == {"model": "local"}
        assert legacy["markers"][0]["snapped_ts"] == 4.2
        assert legacy["backend"] == "auto"
        assert "output_dir" not in legacy
        assert "output_dir" not in document.model_dump()

    def test_relative_artifacts_and_scores_are_normalized(self, tmp_path):
        document = migrate_v1_to_v2(_legacy(tmp_path), tmp_path)

        assert document.artifacts.items == {"slides": "slides.json"}
        assert document.slides[0].image == "slides/slide_001.png"
        assert document.scores.timestamps == [0.0, 1.0]
        assert document.scores.values == [0.1, 0.2]

    def test_absolute_slide_image_inside_root_becomes_relative(self, tmp_path):
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir()
        image = slides_dir / "slide_001.png"
        image.write_bytes(b"image")
        legacy = _legacy(tmp_path)
        legacy["slides"][0]["image"] = str(image)

        document = migrate_v1_to_v2(legacy, tmp_path)

        assert document.slides[0].image == "slides/slide_001.png"
