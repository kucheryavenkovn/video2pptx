# FILE: src/video2pptx/config.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Configuration loading — YAML file + CLI arg merge into typed config
#   SCOPE: Load config from YAML file, merge with CLI argument overrides, return validated AppConfig
#   DEPENDS: pyyaml, pydantic, pathlib
#   LINKS: M-CONFIG
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   AppConfig - root typed config aggregating all subsections
#   VideoConfig - video source and decoding backend config (sample_fps, decoder_backend, analysis_max_side)
#   DetectionConfig - slide detection parameters
#   ExportConfig - output format configuration
#   DebugConfig - debug artifact toggle flags
#   LoggingConfig - logging level
#   load_config - load config from YAML path, merge with CLI overrides
#   merge_config - merge CLI kwargs into AppConfig, CLI takes precedence
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class VideoConfig(BaseModel):
    # START_CONTRACT: VideoConfig
    #   PURPOSE: Video source and decoding backend configuration
    #   INPUTS: { sample_fps: float, decoder_backend: str, analysis_max_side: int|None }
    #   OUTPUTS: { VideoConfig }
    #   SIDE_EFFECTS: none
    #   LINKS: M-CONFIG, M-ANALYSIS-SCALE
    # END_CONTRACT: VideoConfig
    sample_fps: float = Field(default=0.5, ge=0.1, le=30.0, description="Frame sampling rate")
    decoder_backend: str = Field(default="auto", description="Decoder backend: auto, opencv, pyav, decord, pynv")
    analysis_max_side: int | None = Field(
        default=480,
        ge=1,
        le=8192,
        description=(
            "Max side length for Pass1 analysis frames only; screenshots always full-res. "
            "Default 480 from Phase 19 Hermes golden mean (~2.15× wall). Set null only via "
            "explicit YAML/config override if native analysis is required."
        ),
    )


class DetectionConfig(BaseModel):
    # START_CONTRACT: DetectionConfig
    #   PURPOSE: Slide detection parameters and post-detection export flags
    #   SCOPE: ROI, threshold, durations, deduplication, export-md/pptx flags
    #   DEPENDS: none
    #   LINKS: M-CONFIG
    # END_CONTRACT: DetectionConfig
    slide_roi: str = Field(default="auto", description="ROI mode or coordinates: auto, full, x1,y1,x2,y2")
    ignore_rois: list[list[int]] = Field(default_factory=list, description="Regions to ignore [[x1,y1,x2,y2], ...]")
    threshold: str | float = Field(default="auto", description="Diff score threshold or auto")
    min_slide_duration: float = Field(default=10.0, ge=0.5, description="Minimum slide duration in seconds")
    # 0.0 disables debounce; values are wall-clock seconds (not FPS-dependent frame counts)
    min_stable_duration: float = Field(default=5.0, ge=0.0, description="Min seconds between change events; 0 disables debounce")
    dedupe_enabled: bool = Field(default=True, description="Enable neighbor deduplication")
    export_md: bool = Field(default=False, description="Export deck.md after detection")
    export_pptx: bool = Field(default=False, description="Export deck.pptx after detection")


class ExportConfig(BaseModel):
    # START_CONTRACT: ExportConfig
    #   PURPOSE: Output format configuration
    #   INPUTS: { markdown_format, include_transcript_as_notes, include_timecodes }
    #   OUTPUTS: { ExportConfig }
    #   SIDE_EFFECTS: none
    #   LINKS: M-CONFIG
    # END_CONTRACT: ExportConfig
    markdown_format: str = Field(default="marp", description="Markdown format: marp, revealjs")
    include_transcript_as_notes: bool = Field(default=True, description="Include transcript in speaker notes")
    include_timecodes: bool = Field(default=True, description="Include start/end timecodes in output")


class DebugConfig(BaseModel):
    # START_CONTRACT: DebugConfig
    #   PURPOSE: Debug artifact toggle flags
    #   INPUTS: { save_sampled_frames, save_diff_scores, save_timeline, save_contact_sheet }
    #   OUTPUTS: { DebugConfig }
    #   SIDE_EFFECTS: none
    #   LINKS: M-CONFIG
    # END_CONTRACT: DebugConfig
    save_sampled_frames: bool = Field(default=False, description="Save individual sampled frames")
    save_diff_scores: bool = Field(default=True, description="Save diff_scores.csv")
    save_timeline: bool = Field(default=True, description="Save timeline.png")
    save_contact_sheet: bool = Field(default=True, description="Save contact_sheet.jpg")


class LoggingConfig(BaseModel):
    # START_CONTRACT: LoggingConfig
    #   PURPOSE: Logging level configuration
    #   INPUTS: { level: str }
    #   OUTPUTS: { LoggingConfig }
    #   SIDE_EFFECTS: none
    #   LINKS: M-CONFIG
    # END_CONTRACT: LoggingConfig
    level: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR")


class LlmConfig(BaseModel):
    # START_CONTRACT: LlmConfig
    #   PURPOSE: LLM provider and model configuration for LM Studio integration
    #   INPUTS: { enabled, provider, base_url, model, context_window, temperature, max_tokens, unload_when_done }
    #   OUTPUTS: { LlmConfig }
    #   SIDE_EFFECTS: none
    #   LINKS: M-CONFIG
    # END_CONTRACT: LlmConfig
    enabled: bool = Field(default=False, description="Enable LLM processing")
    provider: str = Field(default="openai-compat", description="Provider: openai-compat (LM Studio)")
    base_url: str = Field(default="http://localhost:1234/v1", description="LM Studio API base URL")
    model: str = Field(default="gemma-4-26b-a4b-it@q4_k_xl", description="Model name for chat/vision")
    models_url: str = Field(default="", description="URL to fetch model list (empty = base_url + '/models')")
    context_window: int = Field(default=60000, ge=1024, description="Context window size in tokens")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="LLM temperature")
    max_tokens: int = Field(default=4096, ge=64, le=128000, description="Max output tokens")
    api_token: str = Field(default="", description="API key / bearer token for LLM provider authentication")
    unload_when_done: bool = Field(default=True, description="Unload model from VRAM after processing")
    vision_prompt: str = Field(
        default="Describe this slide image. List ALL key technical terms, concepts, formulas, "
                "and any visible text. Be specific and thorough — use the exact spelling of terms as they appear on screen.",
        description="System prompt for slide image vision analysis"
    )
    correction_prompt: str = Field(
        default="You are a transcript editor. Below is a slide description with technical terms "
                "and a raw transcript. Correct the transcript:\n"
                "- Fix misspelled technical terms using the exact terms from the slide description\n"
                "- Remove filler words and repetitions\n"
                "- Keep the original meaning and flow\n"
                "- Return ONLY the corrected transcript, no commentary",
        description="System prompt for transcript correction with slide context"
    )


class AppConfig(BaseModel):
    # START_CONTRACT: AppConfig
    #   PURPOSE: Root typed config aggregating all subsections
    #   INPUTS: { video, detection, export, debug, logging, llm }
    #   OUTPUTS: { AppConfig }
    #   SIDE_EFFECTS: none
    #   LINKS: M-CONFIG
    # END_CONTRACT: AppConfig
    video: VideoConfig = Field(default_factory=VideoConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    debug: DebugConfig = Field(default_factory=DebugConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    llm: LlmConfig = Field(default_factory=LlmConfig)


def load_config(
    config_path: str | Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> AppConfig:
    # START_CONTRACT: load_config
    #   PURPOSE: Load config from YAML path, merge with CLI overrides
    #   INPUTS: { config_path: str|Path|None, cli_overrides: dict|None }
    #   OUTPUTS: { AppConfig }
    #   SIDE_EFFECTS: reads YAML file if path provided
    #   LINKS: M-CONFIG
    # END_CONTRACT: load_config

    # START_BLOCK_LOAD_YAML
    config: dict[str, Any] = {}
    if config_path:
        path = Path(config_path)
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        else:
            import warnings
            warnings.warn(f"Config file not found: {config_path}")
    # END_BLOCK_LOAD_YAML

    if cli_overrides:
        config = merge_config(config, cli_overrides)

    return AppConfig.model_validate(config)


def merge_config(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    # START_CONTRACT: merge_config
    #   PURPOSE: Merge CLI kwargs into AppConfig dict, CLI takes precedence (deep merge)
    #   INPUTS: { base: dict, overrides: dict }
    #   OUTPUTS: { dict }
    #   SIDE_EFFECTS: none
    #   LINKS: M-CONFIG
    # END_CONTRACT: merge_config

    # START_BLOCK_MERGE_CONFIG
    result = base.copy()
    for key, value in overrides.items():
        if value is None:
            continue
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = {**result[key], **value}
        else:
            result[key] = value
    return result
    # END_BLOCK_MERGE_CONFIG
