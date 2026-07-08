# FILE: tests/test_config.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for configuration loading and merging
#   SCOPE: YAML loading, CLI merge, defaults, validation
#   DEPENDS: pytest, yaml, video_slide_md.config
#   LINKS: V-M-CONFIG
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import json

import pytest
import yaml
from pydantic import ValidationError

from video_slide_md.config import (
    AppConfig,
    DebugConfig,
    DetectionConfig,
    ExportConfig,
    LoggingConfig,
    VideoConfig,
    load_config,
    merge_config,
)


class TestVideoConfig:
    def test_defaults(self):
        vc = VideoConfig()
        assert vc.sample_fps == 2.0
        assert vc.decoder_backend == "auto"

    def test_custom(self):
        vc = VideoConfig(sample_fps=5.0, decoder_backend="pynv")
        assert vc.sample_fps == 5.0
        assert vc.decoder_backend == "pynv"

    def test_invalid_fps_negative(self):
        with pytest.raises(ValidationError):
            VideoConfig(sample_fps=-1.0)

    def test_invalid_fps_too_high(self):
        with pytest.raises(ValidationError):
            VideoConfig(sample_fps=60.0)


class TestDetectionConfig:
    def test_defaults(self):
        dc = DetectionConfig()
        assert dc.slide_roi == "auto"
        assert dc.ignore_rois == []
        assert dc.min_slide_duration == 3.0
        assert dc.min_stable_duration == 1.5
        assert dc.dedupe_enabled is True

    def test_with_ignore_rois(self):
        dc = DetectionConfig(ignore_rois=[[1450, 720, 1900, 1080]])
        assert len(dc.ignore_rois) == 1

    def test_threshold_manual(self):
        dc = DetectionConfig(threshold=0.5)
        assert dc.threshold == 0.5

    def test_threshold_auto(self):
        dc = DetectionConfig(threshold="auto")
        assert dc.threshold == "auto"


class TestExportConfig:
    def test_defaults(self):
        ec = ExportConfig()
        assert ec.markdown_format == "marp"
        assert ec.include_timecodes is True


class TestDebugConfig:
    def test_defaults(self):
        dc = DebugConfig()
        assert dc.save_diff_scores is True
        assert dc.save_contact_sheet is True
        assert dc.save_sampled_frames is False


class TestAppConfig:
    def test_defaults(self):
        cfg = AppConfig()
        assert cfg.video.sample_fps == 2.0
        assert cfg.detection.min_slide_duration == 3.0
        assert cfg.export.markdown_format == "marp"
        assert cfg.debug.save_timeline is True
        assert cfg.logging.level == "INFO"

    def test_full_config(self):
        cfg = AppConfig(
            video=VideoConfig(sample_fps=3.0),
            detection=DetectionConfig(slide_roi="full", threshold=0.25),
            export=ExportConfig(include_timecodes=False),
            debug=DebugConfig(save_sampled_frames=True),
        )
        assert cfg.video.sample_fps == 3.0
        assert cfg.detection.threshold == 0.25
        assert cfg.export.include_timecodes is False
        assert cfg.debug.save_sampled_frames is True


class TestMergeConfig:
    def test_merge_flat(self):
        base = {"video": {"sample_fps": 2.0}}
        overrides = {"video": {"sample_fps": 5.0}}
        result = merge_config(base, overrides)
        assert result["video"]["sample_fps"] == 5.0

    def test_merge_ignore_none(self):
        base = {"detection": {"threshold": "auto"}}
        overrides = {"detection": {"threshold": None}}
        result = merge_config(base, overrides)
        assert result["detection"]["threshold"] is None

    def test_merge_preserves_base(self):
        base = {"video": {"sample_fps": 2.0, "decoder_backend": "auto"}}
        overrides = {"video": {"sample_fps": 3.0}}
        result = merge_config(base, overrides)
        assert result["video"]["sample_fps"] == 3.0
        assert result["video"]["decoder_backend"] == "auto"


class TestLoadConfig:
    def test_load_from_yaml(self, tmp_path):
        data = {
            "video": {"sample_fps": 5.0, "decoder_backend": "opencv"},
            "detection": {"threshold": 0.5, "min_slide_duration": 5.0},
        }
        cfg_file = tmp_path / "config.yaml"
        with open(cfg_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

        cfg = load_config(config_path=cfg_file)
        assert cfg.video.sample_fps == 5.0
        assert cfg.video.decoder_backend == "opencv"
        assert cfg.detection.threshold == 0.5
        assert cfg.detection.min_slide_duration == 5.0

    def test_load_from_yaml_with_cli_overrides(self, tmp_path):
        data = {"video": {"sample_fps": 2.0}, "detection": {"threshold": "auto"}}
        cfg_file = tmp_path / "config.yaml"
        with open(cfg_file, "w") as f:
            yaml.dump(data, f)

        cfg = load_config(
            config_path=cfg_file,
            cli_overrides={"video": {"sample_fps": 10.0}},
        )
        assert cfg.video.sample_fps == 10.0
        assert cfg.detection.threshold == "auto"

    def test_defaults_without_file(self):
        cfg = load_config()
        assert cfg.video.sample_fps == 2.0
        assert cfg.detection.min_slide_duration == 3.0

    def test_missing_file_falls_back(self):
        cfg = load_config(config_path="/nonexistent/config.yaml")
        assert cfg.video.sample_fps == 2.0

    def test_json_serialization(self):
        cfg = AppConfig()
        raw = cfg.model_dump_json()
        restored = AppConfig.model_validate_json(raw)
        assert restored.video.sample_fps == 2.0
