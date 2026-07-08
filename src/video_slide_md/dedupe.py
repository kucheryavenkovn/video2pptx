# FILE: src/video_slide_md/dedupe.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Deduplicate adjacent slide segments via hash/SSIM/OCR similarity
#   SCOPE: Merge neighbour segments that represent the same slide, flag warnings
#   DEPENDS: models, imagehash, scikit-image
#   LINKS: M-DEDUPE
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
