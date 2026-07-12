# FILE: src/video2pptx/bootstrap/__init__.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Barrel export for bootstrap modules.
#   SCOPE: Export ApplicationServices
#   DEPENDS: video2pptx.bootstrap.application
#   LINKS: M-APP-BOOTSTRAP
#   ROLE: BARREL
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ApplicationServices - neutral composition root for transport adapters
# END_MODULE_MAP

from video2pptx.bootstrap.application import ApplicationServices

__all__ = ["ApplicationServices"]
