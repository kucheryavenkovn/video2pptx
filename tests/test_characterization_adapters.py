# FILE: tests/test_characterization_adapters.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Characterize equivalent current behavior across direct application services and CLI.
#   SCOPE: Detect structural equivalence and Quick Preview side-effect invariants.
#   DEPENDS: pytest, Typer CliRunner, M-APP-SERVICE, M-CLI, M-MODELS
#   LINKS: V-REF-CHAR-TESTS, CHAR-001
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import math
from pathlib import Path

from typer.testing import CliRunner

from video2pptx.app_service import run_detect, run_preview
from video2pptx.cli import app
from video2pptx.config import load_config
from video2pptx.models import SlidesDocument


def _load_document(directory: Path) -> SlidesDocument:
    return SlidesDocument.model_validate_json(
        (directory / "slides.json").read_text(encoding="utf-8")
    )


def _normalized_detection(directory: Path) -> dict:
    document = _load_document(directory)
    return {
        "video": {
            "duration": round(document.video.duration, 3),
            "width": document.video.width,
            "height": document.video.height,
            "fps": round(document.video.fps, 3),
        },
        "slides": [
            {
                "index": slide.index,
                "start": round(slide.start, 3),
                "end": round(slide.end, 3),
                "representative_timestamp": round(
                    slide.representative_timestamp, 3
                ),
                "confidence": round(slide.confidence, 3),
                "manual": slide.manual,
                "image_name": Path(slide.image).name,
                "image_exists": (directory / slide.image).is_file(),
            }
            for slide in document.slides
        ],
        "score_count": len(document.score_values),
        "score_timestamp_count": len(document.score_timestamps),
    }


def test_detect_direct_service_matches_cli_detect_slides(
    tmp_path: Path,
    synthetic_video_path: Path,
):
    direct_dir = tmp_path / "direct"
    cli_dir = tmp_path / "cli"

    direct = run_detect(
        video_path=synthetic_video_path,
        out_dir=direct_dir,
        cfg=load_config(),
    )
    assert direct.success, direct.error

    cli = CliRunner().invoke(
        app,
        ["detect-slides", str(synthetic_video_path), "--out", str(cli_dir)],
    )
    assert cli.exit_code == 0, cli.output

    direct_state = _normalized_detection(direct_dir)
    cli_state = _normalized_detection(cli_dir)
    assert direct_state == cli_state
    assert direct_state["slides"]
    assert all(slide["image_exists"] for slide in direct_state["slides"])


def test_quick_preview_preserves_existing_slide_artifacts(
    tmp_path: Path,
    synthetic_video_path: Path,
):
    project_dir = tmp_path / "preview"
    project_dir.mkdir()
    sentinel = '{"sentinel": true}\n'
    slides_json = project_dir / "slides.json"
    slides_json.write_text(sentinel, encoding="utf-8")

    result = run_preview(
        video_path=synthetic_video_path,
        out_dir=project_dir,
        cfg=load_config(),
    )

    assert result.success, result.error
    timestamps = result.data["score_timestamps"]
    values = result.data["score_values"]
    assert len(timestamps) == len(values)
    assert timestamps == sorted(timestamps)
    assert all(math.isfinite(value) for value in values)
    assert slides_json.read_text(encoding="utf-8") == sentinel
    assert not (project_dir / "slides").exists()
    assert not (project_dir / "deck.md").exists()
    assert not (project_dir / "deck.pptx").exists()
