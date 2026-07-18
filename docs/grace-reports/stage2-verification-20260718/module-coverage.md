# Stage 2 — Module & Verification-Entry Coverage Map

This report separates **module-level** (unique `M-*`) from **verification-entry-level** (all `V-M-*`). Do not treat module counts as entry counts.

## A. Module coverage (unique M-*)

- total_modules: 120
- modules_without_verification: 0
- modules_with_one_verification_entry: 120
- modules_with_multiple_verification_entries: 0
- modules_missing_wave_all_entries (module-level aggregate): 35
- modules_by_aggregate_status:
  - passed: 57
  - blocked: 33
  - planned: 28
  - in_progress: 2
  - failed: 0

### Multi-entry modules (all linked V-M-* preserved)
- (none — each M-* currently has at most one V-M entry; Phase-*/Step-* verification entries are reported at entry level only)

## B. Verification-entry coverage (all V-M-*)

- total_verification_entries: 144
- entries_by_status:
  - passed: 67
  - blocked: 40
  - planned: 34
  - in_progress: 2
  - failed: 0
  - unknown_or_other: 1
- status_sum: 144 (must equal total_verification_entries)
- entries_missing_module_checks: 43
- entries_missing_wave_follow_up: 47
- entries_missing_phase_follow_up: 0
- entries_missing_observable_evidence: 0
- entries_missing_scenarios: 0
- entries_with_missing_test_paths: 0
- entries_with_broken_module_checks: 0
- entries_with_unbounded_wave: 0

### unknown_or_other_entries
- V-M-PERF-DETECT-BOTTLENECK module=Phase-18/Step-18.4 raw_status='done'

## Module coverage classification
- VERIFIED_PASSED: 57
- VERIFICATION_BLOCKED: 33
- VERIFICATION_PLANNED: 28
- VERIFICATION_IN_PROGRESS: 2
- VERIFIED_FAILED: 0
- MISSING_VERIFICATION_ENTRY: 0
- NO_EXECUTABLE_EVIDENCE: 0

## Modules without verification entry
- (none)

## Full module coverage table

| Module | Status | V-M entries | V-Status (agg) | Module-chk | Wave | Phase | Obs | Scen | Test-missing | Classification |
|--------|--------|-------------|----------------|-----------|------|-------|-----|------|--------------|----------------|
| M-ADAPTERS | implemented | V-M-ADAPTERS | blocked | NO | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-APP-ALIGN | implemented | V-M-APP-ALIGN | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-APP-AUTO | implemented | V-M-APP-AUTO | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-APP-BOOTSTRAP | active | V-M-APP-BOOTSTRAP | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-APP-BUILD-META | active | V-M-APP-BUILD-META | blocked | NO | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-APP-COMMON | implemented | V-M-APP-COMMON | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-APP-DETECT | implemented | V-M-APP-DETECT | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-APP-EXPORT | implemented | V-M-APP-EXPORT | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-APP-IDENTITY | active | V-M-APP-IDENTITY | blocked | NO | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-APP-INPUT-RESOLVER | active | V-M-APP-INPUT-RESOLVER | blocked | NO | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-APP-LLM | planned | V-M-APP-LLM | planned | NO | NO | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-APP-NOTES | implemented | V-M-APP-NOTES | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-APP-PREVIEW | implemented | V-M-APP-PREVIEW | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-APP-PROJECT | planned | V-M-APP-PROJECT | planned | NO | NO | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-APP-SERVICE | partial | V-M-APP-SERVICE | planned | NO | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-APP-VALIDATE | implemented | V-M-APP-VALIDATE | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-ARCH-OVERVIEW | planned | V-M-ARCH-OVERVIEW | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-ATOMIC-JSON | planned | V-M-ATOMIC-JSON | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-AUTO-ALIGN | partial | V-M-AUTO-ALIGN | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-BACKEND-OPENCV | implemented | V-M-BACKEND-OPENCV | blocked | NO | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-BACKEND-PYAV | implemented | V-M-BACKEND-PYAV | blocked | yes | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-BACKENDS | implemented | V-M-BACKENDS | in_progress | yes | yes | yes | yes | yes | — | VERIFICATION_IN_PROGRESS |
| M-CANONICAL-COMMANDS | planned | V-M-CANONICAL-COMMANDS | planned | NO | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-CLI | implemented | V-M-CLI | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-CLI-ADAPTER | active | V-M-REF-CLI-ADAPTER | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-COLAB | implemented | V-M-COLAB | blocked | NO | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-CONFIG | implemented | V-M-CONFIG | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-CONFIRM-POLICY | planned | V-M-CONFIRM-POLICY | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-DEBUG-ACTION | implemented | V-M-DEBUG-ACTION | blocked | NO | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-DEBUG-EXPORT | implemented | V-M-DEBUG-EXPORT | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-DEBUG-MCP | implemented | V-M-DEBUG-MCP | blocked | NO | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-DEDUPE | implemented | V-M-DEDUPE | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-DESKTOP-BOOTSTRAP | active | V-M-DESKTOP-BOOTSTRAP | blocked | yes | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-DETECT-BENCHMARK | active | V-M-DETECT-BENCHMARK | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-DETECT-METRICS | active | V-M-DETECT-METRICS | blocked | yes | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-DETECT-PERF-DECISION | done | V-M-DETECT-PERF-DECISION | blocked | yes | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-DETECT-SLIDES | implemented | V-M-DETECT-SLIDES | in_progress | yes | yes | yes | yes | yes | — | VERIFICATION_IN_PROGRESS |
| M-DETECT-TARGET-DISCRIMINATION-R2 | verified | V-M-PERF-DETECT-TARGET-OPTIMIZATION-DISCRIMINATION | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-DOMAIN-EVENTS | planned | V-M-DOMAIN-EVENTS | planned | NO | NO | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-DOMAIN-PROJECT | implemented | V-M-DOMAIN-PROJECT | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-DOMAIN-SLIDE | implemented | V-M-DOMAIN-SLIDE | planned | NO | NO | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-DOMAIN-STATE | implemented | V-M-DOMAIN-STATE | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-DOMAIN-VALUE | implemented | V-M-DOMAIN-VALUE | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-E2E-RUNNER | partial | V-M-E2E-RUNNER | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-E2E-SCENARIOS | planned | V-M-E2E-SCENARIOS | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-E2E-SNAPSHOT | planned | V-M-E2E-SNAPSHOT | planned | NO | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-FILE-REPO | implemented | V-M-FILE-REPO | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-FRAME-FEATURES | implemented | V-M-FRAME-FEATURES | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GITHUB-PROVIDER | implemented | V-M-GITHUB-PROVIDER | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-ABOUT | active | V-M-GUI-ABOUT | blocked | NO | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-APPCONFIG | implemented | V-M-GUI-APPCONFIG | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-CANONICAL-BUTTONS | planned | V-M-GUI-CANONICAL-BUTTONS | planned | NO | NO | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-GUI-DEBUG-DOCK | implemented | V-M-GUI-DEBUG-DOCK | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-HELP-MENU | active | V-M-GUI-HELP-MENU | blocked | yes | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-LOG-BRIDGE | implemented | V-M-GUI-LOG-BRIDGE | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-MAIN | implemented | V-M-GUI-MAIN | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-MARKER-MANAGER | implemented | V-M-GUI-MARKER-MANAGER | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-MARKER-PANEL | implemented | V-M-GUI-MARKER-PANEL | blocked | yes | yes | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-MENUBAR | implemented | V-M-GUI-MENUBAR | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-PIPELINE-CTRL | active | V-M-GUI-PIPELINE-CTRL | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-PIPELINE-WORKER | active | V-M-GUI-PIPELINE-WORKER | blocked | yes | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-PROJECT-CTRL | active | V-M-REF-GUI-ADAPTER | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-ROI-SELECTOR | implemented | V-M-GUI-ROI-SELECTOR | blocked | yes | yes | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-SETTINGS | implemented | V-M-GUI-SETTINGS | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-SETTINGS-APP | implemented | V-M-GUI-SETTINGS-APP | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-SETTINGS-PROJECT | implemented | V-M-GUI-SETTINGS-PROJECT | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-SIGNAL-SPY | implemented | V-M-GUI-SIGNAL-SPY | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-SMART-SNAP | implemented | V-M-GUI-SMART-SNAP | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-STATUS | implemented | V-M-GUI-STATUS | blocked | yes | yes | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-SUBTITLE-EDITOR | implemented | V-M-GUI-SUBTITLE-EDITOR | blocked | yes | yes | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-SUBTITLE-OVERLAY | implemented | V-M-GUI-SUBTITLE-OVERLAY | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-TIMELINE | implemented | V-M-GUI-TIMELINE | blocked | NO | yes | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-TIMELINE-CTRL | active | V-M-GUI-TIMELINE-CTRL | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-TIMELINE-V2 | implemented | V-M-GUI-TIMELINE-V2 | blocked | NO | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-TIMELINE3 | implemented | V-M-GUI-TIMELINE3 | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-UPDATE-CTRL | implemented | V-M-GUI-UPDATE-CTRL | blocked | NO | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-VIDEOPLAYER | implemented | V-M-GUI-VIDEOPLAYER | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-GUI-WINDOW-UI | active | V-M-GUI-WINDOW-UI | blocked | NO | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-WORKER | implemented | V-M-GUI-WORKER | blocked | NO | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-LLM-CLIENT | implemented | V-M-LLM-CLIENT | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-LLM-ORCHESTRATOR | implemented | V-M-LLM-ORCHESTRATOR | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-MCP-ADAPTER | implemented | V-M-MCP-ADAPTER | blocked | NO | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-MCP-COMPOSITION | implemented | V-M-MCP-COMPOSITION | blocked | NO | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-MCP-OPERATIONS | planned | V-M-MCP-OPERATIONS | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-MCP-READ-TOOLS | planned | V-M-MCP-READ-TOOLS | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-MCP-RELIABILITY | planned | V-M-MCP-RELIABILITY | planned | NO | NO | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-MCP-WRITE-TOOLS | planned | V-M-MCP-WRITE-TOOLS | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-MD-EXPORT | implemented | V-M-MD-EXPORT | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-MODELS | implemented | V-M-MODELS | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-NOTES | implemented | V-M-NOTES | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-NOTES-PROCESSOR | implemented | V-M-NOTES-PROCESSOR | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-OPERATION-REGISTRY | implemented | V-M-OPERATION-REGISTRY | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-PERSIST-DETECTION | active | V-M-PERSIST-DETECTION | blocked | yes | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-PERSIST-DTO | implemented | V-M-PERSIST-DTO | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-PERSIST-MIGRATIONS | implemented | V-M-PERSIST-MIGRATIONS | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-PIPELINE | implemented | V-M-CLI-E2E | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-PIPELINE-STATES | partial | V-M-PIPELINE-STATES | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-PORT-ALIGNMENT | implemented | V-M-PORT-ALIGNMENT | blocked | yes | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-PORT-DETECTOR | implemented | V-M-PORT-DETECTOR | blocked | yes | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-PORT-EVENTS | planned | V-M-PORT-EVENTS | planned | NO | NO | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-PORT-EXPORT | implemented | V-M-PORT-EXPORT | blocked | yes | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-PORT-LLM | planned | V-M-PORT-LLM | planned | NO | NO | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-PORT-NOTES | implemented | V-M-PORT-NOTES | blocked | yes | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-PORT-PREVIEW | implemented | V-M-PORT-PREVIEW | blocked | yes | NO | yes | yes | yes | — | VERIFICATION_BLOCKED |
| M-PORT-REPO | implemented | V-M-PORT-REPO | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-PPTX-EXPORT | implemented | V-M-PPTX-EXPORT | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-PROJECT | implemented | V-M-PROJECT | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-PROJECT-MODEL | implemented | V-M-PROJECT-MODEL | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-PROJECT-VALIDATOR | planned | V-M-PROJECT-VALIDATOR | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-ROI | implemented | V-M-ROI | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-ROI-TOOL | implemented | V-M-ROI-TOOL | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-SEGMENTER | implemented | V-M-SEGMENTER | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-SLIDE-ANALYZER | implemented | V-M-SLIDE-ANALYZER | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-SLIDE-DETECTOR | implemented | V-M-SLIDE-DETECTOR | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-STRUCTURED-ERRORS | planned | V-M-STRUCTURED-ERRORS | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-SUBTITLES | implemented | V-M-SUBTITLES | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-TIMELINE-MODEL | implemented | V-M-TIMELINE-MODEL | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-UI-STATE-READER | planned | V-M-UI-STATE-READER | planned | yes | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-UPDATE-CHECKER | implemented | V-M-REF-UPDATE-CHECKER | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-VIDEO-DECODE | implemented | V-M-VIDEO-DECODE | blocked | yes | yes | yes | yes | yes | — | VERIFICATION_BLOCKED |

## Full verification-entry table

| V-M | Module | Status | Module-chk | Wave | Phase | Obs | Scen | Missing tests | Unbounded wave |
|-----|--------|--------|-----------|------|-------|-----|------|---------------|----------------|
| V-M-ADAPTERS | M-ADAPTERS | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-APP-ALIGN | M-APP-ALIGN | passed | yes | yes | yes | yes | yes | — | — |
| V-M-APP-AUTO | M-APP-AUTO | passed | yes | yes | yes | yes | yes | — | — |
| V-M-APP-BOOTSTRAP | M-APP-BOOTSTRAP | passed | yes | yes | yes | yes | yes | — | — |
| V-M-APP-BUILD-META | M-APP-BUILD-META | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-APP-COMMON | M-APP-COMMON | passed | yes | yes | yes | yes | yes | — | — |
| V-M-APP-DETECT | M-APP-DETECT | passed | yes | yes | yes | yes | yes | — | — |
| V-M-APP-EXPORT | M-APP-EXPORT | passed | yes | yes | yes | yes | yes | — | — |
| V-M-APP-IDENTITY | M-APP-IDENTITY | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-APP-INPUT-RESOLVER | M-APP-INPUT-RESOLVER | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-APP-LLM | M-APP-LLM | planned | NO | NO | yes | yes | yes | — | — |
| V-M-APP-NOTES | M-APP-NOTES | passed | yes | yes | yes | yes | yes | — | — |
| V-M-APP-PREVIEW | M-APP-PREVIEW | passed | yes | yes | yes | yes | yes | — | — |
| V-M-APP-PROJECT | M-APP-PROJECT | planned | NO | NO | yes | yes | yes | — | — |
| V-M-APP-SERVICE | M-APP-SERVICE | planned | NO | yes | yes | yes | yes | — | — |
| V-M-APP-VALIDATE | M-APP-VALIDATE | passed | yes | yes | yes | yes | yes | — | — |
| V-M-ARCH-IMPORTS | Phase-16 | planned | NO | yes | yes | yes | yes | — | — |
| V-M-ARCH-OVERVIEW | M-ARCH-OVERVIEW | planned | yes | yes | yes | yes | yes | — | — |
| V-M-ATOMIC-JSON | M-ATOMIC-JSON | planned | yes | yes | yes | yes | yes | — | — |
| V-M-AUTO-ALIGN | M-AUTO-ALIGN | planned | yes | yes | yes | yes | yes | — | — |
| V-M-BACKEND-OPENCV | M-BACKEND-OPENCV | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-BACKEND-PYAV | M-BACKEND-PYAV | blocked | yes | NO | yes | yes | yes | — | — |
| V-M-BACKENDS | M-BACKENDS | in_progress | yes | yes | yes | yes | yes | — | — |
| V-M-CANONICAL-COMMANDS | M-CANONICAL-COMMANDS | planned | NO | yes | yes | yes | yes | — | — |
| V-M-CLI | M-CLI | passed | yes | yes | yes | yes | yes | — | — |
| V-M-CLI-E2E | M-PIPELINE | passed | yes | yes | yes | yes | yes | — | — |
| V-M-COLAB | M-COLAB | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-CONFIG | M-CONFIG | passed | yes | yes | yes | yes | yes | — | — |
| V-M-CONFIRM-POLICY | M-CONFIRM-POLICY | planned | yes | yes | yes | yes | yes | — | — |
| V-M-DEBUG-ACTION | M-DEBUG-ACTION | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-DEBUG-EXPORT | M-DEBUG-EXPORT | passed | yes | yes | yes | yes | yes | — | — |
| V-M-DEBUG-MCP | M-DEBUG-MCP | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-DEDUPE | M-DEDUPE | passed | yes | yes | yes | yes | yes | — | — |
| V-M-DESKTOP-BOOTSTRAP | M-DESKTOP-BOOTSTRAP | blocked | yes | NO | yes | yes | yes | — | — |
| V-M-DETECT-BENCHMARK | M-DETECT-BENCHMARK | passed | yes | yes | yes | yes | yes | — | — |
| V-M-DETECT-METRICS | M-DETECT-METRICS | blocked | yes | NO | yes | yes | yes | — | — |
| V-M-DETECT-PERF-DECISION | M-DETECT-PERF-DECISION | blocked | yes | NO | yes | yes | yes | — | — |
| V-M-DETECT-SLIDES | M-DETECT-SLIDES | in_progress | yes | yes | yes | yes | yes | — | — |
| V-M-DOMAIN-EVENTS | M-DOMAIN-EVENTS | planned | NO | NO | yes | yes | yes | — | — |
| V-M-DOMAIN-PROJECT | M-DOMAIN-PROJECT | planned | yes | yes | yes | yes | yes | — | — |
| V-M-DOMAIN-SLIDE | M-DOMAIN-SLIDE | planned | NO | NO | yes | yes | yes | — | — |
| V-M-DOMAIN-STATE | M-DOMAIN-STATE | planned | yes | yes | yes | yes | yes | — | — |
| V-M-DOMAIN-VALUE | M-DOMAIN-VALUE | planned | yes | yes | yes | yes | yes | — | — |
| V-M-E2E-RUNNER | M-E2E-RUNNER | planned | yes | yes | yes | yes | yes | — | — |
| V-M-E2E-SCENARIOS | M-E2E-SCENARIOS | planned | yes | yes | yes | yes | yes | — | — |
| V-M-E2E-SNAPSHOT | M-E2E-SNAPSHOT | planned | NO | yes | yes | yes | yes | — | — |
| V-M-FILE-REPO | M-FILE-REPO | passed | yes | yes | yes | yes | yes | — | — |
| V-M-FRAME-FEATURES | M-FRAME-FEATURES | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GITHUB-PROVIDER | M-GITHUB-PROVIDER | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-ABOUT | M-GUI-ABOUT | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-GUI-APPCONFIG | M-GUI-APPCONFIG | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-CANONICAL-BUTTONS | M-GUI-CANONICAL-BUTTONS | planned | NO | NO | yes | yes | yes | — | — |
| V-M-GUI-DEBUG-DOCK | M-GUI-DEBUG-DOCK | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-HELP-MENU | M-GUI-HELP-MENU | blocked | yes | NO | yes | yes | yes | — | — |
| V-M-GUI-LOG-BRIDGE | M-GUI-LOG-BRIDGE | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-MAIN | M-GUI-MAIN | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-MARKER-MANAGER | M-GUI-MARKER-MANAGER | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-MARKER-PANEL | M-GUI-MARKER-PANEL | blocked | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-MENUBAR | M-GUI-MENUBAR | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-PIPELINE-CTRL | M-GUI-PIPELINE-CTRL | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-PIPELINE-WORKER | M-GUI-PIPELINE-WORKER | blocked | yes | NO | yes | yes | yes | — | — |
| V-M-GUI-ROI-SELECTOR | M-GUI-ROI-SELECTOR | blocked | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-SETTINGS | M-GUI-SETTINGS | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-SETTINGS-APP | M-GUI-SETTINGS-APP | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-SETTINGS-PROJECT | M-GUI-SETTINGS-PROJECT | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-SIGNAL-SPY | M-GUI-SIGNAL-SPY | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-SMART-SNAP | M-GUI-SMART-SNAP | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-STATUS | M-GUI-STATUS | blocked | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-SUBTITLE-EDITOR | M-GUI-SUBTITLE-EDITOR | blocked | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-SUBTITLE-OVERLAY | M-GUI-SUBTITLE-OVERLAY | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-TIMELINE | M-GUI-TIMELINE | blocked | NO | yes | yes | yes | yes | — | — |
| V-M-GUI-TIMELINE-CTRL | M-GUI-TIMELINE-CTRL | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-TIMELINE-V2 | M-GUI-TIMELINE-V2 | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-GUI-TIMELINE3 | M-GUI-TIMELINE3 | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-UPDATE-CTRL | M-GUI-UPDATE-CTRL | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-GUI-VIDEOPLAYER | M-GUI-VIDEOPLAYER | passed | yes | yes | yes | yes | yes | — | — |
| V-M-GUI-WINDOW-UI | M-GUI-WINDOW-UI | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-GUI-WORKER | M-GUI-WORKER | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-LLM-CLIENT | M-LLM-CLIENT | passed | yes | yes | yes | yes | yes | — | — |
| V-M-LLM-ORCHESTRATOR | M-LLM-ORCHESTRATOR | passed | yes | yes | yes | yes | yes | — | — |
| V-M-MCP-ADAPTER | M-MCP-ADAPTER | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-MCP-COMPOSITION | M-MCP-COMPOSITION | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-MCP-OPERATIONS | M-MCP-OPERATIONS | planned | yes | yes | yes | yes | yes | — | — |
| V-M-MCP-READ-TOOLS | M-MCP-READ-TOOLS | planned | yes | yes | yes | yes | yes | — | — |
| V-M-MCP-RELIABILITY | M-MCP-RELIABILITY | planned | NO | NO | yes | yes | yes | — | — |
| V-M-MCP-WRITE-TOOLS | M-MCP-WRITE-TOOLS | planned | yes | yes | yes | yes | yes | — | — |
| V-M-MD-EXPORT | M-MD-EXPORT | passed | yes | yes | yes | yes | yes | — | — |
| V-M-MODELS | M-MODELS | passed | yes | yes | yes | yes | yes | — | — |
| V-M-NOTES | M-NOTES | passed | yes | yes | yes | yes | yes | — | — |
| V-M-NOTES-PROCESSOR | M-NOTES-PROCESSOR | passed | yes | yes | yes | yes | yes | — | — |
| V-M-OPERATION-REGISTRY | M-OPERATION-REGISTRY | passed | yes | yes | yes | yes | yes | — | — |
| V-M-PERF-DETECT-ACCEPTANCE | Phase-18/Step-18.8 | planned | NO | NO | yes | yes | yes | — | — |
| V-M-PERF-DETECT-BASELINE | Phase-18/Step-18.1 | blocked | yes | yes | yes | yes | yes | — | — |
| V-M-PERF-DETECT-BOTTLENECK | Phase-18/Step-18.4 | done | NO | NO | yes | yes | yes | — | — |
| V-M-PERF-DETECT-HERMES-REBENCHMARK | Phase-18/Step-18.7 | planned | NO | NO | yes | yes | yes | — | — |
| V-M-PERF-DETECT-SHORT-BENCHMARK | Phase-18/Step-18.3 | passed | NO | NO | yes | yes | yes | — | — |
| V-M-PERF-DETECT-SHORT-REBENCHMARK | Phase-18/Step-18.6 | planned | NO | NO | yes | yes | yes | — | — |
| V-M-PERF-DETECT-TARGET-OPTIMIZATION-DISCRIMINATION | M-DETECT-TARGET-DISCRIMINATION-R2 | passed | yes | yes | yes | yes | yes | — | — |
| V-M-PERF-DETECT-TARGETED | Phase-18/Step-18.5 | planned | NO | NO | yes | yes | yes | — | — |
| V-M-PERF-DETECT-TWO-PASS | Phase-18/Step-18.2 | passed | yes | yes | yes | yes | yes | — | — |
| V-M-PERSIST-DETECTION | M-PERSIST-DETECTION | blocked | yes | NO | yes | yes | yes | — | — |
| V-M-PERSIST-DTO | M-PERSIST-DTO | passed | yes | yes | yes | yes | yes | — | — |
| V-M-PERSIST-MIGRATIONS | M-PERSIST-MIGRATIONS | passed | yes | yes | yes | yes | yes | — | — |
| V-M-PIPELINE-STATES | M-PIPELINE-STATES | planned | yes | yes | yes | yes | yes | — | — |
| V-M-PORT-ALIGNMENT | M-PORT-ALIGNMENT | blocked | yes | NO | yes | yes | yes | — | — |
| V-M-PORT-DETECTOR | M-PORT-DETECTOR | blocked | yes | NO | yes | yes | yes | — | — |
| V-M-PORT-EVENTS | M-PORT-EVENTS | planned | NO | NO | yes | yes | yes | — | — |
| V-M-PORT-EXPORT | M-PORT-EXPORT | blocked | yes | NO | yes | yes | yes | — | — |
| V-M-PORT-LLM | M-PORT-LLM | planned | NO | NO | yes | yes | yes | — | — |
| V-M-PORT-NOTES | M-PORT-NOTES | blocked | yes | NO | yes | yes | yes | — | — |
| V-M-PORT-PREVIEW | M-PORT-PREVIEW | blocked | yes | NO | yes | yes | yes | — | — |
| V-M-PORT-REPO | M-PORT-REPO | planned | yes | yes | yes | yes | yes | — | — |
| V-M-PPTX-EXPORT | M-PPTX-EXPORT | passed | yes | yes | yes | yes | yes | — | — |
| V-M-PROJECT | M-PROJECT | passed | yes | yes | yes | yes | yes | — | — |
| V-M-PROJECT-MODEL | M-PROJECT-MODEL | passed | yes | yes | yes | yes | yes | — | — |
| V-M-PROJECT-VALIDATOR | M-PROJECT-VALIDATOR | planned | yes | yes | yes | yes | yes | — | — |
| V-M-REF-APP-SERVICES | Phase-16/Step-5 | passed | yes | yes | yes | yes | yes | — | — |
| V-M-REF-CANONICAL-ROUTE | Phase-16/Step-9.5 | passed | NO | yes | yes | yes | yes | — | — |
| V-M-REF-CHAR-TESTS | Phase-16/Step-1 | blocked | NO | yes | yes | yes | yes | — | — |
| V-M-REF-CLEAN-WINDOWS | Phase-17/Step-6 | planned | NO | NO | yes | yes | yes | — | — |
| V-M-REF-CLI-ADAPTER | M-CLI-ADAPTER | passed | yes | yes | yes | yes | yes | — | — |
| V-M-REF-DETECTION-INPUT | Phase-16/Step-10 | passed | yes | yes | yes | yes | yes | — | — |
| V-M-REF-GUI-ADAPTER | M-GUI-PROJECT-CTRL | passed | yes | yes | yes | yes | yes | — | — |
| V-M-REF-LEGACY | Phase-16/Step-9 | passed | NO | yes | yes | yes | yes | — | — |
| V-M-REF-MCP-ADAPTER | Phase-16/Step-6 | passed | yes | yes | yes | yes | yes | — | — |
| V-M-REF-PACKAGED-MCP | Phase-17/Step-8 | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-REF-PACKAGING-INVENTORY | Phase-17/Step-1 | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-REF-PACKAGING-PARITY | Phase-17/Step-10.5 | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-REF-PERSISTENCE-STABILIZATION | Phase-16/Step-4.7 | passed | yes | yes | yes | yes | yes | — | — |
| V-M-REF-PRODUCT-IDENTITY | Phase-17/Step-0 | passed | yes | yes | yes | yes | yes | — | — |
| V-M-REF-STANDALONE-BUILD | Phase-17/Step-2 | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-REF-UPDATE-CHECKER | M-UPDATE-CHECKER | passed | yes | yes | yes | yes | yes | — | — |
| V-M-REF-WIN-INSTALLER | Phase-17/Step-7 | passed | yes | yes | yes | yes | yes | — | — |
| V-M-REF-WIN-RELEASE | Phase-17/Step-9 | blocked | NO | NO | yes | yes | yes | — | — |
| V-M-ROI | M-ROI | passed | yes | yes | yes | yes | yes | — | — |
| V-M-ROI-TOOL | M-ROI-TOOL | passed | yes | yes | yes | yes | yes | — | — |
| V-M-SEGMENTER | M-SEGMENTER | passed | yes | yes | yes | yes | yes | — | — |
| V-M-SLIDE-ANALYZER | M-SLIDE-ANALYZER | passed | yes | yes | yes | yes | yes | — | — |
| V-M-SLIDE-DETECTOR | M-SLIDE-DETECTOR | passed | yes | yes | yes | yes | yes | — | — |
| V-M-STRUCTURED-ERRORS | M-STRUCTURED-ERRORS | planned | yes | yes | yes | yes | yes | — | — |
| V-M-SUBTITLES | M-SUBTITLES | passed | yes | yes | yes | yes | yes | — | — |
| V-M-TIMELINE-MODEL | M-TIMELINE-MODEL | passed | yes | yes | yes | yes | yes | — | — |
| V-M-UI-STATE-READER | M-UI-STATE-READER | planned | yes | yes | yes | yes | yes | — | — |
| V-M-VIDEO-DECODE | M-VIDEO-DECODE | blocked | yes | yes | yes | yes | yes | — | — |