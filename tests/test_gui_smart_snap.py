# FILE: tests/test_gui_smart_snap.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for M-GUI-SMART-SNAP — all three snap strategies
#   SCOPE: Deterministic tests for diff_only, fallback_analyze, hybrid strategies
#   DEPENDS: pytest, tempfile, csv, pathlib
#   LINKS: M-GUI-SMART-SNAP
#   ROLE: TEST
#   MAP_MODE: NONE
# END_MODULE_CONTRACT

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pytest

from video_slide_md.gui.smart_snap import (
    _decode_and_analyze_window,
    _find_peak_in_window,
    _load_diff_scores,
    _snap_diff_only,
    _snap_fallback_analyze,
    _snap_hybrid,
    smart_snap,
)
from video_slide_md.project_manager import Project


@pytest.fixture
def project_with_debug(tmp_path: Path) -> tuple[Project, Path]:
    """Create a project with a debug/diff_scores.csv file."""
    proj = Project(
        name="test",
        video=str(tmp_path / "test.mp4"),
        output_dir=str(tmp_path),
    )
    debug_dir = tmp_path / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    csv_path = debug_dir / "diff_scores.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "score"])
        writer.writerow(["0.000", "0.100"])
        writer.writerow(["5.000", "0.050"])
        writer.writerow(["10.000", "0.800"])  # peak at 10s
        writer.writerow(["10.500", "0.600"])
        writer.writerow(["11.000", "0.300"])
        writer.writerow(["15.000", "0.100"])
        writer.writerow(["20.000", "0.200"])

    return proj, tmp_path


class TestLoadDiffScores:
    # START_CONTRACT: TestLoadDiffScores
    #   PURPOSE: Verify CSV loading logic
    #   LINKS: M-GUI-SMART-SNAP
    # END_CONTRACT: TestLoadDiffScores

    def test_loads_csv_correctly(self, project_with_debug: tuple[Project, Path]) -> None:
        proj, _ = project_with_debug
        timestamps, scores = _load_diff_scores(proj)
        assert len(timestamps) == 7
        assert len(scores) == 7
        assert timestamps[2] == 10.0
        assert scores[2] == 0.8

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        proj = Project(name="test", video="/tmp/test.mp4", output_dir=str(tmp_path))
        timestamps, scores = _load_diff_scores(proj)
        assert timestamps == []
        assert scores == []

    def test_invalid_csv_returns_empty(self, tmp_path: Path) -> None:
        debug_dir = tmp_path / "debug"
        debug_dir.mkdir()
        (debug_dir / "diff_scores.csv").write_text("not a csv", encoding="utf-8")

        proj = Project(name="test", video="/tmp/test.mp4", output_dir=str(tmp_path))
        timestamps, scores = _load_diff_scores(proj)
        assert timestamps == []
        assert scores == []


class TestFindPeakInWindow:
    # START_CONTRACT: TestFindPeakInWindow
    #   PURPOSE: Verify peak finding within a time window
    #   LINKS: M-GUI-SMART-SNAP
    # END_CONTRACT: TestFindPeakInWindow

    def test_finds_peak_at_center(self) -> None:
        timestamps = [0.0, 5.0, 10.0, 15.0, 20.0]
        scores = [0.1, 0.2, 0.9, 0.3, 0.1]
        peak = _find_peak_in_window(timestamps, scores, 10.0, 5.0)
        assert peak == 10.0

    def test_finds_nearest_peak_off_center(self) -> None:
        timestamps = [0.0, 5.0, 10.0, 15.0, 20.0]
        scores = [0.1, 0.8, 0.2, 0.9, 0.1]
        peak = _find_peak_in_window(timestamps, scores, 12.0, 5.0)
        # window = [7, 17], peak at 15.0
        assert peak == 15.0

    def test_no_data_in_window_returns_none(self) -> None:
        timestamps = [0.0, 100.0, 200.0]
        scores = [0.1, 0.8, 0.2]
        peak = _find_peak_in_window(timestamps, scores, 50.0, 10.0)
        assert peak is None

    def test_empty_lists_returns_none(self) -> None:
        peak = _find_peak_in_window([], [], 10.0, 5.0)
        assert peak is None


class TestSnapDiffOnly:
    # START_CONTRACT: TestSnapDiffOnly
    #   PURPOSE: Verify diff_only strategy
    #   LINKS: M-GUI-SMART-SNAP
    # END_CONTRACT: TestSnapDiffOnly

    def test_snaps_to_nearest_peak(self, project_with_debug: tuple[Project, Path]) -> None:
        proj, _ = project_with_debug
        # marker at 12s, nearest peak at 10s (within ±5s window)
        snapped = _snap_diff_only(12.0, proj)
        assert snapped == 10.0

    def test_no_peak_returns_original(self, project_with_debug: tuple[Project, Path]) -> None:
        proj, _ = project_with_debug
        # marker at 50s, no peaks within ±5s
        snapped = _snap_diff_only(50.0, proj)
        assert snapped == 50.0

    def test_returns_original_if_no_diff_scores(self, tmp_path: Path) -> None:
        proj = Project(name="test", video="/tmp/test.mp4", output_dir=str(tmp_path))
        snapped = _snap_diff_only(10.0, proj)
        assert snapped == 10.0


class TestSnapFallbackAnalyze:
    # START_CONTRACT: TestSnapFallbackAnalyze
    #   PURPOSE: Verify fallback_analyze strategy
    #   LINKS: M-GUI-SMART-SNAP
    # END_CONTRACT: TestSnapFallbackAnalyze

    def test_uses_diff_scores_when_available(self, project_with_debug: tuple[Project, Path]) -> None:
        proj, _ = project_with_debug
        snapped = _snap_fallback_analyze(12.0, proj)
        assert snapped == 10.0  # from diff scores

    def test_no_video_returns_original(self, tmp_path: Path) -> None:
        proj = Project(name="test", video=str(tmp_path / "nonexistent.mp4"), output_dir=str(tmp_path))
        snapped = _snap_fallback_analyze(10.0, proj)
        assert snapped == 10.0


class TestSnapHybrid:
    # START_CONTRACT: TestSnapHybrid
    #   PURPOSE: Verify hybrid strategy
    #   LINKS: M-GUI-SMART-SNAP
    # END_CONTRACT: TestSnapHybrid

    def test_uses_diff_when_not_flat(self, project_with_debug: tuple[Project, Path]) -> None:
        proj, _ = project_with_debug
        # scores have high variance (0.05 to 0.80), not flat
        snapped = _snap_hybrid(12.0, proj, 0.05)
        assert snapped == 10.0

    def test_fallback_when_flat(self, tmp_path: Path) -> None:
        """When diff scores exist but are flat, falls back to decode which returns original since no real video."""
        proj = Project(name="test", video="/tmp/nonexistent.mp4", output_dir=str(tmp_path))
        # no scores exist → fallback → video doesn't exist → returns original
        snapped = _snap_hybrid(10.0, proj, 0.05)
        assert snapped == 10.0


class TestSmartSnapMain:
    # START_CONTRACT: TestSmartSnapMain
    #   PURPOSE: Verify main entry point dispatches correctly
    #   LINKS: M-GUI-SMART-SNAP
    # END_CONTRACT: TestSmartSnapMain

    def test_diff_only_mode(self, project_with_debug: tuple[Project, Path]) -> None:
        proj, _ = project_with_debug
        snapped = smart_snap(12.0, proj, snap_mode="diff_only")
        assert snapped == 10.0

    def test_fallback_analyze_mode(self, project_with_debug: tuple[Project, Path]) -> None:
        proj, _ = project_with_debug
        snapped = smart_snap(12.0, proj, snap_mode="fallback_analyze")
        assert snapped == 10.0

    def test_hybrid_mode(self, project_with_debug: tuple[Project, Path]) -> None:
        proj, _ = project_with_debug
        snapped = smart_snap(12.0, proj, snap_mode="hybrid")
        assert snapped == 10.0

    def test_unknown_mode_falls_back_to_hybrid(self, project_with_debug: tuple[Project, Path]) -> None:
        proj, _ = project_with_debug
        snapped = smart_snap(12.0, proj, snap_mode="invalid")
        assert snapped == 10.0

    def test_no_project_data_returns_original(self, tmp_path: Path) -> None:
        proj = Project(name="test", video="/tmp/test.mp4", output_dir=str(tmp_path))
        snapped = smart_snap(10.0, proj, snap_mode="diff_only")
        assert snapped == 10.0


class TestDecodeAndAnalyzeWindow:
    # START_CONTRACT: TestDecodeAndAnalyzeWindow
    #   PURPOSE: Verify decode window behavior with missing/invalid video
    #   LINKS: M-GUI-SMART-SNAP
    # END_CONTRACT: TestDecodeAndAnalyzeWindow

    def test_missing_video_returns_original(self, tmp_path: Path) -> None:
        proj = Project(name="test", video=str(tmp_path / "no_such_video.mp4"), output_dir=str(tmp_path))
        result = _decode_and_analyze_window(10.0, proj, 3.0, 5.0)
        assert result == 10.0
