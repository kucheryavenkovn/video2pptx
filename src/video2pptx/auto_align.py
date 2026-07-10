# FILE: src/video2pptx/auto_align.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Align visual slide boundaries to subtitle anchors for better transcript segmentation
#   SCOPE: Candidate generation from subtitle cues, cost function, sequential boundary optimization,
#          invariant validation, alignment report generation
#   DEPENDS: M-SUBTITLES, M-MODELS, pysubs2
#   LINKS: M-AUTO-ALIGN
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   align_slides_to_subtitles - main entry: slides + subtitles → aligned slides + report
#   AlignmentReport - structured result with per-boundary details
#   SubtitleAnchorProvider - extracts anchor candidates from subtitle cues
# END_MODULE_MAP

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from loguru import logger

from video2pptx.models import SlideSegment
from video2pptx.subtitles import SubtitleCue, parse_subtitles


@dataclass
class AlignmentBoundary:
    slide_index: int
    visual_boundary: float
    aligned_boundary: float
    delta_sec: float
    source: str
    subtitle_uid: str | None = None
    confidence: float = 1.0


@dataclass
class AlignmentReport:
    boundaries_total: int = 0
    boundaries_moved: int = 0
    avg_shift: float = 0.0
    max_shift: float = 0.0
    fallback_count: int = 0
    failed_count: int = 0
    details: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundaries_total": self.boundaries_total,
            "boundaries_moved": self.boundaries_moved,
            "avg_shift": round(self.avg_shift, 3),
            "max_shift": round(self.max_shift, 3),
            "fallback_count": self.fallback_count,
            "failed_count": self.failed_count,
            "details": self.details,
        }


class AlignmentAnchorProvider(Protocol):
    def anchors(self, video_duration: float) -> list[float]:
        ...


class SubtitleAnchorProvider:
    def __init__(self, cues: list[SubtitleCue]) -> None:
        self._cues = cues

    def anchors(self, video_duration: float) -> list[float]:
        anchors: list[float] = []
        for i, cue in enumerate(self._cues):
            anchors.append(cue.start)
            if i > 0:
                gap_start = self._cues[i - 1].end
                gap_end = cue.start
                if gap_end - gap_start > 0.01:
                    anchors.append((gap_start + gap_end) / 2)
        return anchors


def _find_best_anchor(
    visual_boundary: float,
    anchors: list[float],
    max_shift: float,
    cues: list[SubtitleCue],
) -> tuple[float, str, str | None, float]:
    best_ts = visual_boundary
    best_source = "visual_fallback"
    best_uid: str | None = None
    best_score = -1.0

    for anchor in anchors:
        shift = abs(anchor - visual_boundary)
        if shift > max_shift:
            continue
        score = 1.0 - (shift / max_shift) if max_shift > 0 else 1.0

        for cue in cues:
            if abs(cue.start - anchor) < 0.01:
                score += 0.3
                best_uid = f"cue_{cue.start:.3f}_{cue.end:.3f}"
                break

        if score > best_score:
            best_score = score
            best_ts = anchor
            best_source = "subtitle_start" if best_uid else "subtitle_anchor"

    if best_source == "visual_fallback":
        best_score = 0.5

    return best_ts, best_source, best_uid, best_score


def _validate_boundaries(
    slides: list[SlideSegment],
    video_duration: float,
    min_duration: float = 1.0,
) -> list[str]:
    errors: list[str] = []
    for i, s in enumerate(slides):
        if s.start < 0:
            errors.append(f"slide[{i}].start < 0: {s.start}")
        if s.start >= s.end:
            errors.append(f"slide[{i}].start >= end: {s.start} >= {s.end}")
        if s.duration < min_duration:
            errors.append(f"slide[{i}].duration < {min_duration}: {s.duration}")
        if i > 0 and s.start < slides[i - 1].end - 0.01:
            errors.append(f"slide[{i}].start < prev.end: {s.start} < {slides[i-1].end}")
    if slides and slides[-1].end > video_duration + 0.5:
        errors.append(f"last slide end > video_duration: {slides[-1].end} > {video_duration}")
    return errors


def align_slides_to_subtitles(
    slides: list[SlideSegment],
    subtitles_path: Path,
    max_shift_sec: float = 3.0,
    dry_run: bool = False,
    include_manual: bool = False,
    video_duration: float | None = None,
) -> AlignmentReport:
    # START_CONTRACT: align_slides_to_subtitles
    #   PURPOSE: Align internal visual boundaries between adjacent slides to nearest subtitle anchors
    #   INPUTS: {
    #       slides: list[SlideSegment],
    #       subtitles_path: Path — SRT/VTT file,
    #       max_shift_sec: float — max allowed shift per boundary,
    #       dry_run: bool — if True, compute plan without modifying slides,
    #       include_manual: bool — if True, also shift manual boundaries,
    #       video_duration: float | None — for invariant validation
    #   }
    #   OUTPUTS: AlignmentReport with per-boundary details
    #   SIDE_EFFECTS: modifies slide start/end times in-place (unless dry_run)
    #   LINKS: M-AUTO-ALIGN
    # END_CONTRACT: align_slides_to_subtitles

    if len(slides) < 2:
        return AlignmentReport(boundaries_total=0)

    content = subtitles_path.read_text(encoding="utf-8-sig")
    fmt = "vtt" if subtitles_path.suffix.lower() == ".vtt" else "srt"
    cues = parse_subtitles(content, format=fmt)
    logger.info(f"[AutoAlign] Loaded {len(cues)} subtitle cues")

    provider = SubtitleAnchorProvider(cues)
    anchors = provider.anchors(video_duration or slides[-1].end)
    logger.info(f"[AutoAlign] Generated {len(anchors)} anchor candidates")

    boundaries: list[tuple[int, float]] = []
    for i in range(len(slides) - 1):
        if not include_manual and (slides[i].manual or slides[i + 1].manual):
            logger.debug(f"[AutoAlign] Skipping manual boundary at slide {i+1}/{i+2}")
            continue
        boundary = slides[i].end
        boundaries.append((i, boundary))

    report = AlignmentReport(boundaries_total=len(boundaries))
    shifts: list[float] = []

    for slide_idx, visual_b in boundaries:
        best_ts, source, uid, conf = _find_best_anchor(
            visual_b, anchors, max_shift_sec, cues
        )

        delta = best_ts - visual_b
        detail = {
            "slide_index": slide_idx + 1,
            "visual_boundary": round(visual_b, 3),
            "aligned_boundary": round(best_ts, 3),
            "delta_sec": round(delta, 3),
            "source": source,
            "subtitle_uid": uid,
            "confidence": round(conf, 3),
        }
        report.details.append(detail)

        if abs(delta) > 0.01:
            report.boundaries_moved += 1
            shifts.append(abs(delta))
        if source == "visual_fallback":
            report.fallback_count += 1

        if not dry_run:
            slides[slide_idx].end = best_ts
            slides[slide_idx].duration = best_ts - slides[slide_idx].start
            slides[slide_idx + 1].start = best_ts
            slides[slide_idx + 1].duration = slides[slide_idx + 1].end - best_ts

    if shifts:
        report.avg_shift = sum(shifts) / len(shifts)
        report.max_shift = max(shifts)

    if not dry_run and video_duration:
        errors = _validate_boundaries(slides, video_duration)
        if errors:
            report.failed_count = len(errors)
            logger.error(f"[AutoAlign] Invariant violations after alignment: {errors}")
        else:
            logger.info(
                f"[AutoAlign] Alignment done | moved={report.boundaries_moved} "
                f"avg_shift={report.avg_shift:.3f}s max_shift={report.max_shift:.3f}s"
            )

    return report
