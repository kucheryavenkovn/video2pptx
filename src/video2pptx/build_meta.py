# FILE: src/video2pptx/build_meta.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Build-time injected metadata (commit SHA, build type).
#            Overwritten by CI/CD pipeline during packaging.
#            Falls back to empty values in dev/source mode.
#   DEPENDS: none
#   LINKS: M-APP-BUILD-META, M-APP-IDENTITY
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   BUILD_META - dict with commit_sha, build_type, packaging_tool
# END_MODULE_MAP

from __future__ import annotations

BUILD_META: dict[str, str] = {
    "commit_sha": "",
    "build_type": "source",
    "packaging_tool": "",
}
