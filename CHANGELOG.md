# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **F-0022**: Markdown export double path prefix `slides/slides/slide_001.png` — centralized path resolver
- **F-0023**: `export-md` CLI params (`--image-as-bg`, `--transcript-location`, `--timecodes`) now functional
- **F-0024**: Circular dependency `notes_processor → pptx_export._fmt_time` eliminated via `paths.format_time`
- **F-0025**: LLM orchestrator now closes httpx.Client and unloads model via `try/finally`
- **F-0026**: `detect --llm --export-md/--export-pptx` now uses enriched document for exports
- **F-0027**: Added missing `[gui]` extra in pyproject.toml
- **F-0028**: Added `httpx` to `[llm]` extra (was missing entirely)
- **F-0029**: Unified version source — hatch dynamic version from `__init__.py`
- **F-0030**: Removed `Private :: Do Not Upload` classifier
- **F-0031**: Fixed placeholder documentation URL
- **F-0032**: `notes --notes-mode llm` now passes `LlmConfig` to pipeline
- **F-0033**: PPTX export `notes_mode=llm` uses enriched transcript instead of silent basic fallback
- **F-0034**: Unified detection pipeline — `cli.detect` delegates to `run_detect_slides`

### Changed
- Extras restructured: `[gui]`, `[pptx]`, `[llm]`, `[gpu]`, `[dev]`, `[all]`
- Removed unused dependencies: `decord`, `torch`, `streamlit` from extras
- Author updated to `kucheryavenkovn`
- All project URLs updated to `github.com/kucheryavenkovn/video2pptx`

### Removed
- Committed output artifacts (`out2/` through `out7/`)
- Committed input files (`in/*.srt`)
- Session log files, root `project.json`, `.mcp_port`
- One-time migration script `add_decorators.py`
- Disassembly dump files

### Added
- `M-PATHS` module (`src/video2pptx/paths.py`) — centralized artifact path resolution
- Ruff lint configuration with import sorting
- pytest markers: `gpu`, `llm`, `gui`, `slow`
- GitHub Actions CI (lint, test matrix, GUI tests, package build)
- `docs/audit-report.md`

## [0.5.0] - 2026-07-09

### Added
- QuickDetect mode (keyframes + pixel MAE)
- Manual slides with drag/resize on timeline
- SubtitleEditor with LLM vision analysis
- StatusBarManager with progress/ETA
- MCP debug server (HTTP/SSE on :9812)
- Debug dock with live log viewer and state tree
- Smart snap for manual markers (diff_only/fallback/hybrid)
- Project model with Qt signals
- Timeline3 (QGraphicsView multi-track)
- Export dropdown, Save button
