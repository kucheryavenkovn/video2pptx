# FILE: src/video2pptx/application/ports/presentation_exporter.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Port for staging Markdown/PPTX output from immutable project snapshots.
#   SCOPE: ExportOutput, PresentationExporterPort Protocol
#   DEPENDS: none
#   LINKS: M-PORT-EXPORT, V-REF-APP-SERVICES
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ExportOutput - immutable result with artifact metadata (path, slide_count, image_count, warnings)
#   PresentationExporterPort - Protocol for staging Markdown or PPTX output
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Pass presentation title through the exporter port
#   v1.0.0 - Add presentation exporter port and output DTO
# END_CHANGE_SUMMARY

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ExportOutput:
    format: str  # "markdown" | "pptx"
    output_path: str
    slide_count: int = 0
    image_count: int = 0
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class PresentationExporterPort(Protocol):
    """Port for staging Markdown or PPTX output from immutable project snapshots."""

    def export(
        self,
        slides_data: list[dict[str, Any]],
        output_path: str,
        *,
        format: str = "markdown",
        title: str = "Presentation",
    ) -> ExportOutput:
        ...
