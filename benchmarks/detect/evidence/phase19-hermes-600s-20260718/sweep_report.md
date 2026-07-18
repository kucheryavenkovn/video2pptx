# Phase 19 — Analysis Resolution Sweep Report

- Created: `2026-07-18T11:12:32.610567+00:00`
- HEAD: `51118330fc4e2fdbae11d98bd2920c3b99a9d038`
- Video: `hermes-0000-1000.mp4`
- Grid: max_sides=[None, 960, 640, 480, 320] sample_fps=[2.0] runs=2

## Results (median wall-clock)

| label | wall_s | vs native | extract_s | extract Δ% | p1_decode_s | slides | missed | false_split | full_res | gates |
|-------|--------|-----------|-----------|------------|-------------|--------|--------|-------------|---------|-------|
| side=native_fps=2 | 243.85 | 0.0% | 85.95 | 0.0% | 103.07 | 4 | 0.0 | 0.0 | True | True |
| side=960_fps=2 | 148.20 | 39.2% | 21.69 | 74.8% | 71.54 | 6 | 0.0 | 0.3333333333333333 | True | False |
| side=640_fps=2 | 117.40 | 51.9% | 10.23 | 88.1% | 52.42 | 6 | 0.0 | 0.3333333333333333 | True | False |
| side=480_fps=2 | 113.25 | 53.6% | 5.67 | 93.4% | 52.00 | 4 | 0.0 | 0.0 | True | True |
| side=320_fps=2 | 110.58 | 54.7% | 2.96 | 96.6% | 52.10 | 6 | 0.0 | 0.3333333333333333 | True | False |

## Decision

```json
{
  "selected_analysis_scale": 480,
  "selected_sample_fps": 2.0,
  "selected_label": "side=480_fps=2",
  "reason": "highest wall speedup among gate-passers with >=5% wall reduction",
  "wall_reduction_pct": 53.555312985969664,
  "extract_features_reduction_pct": 93.40752736461565,
  "speedup_vs_native_wall": 2.1530988026637212,
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
