# Stage 2 — Module Coverage Map

- Total modules: 120
- Total V-M entries: 144
- Modules without verification entry: 0

## Verification status counts
- passed: 58
- blocked: 32
- planned: 28
- in_progress: 2
- failed: 0

## Coverage classification
- VERIFIED_PASSED: 58
- VERIFICATION_BLOCKED: 32
- VERIFICATION_PLANNED: 28
- VERIFICATION_IN_PROGRESS: 2
- VERIFIED_FAILED: 0
- MISSING_VERIFICATION_ENTRY: 0
- NO_EXECUTABLE_EVIDENCE: 0

## Existing V-M entries missing follow-up structure
- entries missing module-checks: 27
- entries missing wave-follow-up: 35
- entries missing phase-follow-up: 0
- entries missing observable-evidence: 0
- entries missing scenarios: 0
- entries with test files missing on disk: 0

## Modules without verification entry

## Full coverage table

| Module | Status | V-M | V-Status | Module-chk | Wave | Phase | Obs | Scen | Test-missing | Classification |
|--------|--------|-----|----------|-----------|------|-------|-----|------|--------------|----------------|
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
| M-VIDEO-DECODE | implemented | V-M-VIDEO-DECODE | passed | yes | yes | yes | yes | yes | — | VERIFIED_PASSED |