# FILE: src/video2pptx/gui/controllers/__init__.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Barrel module exporting all GUI controller classes.
#   SCOPE: Re-export ProjectController, PipelineController, TimelineController
#   DEPENDS: video2pptx.gui.controllers.project_controller
#   LINKS: M-GUI-PROJECT-CTRL, M-GUI-PIPELINE-CTRL, M-GUI-TIMELINE-CTRL
#   ROLE: BARREL
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ProjectController - create/open/save/close project lifecycle via ApplicationServices
# END_MODULE_MAP

from __future__ import annotations

from video2pptx.gui.controllers.project_controller import ProjectController

__all__ = [
    "ProjectController",
]
