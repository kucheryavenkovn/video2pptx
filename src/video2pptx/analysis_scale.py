# FILE: src/video2pptx/analysis_scale.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Pure analysis-resolution policy — downscale frames for detection features without changing screenshot export resolution
#   SCOPE: scale_for_analysis, normalize_analysis_max_side
#   DEPENDS: numpy, opencv-python
#   LINKS: M-ANALYSIS-SCALE, V-M-ANALYSIS-SCALE
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   scale_for_analysis - downscale RGB frame to analysis_max_side (INTER_AREA); identity if None/smaller
#   normalize_analysis_max_side - coerce 0/negative/None to None for config callers
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Phase 19.1/19.2 initial analysis scale helper
# END_CHANGE_SUMMARY

from __future__ import annotations

import cv2
import numpy as np


def normalize_analysis_max_side(value: int | None) -> int | None:
    # START_CONTRACT: normalize_analysis_max_side
    #   PURPOSE: Coerce unset/zero analysis_max_side to None (native identity)
    #   INPUTS: { value: int|None }
    #   OUTPUTS: { int|None — positive max side or None for identity }
    #   SIDE_EFFECTS: none
    #   LINKS: M-ANALYSIS-SCALE
    #   NOTES: Does not enforce product custom range [240,2160]; that is validate_custom_max_side.
    #          Runtime scale path treats any positive int as a max side (no silent clamp to 480).
    # END_CONTRACT: normalize_analysis_max_side
    if value is None or value <= 0:
        return None
    return int(value)


def scale_for_analysis(
    image: np.ndarray,
    max_side: int | None,
) -> tuple[np.ndarray, float]:
    # START_CONTRACT: scale_for_analysis
    #   PURPOSE: Downscale RGB frame for Pass1 feature extraction; never upscale
    #   INPUTS: { image: np.ndarray RGB HxWxC, max_side: int|None }
    #   OUTPUTS: { (scaled_image, scale_factor) — scale_factor = out_long / in_long }
    #   SIDE_EFFECTS: none (returns view or new array; does not mutate when identity)
    #   LINKS: M-ANALYSIS-SCALE, V-M-ANALYSIS-SCALE
    # END_CONTRACT: scale_for_analysis

    # START_BLOCK_IDENTITY
    side = normalize_analysis_max_side(max_side)
    if side is None:
        return image, 1.0
    if image is None or image.size == 0:
        return image, 1.0
    h, w = image.shape[:2]
    if h <= 0 or w <= 0:
        return image, 1.0
    long_side = max(h, w)
    if long_side <= side:
        return image, 1.0
    # END_BLOCK_IDENTITY

    # START_BLOCK_DOWNSCALE
    scale = side / float(long_side)
    if w >= h:
        new_w = side
        new_h = max(1, int(round(h * scale)))
    else:
        new_h = side
        new_w = max(1, int(round(w * scale)))
    scaled = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    scale_factor = max(new_h, new_w) / float(long_side)
    return scaled, scale_factor
    # END_BLOCK_DOWNSCALE
