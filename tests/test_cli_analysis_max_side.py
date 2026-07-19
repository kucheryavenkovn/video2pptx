# FILE: tests/test_cli_analysis_max_side.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Canonical CLI --analysis-max-side for detect/auto (Phase 20 correction)
#   LINKS: V-M-ANALYSIS-QUALITY, M-CLI-ADAPTER
#   ROLE: TEST
# END_MODULE_CONTRACT

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from video2pptx.adapters.cli.app import build_app
from video2pptx.analysis_quality import UNSET
from video2pptx.application.dto import ServiceResult
from video2pptx.domain.project import Project
from video2pptx.infrastructure.persistence.file_project_repository import FileProjectRepository

runner = CliRunner()


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    loc = tmp_path / "p"
    p = Project.create_new(name="p", output_dir=str(loc))
    p.detection.analysis_max_side = 480
    p.video_path = str(tmp_path / "v.mp4")
    (tmp_path / "v.mp4").write_bytes(b"x")
    FileProjectRepository().create(loc, p)
    return loc


def _patch_detect_capture():
    captured: dict = {}

    def _exec(self, project_location, video_path=None, **kwargs):
        captured["kwargs"] = kwargs
        captured["analysis_max_side"] = kwargs.get("analysis_max_side", "MISSING")
        return ServiceResult.ok("detect", data={"slides_count": 0})

    return captured, _exec


class TestCanonicalDetectCli:
    def test_omitted_uses_unset(self, project_dir: Path):
        captured, _exec = _patch_detect_capture()
        app = build_app()
        with patch(
            "video2pptx.application.services.detection_service.DetectionService.execute",
            _exec,
        ):
            result = runner.invoke(app, ["detect", str(project_dir)])
        assert result.exit_code == 0, result.output
        assert captured["analysis_max_side"] is UNSET or isinstance(
            captured["analysis_max_side"], type(UNSET)
        )

    def test_native_explicit_none(self, project_dir: Path):
        captured, _exec = _patch_detect_capture()
        app = build_app()
        with patch(
            "video2pptx.application.services.detection_service.DetectionService.execute",
            _exec,
        ):
            result = runner.invoke(
                app, ["detect", str(project_dir), "--analysis-max-side", "native"]
            )
        assert result.exit_code == 0, result.output
        assert captured["analysis_max_side"] is None

    def test_numeric_override(self, project_dir: Path):
        captured, _exec = _patch_detect_capture()
        app = build_app()
        with patch(
            "video2pptx.application.services.detection_service.DetectionService.execute",
            _exec,
        ):
            result = runner.invoke(
                app, ["detect", str(project_dir), "--analysis-max-side", "720"]
            )
        assert result.exit_code == 0, result.output
        assert captured["analysis_max_side"] == 720

    def test_custom_512(self, project_dir: Path):
        captured, _exec = _patch_detect_capture()
        app = build_app()
        with patch(
            "video2pptx.application.services.detection_service.DetectionService.execute",
            _exec,
        ):
            result = runner.invoke(
                app, ["detect", str(project_dir), "--analysis-max-side", "512"]
            )
        assert result.exit_code == 0, result.output
        assert captured["analysis_max_side"] == 512

    @pytest.mark.parametrize("bad", ["239", "2161", "abc", "480.0", "0", "-1"])
    def test_invalid_rejected_before_service(self, project_dir: Path, bad: str):
        called = {"n": 0}

        def _exec(self, *a, **k):
            called["n"] += 1
            return ServiceResult.ok("detect", data={})

        app = build_app()
        with patch(
            "video2pptx.application.services.detection_service.DetectionService.execute",
            _exec,
        ):
            result = runner.invoke(
                app, ["detect", str(project_dir), "--analysis-max-side", bad]
            )
        assert result.exit_code != 0
        assert called["n"] == 0


class TestCanonicalAutoCli:
    def test_auto_native(self, project_dir: Path):
        captured: dict = {}

        def _exec(self, project_location, **kwargs):
            captured["analysis_max_side"] = kwargs.get("analysis_max_side", "MISSING")
            return ServiceResult.ok("auto", data={"success": True})

        app = build_app()
        with patch(
            "video2pptx.application.services.auto_service.AutoService.execute",
            _exec,
        ):
            result = runner.invoke(
                app, ["auto", str(project_dir), "--analysis-max-side", "NATIVE"]
            )
        assert result.exit_code == 0, result.output
        assert captured["analysis_max_side"] is None

    def test_auto_omitted_unset(self, project_dir: Path):
        captured: dict = {}

        def _exec(self, project_location, **kwargs):
            captured["analysis_max_side"] = kwargs.get("analysis_max_side", "MISSING")
            return ServiceResult.ok("auto", data={"success": True})

        app = build_app()
        with patch(
            "video2pptx.application.services.auto_service.AutoService.execute",
            _exec,
        ):
            result = runner.invoke(app, ["auto", str(project_dir)])
        assert result.exit_code == 0, result.output
        assert captured["analysis_max_side"] is UNSET or isinstance(
            captured["analysis_max_side"], type(UNSET)
        )
