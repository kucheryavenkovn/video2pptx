# FILE: src/video2pptx/roi.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: ROI management — crop slide region, mask ignore regions
#   SCOPE: Parse ROI string (auto/full/x1,y1,x2,y2), crop frame, apply ignore masks
#   DEPENDS: numpy, opencv-python, models, loguru
#   LINKS: M-ROI
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   SlideRegion - region descriptor with crop and mask methods
#   parse_roi - parse ROI string into SlideRegion
#   apply_roi - crop frame to slide region
#   apply_ignore_masks - apply ignore regions (zero out)
# END_MODULE_MAP

from __future__ import annotations

import re
from collections.abc import Sequence

import numpy as np
from loguru import logger

from video2pptx.models import Roi


class SlideRegion:
    # START_CONTRACT: SlideRegion
    #   PURPOSE: Region descriptor with crop and mask methods for slide area
    #   INPUTS: { roi: Roi|None, ignore_rois: list[Roi], frame_shape: tuple[int,int,int] }
    #   OUTPUTS: SlideRegion
    #   SIDE_EFFECTS: none
    #   LINKS: M-ROI
    # END_CONTRACT: SlideRegion

    def __init__(
        self,
        roi: Roi | None = None,
        ignore_rois: list[Roi] | None = None,
    ):
        self.roi = roi
        self.ignore_rois = ignore_rois or []

    def crop(self, frame: np.ndarray) -> np.ndarray:
        # START_CONTRACT: crop
        #   PURPOSE: Crop frame to slide ROI, or return full frame if no ROI
        #   INPUTS: { frame: np.ndarray }
        #   OUTPUTS: np.ndarray — cropped region
        #   SIDE_EFFECTS: none
        #   LINKS: M-ROI
        # END_CONTRACT: crop

        if self.roi is None:
            return frame
        h, w = frame.shape[:2]
        x1 = max(0, self.roi.x1)
        y1 = max(0, self.roi.y1)
        x2 = min(w, self.roi.x2)
        y2 = min(h, self.roi.y2)
        return frame[y1:y2, x1:x2]

    def apply_masks(self, frame: np.ndarray) -> np.ndarray:
        # START_CONTRACT: apply_masks
        #   PURPOSE: Zero out ignore regions in the frame so they don't affect comparison
        #   INPUTS: { frame: np.ndarray }
        #   OUTPUTS: np.ndarray — frame with ignore regions blacked out
        #   SIDE_EFFECTS: none
        #   LINKS: M-ROI
        # END_CONTRACT: apply_masks

        if not self.ignore_rois:
            return frame
        result = frame.copy()
        h, w = frame.shape[:2]
        for region in self.ignore_rois:
            x1 = max(0, region.x1)
            y1 = max(0, region.y1)
            x2 = min(w, region.x2)
            y2 = min(h, region.y2)
            result[y1:y2, x1:x2] = 0
        return result

    def process(self, frame: np.ndarray) -> np.ndarray:
        # START_CONTRACT: process
        #   PURPOSE: Apply crop then masks in one call
        #   INPUTS: { frame: np.ndarray }
        #   OUTPUTS: np.ndarray
        #   SIDE_EFFECTS: none
        #   LINKS: M-ROI
        # END_CONTRACT: process

        frame = self.crop(frame)
        frame = self.apply_masks(frame)
        return frame


def parse_roi(value: str | Sequence[int] | None, frame_width: int = 0, frame_height: int = 0) -> SlideRegion:
    # START_CONTRACT: parse_roi
    #   PURPOSE: Parse ROI string or int list into SlideRegion
    #   INPUTS: { value: str|list[int]|None, frame_width, frame_height }
    #   OUTPUTS: SlideRegion
    #   SIDE_EFFECTS: none
    #   LINKS: M-ROI
    # END_CONTRACT: parse_roi

    # START_BLOCK_PARSE_ROI
    if value is None:
        logger.debug("[ROI][parse_roi] No ROI specified, using full frame")
        return SlideRegion(roi=None)

    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("auto", "full"):
            logger.debug(f"[ROI][parse_roi] ROI mode={v}, using full frame")
            return SlideRegion(roi=None)

        try:
            parts = [int(x) for x in re.split(r"[\s,]+", v)]
            if len(parts) == 4:
                roi = Roi(x1=parts[0], y1=parts[1], x2=parts[2], y2=parts[3])
                logger.info(f"[ROI][parse_roi] Manual ROI | roi=({roi.as_tuple()})")
                return SlideRegion(roi=roi)
        except (ValueError, IndexError):
            pass

        logger.warning(f"[ROI][parse_roi] Invalid ROI format: {value}, falling back to full frame")
        return SlideRegion(roi=None)

    if isinstance(value, (list, tuple)) and len(value) == 4:
        roi = Roi(x1=int(value[0]), y1=int(value[1]), x2=int(value[2]), y2=int(value[3]))
        logger.info(f"[ROI][parse_roi] Manual ROI from list | roi=({roi.as_tuple()})")
        return SlideRegion(roi=roi)

    logger.warning(f"[ROI][parse_roi] Invalid ROI value: {value}, using full frame")
    return SlideRegion(roi=None)
    # END_BLOCK_PARSE_ROI


def parse_ignore_rois(values: list[list[int]] | None) -> list[Roi]:
    # START_CONTRACT: parse_ignore_rois
    #   PURPOSE: Parse list of ignore regions into Roi objects
    #   INPUTS: { values: list[list[int]] }
    #   OUTPUTS: list[Roi]
    #   SIDE_EFFECTS: none
    #   LINKS: M-ROI
    # END_CONTRACT: parse_ignore_rois

    if not values:
        return []
    regions = []
    for v in values:
        if len(v) == 4:
            regions.append(Roi(x1=v[0], y1=v[1], x2=v[2], y2=v[3]))
    if regions:
        logger.info(f"[ROI][parse_ignore_rois] Ignore regions | count={len(regions)}")
    return regions
