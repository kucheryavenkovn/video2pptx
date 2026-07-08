# FILE: src/video_slide_md/markdown_export.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Export slides.json to Marp-formatted Markdown presentation
#   SCOPE: Generate deck.md with slide images, transcript snippets, Marp front-matter
#   DEPENDS: models, pathlib, loguru
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

from video_slide_md.models import SlideSegment, SlidesDocument


def export_to_markdown(
    document: SlidesDocument,
    output_path: Path,
    slides_dir: str | Path = "slides",
    title: str = "Presentation",
) -> Path:
    # START_CONTRACT: export_to_markdown
    #   PURPOSE: Write Marp-formatted deck.md from SlidesDocument
    #   INPUTS: { document, output_path, slides_dir, title }
    #   OUTPUTS: Path to deck.md
    #   SIDE_EFFECTS: Creates/writes deck.md
    #   LINKS: M-MD-EXPORT
    # END_CONTRACT: export_to_markdown

    # START_BLOCK_MD_BUILD
    lines: list[str] = []
    lines.append("---")
    lines.append("marp: true")
    lines.append(f'title: "{title}"')
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
        lines.extend(render_slide(seg, slides_dir))

    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(
        f"[MarkdownExport][export_to_markdown] Deck written | "
        f"path={output_path} slides={len(document.slides)}"
    )
    return output_path
    # END_BLOCK_MD_BUILD


def render_slide(seg: SlideSegment, slides_dir: str | Path) -> list[str]:
    # START_CONTRACT: render_slide
    #   PURPOSE: Produce Marp slide section lines
    #   INPUTS: { seg: SlideSegment, slides_dir: str | Path }
    #   OUTPUTS: list[str] - slide lines
    #   SIDE_EFFECTS: none
    #   LINKS: M-MD-EXPORT
    # END_CONTRACT: render_slide

    lines: list[str] = []

    # Slide image
    if seg.image:
        img_rel = Path(slides_dir) / seg.image
        lines.append(f"![Slide {seg.index}]({img_rel.as_posix()})")
        lines.append("")

    # Timestamp info
    lines.append(f"> ⏱ {_fmt_time(seg.start)} – {_fmt_time(seg.end)}")

    # Transcript
    transcript = (seg.transcript or "").strip()
    if transcript:
        lines.append("")
        lines.append(transcript)

    # Warnings
    for warn in (seg.warnings or []):
        lines.append("")
        lines.append(f"> ⚠️ {warn}")

    return lines


def _fmt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
