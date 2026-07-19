# tools/

Инструменты для разработки, бенчмарков и дискриминации оптимизаций.

## Phase 19 — analysis resolution sweep

```bash
# Fixture smoke
python tools/sweep_analysis_resolution.py ^
  --video tests/fixtures/test_slides.mp4 ^
  --out benchmarks/detect/evidence/phase19-fixture-smoke ^
  --max-sides none,320,160 --sample-fps 0.5 --runs 2 ^
  --min-slide-duration 1 --min-stable-duration 0.5 --warmup

# Hermes 600s (local media; real wall-clock)
python tools/sweep_analysis_resolution.py ^
  --video .benchmarks/phase18/media/hermes-0000-1000.mp4 ^
  --out benchmarks/detect/evidence/phase19-hermes-600s ^
  --max-sides none,960,640,480,320 --sample-fps 2.0 --runs 2 --warmup
```

Emits `sweep_summary.json`, `sweep_report.md`, `golden_mean_decision.json`, per-cell JSON.

## Phase 18 — detect benchmark

`tools/benchmark_detect.py` — canonical DetectionService telemetry (see Phase 18 docs).
