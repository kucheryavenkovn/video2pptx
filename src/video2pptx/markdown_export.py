# FILE: src/video2pptx/markdown_export.py
# VERSION: 0.2.0
# START_MODULE_CONTRACT
#   PURPOSE: Export slides.json to Marp-formatted Markdown presentation
#   SCOPE: Generate deck.md with slide images, transcript snippets, Marp front-matter,
#          configurable image background, transcript location (body/notes/none), timecodes
#   DEPENDS: models, paths, pathlib, loguru
#   LINKS: M-MD-EXPORT
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   export_to_markdown - write deck.md with all slides
#   render_slide - produce one Marp slide section
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

from loguru import logger

from video2pptx.models import SlideSegment, SlidesDocument
from video2pptx.paths import format_time, resolve_markdown_image_path


def export_to_markdown(
    document: SlidesDocument,
    output_path: Path,
    slides_dir: str | Path | None = None,
    title: str = "Presentation",
    image_as_background: bool = True,
    transcript_location: str = "body",
    include_timecodes: bool = True,
) -> Path:
    # START_CONTRACT: export_to_markdown
    #   PURPOSE: Write Marp-formatted deck.md from SlidesDocument
    #   INPUTS: {
    #       document: SlidesDocument,
    #       output_path: Path — target deck.md,
    #       slides_dir: str|Path|None — base dir for resolving slide images (default: output_path.parent),
    #       title: str,
    #       image_as_background: bool — use Marp backgroundImage directive instead of inline image,
    #       transcript_location: str — "body" | "comment" | "none",
    #       include_timecodes: bool
    #   }
    #   OUTPUTS: Path to deck.md
    #   SIDE_EFFECTS: Creates/writes deck.md
    #   LINKS: M-MD-EXPORT
    # END_CONTRACT: export_to_markdown

    if transcript_location not in ("body", "comment", "none"):
        raise ValueError(
            f"transcript_location must be 'body', 'comment', or 'none', got: {transcript_location!r}"
        )

    base_dir = Path(slides_dir) if slides_dir else output_path.parent

    # START_BLOCK_MD_BUILD
    lines: list[str] = []
    lines.append("---")
    lines.append("marp: true")
    lines.append(f'title: "{_escape_yaml(title)}"')
    lines.append("theme: uncover")
    lines.append("class:")
    lines.append("  - lead")
    lines.append("  - invert")
    lines.append("---")
    lines.append("")

    for seg in document.slides:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.extend(
            render_slide(
                seg,
                base_dir=base_dir,
                image_as_background=image_as_background,
                transcript_location=transcript_location,
                include_timecodes=include_timecodes,
            )
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(
        f"[MarkdownExport][export_to_markdown] Deck written | "
        f"path={output_path} slides={len(document.slides)}"
    )
    return output_path
    # END_BLOCK_MD_BUILD


def render_slide(
    seg: SlideSegment,
    base_dir: str | Path | None = None,
    image_as_background: bool = True,
    transcript_location: str = "body",
    include_timecodes: bool = True,
) -> list[str]:
    # START_CONTRACT: render_slide
    #   PURPOSE: Produce Marp slide section lines
    #   INPUTS: { seg: SlideSegment, base_dir, image_as_background, transcript_location, include_timecodes }
    #   OUTPUTS: list[str] - slide lines
    #   SIDE_EFFECTS: none
    #   LINKS: M-MD-EXPORT
    # END_CONTRACT: render_slide

    lines: list[str] = []

    # Slide image
    if seg.image:
        img_rel = resolve_markdown_image_path(base_dir, seg.image)
        if img_rel:
            if image_as_background:
                lines.append(f'![bg]({img_rel})')
            else:
                lines.append(f"![Slide {seg.index}]({img_rel})")
            lines.append("")

    # Timecodes
    if include_timecodes:
        lines.append(f"> {format_time(seg.start)} – {format_time(seg.end)}")

    # Transcript
    transcript = (seg.transcript or "").strip()
    if transcript:
        if transcript_location == "body":
            lines.append("")
            lines.append(transcript)
        elif transcript_location == "comment":
            lines.append("")
            lines.append(f"<!-- {transcript} -->")

    # Warnings
    for warn in (seg.warnings or []):
        lines.append("")
        lines.append(f"> ⚠️ {warn}")

    return lines


def _escape_yaml(text: str) -> str:
    return text.replace('"', '\\"')


def _fmt_time(seconds: float) -> str:
    return format_time(seconds)
