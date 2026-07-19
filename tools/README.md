# tools/

Инструменты для разработки, бенчмарков и дискриминации оптимизаций.

## GRACE Atlas (git submodule)

Проекция GRACE XML + source markup в Obsidian Vault.

- Upstream: https://github.com/kucheryavenkovn/grace-atlas  
- Path: `tools/grace_atlas` (submodule)  
- Config: `grace-atlas.toml` in repo root  
- Vault (generated, gitignored): `.grace-atlas/vault/`

```powershell
# first-time / after clone
git submodule update --init --recursive

# build vault
python tools/grace_atlas.py build --project-root .
python tools/grace_atlas.py status --project-root .
python tools/grace_atlas.py trace M-APP-AUTO --project-root .
```

Open `.grace-atlas/vault` as an Obsidian vault → Graph view / Canvas.

Update submodule to latest:

```powershell
cd tools/grace_atlas
git pull origin main
cd ../..
git add tools/grace_atlas
git commit -m "chore: bump grace-atlas submodule"
```

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
