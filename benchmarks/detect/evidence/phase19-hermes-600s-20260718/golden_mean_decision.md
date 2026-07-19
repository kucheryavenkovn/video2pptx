# Phase 19 — Golden Mean Decision (Hermes 600s)

**Date:** 2026-07-18  
**Code HEAD:** `51118330fc4e2fdbae11d98bd2920c3b99a9d038`  
**Video:** `.benchmarks/phase18/media/hermes-0000-1000.mp4` (1920×1080@60, 600.02 s, H.264)  
**Protocol:** `sample_fps=2.0`, `min_slide_duration=10`, `min_stable_duration=5`, **2 runs median**, 1 discarded warmup  
**Phase 18:** NOT reopened (`selected_optimization=NONE` remains)

## Does analysis_max_side help?

**Yes — clearly on wall-clock and extract_features.**

| analysis_max_side | wall median (s) | wall Δ vs native | extract_features (s) | extract Δ | p1_decode (s) | slides | gates vs native |
|-------------------|-----------------|------------------|----------------------|-----------|---------------|--------|-----------------|
| native (None)     | **243.85**      | —                | **85.95**            | —         | 103.07        | 4      | PASS (ref)      |
| 960               | 148.20          | **−39.2%**       | 21.69                | −74.8%    | 71.54         | 6      | FAIL false_split 33% |
| 640               | 117.40          | **−51.9%**       | 10.23                | −88.1%    | 52.42         | 6      | FAIL false_split 33% |
| **480**           | **113.25**      | **−53.6%**       | **5.67**             | **−93.4%**| 52.00         | **4**  | **PASS**        |
| 320               | 110.58          | −54.7%           | 2.96                 | −96.6%    | 52.10         | 6      | FAIL false_split 33% |

### Direct answers

1. **Does it speed up detect?**  
   Yes. Gate-passing `analysis_max_side=480` is **~2.15× faster** wall-clock (243.85 → 113.25 s).

2. **Where does the gain come from?**  
   - **Primary intended lever:** `extract_features` 85.95 → 5.67 s (**−93%**).  
   - Full-res PNG Pass2 invariant: **True** for all cells.  
   - `p1_decode` also fell (103 → ~52 s) for scaled cells. That is **larger than expected** from pure feature work (decode still yields native RGB). Treat part of the decode drop as **order/cache/environment coupling**, not a proven pure decode optimization. Even if only extract savings counted:  
     `85.95 − 5.67 ≈ 80 s` alone is already a large fraction of the wall reduction.

3. **Quality tradeoff**  
   Relative to **this run’s native reference** (4 slides):  
   - 480: same count, missed=0, false_split=0 → **gates PASS**  
   - 960/640/320: 6 slides → false_split_rate=33% → **FAIL** (≥10% gate)  
   Caveat: native Hermes under these settings only emits **4** long segments (many short candidates filtered by `min_slide_duration=10`). This is relative parity to native, **not** absolute ground-truth slide accuracy (see historical F-0088).

## Selected golden mean

```json
{
  "selected_analysis_scale": 480,
  "selected_sample_fps": 2.0,
  "wall_reduction_pct": 53.6,
  "extract_features_reduction_pct": 93.4,
  "speedup_vs_native_wall": 2.15,
  "full_res_screenshots": true,
  "phase18_reopened": false
}
```

**Recommendation:** use `video.analysis_max_side: 480` for 1080p lecture-style content when quality is judged vs current native detector. Keep `None` available for max-sensitivity experiments. Do **not** default to 320/640 on Hermes without revisiting quality (false splits vs this native baseline).

## Fixture smoke (supporting, not decisive)

`tests/fixtures/test_slides.mp4` is already 640×480 — limited headroom. Still shows extract −72…91% and wall −10…14% with gates PASS. See `phase19-fixture-smoke/`.

## Artifacts

- `sweep_summary.json` — full machine-readable grid  
- `sweep_report.md` — table  
- `cell_*.json` — per-cell metrics  
- `cells/` — run outputs (local only; PNGs not required in git)

## Next

- Step 19.8: optionally document `480` in `config.example.yaml` as recommended (default remains `None` until product sign-off).  
- Optional: re-run with randomized cell order to isolate decode-timer order effects.  
- Optional: ground-truth labels for absolute missed_slide_rate (beyond native-relative).
