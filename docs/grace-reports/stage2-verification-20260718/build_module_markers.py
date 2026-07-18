"""Map modules to source files and extract real log markers.

For each module in knowledge-graph.xml:
- collect source paths (from <path> children)
- scan those files for logger calls matching the GRACE marker format
- extract the [Module][fn] or [Module][fn][BLOCK] prefix as candidate markers

Output: module-markers.json
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs"
REPORT_DIR = DOCS / "grace-reports" / "stage2-verification-20260718"


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


kg = ET.parse(DOCS / "knowledge-graph.xml").getroot()
modules = {}
for mod in kg.iter():
    mid = strip_ns(mod.tag)
    if not (mid.startswith("M-") and re.fullmatch(r"M-[A-Z0-9-]+", mid)):
        continue
    paths = []
    for child in mod.iter():
        if strip_ns(child.tag) == "path":
            txt = (child.text or "").strip()
            if txt:
                paths.append(txt)
    modules[mid] = {
        "name": mod.get("NAME") or "",
        "status": mod.get("STATUS") or "",
        "paths": paths,
    }

# Pattern for a logger call line containing a GRACE-style marker.
# Marker format: [Word][word] possibly followed by [BLOCK_NAME]
MARKER_RE = re.compile(r"(\[(?:[A-Za-z][A-Za-z0-9_]*)\]\[[A-Za-z_][A-Za-z0-9_]*\](?:\[[A-Z0-9_]+\])?)")
# Evidence-emission detection: line must look like logging call
EMIT_RE = re.compile(r"(logger\.|log\.|logging\.|console\.|tracer\.|trace\(|emit\(|\.(info|warn|warning|error|debug|trace)\s*\()")
COMMENT_RE = re.compile(r"^\s*(//|#|--|;+|\*)")


def extract_markers_from_file(filepath: Path) -> list[str]:
    if not filepath.exists():
        return []
    markers = []
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    for line in text.splitlines():
        if COMMENT_RE.match(line):
            continue
        if not EMIT_RE.search(line):
            continue
        for m in MARKER_RE.findall(line):
            if m not in markers:
                markers.append(m)
    return markers


result = {}
for mid, info in modules.items():
    file_markers = {}
    all_markers = []
    for rel in info["paths"]:
        p = ROOT / rel
        # handle directory paths
        if p.is_dir():
            for py in p.rglob("*.py"):
                ms = extract_markers_from_file(py)
                rel_py = str(py.relative_to(ROOT)).replace("\\", "/")
                if ms:
                    file_markers[rel_py] = ms
                    all_markers.extend(ms)
        elif p.suffix == ".py" or p.exists():
            ms = extract_markers_from_file(p)
            rel_p = str(p.relative_to(ROOT)).replace("\\", "/")
            if ms:
                file_markers[rel_p] = ms
                all_markers.extend(ms)
    # dedupe preserve order
    seen = set()
    unique = []
    for m in all_markers:
        if m not in seen:
            seen.add(m)
            unique.append(m)
    result[mid] = {
        "name": info["name"],
        "status": info["status"],
        "paths": info["paths"],
        "source_files_with_markers": file_markers,
        "markers": unique,
        "has_runtime_markers": len(unique) > 0,
    }

with open(REPORT_DIR / "module-markers.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

total = len(result)
with_markers = sum(1 for v in result.values() if v["has_runtime_markers"])
print(f"Modules: {total}")
print(f"Modules with real runtime markers: {with_markers}")
print(f"Modules without markers (need trace-assertions): {total - with_markers}")
print()
print("Sample markers (first 10 modules with markers):")
shown = 0
for mid, v in result.items():
    if v["has_runtime_markers"] and shown < 10:
        print(f"  {mid}: {v['markers'][:3]}")
        shown += 1
