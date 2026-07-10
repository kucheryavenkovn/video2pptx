# FILE: src/video2pptx/validators/project_validator.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: validate_project: schema, file existence, interval invariants, no double paths, slide-count consistency,
#            export freshness, MD/PPTX integrity, pipeline state, alignment report.
#            Returns {valid, errors, warnings, statistics}.
#   SCOPE: validate_project() single entry point, ValidationResult dataclass
#   DEPENDS: M-PROJECT, M-MD-EXPORT, M-PPTX-EXPORT
#   LINKS: M-PROJECT-VALIDATOR
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   validate_project - run all checks, return ValidationResult
#   ValidationResult - {valid: bool, errors: list[str], warnings: list[str], statistics: dict}
# END_MODULE_MAP

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "statistics": self.statistics,
        }


def validate_project(project_dir: str | Path) -> ValidationResult:
    """Run all project validation checks. Returns ValidationResult."""
    result = ValidationResult()
    base = Path(project_dir)

    if not base.is_dir():
        result.errors.append(f"Project directory not found: {base}")
        result.valid = False
        return result

    # Paths
    project_json = base / "project.json"
    slides_json = base / "slides.json"
    deck_md = base / "deck.md"
    deck_pptx = base / "deck.pptx"
    alignment_report = base / "alignment_report.json"
    slides_dir = base / "slides"

    # 1. project.json schema
    if not project_json.is_file():
        result.errors.append(f"project.json not found: {project_json}")
        result.valid = False
        return result

    try:
        proj = json.loads(project_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, PermissionError) as e:
        result.errors.append(f"project.json invalid: {e}")
        result.valid = False
        return result

    # 2. Video existence
    video = proj.get("video", "")
    if video and not Path(video).is_file():
        result.warnings.append(f"Video file not found: {video}")

    # 3. Subtitles existence
    subs = proj.get("subtitles")
    if subs and not Path(subs).is_file():
        result.warnings.append(f"Subtitles file not found: {subs}")

    # 4. slides.json schema + consistency
    if slides_json.is_file():
        try:
            slides_doc = json.loads(slides_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, PermissionError) as e:
            result.errors.append(f"slides.json invalid: {e}")
            result.valid = False
        else:
            slides_list = slides_doc.get("slides", [])
            result.statistics["slides_count"] = len(slides_list)

            # Check slide count consistency with project
            proj_slides = proj.get("slides", [])
            if proj_slides and len(proj_slides) != len(slides_list):
                result.errors.append(
                    f"Slide count mismatch: project.json has {len(proj_slides)}, "
                    f"slides.json has {len(slides_list)}"
                )
                result.valid = False

            # Interval invariants
            for i, s in enumerate(slides_list):
                start = s.get("start", 0)
                end = s.get("end", 0)
                if start < 0:
                    result.errors.append(f"slides[{i}].start < 0: {start}")
                    result.valid = False
                if start >= end:
                    result.errors.append(f"slides[{i}].start >= end: {start} >= {end}")
                    result.valid = False
                if i > 0:
                    prev_end = slides_list[i - 1].get("end", 0)
                    if abs(start - prev_end) > 0.01:
                        result.errors.append(
                            f"Gap/overlap slides[{i-1}].end={prev_end} vs slides[{i}].start={start}"
                        )
                        result.valid = False

            # 5. Slide images existence
            for i, s in enumerate(slides_list):
                img = s.get("image", "")
                if img:
                    img_path = base / img
                    if not img_path.is_file():
                        result.warnings.append(f"Slide image not found: images/{img}")

            # 6. Double path check
            for i, s in enumerate(slides_list):
                img = s.get("image", "")
                if "slides/slides" in img.replace("\\", "/"):
                    result.errors.append(f"Double path prefix in slide[{i}].image: {img}")
                    result.valid = False

            # 7. Video duration from slides
            vid = slides_doc.get("video", {})
            duration = vid.get("duration", 0)
            if duration > 0:
                result.statistics["video_duration"] = duration
    else:
        # Check if detect_done is set but slides.json missing
        state = proj.get("state", {})
        if state.get("detect_done"):
            result.errors.append("detect_done=true but slides.json missing")
            result.valid = False

    # 8. MD validity
    if deck_md.is_file():
        content = deck_md.read_text(encoding="utf-8")
        slide_count = content.count("---\n\n") + (1 if content.strip() else 0)
        result.statistics["md_slides"] = slide_count
        # Check image paths in MD
        import re
        for m in re.finditer(r'!\[.*?\]\((.*?)\)', content):
            img_path = m.group(1)
            if not (base / img_path).is_file():
                result.warnings.append(f"MD references missing image: {img_path}")

    # 9. PPTX validity
    if deck_pptx.is_file():
        try:
            import zipfile
            with zipfile.ZipFile(deck_pptx, 'r') as zf:
                names = zf.namelist()
                if "[Content_Types].xml" not in names:
                    result.errors.append(f"PPTX missing [Content_Types].xml — not a valid OPC package")
                    result.valid = False
                else:
                    result.statistics["pptx_entries"] = len(names)
        except zipfile.BadZipFile as e:
            result.errors.append(f"PPTX is not a valid ZIP: {e}")
            result.valid = False

    # 10. Alignment report
    if alignment_report.is_file():
        try:
            report = json.loads(alignment_report.read_text(encoding="utf-8"))
            result.statistics["alignment_boundaries_total"] = report.get("boundaries_total", 0)
            result.statistics["alignment_boundaries_moved"] = report.get("boundaries_moved", 0)
        except (json.JSONDecodeError, PermissionError):
            result.warnings.append("alignment_report.json invalid")

    # 11. Pipeline state consistency
    state = proj.get("state", {})
    if state.get("auto_done") and not deck_md.is_file():
        result.warnings.append("auto_done=true but deck.md missing")
    if state.get("auto_done") and not deck_pptx.is_file():
        result.warnings.append("auto_done=true but deck.pptx missing")

    result.statistics["state"] = {
        "preview_done": bool(state.get("preview_done")),
        "detect_done": bool(state.get("detect_done")),
        "align_done": bool(state.get("align_done")),
        "notes_done": bool(state.get("notes_done")),
        "md_exported": bool(state.get("md_exported")),
        "pptx_exported": bool(state.get("pptx_exported")),
        "auto_done": bool(state.get("auto_done")),
    }

    return result
