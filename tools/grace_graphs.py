#!/usr/bin/env python3
# FILE: tools/grace_graphs.py
# PURPOSE: Wrapper → grace-atlas submodule graph generator (Graphviz + Mermaid).
"""Run: python tools/grace_graphs.py --project-root ."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> int:
    script = Path(__file__).resolve().parent / "grace_atlas" / "tools" / "grace_graphs" / "generate_grace_graphs.py"
    if not script.is_file():
        print(
            "Missing generator in submodule:\n"
            f"  expected: {script}\n"
            "  git submodule update --init --recursive\n"
            "  # https://github.com/kucheryavenkovn/grace-atlas",
            file=sys.stderr,
        )
        return 2
    sys.argv = [str(script), *sys.argv[1:]]
    runpy.run_path(str(script), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
