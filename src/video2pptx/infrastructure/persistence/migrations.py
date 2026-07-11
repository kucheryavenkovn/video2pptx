# FILE: src/video2pptx/infrastructure/persistence/migrations.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Deterministically migrate legacy schema 1.0 project data to ProjectDocumentV2.
#   SCOPE: Legacy pipeline flags, slides, portable artifacts, revision, and extension preservation.
#   DEPENDS: json, uuid, video2pptx.domain, video2pptx.infrastructure.persistence.dto
#   LINKS: M-PERSIST-MIGRATIONS, M-PERSIST-DTO, V-PERSIST-MIGRATIONS
#   ROLE: DATA_LAYER
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   migrate_v1_to_v2 - convert one legacy project mapping into a strict canonical V2 document
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add deterministic schema 1.0 to 2.0 migration
# END_CHANGE_SUMMARY

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from video2pptx.domain.artifacts import ArtifactRef, migrate_legacy_artifact
from video2pptx.domain.errors import ValidationError as DomainValidationError
from video2pptx.domain.pipeline_state import PIPELINE_STAGES, StageStatus
from video2pptx.infrastructure.persistence.dto import (
    ArtifactDocument,
    PipelineDocument,
    ProjectDocumentV2,
    ScoreDocument,
    SlideDocument,
    StageStateDocument,
)

_MIGRATION_NAMESPACE = uuid.UUID("299b7514-229b-4c55-a684-38023c68ce8b")
_CONSUMED_PROJECT_FIELDS = {
    "schema_version",
    "revision",
    "version",
    "name",
    "video",
    "subtitles",
    "state",
    "slides",
    "slides_json",
    "score_timestamps",
    "score_values",
    "output_dir",
}
_CONSUMED_SLIDE_FIELDS = {
    "uid",
    "id",
    "index",
    "start",
    "end",
    "duration",
    "image",
    "representative_timestamp",
    "transcript",
    "notes",
    "llm_description",
    "confidence",
    "manual",
}


def _stable_hex(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return uuid.uuid5(_MIGRATION_NAMESPACE, payload).hex


def _portable_artifact(raw: Any, project_root: Path) -> str | None:
    if not raw or not str(raw).strip():
        return None
    text = str(raw)
    try:
        return ArtifactRef.parse(text).as_posix()
    except DomainValidationError:
        return migrate_legacy_artifact(text, project_root).as_posix()


def _migrate_pipeline(data: dict[str, Any]) -> PipelineDocument:
    state = data.get("state") or {}
    completed = {
        "preview": bool(state.get("preview_done", False)),
        "detect": bool(state.get("detect_done", False)),
        "align": bool(state.get("align_done", False)),
        "notes": bool(state.get("notes_done", False)),
        "llm": bool(state.get("llm_done", False)),
        "markdown_export": bool(state.get("md_exported", False)),
        "pptx_export": bool(state.get("pptx_exported", False)),
        "auto": bool(state.get("auto_done", False)),
    }
    return PipelineDocument(
        stages={
            stage: StageStateDocument(
                status=StageStatus.SUCCEEDED if completed[stage] else StageStatus.NOT_STARTED
            )
            for stage in PIPELINE_STAGES
        }
    )


def _migrate_slides(data: dict[str, Any], project_root: Path) -> list[SlideDocument]:
    raw_slides = sorted(
        (dict(slide) for slide in data.get("slides") or []),
        key=lambda slide: (float(slide.get("start", 0.0)), float(slide.get("end", 0.0))),
    )
    migrated: list[SlideDocument] = []
    for index, raw in enumerate(raw_slides, start=1):
        start = float(raw.get("start", 0.0))
        end = float(raw.get("end", start + 1.0))
        representative = float(raw.get("representative_timestamp", (start + end) / 2))
        if not start <= representative <= end:
            representative = (start + end) / 2
        uid = str(raw.get("uid") or raw.get("id") or "").strip()
        if not uid:
            uid = _stable_hex({"slide": raw, "position": index})
        migrated.append(
            SlideDocument(
                uid=uid,
                index=index,
                start=start,
                end=end,
                image=_portable_artifact(raw.get("image"), project_root),
                representative_timestamp=representative,
                transcript=str(raw.get("transcript", "")),
                notes=str(raw.get("notes", "")),
                llm_description=raw.get("llm_description"),
                confidence=float(raw.get("confidence", 1.0)),
                manual=bool(raw.get("manual", False)),
                extra={key: value for key, value in raw.items() if key not in _CONSUMED_SLIDE_FIELDS},
            )
        )
    return migrated


# START_CONTRACT: migrate_v1_to_v2
#   PURPOSE: Deterministically convert one legacy schema 1.0 mapping to ProjectDocumentV2.
#   INPUTS: { data: dict[str, Any] - legacy project fields, project_root: str|Path - runtime project location }
#   OUTPUTS: { ProjectDocumentV2 - strict canonical schema 2.0 document }
#   SIDE_EFFECTS: none
#   LINKS: M-PERSIST-MIGRATIONS, M-PERSIST-DTO
# END_CONTRACT: migrate_v1_to_v2
def migrate_v1_to_v2(
    data: dict[str, Any],
    project_root: str | Path,
) -> ProjectDocumentV2:
    """Migrate legacy data without retaining non-portable output_dir."""
    root = Path(project_root)
    slides = _migrate_slides(data, root)
    score_timestamps = [float(value) for value in data.get("score_timestamps") or []]
    score_values = [float(value) for value in data.get("score_values") or []]

    artifact_items: dict[str, str] = {}
    slides_json = _portable_artifact(data.get("slides_json"), root)
    if slides_json is not None:
        artifact_items["slides"] = slides_json

    legacy_extensions = {
        key: value
        for key, value in data.items()
        if key not in _CONSUMED_PROJECT_FIELDS
    }
    revision = str(data.get("revision") or "").strip() or _stable_hex(data)
    name = str(data.get("name") or "Untitled").strip() or "Untitled"

    return ProjectDocumentV2(
        revision=revision,
        name=name,
        video_path=str(data.get("video") or ""),
        subtitle_path=(str(data["subtitles"]) if data.get("subtitles") else None),
        slides=slides,
        pipeline=_migrate_pipeline(data),
        scores=ScoreDocument(timestamps=score_timestamps, values=score_values),
        artifacts=ArtifactDocument(items=artifact_items),
        extensions={"legacy": legacy_extensions} if legacy_extensions else {},
    )
