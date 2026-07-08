# FILE: src/video_slide_md/models.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Pydantic data models for slides document
#   SCOPE: All data structures: VideoInfo, Roi, SubtitleCue, FrameFeatures, SlideSegment, SlidesDocument
#   DEPENDS: pydantic, numpy
#   LINKS: M-MODELS
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   VideoInfo - source video metadata
#   Roi - rectangular region of interest
#   SubtitleCue - single subtitle entry with time range and text
#   FrameFeatures - extracted frame signature for comparison
#   SlideSegment - one detected slide interval with transcript and metadata
#   SlidesDocument - root document containing all slide segments, video info, config, debug
# END_MODULE_MAP

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from pydantic import BaseModel, Field


class VideoInfo(BaseModel):
    # START_CONTRACT: VideoInfo
    #   PURPOSE: Metadata describing source video
    #   INPUTS: { path: str, duration: float, width: int, height: int, fps: float }
    #   OUTPUTS: { VideoInfo }
    #   SIDE_EFFECTS: none
    #   LINKS: M-MODELS
    # END_CONTRACT: VideoInfo
    path: str = Field(description="Path to source video file")
    duration: float = Field(ge=0, description="Video duration in seconds")
    width: int = Field(ge=1, description="Frame width in pixels")
    height: int = Field(ge=1, description="Frame height in pixels")
    fps: float = Field(ge=0, description="Frames per second")


class Roi(BaseModel):
    # START_CONTRACT: Roi
    #   PURPOSE: Rectangular region of interest defined by top-left and bottom-right corners
    #   INPUTS: { x1: int, y1: int, x2: int, y2: int }
    #   OUTPUTS: { Roi }
    #   SIDE_EFFECTS: none
    #   LINKS: M-MODELS
    # END_CONTRACT: Roi
    x1: int = Field(ge=0, description="Left edge (inclusive)")
    y1: int = Field(ge=0, description="Top edge (inclusive)")
    x2: int = Field(ge=0, description="Right edge (exclusive)")
    y2: int = Field(ge=0, description="Bottom edge (exclusive)")

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)


class SubtitleCue(BaseModel):
    # START_CONTRACT: SubtitleCue
    #   PURPOSE: Single subtitle entry with time range and text
    #   INPUTS: { start: float, end: float, text: str }
    #   OUTPUTS: { SubtitleCue }
    #   SIDE_EFFECTS: none
    #   LINKS: M-MODELS
    # END_CONTRACT: SubtitleCue
    start: float = Field(ge=0, description="Start time in seconds")
    end: float = Field(ge=0, description="End time in seconds")
    text: str = Field(description="Subtitle text")


class FrameFeatures(BaseModel):
    # START_CONTRACT: FrameFeatures
    #   PURPOSE: Frame signature extracted for slide comparison
    #   INPUTS: { timestamp: float, phash: str, dhash: str, hist: list[float], gray_mean: float }
    #   OUTPUTS: { FrameFeatures }
    #   SIDE_EFFECTS: none
    #   LINKS: M-MODELS
    # END_CONTRACT: FrameFeatures
    timestamp: float = Field(ge=0, description="Frame timestamp in seconds")
    phash: str = Field(default="", description="Perceptual hash hex string")
    dhash: str = Field(default="", description="Difference hash hex string")
    hist: list[float] = Field(default_factory=list, description="Normalized color histogram")
    gray_mean: float = Field(default=0.0, description="Mean grayscale brightness")
    gray_thumb: list[float] = Field(default_factory=list, description="48x48 grayscale thumbnail flattened")


@dataclass
class VideoFrame:
    # START_CONTRACT: VideoFrame
    #   PURPOSE: Decoded video frame with timestamp
    #   INPUTS: { timestamp: float, image: np.ndarray }
    #   OUTPUTS: { VideoFrame }
    #   SIDE_EFFECTS: none
    #   LINKS: M-MODELS
    # END_CONTRACT: VideoFrame
    timestamp: float
    image: np.ndarray


class SlideSegment(BaseModel):
    # START_CONTRACT: SlideSegment
    #   PURPOSE: One detected slide interval with transcript and metadata
    #   INPUTS: { index: int, start: float, end: float, duration: float, image: str,
    #             representative_timestamp: float, phash: str|None, dhash: str|None,
    #             ocr_text: str|None, transcript: str, subtitle_cues: list[SubtitleCue],
    #             confidence: float, warnings: list[str] }
    #   OUTPUTS: { SlideSegment }
    #   SIDE_EFFECTS: none
    #   LINKS: M-MODELS
    # END_CONTRACT: SlideSegment
    index: int = Field(ge=1, description="Slide number (1-based)")
    start: float = Field(ge=0, description="Interval start in seconds")
    end: float = Field(ge=0, description="Interval end in seconds")
    duration: float = Field(ge=0, description="Interval duration in seconds")
    image: str = Field(default="", description="Relative path to slide image")
    representative_timestamp: float = Field(ge=0, description="Best frame timestamp for this slide")
    phash: str | None = Field(default=None, description="Perceptual hash of representative frame")
    dhash: str | None = Field(default=None, description="Difference hash of representative frame")
    ocr_text: str | None = Field(default=None, description="Optional OCR-extracted text")
    transcript: str = Field(default="", description="Subtitle/transcript text aligned to this slide")
    subtitle_cues: list[SubtitleCue] = Field(default_factory=list, description="Subtitle cues overlapping this interval")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Detection confidence score")
    warnings: list[str] = Field(default_factory=list, description="Non-critical issues with this segment")


class SlidesDocument(BaseModel):
    # START_CONTRACT: SlidesDocument
    #   PURPOSE: Root document containing all slide segments, video info, config, debug
    #   INPUTS: { schema_version: str, video: VideoInfo, config: dict, slides: list[SlideSegment], debug: dict }
    #   OUTPUTS: { SlidesDocument }
    #   SIDE_EFFECTS: none
    #   LINKS: M-MODELS
    # END_CONTRACT: SlidesDocument
    schema_version: str = Field(default="1.0", description="JSON schema version")
    video: VideoInfo = Field(description="Source video metadata")
    config: dict[str, Any] = Field(default_factory=dict, description="Detection config used")
    slides: list[SlideSegment] = Field(default_factory=list, description="Detected slide segments")
    debug: dict[str, str] = Field(default_factory=dict, description="Paths to debug artifacts")
