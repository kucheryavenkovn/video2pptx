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
    cue_crossings_before: int = 0
    cue_crossings_after: int = 0
    multi_slide_cues_before: int = 0
    multi_slide_cues_after: int = 0
    details: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundaries_total": self.boundaries_total,
            "boundaries_moved": self.boundaries_moved,
            "avg_shift": round(self.avg_shift, 3),
            "max_shift": round(self.max_shift, 3),
            "fallback_count": self.fallback_count,
            "failed_count": self.failed_count,
            "cue_crossings_before": self.cue_crossings_before,
            "cue_crossings_after": self.cue_crossings_after,
            "multi_slide_cues_before": self.multi_slide_cues_before,
            "multi_slide_cues_after": self.multi_slide_cues_after,
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


def _compute_cue_crossings(slides: list[SlideSegment], cues: list) -> dict[str, Any]:
    """Compute metrics: cues crossing boundaries, multi-slide cues, avg overlap."""
    total_crossings = 0
    multi_slide_cues = 0
    empty_slides_with_cues = 0
    for i in range(len(slides) - 1):
        boundary = slides[i].end
        for cue in cues:
            if cue.start < boundary < cue.end:
                total_crossings += 1
    for cue in cues:
        assigned = 0
        for s in slides:
            if s.start <= cue.start < s.end or (s.start < cue.end <= s.end):
                assigned += 1
            elif s.start >= cue.start and s.end <= cue.end:
                assigned += 1
        if assigned > 1:
            multi_slide_cues += 1
    return {
        "cue_crossings": total_crossings,
        "multi_slide_cues": multi_slide_cues,
    }


def _coordinated_choice(
    slides: list[SlideSegment],
    anchors: list[float],
    cues: list,
    max_shift: float,
    include_manual: bool,
    min_duration: float = 1.0,
) -> list[dict]:
    """Sequential boundary optimization with neighbor duration check.
    For each internal boundary, find the best anchor that does not cause
    the current or next slide to fall below min_duration.
    Falls back to visual boundary if no anchor satisfies constraints.
    """
    decisions: list[dict] = []
    n = len(slides)

    for i in range(n - 1):
        if not include_manual and (slides[i].manual or slides[i + 1].manual):
            decisions.append({
                "slide_index": i + 1,
                "visual_boundary": slides[i].end,
                "aligned_boundary": slides[i].end,
                "delta_sec": 0.0,
                "source": "manual_skip",
                "subtitle_uid": None,
                "confidence": 1.0,
            })
            continue

        visual_b = slides[i].end
        best_ts = visual_b
        best_source = "visual_fallback"
        best_uid: str | None = None
        best_conf = 0.5

        prev_start = slides[i].start
        next_end = slides[i + 1].end

        for anchor in anchors:
            shift = abs(anchor - visual_b)
            if shift > max_shift:
                continue

            # Check neighbor durations
            new_prev_dur = anchor - prev_start
            new_next_dur = next_end - anchor
            if new_prev_dur < min_duration or new_next_dur < min_duration:
                continue

            conf = 1.0 - (shift / max_shift) if max_shift > 0 else 1.0

            uid: str | None = None
            for cue in cues:
                if abs(cue.start - anchor) < 0.01:
                    conf += 0.3
                    uid = f"cue_{cue.start:.3f}_{cue.end:.3f}"
                    break

            if conf > best_conf:
                best_conf = conf
                best_ts = anchor
                best_source = "subtitle_start" if uid else "subtitle_anchor"
                best_uid = uid

        delta = best_ts - visual_b
        decisions.append({
            "slide_index": i + 1,
            "visual_boundary": round(visual_b, 3),
            "aligned_boundary": round(best_ts, 3),
            "delta_sec": round(delta, 3),
            "source": best_source,
            "subtitle_uid": best_uid,
            "confidence": round(best_conf, 3),
        })

    return decisions


def _build_cue_crossings_report(slides_before: list[SlideSegment], slides_after: list[SlideSegment], cues: list) -> dict:
    before = _compute_cue_crossings(slides_before, cues)
    after = _compute_cue_crossings(slides_after, cues)
    return {
        "cue_crossings_before": before["cue_crossings"],
        "cue_crossings_after": after["cue_crossings"],
        "multi_slide_cues_before": before["multi_slide_cues"],
        "multi_slide_cues_after": after["multi_slide_cues"],
    }


def rollback_alignment(slides: list[SlideSegment], report_path: Path) -> int:
    """Restore visual boundaries from alignment report. Returns number of boundaries restored.
    Uses 'visual_boundary' field from report. Only restores boundaries that differ.
    """
    if not report_path.is_file():
        logger.warning(f"[AutoAlign][rollback] No alignment report: {report_path}")
        return 0

    import json
    data = json.loads(report_path.read_text(encoding="utf-8"))
    restored = 0
    for detail in data.get("details", []):
        idx = detail.get("slide_index", 1) - 1
        vb = detail.get("visual_boundary")
        if vb is None or idx < 0 or idx >= len(slides) - 1:
            continue
        current = slides[idx].end
        if abs(current - vb) > 0.01:
            slides[idx].end = vb
            slides[idx].duration = vb - slides[idx].start
            slides[idx + 1].start = vb
            slides[idx + 1].duration = slides[idx + 1].end - vb
            restored += 1

    logger.info(f"[AutoAlign][rollback] Restored {restored} boundaries")
    return restored


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

    # Save pre-alignment snapshots for metrics
    pre_slides = [SlideSegment.model_validate(s.model_dump()) for s in slides]

    # Coordinated choice with neighbor-check
    decisions = _coordinated_choice(slides, anchors, cues, max_shift_sec, include_manual)

    report = AlignmentReport(boundaries_total=len(decisions))
    shifts: list[float] = []

    for d in decisions:
        report.details.append(d)
        if d["source"] == "visual_fallback":
            report.fallback_count += 1
        if abs(d["delta_sec"]) > 0.01:
            report.boundaries_moved += 1
            shifts.append(abs(d["delta_sec"]))

        if not dry_run:
            idx = d["slide_index"] - 1
            ts = d["aligned_boundary"]
            slides[idx].end = ts
            slides[idx].duration = ts - slides[idx].start
            slides[idx + 1].start = ts
            slides[idx + 1].duration = slides[idx + 1].end - ts

    if shifts:
        report.avg_shift = sum(shifts) / len(shifts)
        report.max_shift = max(shifts)

    # Compute cue crossing metrics
    metrics = _build_cue_crossings_report(pre_slides, slides, cues)
    report.cue_crossings_before = metrics["cue_crossings_before"]
    report.cue_crossings_after = metrics["cue_crossings_after"]
    report.multi_slide_cues_before = metrics["multi_slide_cues_before"]
    report.multi_slide_cues_after = metrics["multi_slide_cues_after"]

    if not dry_run and video_duration:
        errors = _validate_boundaries(slides, video_duration)
        if errors:
            report.failed_count = len(errors)
            logger.error(f"[AutoAlign] Invariant violations after alignment: {errors}")
        else:
            logger.info(
                f"[AutoAlign] Alignment done | moved={report.boundaries_moved} "
                f"avg_shift={report.avg_shift:.3f}s max_shift={report.max_shift:.3f}s "
                f"crossings={metrics['cue_crossings_before']}->{metrics['cue_crossings_after']}"
            )

    return report
