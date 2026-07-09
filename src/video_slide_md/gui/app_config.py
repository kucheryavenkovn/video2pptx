# FILE: src/video_slide_md/gui/app_config.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: App-wide configuration persistence — load/save app-config.yaml in platform config dir
#   SCOPE: AppConfigModel Pydantic model, load/save/apply_defaults, platform-appropriate config directory
#   DEPENDS: PyYAML, pydantic, pathlib
#   LINKS: M-GUI-APPCONFIG
#   ROLE: DATA_LAYER
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   AppConfigModel - Pydantic model for app-wide settings (LLM, GPU, snap, defaults)
#   load_app_config - load from app-config.yaml or return defaults
#   save_app_config - write AppConfigModel to app-config.yaml
#   apply_defaults_to_project - merge app config defaults into a Project object
#   get_config_dir - return platform-appropriate config directory path
# END_MODULE_MAP

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from loguru import logger
from pydantic import BaseModel, Field

from video_slide_md.config import LlmConfig
from video_slide_md.project_manager import Project


class AppConfigModel(BaseModel):
    # START_CONTRACT: AppConfigModel
    #   PURPOSE: App-wide settings that persist across projects and sessions
    #   INPUTS: { llm, backend, snap_mode, snap_flat_threshold, default_project_dir }
    #   OUTPUTS: { AppConfigModel }
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-APPCONFIG
    # END_CONTRACT: AppConfigModel
    version: str = Field(default="1.0", description="Config schema version")
    llm: LlmConfig = Field(default_factory=LlmConfig, description="Default LLM settings for new projects")
    backend: str = Field(default="auto", description="Default GPU/decoder backend: auto, opencv, pyav")
    snap_mode: str = Field(default="hybrid", description="Smart snap strategy: diff_only, fallback_analyze, hybrid")
    snap_flat_threshold: float = Field(default=0.05, ge=0.001, le=1.0, description="Flat graph threshold for hybrid snap")
    default_project_dir: str = Field(default="", description="Default directory for new projects")
    last_project_path: str = Field(default="", description="Path to the last opened project for auto-restore")


def get_config_dir() -> Path:
    # START_CONTRACT: get_config_dir
    #   PURPOSE: Return platform-appropriate config directory path, create if missing
    #   INPUTS: none
    #   OUTPUTS: Path
    #   SIDE_EFFECTS: creates directory on first call if missing
    #   LINKS: M-GUI-APPCONFIG
    # END_CONTRACT: get_config_dir

    # START_BLOCK_GET_CONFIG_DIR
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"

    config_dir = base / "video-slide-md"
    config_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"[GUI-AppConfig][get_config_dir] Config dir | path={config_dir}")
    return config_dir
    # END_BLOCK_GET_CONFIG_DIR


def load_app_config() -> AppConfigModel:
    # START_CONTRACT: load_app_config
    #   PURPOSE: Load app-config.yaml from platform config dir, return defaults if missing or invalid
    #   INPUTS: none
    #   OUTPUTS: AppConfigModel
    #   SIDE_EFFECTS: reads file if exists, logs warning on parse failure
    #   LINKS: M-GUI-APPCONFIG
    # END_CONTRACT: load_app_config

    # START_BLOCK_LOAD_APP_CONFIG
    config_path = get_config_dir() / "app-config.yaml"

    if not config_path.is_file():
        logger.info("[GUI-AppConfig][load_app_config] No config file found, returning defaults")
        return AppConfigModel()

    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            logger.warning("[GUI-AppConfig][load_app_config] Invalid config format, returning defaults")
            return AppConfigModel()
        return AppConfigModel.model_validate(data)
    except Exception as exc:
        logger.warning(f"[GUI-AppConfig][load_app_config] Failed to parse config | error={exc}")
        return AppConfigModel()
    # END_BLOCK_LOAD_APP_CONFIG


def save_app_config(config: AppConfigModel) -> None:
    # START_CONTRACT: save_app_config
    #   PURPOSE: Write AppConfigModel to app-config.yaml in platform config dir
    #   INPUTS: { config: AppConfigModel }
    #   OUTPUTS: None
    #   SIDE_EFFECTS: writes YAML file, creates config dir if missing
    #   LINKS: M-GUI-APPCONFIG
    # END_CONTRACT: save_app_config

    # START_BLOCK_SAVE_APP_CONFIG
    config_dir = get_config_dir()
    config_path = config_dir / "app-config.yaml"

    data = config.model_dump(mode="python", exclude_none=True)
    config_path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True), encoding="utf-8")
    logger.info(f"[GUI-AppConfig][save_app_config] Config saved | path={config_path}")
    # END_BLOCK_SAVE_APP_CONFIG


def apply_defaults_to_project(project: Project, app_config: AppConfigModel | None = None) -> Project:
    # START_CONTRACT: apply_defaults_to_project
    #   PURPOSE: Merge app config defaults into a newly created Project object
    #   INPUTS: { project: Project, app_config: AppConfigModel | None }
    #   OUTPUTS: Project — with inherited defaults applied
    #   SIDE_EFFECTS: modifies project.detection and project.llm fields
    #   LINKS: M-GUI-APPCONFIG
    # END_CONTRACT: apply_defaults_to_project

    # START_BLOCK_APPLY_DEFAULTS
    cfg = app_config or load_app_config()

    # Inherit LLM settings
    project.llm = cfg.llm.model_copy(deep=True)

    # Inherit backend default
    if cfg.backend != "auto":
        project.backend = cfg.backend

    logger.info(
        f"[GUI-AppConfig][apply_defaults_to_project] Defaults applied | "
        f"project={project.name} backend={cfg.backend} snap_mode={cfg.snap_mode}"
    )
    return project
    # END_BLOCK_APPLY_DEFAULTS
