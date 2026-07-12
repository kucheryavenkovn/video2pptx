# FILE: src/video2pptx/adapters/legacy_exporter.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Wrap old markdown/pptx export functions behind PresentationExporterPort
#   SCOPE: LegacyExporter.export — produce titled deck.md or deck.pptx from slides data
#   DEPENDS: video2pptx.application.ports.presentation_exporter, video2pptx.markdown_export,
#            video2pptx.pptx_export, video2pptx.models
#   LINKS: M-PORT-EXPORT, M-ADAPTERS
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   LegacyExporter - adapt legacy Markdown/PPTX export to PresentationExporterPort
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Complete Phase 16 MCP port adapter integration
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path
from typing import Any

from video2pptx.application.ports.presentation_exporter import (
    ExportOutput,
    PresentationExporterPort,
)
from video2pptx.markdown_export import export_to_markdown
from video2pptx.models import SlidesDocument
from video2pptx.pptx_export import export_to_pptx


class LegacyExporter(PresentationExporterPort):
    """Produce export artifact on disk from slides data dicts.

    No project state files are modified — only the output artifact
    (deck.md or deck.pptx) and any helper files are created.
    """

    def export(
        self,
        slides_data: list[dict[str, Any]],
        output_path: str,
        *,
        format: str = "markdown",
        title: str = "Presentation",
    ) -> ExportOutput:
        output = Path(output_path)
        artifacts_root = output.parent

        doc = SlidesDocument(
            video={"path": "", "duration": 0, "width": 1, "height": 1, "fps": 0},
            slides=[dict(item) for item in slides_data],
        )

        if format == "markdown":
            export_to_markdown(
                doc,
                output,
                slides_dir=artifacts_root,
                title=title,
            )
        elif format == "pptx":
            export_to_pptx(
                doc,
                output,
                slides_dir=artifacts_root,
                title=title,
            )
        else:
            raise ValueError(f"Unsupported export format: {format}")

        return ExportOutput(
            format=format,
            output_path=str(output),
            slide_count=len(slides_data),
        )
