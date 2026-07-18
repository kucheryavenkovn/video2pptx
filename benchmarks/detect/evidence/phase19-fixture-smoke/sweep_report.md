# Phase 19 — Analysis Resolution Sweep Report

- Created: `2026-07-18T10:39:59.193488+00:00`
- HEAD: `51118330fc4e2fdbae11d98bd2920c3b99a9d038`
- Video: `test_slides.mp4`
- Grid: max_sides=[None, 320, 160] sample_fps=[0.5] runs=2

## Results (median wall-clock)

| label | wall_s | vs native | extract_s | extract Δ% | p1_decode_s | slides | missed | false_split | full_res | gates |
|-------|--------|-----------|-----------|------------|-------------|--------|--------|-------------|---------|-------|
| side=native_fps=0.5 | 0.66 | 0.0% | 0.08 | 0.0% | 0.29 | 1 | 0.0 | 0.0 | True | True |
| side=320_fps=0.5 | 0.59 | 10.1% | 0.02 | 72.6% | 0.28 | 1 | 0.0 | 0.0 | True | True |
| side=160_fps=0.5 | 0.57 | 13.7% | 0.01 | 91.5% | 0.28 | 1 | 0.0 | 0.0 | True | True |

## Decision

```json
{
  "selected_analysis_scale": 160,
  "selected_sample_fps": 0.5,
  "selected_label": "side=160_fps=0.5",
  "reason": "highest wall speedup among gate-passers with >=5% wall reduction",
  "wall_reduction_pct": 13.686123887601253,
  "extract_features_reduction_pct": 91.50878759557169,
  "speedup_vs_native_wall": 1.1585622672046272,
  "phase18_reopened": false,
  "phase18_selected_optimization": "NONE (unchanged)"
}
```

## Notes

- Decode path still processes native H.264 frames; analysis_max_side mainly cuts extract_features CPU after ROI.
- Wall-clock speedup may be modest if decode dominates (~60% in Phase 18 Hermes).
- extract_features_reduction_pct is the direct lever; wall_reduction_pct is the user-visible outcome.
- full_res_screenshot_ok must remain true for all accepted configs.
- Quality is vs native reference at the same sample_fps (soft parity, not score byte-identity).
