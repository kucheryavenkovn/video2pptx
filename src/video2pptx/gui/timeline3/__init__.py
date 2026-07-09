# FILE: src/video2pptx/gui/timeline3/__init__.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Multi-track timeline (DaVinci-like) with zoom/pan, QGraphicsView-based. Tracks: slides, markers, subtitles, waveform.
#   SCOPE: Export TimelineWidget — full replacement for TimelineV2Widget
#   DEPENDS: PySide6
#   LINKS: M-GUI-TIMELINE3
#   ROLE: BARREL
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT

from video2pptx.gui.timeline3.widget import TimelineWidget

__all__ = ["TimelineWidget"]
