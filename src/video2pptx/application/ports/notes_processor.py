# FILE: src/video2pptx/application/ports/notes_processor.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Port for processing slide transcripts from subtitle cues without aggregate mutation.
#   SCOPE: NotesOutput, NotesProcessorPort Protocol
#   DEPENDS: none
#   LINKS: M-PORT-NOTES, V-REF-APP-SERVICES
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   NotesOutput - immutable result with processed notes per slide UID
#   NotesProcessorPort - Protocol for computing notes from slide data and subtitles
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add notes processor port and output DTO
# END_CHANGE_SUMMARY

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class NotesOutput:
    notes_by_uid: dict[str, str] = field(default_factory=dict)
    llm_descriptions_by_uid: dict[str, str | None] = field(default_factory=dict)
    raw_cues_preserved: bool = True


class NotesProcessorPort(Protocol):
    """Port for computing speaker notes from slide intervals and subtitles."""

    def process(
        self,
        slides_data: list[dict[str, Any]],
        subtitles_path: str,
        *,
        mode: str = "basic",
    ) -> NotesOutput:
        ...
