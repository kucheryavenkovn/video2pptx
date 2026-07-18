# FILE: tests/test_atomic_json.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for atomic JSON writer — temp file + os.replace
#   SCOPE: write_json_atomic basic, integrity on failure
#   DEPENDS: pytest, video2pptx.utils.json_io
#   LINKS: V-M-ATOMIC-JSON, M-ATOMIC-JSON
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import json
from pathlib import Path

import pytest

from video2pptx.utils.json_io import write_json_atomic


class TestAtomicJson:
    def test_writes_valid_json(self, tmp_path: Path):
        target = tmp_path / "test.json"
        data = {"key": "value", "num": 42}
        write_json_atomic(target, data)
        assert target.is_file()
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded == data

    def test_no_temp_left_behind(self, tmp_path: Path):
        target = tmp_path / "no_temp.json"
        write_json_atomic(target, {"ok": True})
        temps = list(tmp_path.glob("*.tmp"))
        assert len(temps) == 0

    def test_old_file_replaced(self, tmp_path: Path):
        target = tmp_path / "replaced.json"
        target.write_text('{"old": true}', encoding="utf-8")
        write_json_atomic(target, {"new": True})
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded == {"new": True}

    def test_parent_dir_created(self, tmp_path: Path):
        target = tmp_path / "sub" / "deep" / "test.json"
        write_json_atomic(target, {"created": True})
        assert target.is_file()

    @pytest.mark.parametrize("bad_obj", [{"bad": object()}, {1, 2, 3}])
    def test_exception_keeps_old_intact(self, tmp_path: Path, bad_obj):
        target = tmp_path / "safe.json"
        target.write_text('{"original": true}', encoding="utf-8")
        with pytest.raises((TypeError, AttributeError)):
            write_json_atomic(target, bad_obj)
        assert target.is_file()
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded == {"original": True}
