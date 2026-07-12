# FILE: src/video2pptx/paths.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Centralized artifact path resolution and time formatting utilities
#   SCOPE: resolve slide image paths relative to a document/project dir; format seconds as timecodes
#   DEPENDS: pathlib
#   LINKS: M-PATHS
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   resolve_artifact_path - canonical resolver for slide images stored in slides.json
#   format_time - format seconds as H:MM:SS or M:SS string
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path, PurePosixPath


def resolve_artifact_path(
    base_dir: str | Path | None,
    artifact_path: str,
) -> Path:
    # START_CONTRACT: resolve_artifact_path
    #   PURPOSE: Resolve a slide image path stored in slides.json against a base directory,
    #            correctly handling bare filenames, relative paths with slides/ prefix,
    #            absolute paths, and cross-platform separators.
    #   INPUTS: {
    #       base_dir: str|Path|None — the directory containing slides.json (or None for cwd),
    #       artifact_path: str — the stored image value, e.g. "slide_001.png", "slides/slide_001.png", or abs path
    #   }
    #   OUTPUTS: Path — absolute or base_dir-relative path that should exist on disk
    #   SIDE_EFFECTS: none
    #   LINKS: M-PATHS
    # END_CONTRACT: resolve_artifact_path

    if not artifact_path:
        return Path()

    p = Path(*PurePosixPath(artifact_path.replace("\\", "/")).parts)

    # Absolute path — use as-is
    if p.is_absolute():
        return p

    base = Path(base_dir) if base_dir else Path()

    # The stored value may already be "slides/slide_001.png" (full relative path)
    # or just "slide_001.png" (bare filename). The canonical layout is base_dir/slides/*.png.
    # If the path already contains a "slides" component, join against base directly.
    parts = p.parts
    if parts and parts[0] == "slides":
        return base / p

    # Bare filename — assume it lives under base_dir/slides/
    return base / "slides" / p


def resolve_markdown_image_path(
    base_dir: str | Path | None,
    artifact_path: str,
) -> str:
    # START_CONTRACT: resolve_markdown_image_path
    #   PURPOSE: Produce a POSIX-style relative path suitable for Markdown image links,
    #            avoiding the "slides/slides/" double-prefix bug.
    #   INPUTS: {
    #       base_dir: str|Path|None — directory containing deck.md (output dir),
    #       artifact_path: str — stored image value from slides.json
    #   }
    #   OUTPUTS: str — POSIX relative path, e.g. "slides/slide_001.png"
    #   SIDE_EFFECTS: none
    #   LINKS: M-PATHS
    # END_CONTRACT: resolve_markdown_image_path

    if not artifact_path:
        return ""

    p = Path(artifact_path)

    # If absolute, try to make relative to base_dir
    if p.is_absolute() and base_dir is not None:
        try:
            rel = p.relative_to(Path(base_dir).resolve())
            return PurePosixPath(*rel.parts).as_posix()
        except ValueError:
            # Outside base_dir — return as-is
            return PurePosixPath(*p.parts).as_posix()

    if p.is_absolute():
        return PurePosixPath(*p.parts).as_posix()

    parts = p.parts
    if parts and parts[0] == "slides":
        return PurePosixPath(*parts).as_posix()

    # Bare filename — prepend slides/
    return f"slides/{p.as_posix()}"


def format_time(seconds: float) -> str:
    # START_CONTRACT: format_time
    #   PURPOSE: Format seconds as a compact timecode string (H:MM:SS or M:SS)
    #   INPUTS: { seconds: float }
    #   OUTPUTS: str
    #   SIDE_EFFECTS: none
    #   LINKS: M-PATHS
    # END_CONTRACT: format_time

    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
