#!/usr/bin/env python3
# FILE: tools/grace_atlas.py
# VERSION: 0.2.0
# START_MODULE_CONTRACT
#   PURPOSE: Host-repo wrapper for the grace-atlas git submodule under tools/grace_atlas.
#   SCOPE: path check, PYTHONPATH bootstrap, CLI dispatch
#   DEPENDS: tools/grace_atlas (submodule → https://github.com/kucheryavenkovn/grace-atlas)
#   ROLE: ENTRY_POINT
# END_MODULE_CONTRACT

"""Wrapper: `python tools/grace_atlas.py build` from repository root.

Requires the git submodule:
  git submodule update --init --recursive
  # source: https://github.com/kucheryavenkovn/grace-atlas
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    pkg_root = root / "grace_atlas"
    src = pkg_root / "src"
    marker = pkg_root / "pyproject.toml"

    if not marker.is_file() or not (src / "grace_atlas").is_dir():
        print(
            "GRACE Atlas submodule is missing or empty at tools/grace_atlas.\n"
            "  git submodule update --init --recursive\n"
            "  # https://github.com/kucheryavenkovn/grace-atlas",
            file=sys.stderr,
        )
        return 2

    sys.path.insert(0, str(src))
    from grace_atlas.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
