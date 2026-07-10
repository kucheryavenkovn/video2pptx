# FILE: src/video2pptx/utils/json_io.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Atomic JSON writer — temp file + os.replace. Prevents partial-file corruption on all project/slides/alignment writes.
#   SCOPE: write_json_atomic()
#   DEPENDS: none
#   LINKS: M-ATOMIC-JSON
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   write_json_atomic - write obj as JSON to .tmp in same dir, then os.replace to target
# END_MODULE_MAP

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from loguru import logger


def write_json_atomic(path: str | Path, obj: Any, **json_kwargs: Any) -> None:
    target = Path(path)
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        suffix=".tmp",
        prefix=target.stem + "_",
        dir=str(parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, **json_kwargs)
        os.replace(tmp_path, str(target))
        logger.debug(f"[AtomicJson] Wrote {target} ({target.stat().st_size} bytes)")
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
