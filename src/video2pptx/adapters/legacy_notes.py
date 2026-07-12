# FILE: src/video2pptx/adapters/legacy_notes.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Wrap old process_notes pipeline behind NotesProcessorPort
#   SCOPE: LegacyNotesProcessor.process — compute notes from slides_data and subtitles
#   DEPENDS: video2pptx.application.ports.notes_processor, video2pptx.notes_processor,
#            video2pptx.subtitles, video2pptx.models
#   LINKS: M-PORT-NOTES, M-ADAPTERS
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   LegacyNotesProcessor - adapt legacy subtitle notes processing to NotesProcessorPort
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Complete Phase 16 MCP port adapter integration
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path
from typing import Any

from video2pptx.application.ports.notes_processor import NotesOutput, NotesProcessorPort
from video2pptx.models import SlideSegment
from video2pptx.notes_processor import process_notes
from video2pptx.subtitles import align_cues_to_segments, parse_subtitles


class LegacyNotesProcessor(NotesProcessorPort):
    """Compute cleaned speaker notes from slides data and subtitle file.

    No files are written. Returns notes and optional LLM descriptions keyed by slide UID.
    """

    def process(
        self,
        slides_data: list[dict[str, Any]],
        subtitles_path: str,
        *,
        mode: str = "basic",
    ) -> NotesOutput:
        segments = [SlideSegment(**data) for data in slides_data]

        if subtitles_path:
            raw = Path(subtitles_path).read_text(encoding="utf-8")
            fmt = "srt" if subtitles_path.lower().endswith(".srt") else "vtt"
            cues = parse_subtitles(raw, format=fmt)
            align_cues_to_segments(segments, cues)
        else:
            cues = []

        transcripts_by_uid: dict[str, str] = {}
        notes_by_uid: dict[str, str] = {}
        llm_descriptions_by_uid: dict[str, str | None] = {}

        for seg in segments:
            cleaned = process_notes(seg, mode=mode)
            transcripts_by_uid[seg.uid] = seg.transcript
            notes_by_uid[seg.uid] = cleaned
            llm_descriptions_by_uid[seg.uid] = getattr(seg, "llm_description", None)

        return NotesOutput(
            transcripts_by_uid=transcripts_by_uid,
            notes_by_uid=notes_by_uid,
            llm_descriptions_by_uid=llm_descriptions_by_uid,
            raw_cues_preserved=bool(cues),
        )
