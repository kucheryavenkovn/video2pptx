from __future__ import annotations

import hashlib
import json
from pathlib import Path

from video2pptx.config import AppConfig
from video2pptx.detect_slides import run_detect_slides

FIXTURES = Path(__file__).parent / "fixtures"
TEST_VIDEO = FIXTURES / "test_slides.mp4"
REFERENCE = (
    Path(__file__).resolve().parent.parent
    / "benchmarks"
    / "detect"
    / "reference"
    / "pre-twopass-3472e62.json"
)

_TOLERANCE = 1e-4


def test_reference_artifact_exists():
    assert REFERENCE.is_file(), f"Reference artifact not found: {REFERENCE}"


def test_two_pass_matches_pre_twopass(tmp_path):
    ref = json.loads(REFERENCE.read_text(encoding="utf-8"))

    cfg = AppConfig()
    cfg.video.sample_fps = ref["config"]["sample_fps"]
    cfg.detection.threshold = ref["config"]["threshold"]
    cfg.detection.min_slide_duration = ref["config"]["min_slide_duration"]
    cfg.detection.min_stable_duration = ref["config"]["min_stable_duration"]
    cfg.detection.dedupe_enabled = ref["config"]["dedupe_enabled"]
    cfg.detection.slide_roi = ref["config"]["slide_roi"]

    doc = run_detect_slides(video_path=TEST_VIDEO, out_dir=tmp_path, cfg=cfg)

    assert len(doc.score_timestamps) == len(ref["score_timestamps"])
    for i, (a, b) in enumerate(zip(doc.score_timestamps, ref["score_timestamps"], strict=True)):
        assert abs(a - b) < _TOLERANCE, f"score_timestamps[{i}]: {a} vs {b}"

    assert len(doc.score_values) == len(ref["score_values"])
    for i, (a, b) in enumerate(zip(doc.score_values, ref["score_values"], strict=True)):
        assert abs(a - b) < _TOLERANCE, f"score_values[{i}]: {a} vs {b}"

    assert len(doc.slides) == len(ref["segments"])
    for i, (seg, ref_seg) in enumerate(zip(doc.slides, ref["segments"], strict=True)):
        assert seg.index == ref_seg["index"]
        assert abs(seg.start - ref_seg["start"]) < _TOLERANCE
        assert abs(seg.end - ref_seg["end"]) < _TOLERANCE
        assert abs(seg.representative_timestamp - ref_seg["representative_timestamp"]) < _TOLERANCE

    slides_dir = tmp_path / "slides"
    png_files = sorted(slides_dir.glob("*.png")) if slides_dir.is_dir() else []
    assert len(png_files) == len(ref["screenshots"])

    for png, ref_ss in zip(png_files, ref["screenshots"], strict=True):
        png_sha = hashlib.sha256(png.read_bytes()).hexdigest()
        assert png_sha == ref_ss["sha256"], (
            f"Screenshot SHA-256 mismatch: {png.name} "
            f"got {png_sha} expected {ref_ss['sha256']}"
        )
