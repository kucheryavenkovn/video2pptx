# FILE: src/video_slide_md/debug_export.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Generate debug artifacts: diff_scores.csv, timeline plot, contact sheet
#   SCOPE: CSV export of diff scores, simple text-based timeline, image contact sheet
#   DEPENDS: models, pathlib, loguru, csv
#   LINKS: M-DEBUG-EXPORT
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   export_debug_csv - write diff_scores.csv
#   export_debug_report - write debug_report.txt summary
#   export_contact_sheet - combine representative images into a contact sheet (if PIL available)
# END_MODULE_MAP

from __future__ import annotations

import csv
from pathlib import Path

from loguru import logger

from video_slide_md.models import SlideSegment


def export_debug_csv(
    scores: list[float],
    timestamps: list[float],
    output_path: Path,
) -> Path:
    # START_CONTRACT: export_debug_csv
    #   PURPOSE: Write frame diff scores to CSV
    #   INPUTS: { scores: list[float], timestamps: list[float], output_path: Path }
    #   OUTPUTS: Path to CSV file
    #   SIDE_EFFECTS: Creates CSV file
    #   LINKS: M-DEBUG-EXPORT
    # END_CONTRACT: export_debug_csv

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "score"])
        for ts, sc in zip(timestamps, scores):
            writer.writerow([f"{ts:.3f}", f"{sc:.6f}"])

    logger.info(f"[DebugExport][export_debug_csv] Scores written | path={output_path} rows={len(scores)}")
    return output_path


def export_debug_report(
    segments: list[SlideSegment],
    video_path: str,
    output_path: Path,
) -> Path:
    # START_CONTRACT: export_debug_report
    #   PURPOSE: Write text summary report of segments
    #   INPUTS: { segments, video_path, output_path }
    #   OUTPUTS: Path to report file
    #   SIDE_EFFECTS: Creates text file
    #   LINKS: M-DEBUG-EXPORT
    # END_CONTRACT: export_debug_report

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        f.write(f"Debug Report: {video_path}\n")
        f.write(f"Total segments: {len(segments)}\n")
        f.write("=" * 60 + "\n\n")

        for seg in segments:
            f.write(f"Slide #{seg.index}\n")
            f.write(f"  Time: {seg.start:.2f}s – {seg.end:.2f}s (duration: {seg.duration:.2f}s)\n")
            f.write(f"  Representative: {seg.representative_timestamp:.2f}s\n")
            f.write(f"  Confidence: {seg.confidence:.2f}\n")
            f.write(f"  Image: {seg.image or '(none)'}\n")
            if seg.transcript:
                f.write(f"  Transcript: {seg.transcript[:100]}{'…' if len(seg.transcript) > 100 else ''}\n")
            f.write("\n")

    logger.info(f"[DebugExport][export_debug_report] Report written | path={output_path}")
    return output_path


def export_contact_sheet(
    segments: list[SlideSegment],
    frames: dict,
    output_path: Path,
    cols: int = 5,
) -> Path:
    # START_CONTRACT: export_contact_sheet
    #   PURPOSE: Create contact sheet image from representative frames (requires PIL)
    #   INPUTS: { segments, frames, output_path, cols }
    #   OUTPUTS: Path to image file (or warning if PIL not available)
    #   SIDE_EFFECTS: Creates image file if PIL available
    #   LINKS: M-DEBUG-EXPORT
    # END_CONTRACT: export_contact_sheet

    import warnings

    try:
        from PIL import Image
    except ImportError:
        warnings.warn("Pillow not installed — skipping contact sheet")
        logger.warning("[DebugExport][export_contact_sheet] Pillow not available, skipping")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Collect available images
    images: list[Image.Image] = []
    for seg in segments:
        img = frames.get(seg.representative_timestamp)
        if img is not None:
            img_pil = Image.fromarray(img)
            img_pil.thumbnail((200, 150))
            images.append(img_pil)

    if not images:
        warnings.warn("No images available for contact sheet")
        return output_path

    rows = (len(images) + cols - 1) // cols
    cell_w = images[0].width if images else 200
    cell_h = images[0].height if images else 150

    canvas = Image.new("RGB", (cols * cell_w, rows * cell_h), (32, 32, 32))

    for i, img in enumerate(images):
        x = (i % cols) * cell_w
        y = (i // cols) * cell_h
        canvas.paste(img, (x, y))

    canvas.save(output_path)
    logger.info(
        f"[DebugExport][export_contact_sheet] Contact sheet written | "
        f"path={output_path} images={len(images)}"
    )
    return output_path
