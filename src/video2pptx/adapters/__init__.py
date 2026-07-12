# FILE: src/video2pptx/adapters/__init__.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Concrete port adapters wrapping legacy pipeline code behind Phase 16 Protocols.
#   SCOPE: Barrel — re-export all legacy adapter classes
#   DEPENDS: video2pptx.adapters.legacy_preview, legacy_detector, legacy_aligner, legacy_notes, legacy_exporter
#   LINKS: M-ADAPTERS
#   ROLE: BARREL
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   LegacyPreviewAnalyzer - preview analyzer adapter
#   LegacySlideDetector - slide detector adapter
#   LegacyAligner - subtitle alignment adapter
#   LegacyNotesProcessor - notes processor adapter
#   LegacyExporter - presentation exporter adapter
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Export concrete Phase 16 legacy port adapters
# END_CHANGE_SUMMARY

from video2pptx.adapters.legacy_aligner import LegacyAligner
from video2pptx.adapters.legacy_detector import LegacySlideDetector
from video2pptx.adapters.legacy_exporter import LegacyExporter
from video2pptx.adapters.legacy_notes import LegacyNotesProcessor
from video2pptx.adapters.legacy_preview import LegacyPreviewAnalyzer

__all__ = [
    "LegacyPreviewAnalyzer",
    "LegacySlideDetector",
    "LegacyAligner",
    "LegacyNotesProcessor",
    "LegacyExporter",
]
