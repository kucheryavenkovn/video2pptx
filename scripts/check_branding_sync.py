#!/usr/bin/env python3
"""Verify branding_rc.py is in sync with branding.qrc and PNG assets.

Exit 0 = up to date.  Exit 1 = out of sync.
"""

import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
QRC = REPO / "src" / "video2pptx" / "gui" / "resources" / "branding.qrc"
RC_PY = REPO / "src" / "video2pptx" / "gui" / "resources" / "branding_rc.py"
ASSETS = [
    REPO / "assets" / "branding" / "Video2PPTX-logo.png",
    REPO / "assets" / "branding" / "Video2PPTX-icon.png",
]


def compute_digest() -> str:
    h = hashlib.sha256()
    h.update(QRC.read_bytes())
    for a in ASSETS:
        h.update(a.read_bytes())
    return h.hexdigest()


def main() -> int:
    for f in [QRC] + ASSETS:
        if not f.is_file():
            print(f"MISSING: {f}")
            return 1
    if not RC_PY.is_file():
        print(f"MISSING: {RC_PY} — run pyside6-rcc to regenerate")
        return 1

    expected = compute_digest()
    rc_text = RC_PY.read_text(encoding="utf-8")
    stored = ""
    for line in rc_text.splitlines():
        if line.startswith("# input_hash:"):
            stored = line.split(":", 1)[1].strip()
            break

    if not stored:
        print(f"ERROR: {RC_PY} missing # input_hash marker — regenerate")
        return 1

    if expected != stored:
        print("OUT OF SYNC: branding inputs changed since branding_rc.py was generated")
        print(f"  expected: {expected}")
        print(f"  stored:   {stored}")
        print("Run: pyside6-rcc src/video2pptx/gui/resources/branding.qrc -o src/video2pptx/gui/resources/branding_rc.py")
        print("  Then append: # input_hash:<hash>")
        return 1

    print("OK: branding_rc.py is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
