# FILE: tests/test_project_validator.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for ProjectValidator — schema, files, intervals, exports
#   SCOPE: validate_project() happy/failure paths
#   DEPENDS: pytest, video2pptx.validators.project_validator
#   LINKS: V-M-PROJECT-VALIDATOR
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import json
from pathlib import Path

from video2pptx.validators.project_validator import validate_project


def _write_project(tmp_path: Path, overrides: dict | None = None) -> Path:
    pj = {
        "version": "1.0",
        "name": "test",
        "video": str(tmp_path / "test.mp4"),
        "slides_json": "slides.json",
        "slides": [
            {"start": 0.0, "end": 10.0, "image": "slides/slide_001.png", "uid": "a"},
            {"start": 10.0, "end": 20.0, "image": "slides/slide_002.png", "uid": "b"},
        ],
        "state": {"detect_done": True},
    }
    if overrides:
        pj.update(overrides)
    (tmp_path / "project.json").write_text(json.dumps(pj, indent=2), encoding="utf-8")
    return tmp_path


class TestValidateProject:
    def test_missing_dir(self, tmp_path: Path):
        r = validate_project(tmp_path / "nonexistent")
        assert r.valid is False
        assert any("not found" in e for e in r.errors)

    def test_missing_project_json(self, tmp_path: Path):
        r = validate_project(tmp_path)
        assert r.valid is False
        assert any("project.json" in e for e in r.errors)

    def test_valid_project(self, tmp_path: Path):
        d = _write_project(tmp_path)
        # Create video and slides dir
        (tmp_path / "test.mp4").write_text("fake video")
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir(exist_ok=True)
        (slides_dir / "slide_001.png").write_text("img1")
        (slides_dir / "slide_002.png").write_text("img2")
        # Create slides.json
        (tmp_path / "slides.json").write_text(json.dumps({
            "video": {"duration": 20.0},
            "slides": [
                {"start": 0.0, "end": 10.0, "image": "slides/slide_001.png"},
                {"start": 10.0, "end": 20.0, "image": "slides/slide_002.png"},
            ],
        }), encoding="utf-8")

        r = validate_project(d)
        assert r.valid, f"Expected valid, got: {r.errors}"
        assert len(r.errors) == 0

    def test_slide_count_mismatch(self, tmp_path: Path):
        d = _write_project(tmp_path)
        (tmp_path / "test.mp4").write_text("fake video")
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir(exist_ok=True)
        # slides.json has 1 slide, project has 2
        (tmp_path / "slides.json").write_text(json.dumps({
            "video": {"duration": 20.0},
            "slides": [{"start": 0.0, "end": 20.0, "image": ""}],
        }), encoding="utf-8")

        r = validate_project(d)
        assert r.valid is False
        assert any("mismatch" in e for e in r.errors)

    def test_slide_interval_invariant(self, tmp_path: Path):
        d = _write_project(tmp_path)
        (tmp_path / "test.mp4").write_text("fake video")
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir(exist_ok=True)
        # Overlap intervals
        (tmp_path / "slides.json").write_text(json.dumps({
            "video": {"duration": 20.0},
            "slides": [
                {"start": 0.0, "end": 15.0, "image": ""},
                {"start": 10.0, "end": 20.0, "image": ""},
            ],
        }), encoding="utf-8")

        r = validate_project(d)
        assert r.valid is False
        assert any("Gap/overlap" in e for e in r.errors)

    def test_double_path_slides(self, tmp_path: Path):
        d = _write_project(tmp_path, {"slides": [
            {"start": 0.0, "end": 10.0, "image": "slides/slides/img.png"},
        ]})
        (tmp_path / "test.mp4").write_text("fake video")
        (tmp_path / "slides.json").write_text(json.dumps({
            "video": {"duration": 10.0},
            "slides": [{"start": 0.0, "end": 10.0, "image": "slides/slides/img.png"}],
        }), encoding="utf-8")

        r = validate_project(d)
        assert r.valid is False
        assert any("Double path" in e for e in r.errors)
