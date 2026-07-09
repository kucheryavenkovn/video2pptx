# FILE: tests/test_gui_app_config.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for M-GUI-APPCONFIG — AppConfigModel, load/save, apply_defaults_to_project
#   SCOPE: Deterministic tests for app config persistence and project inheritance
#   DEPENDS: pytest, yaml, pydantic
#   LINKS: M-GUI-APPCONFIG
#   ROLE: TEST
#   MAP_MODE: NONE
# END_MODULE_CONTRACT

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

from video_slide_md.config import LlmConfig
from video_slide_md.gui.app_config import (
    AppConfigModel,
    apply_defaults_to_project,
    get_config_dir,
    load_app_config,
    save_app_config,
)
from video_slide_md.project_manager import Project


class TestGetConfigDir:
    # START_CONTRACT: TestGetConfigDir
    #   PURPOSE: Verify platform-appropriate config directory resolution
    #   INPUTS: none
    #   OUTPUTS: assertions
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-APPCONFIG
    # END_CONTRACT: TestGetConfigDir

    def test_returns_path(self) -> None:
        path = get_config_dir()
        assert isinstance(path, Path)
        assert path.exists()

    def test_ends_with_video_slide_md(self) -> None:
        path = get_config_dir()
        assert path.name == "video-slide-md"

    def test_based_on_platform(self) -> None:
        path = get_config_dir()
        if sys.platform == "win32":
            assert "AppData" in str(path) or "Roaming" in str(path)
        elif sys.platform == "darwin":
            assert "Application Support" in str(path)
        else:
            assert ".config" in str(path)


class TestAppConfigModel:
    # START_CONTRACT: TestAppConfigModel
    #   PURPOSE: Verify AppConfigModel defaults and field constraints
    #   INPUTS: none
    #   OUTPUTS: assertions
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-APPCONFIG
    # END_CONTRACT: TestAppConfigModel

    def test_default_creation(self) -> None:
        cfg = AppConfigModel()
        assert cfg.version == "1.0"
        assert cfg.snap_mode == "hybrid"
        assert cfg.snap_flat_threshold == 0.05
        assert cfg.backend == "auto"
        assert cfg.default_project_dir == ""

    def test_snap_flat_threshold_ge(self) -> None:
        with pytest.raises(Exception):
            AppConfigModel(snap_flat_threshold=0.0)

    def test_snap_flat_threshold_le(self) -> None:
        with pytest.raises(Exception):
            AppConfigModel(snap_flat_threshold=1.5)

    def test_llm_config_defaults(self) -> None:
        cfg = AppConfigModel()
        assert isinstance(cfg.llm, LlmConfig)
        assert cfg.llm.model == "gemma-4-26b-a4b-it@q4_k_xl"

    def test_serialize_roundtrip(self) -> None:
        cfg = AppConfigModel(snap_mode="diff_only", backend="opencv")
        data = cfg.model_dump(mode="python", exclude_none=True)
        assert data["snap_mode"] == "diff_only"
        assert data["backend"] == "opencv"

        restored = AppConfigModel.model_validate(data)
        assert restored.snap_mode == "diff_only"
        assert restored.backend == "opencv"


class TestLoadSaveAppConfig:
    # START_CONTRACT: TestLoadSaveAppConfig
    #   PURPOSE: Verify app config file I/O
    #   INPUTS: none
    #   OUTPUTS: assertions
    #   SIDE_EFFECTS: writes/reads temporary files in real config dir (test-safe)
    #   LINKS: M-GUI-APPCONFIG
    # END_CONTRACT: TestLoadSaveAppConfig

    @pytest.fixture(autouse=True)
    def _backup_and_restore(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._tmp_dir = Path(__file__).parent / "_tmp_app_config"
        if self._tmp_dir.exists():
            import shutil
            shutil.rmtree(self._tmp_dir)
        self._tmp_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("video_slide_md.gui.app_config.get_config_dir", lambda: self._tmp_dir)
        yield
        if self._tmp_dir.exists():
            import shutil
            shutil.rmtree(self._tmp_dir)

    def test_save_and_load(self) -> None:
        cfg = AppConfigModel(snap_mode="fallback_analyze", backend="pyav")
        save_app_config(cfg)

        config_path = self._tmp_dir / "app-config.yaml"
        assert config_path.is_file()

        loaded = load_app_config()
        assert loaded.snap_mode == "fallback_analyze"
        assert loaded.backend == "pyav"

    def test_load_missing_returns_defaults(self) -> None:
        cfg = load_app_config()
        assert cfg.snap_mode == "hybrid"
        assert cfg.backend == "auto"

    def test_load_invalid_yaml_returns_defaults(self) -> None:
        config_path = self._tmp_dir / "app-config.yaml"
        config_path.write_text("invalid: yaml: : : broken", encoding="utf-8")

        cfg = load_app_config()
        assert cfg.snap_mode == "hybrid"

    def test_save_creates_dir(self) -> None:
        nested = self._tmp_dir / "sub" / "dir"
        cfg_path = nested / "app-config.yaml"

        def mock_get_config_dir() -> Path:
            nested.mkdir(parents=True, exist_ok=True)
            return nested

        import video_slide_md.gui.app_config as ac
        original = ac.get_config_dir
        ac.get_config_dir = mock_get_config_dir
        try:
            cfg = AppConfigModel(snap_mode="diff_only")
            save_app_config(cfg)
            assert cfg_path.is_file()
        finally:
            ac.get_config_dir = original

    def test_roundtrip_preserves_all_fields(self) -> None:
        cfg = AppConfigModel(
            snap_mode="diff_only",
            snap_flat_threshold=0.1,
            backend="opencv",
            default_project_dir="/home/user/projects",
            llm=LlmConfig(model="test-model", base_url="http://test:1234/v1"),
        )
        save_app_config(cfg)
        loaded = load_app_config()
        assert loaded.snap_mode == "diff_only"
        assert loaded.snap_flat_threshold == 0.1
        assert loaded.backend == "opencv"
        assert loaded.default_project_dir == "/home/user/projects"
        assert loaded.llm.model == "test-model"
        assert loaded.llm.base_url == "http://test:1234/v1"


class TestApplyDefaultsToProject:
    # START_CONTRACT: TestApplyDefaultsToProject
    #   PURPOSE: Verify that app config defaults are correctly inherited by new projects
    #   INPUTS: none
    #   OUTPUTS: assertions
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-APPCONFIG
    # END_CONTRACT: TestApplyDefaultsToProject

    def test_inherits_llm_config(self) -> None:
        app_cfg = AppConfigModel(llm=LlmConfig(model="custom-model", base_url="http://custom:8080/v1"))
        project = Project(video="/tmp/test.mp4")

        result = apply_defaults_to_project(project, app_cfg)
        assert result.llm.model == "custom-model"
        assert result.llm.base_url == "http://custom:8080/v1"

    def test_inherits_backend_when_not_auto(self) -> None:
        app_cfg = AppConfigModel(backend="pyav")
        project = Project(video="/tmp/test.mp4")

        result = apply_defaults_to_project(project, app_cfg)
        assert result.backend == "pyav"

    def test_auto_backend_does_not_override(self) -> None:
        app_cfg = AppConfigModel(backend="auto")
        project = Project(video="/tmp/test.mp4")

        result = apply_defaults_to_project(project, app_cfg)
        assert result.backend == "auto"

    def test_returns_same_project_object(self) -> None:
        app_cfg = AppConfigModel()
        project = Project(video="/tmp/test.mp4")

        result = apply_defaults_to_project(project, app_cfg)
        assert result is project
