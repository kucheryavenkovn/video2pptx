# FILE: src/video_slide_md/models.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Pydantic data models for slides document
#   SCOPE: All data structures: VideoInfo, Roi, SubtitleCue, SlideSegment, SlidesDocument
#   DEPENDS: pydantic
#   LINKS: M-MODELS
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT

from pydantic import BaseModel, Field
