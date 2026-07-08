# FILE: src/video_slide_md/cli.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Typer CLI entry point for video-slide-md
#   SCOPE: CLI command definitions (detect, export-md, debug, review)
#   DEPENDS: typer, rich, video_slide_md.config
#   LINKS: M-CLI
#   ROLE: SCRIPT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT

import typer

app = typer.Typer(name="video-slide-md")
