# Audit Report — video2pptx Release Hardening

Date: 2026-07-10
Branch: `fix/release-hardening`
Auditor: AI engineering audit (GRACE methodology)

## Summary

Full repository audit covering packaging, CLI, pipeline, export, LLM, paths, tests, static analysis, CI, and documentation. 15 defects identified and fixed (F-0022 through F-0036). All 491 tests pass after changes.

## Findings Table

| ID | Severity | Area | Problem | Fix | Test |
|----|----------|------|---------|-----|------|
| F-0022 | Blocker | export | Markdown double path `slides/slides/` | `paths.resolve_markdown_image_path()` | `test_double_path_bug_fixed` |
| F-0023 | Major | cli | export-md params silently ignored | Implemented in `export_to_markdown` | `test_image_as_background`, `test_no_timecodes`, etc. |
| F-0024 | Major | export | Circular dep `notes_processor → pptx_export._fmt_time` | `paths.format_time()` | Import isolation verified |
| F-0025 | Critical | llm | LLM orchestrator leaks httpx.Client + never unloads model | `try/finally` with `unload_model()` + `close()` | Orchestrator tests pass |
| F-0026 | Critical | cli | `detect --llm --export-*` uses stale pre-LLM doc | Reload doc from disk after LLM | CLI e2e tests |
| F-0027 | Blocker | packaging | Missing `gui` extra; README broken | Added all extras | CI install matrix |
| F-0028 | Blocker | packaging | `httpx` missing from dependencies | Added to `[llm]` and `[all]` | CI |
| F-0029 | Major | packaging | `__version__` 0.1.0 vs pyproject 0.5.0 | Hatch dynamic version | `pip show` |
| F-0030 | Major | packaging | `Private::Do Not Upload` conflicts with install docs | Removed classifier | `twine check` |
| F-0031 | Minor | packaging | Placeholder URL `github.com/user/...` | Updated to real URL | `pip show` |
| F-0032 | Major | cli | `notes --notes-mode llm` doesn't pass LlmConfig | Pass config in `notes_cmd` | Notes pipeline tests |
| F-0033 | Major | export | PPTX `notes_mode=llm` silently does basic | Use enriched transcript + description | PPTX export tests |
| F-0034 | Major | pipeline | Two independent detection implementations | Unified via `run_detect_slides` | CLI tests |
| F-0035 | Minor | repo | Committed output artifacts + session files | `git rm --cached` + `.gitignore` | `git status` |
| F-0036 | Minor | repo | One-time migration script tracked | Deleted | `git ls-files` |

## Architecture Changes

### Added
- `M-PATHS` (`src/video2pptx/paths.py`) — centralized artifact path resolver + time formatting utility. Eliminates double-path bug and circular import.

### Modified
- `M-CLI` — `detect` now delegates to `run_detect_slides()` instead of reimplementing pipeline; `notes_cmd` passes `LlmConfig`; `export_md` passes all formatting params.
- `M-LLM-ORCHESTRATOR` — `try/finally` resource cleanup; uses `resolve_artifact_path` for image resolution.
- `M-NOTES` — `run_notes` wraps processing in `try/finally` for client cleanup; uses `resolve_artifact_path`.
- `M-MD-EXPORT` — accepts `image_as_background`, `transcript_location`, `include_timecodes`; uses `resolve_markdown_image_path`.
- `M-PPTX-EXPORT` — uses `resolve_artifact_path`; llm mode uses enriched transcript.
- `M-NOTES-PROCESSOR` — uses `paths.format_time` instead of importing from `pptx_export`.

### Dependency Changes

| Package | Before | After |
|---------|--------|-------|
| httpx | missing | `[llm]`, `[all]`, `[dev]` |
| PySide6 | missing | `[gui]`, `[all]` |
| python-pptx | `[pptx]` only | `[pptx]`, `[dev]`, `[all]` |
| decord | `[gpu]` | removed (unused) |
| torch | `[gpu]` | removed (unused) |
| streamlit | `[review]` | removed (unused) |
| ruff | not configured | `[dev]` + pyproject config |
| mypy | not configured | `[dev]` + pyproject config |
| pytest-cov | not listed | `[dev]` |

## Verification Results

```
pytest tests/          → 491 passed, 8 skipped (GUI platform)
ruff check src/ tests/ → All checks passed
video2pptx --help      → OK (no optional deps required)
```

## Remaining Limitations

1. **GPU/CUDA testing** — not available in CI; PyAV CUDA backend tested via fallback only.
2. **LM Studio integration** — LLM tests use mock; real LM Studio not tested in CI.
3. **PowerPoint/LibreOffice rendering** — PPTX validated via python-pptx re-read only.
4. **Python 3.13** — local dev uses 3.14; CI targets 3.10–3.12 until all deps confirm 3.13 support.
5. **Score waveform in debug command** — `video2pptx debug slides.json` uses `doc.score_values` if present in JSON; standalone debug without prior detection has no scores.
