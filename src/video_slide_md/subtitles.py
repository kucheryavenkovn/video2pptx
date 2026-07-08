# FILE: src/video_slide_md/subtitles.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Parse SRT/VTT subtitle files and align cues to slide intervals
#   SCOPE: Parse text subtitle files, align cues to segments by timestamp overlap
#   DEPENDS: models, loguru, re
#   LINKS: M-SUBTITLES
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   parse_subtitles - parse SRT/VTT content into SubtitleCue list
#   align_cues_to_segments - assign cues to segments by timestamp overlap
# END_MODULE_MAP

from __future__ import annotations

import re

from loguru import logger

from video_slide_md.models import SlideSegment, SubtitleCue


def parse_subtitles(content: str, format: str = "auto") -> list[SubtitleCue]:
    # START_CONTRACT: parse_subtitles
    #   PURPOSE: Parse SRT or VTT content into SubtitleCue objects
    #   INPUTS: { content: str - file content, format: str - "srt" | "vtt" | "auto" }
    #   OUTPUTS: list[SubtitleCue]
    #   SIDE_EFFECTS: none
    #   LINKS: M-SUBTITLES
    # END_CONTRACT: parse_subtitles

    if format == "auto":
        format = _detect_format(content)

    logger.debug(f"[Subtitles][parse_subtitles] Format detected | format={format}")

    if format == "vtt":
        # Strip VTT header (everything before first blank line after WEBVTT)
        content = _strip_vtt_header(content)

    return _parse_srt_style(content)


def _detect_format(content: str) -> str:
    if content.strip().startswith("WEBVTT"):
        return "vtt"
    return "srt"


def _strip_vtt_header(content: str) -> str:
    lines = content.splitlines()
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip() == "" and i > 0:
            start_idx = i + 1
            break
        # Some VTT files have cues immediately
        if "-->" in line and i > 0:
            start_idx = i
            break
    return "\n".join(lines[start_idx:])


# START_BLOCK_PARSE_SRT
def _parse_srt_style(content: str) -> list[SubtitleCue]:
    cues: list[SubtitleCue] = []
    # SRT pattern: index\nHH:MM:SS,mmm --> HH:MM:SS,mmm\ntext\n\n
    # VTT pattern: HH:MM:SS.mmm --> HH:MM:SS.mmm\ntext\n\n
    block_pattern = re.compile(
        r"(?:\d+\s*\n)?"                           # optional index line
        r"(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*"  # start timestamp
        r"(\d{2}:\d{2}:\d{2}[.,]\d{3})"           # end timestamp
        r"\s*\n(.+?)(?=\n\n|\Z)",                  # text (lazy)
        re.DOTALL
    )

    for match in block_pattern.finditer(content):
        start_raw, end_raw, text_raw = match.groups()
        start = _parse_timestamp(start_raw)
        end = _parse_timestamp(end_raw)
        text = " ".join(text_raw.strip().splitlines())
        cues.append(SubtitleCue(start=start, end=end, text=text))

    return cues
# END_BLOCK_PARSE_SRT


def _parse_timestamp(ts: str) -> float:
    """Convert HH:MM:SS.mmm (or with comma) to seconds as float."""
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
    else:
        h, m, s = "0", parts[0], parts[1]
    return int(h) * 3600 + int(m) * 60 + float(s)


def align_cues_to_segments(
    segments: list[SlideSegment],
    cues: list[SubtitleCue],
) -> list[SlideSegment]:
    # START_CONTRACT: align_cues_to_segments
    #   PURPOSE: Assign subtitle cues to slide segments based on timestamp overlap
    #   INPUTS: { segments: list[SlideSegment], cues: list[SubtitleCue] }
    #   OUTPUTS: list[SlideSegment] with subtitle_cues and transcript filled
    #   SIDE_EFFECTS: none
    #   LINKS: M-SUBTITLES
    # END_CONTRACT: align_cues_to_segments

    # START_BLOCK_ALIGN
    for seg in segments:
        seg.subtitle_cues = []
        seg.transcript = ""

    for cue in cues:
        # Find the segment that contains the cue start (or overlaps)
        for seg in segments:
            # Cue overlaps segment if cue.start < seg.end and cue.end > seg.start
            if cue.start < seg.end and cue.end > seg.start:
                seg.subtitle_cues.append(cue)
                break  # assign to first matching segment

    # Build transcript text per segment
    for seg in segments:
        seg.subtitle_cues.sort(key=lambda c: c.start)
        seg.transcript = " ".join(c.text for c in seg.subtitle_cues)

    logger.info(
        f"[Subtitles][align_cues_to_segments] Aligned | "
        f"segments={len(segments)} cues={len(cues)}"
    )
    return segments
    # END_BLOCK_ALIGN
