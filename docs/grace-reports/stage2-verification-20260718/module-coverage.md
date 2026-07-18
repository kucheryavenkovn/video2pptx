# Stage 2 — Module Coverage Map

- Total modules: 120
- Total V-M entries: 144
- Modules without verification entry: 0

## Coverage classification
- VERIFIED_PASSED: 63
- VERIFIED_FAILED: 0
- VERIFICATION_PLANNED: 28
- VERIFICATION_BLOCKED: 27
- MISSING_VERIFICATION_ENTRY: 0
- STALE_VERIFICATION_ENTRY: 0
- NO_EXECUTABLE_EVIDENCE: 2

## Existing V-M entries missing follow-up structure
- entries missing wave-checks: 114
- entries missing phase-checks: 116
- entries missing observable-evidence: 0
- entries missing scenarios: 0
- entries with test files missing on disk: 0

## Modules without verification entry

## Full coverage table

| Module | Status | V-M | V-Status | Wave | Phase | Obs | Scen | Test-missing | Classification |
|--------|--------|-----|----------|------|-------|-----|------|--------------|----------------|
| M-ADAPTERS | implemented | V-M-ADAPTERS | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-APP-ALIGN | implemented | V-M-APP-ALIGN | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-APP-AUTO | implemented | V-M-APP-AUTO | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-APP-BOOTSTRAP | active | V-M-APP-BOOTSTRAP | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-APP-BUILD-META | active | V-M-APP-BUILD-META | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-APP-COMMON | implemented | V-M-APP-COMMON | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-APP-DETECT | implemented | V-M-APP-DETECT | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-APP-EXPORT | implemented | V-M-APP-EXPORT | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-APP-IDENTITY | active | V-M-APP-IDENTITY | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-APP-INPUT-RESOLVER | active | V-M-APP-INPUT-RESOLVER | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-APP-LLM | planned | V-M-APP-LLM | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-APP-NOTES | implemented | V-M-APP-NOTES | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-APP-PREVIEW | implemented | V-M-APP-PREVIEW | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-APP-PROJECT | planned | V-M-APP-PROJECT | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-APP-SERVICE | partial | V-M-APP-SERVICE | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-APP-VALIDATE | implemented | V-M-APP-VALIDATE | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-ARCH-OVERVIEW | planned | V-M-ARCH-OVERVIEW | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-ATOMIC-JSON | planned | V-M-ATOMIC-JSON | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-AUTO-ALIGN | partial | V-M-AUTO-ALIGN | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-BACKEND-OPENCV | implemented | V-M-BACKEND-OPENCV | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-BACKEND-PYAV | implemented | V-M-BACKEND-PYAV | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-BACKENDS | implemented | V-M-BACKENDS | in_progress | NO | NO | yes | yes | — | NO_EXECUTABLE_EVIDENCE |
| M-CANONICAL-COMMANDS | planned | V-M-CANONICAL-COMMANDS | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-CLI | implemented | V-M-CLI | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-CLI-ADAPTER | active | V-M-REF-CLI-ADAPTER | passed | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-COLAB | implemented | V-M-COLAB | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-CONFIG | implemented | V-M-CONFIG | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-CONFIRM-POLICY | planned | V-M-CONFIRM-POLICY | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-DEBUG-ACTION | implemented | V-M-DEBUG-ACTION | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-DEBUG-EXPORT | implemented | V-M-DEBUG-EXPORT | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-DEBUG-MCP | implemented | V-M-DEBUG-MCP | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-DEDUPE | implemented | V-M-DEDUPE | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-DESKTOP-BOOTSTRAP | active | V-M-DESKTOP-BOOTSTRAP | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-DETECT-BENCHMARK | active | V-M-DETECT-BENCHMARK | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-DETECT-METRICS | active | V-M-DETECT-METRICS | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-DETECT-PERF-DECISION | done | V-M-DETECT-PERF-DECISION | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-DETECT-SLIDES | implemented | V-M-DETECT-SLIDES | in_progress | NO | NO | yes | yes | — | NO_EXECUTABLE_EVIDENCE |
| M-DETECT-TARGET-DISCRIMINATION-R2 | verified | V-M-PERF-DETECT-TARGET-OPTIMIZATION-DISCRIMINATION | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-DOMAIN-EVENTS | planned | V-M-DOMAIN-EVENTS | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-DOMAIN-PROJECT | implemented | V-M-DOMAIN-PROJECT | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-DOMAIN-SLIDE | implemented | V-M-DOMAIN-SLIDE | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-DOMAIN-STATE | implemented | V-M-DOMAIN-STATE | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-DOMAIN-VALUE | implemented | V-M-DOMAIN-VALUE | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-E2E-RUNNER | partial | V-M-E2E-RUNNER | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-E2E-SCENARIOS | planned | V-M-E2E-SCENARIOS | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-E2E-SNAPSHOT | planned | V-M-E2E-SNAPSHOT | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-FILE-REPO | implemented | V-M-FILE-REPO | passed | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-FRAME-FEATURES | implemented | V-M-FRAME-FEATURES | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GITHUB-PROVIDER | implemented | V-M-GITHUB-PROVIDER | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-ABOUT | active | V-M-GUI-ABOUT | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-APPCONFIG | implemented | V-M-GUI-APPCONFIG | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-CANONICAL-BUTTONS | planned | V-M-GUI-CANONICAL-BUTTONS | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-GUI-DEBUG-DOCK | implemented | V-M-GUI-DEBUG-DOCK | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-HELP-MENU | active | V-M-GUI-HELP-MENU | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-LOG-BRIDGE | implemented | V-M-GUI-LOG-BRIDGE | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-MAIN | implemented | V-M-GUI-MAIN | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-MARKER-MANAGER | implemented | V-M-GUI-MARKER-MANAGER | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-MARKER-PANEL | implemented | V-M-GUI-MARKER-PANEL | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-MENUBAR | implemented | V-M-GUI-MENUBAR | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-PIPELINE-CTRL | active | V-M-GUI-PIPELINE-CTRL | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-PIPELINE-WORKER | active | V-M-GUI-PIPELINE-WORKER | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-PROJECT-CTRL | active | V-M-REF-GUI-ADAPTER | passed | yes | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-ROI-SELECTOR | implemented | V-M-GUI-ROI-SELECTOR | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-SETTINGS | implemented | V-M-GUI-SETTINGS | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-SETTINGS-APP | implemented | V-M-GUI-SETTINGS-APP | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-SETTINGS-PROJECT | implemented | V-M-GUI-SETTINGS-PROJECT | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-SIGNAL-SPY | implemented | V-M-GUI-SIGNAL-SPY | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-SMART-SNAP | implemented | V-M-GUI-SMART-SNAP | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-STATUS | implemented | V-M-GUI-STATUS | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-SUBTITLE-EDITOR | implemented | V-M-GUI-SUBTITLE-EDITOR | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-SUBTITLE-OVERLAY | implemented | V-M-GUI-SUBTITLE-OVERLAY | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-TIMELINE | implemented | V-M-GUI-TIMELINE | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-TIMELINE-CTRL | active | V-M-GUI-TIMELINE-CTRL | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-TIMELINE-V2 | implemented | V-M-GUI-TIMELINE-V2 | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-TIMELINE3 | implemented | V-M-GUI-TIMELINE3 | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-UPDATE-CTRL | implemented | V-M-GUI-UPDATE-CTRL | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-VIDEOPLAYER | implemented | V-M-GUI-VIDEOPLAYER | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-GUI-WINDOW-UI | active | V-M-GUI-WINDOW-UI | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-GUI-WORKER | implemented | V-M-GUI-WORKER | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-LLM-CLIENT | implemented | V-M-LLM-CLIENT | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-LLM-ORCHESTRATOR | implemented | V-M-LLM-ORCHESTRATOR | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-MCP-ADAPTER | implemented | V-M-MCP-ADAPTER | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-MCP-COMPOSITION | implemented | V-M-MCP-COMPOSITION | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-MCP-OPERATIONS | planned | V-M-MCP-OPERATIONS | planned | yes | yes | yes | yes | — | VERIFICATION_PLANNED |
| M-MCP-READ-TOOLS | planned | V-M-MCP-READ-TOOLS | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-MCP-RELIABILITY | planned | V-M-MCP-RELIABILITY | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-MCP-WRITE-TOOLS | planned | V-M-MCP-WRITE-TOOLS | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-MD-EXPORT | implemented | V-M-MD-EXPORT | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-MODELS | implemented | V-M-MODELS | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-NOTES | implemented | V-M-NOTES | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-NOTES-PROCESSOR | implemented | V-M-NOTES-PROCESSOR | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-OPERATION-REGISTRY | implemented | V-M-OPERATION-REGISTRY | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-PERSIST-DETECTION | active | V-M-PERSIST-DETECTION | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-PERSIST-DTO | implemented | V-M-PERSIST-DTO | passed | yes | NO | yes | yes | — | VERIFIED_PASSED |
| M-PERSIST-MIGRATIONS | implemented | V-M-PERSIST-MIGRATIONS | passed | yes | yes | yes | yes | — | VERIFIED_PASSED |
| M-PIPELINE | implemented | V-M-CLI-E2E | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-PIPELINE-STATES | partial | V-M-PIPELINE-STATES | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-PORT-ALIGNMENT | implemented | V-M-PORT-ALIGNMENT | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-PORT-DETECTOR | implemented | V-M-PORT-DETECTOR | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-PORT-EVENTS | planned | V-M-PORT-EVENTS | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-PORT-EXPORT | implemented | V-M-PORT-EXPORT | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-PORT-LLM | planned | V-M-PORT-LLM | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-PORT-NOTES | implemented | V-M-PORT-NOTES | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-PORT-PREVIEW | implemented | V-M-PORT-PREVIEW | blocked | NO | NO | yes | yes | — | VERIFICATION_BLOCKED |
| M-PORT-REPO | implemented | V-M-PORT-REPO | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-PPTX-EXPORT | implemented | V-M-PPTX-EXPORT | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-PROJECT | implemented | V-M-PROJECT | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-PROJECT-MODEL | implemented | V-M-PROJECT-MODEL | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-PROJECT-VALIDATOR | planned | V-M-PROJECT-VALIDATOR | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-ROI | implemented | V-M-ROI | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-ROI-TOOL | implemented | V-M-ROI-TOOL | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-SEGMENTER | implemented | V-M-SEGMENTER | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-SLIDE-ANALYZER | implemented | V-M-SLIDE-ANALYZER | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-SLIDE-DETECTOR | implemented | V-M-SLIDE-DETECTOR | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-STRUCTURED-ERRORS | planned | V-M-STRUCTURED-ERRORS | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-SUBTITLES | implemented | V-M-SUBTITLES | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-TIMELINE-MODEL | implemented | V-M-TIMELINE-MODEL | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-UI-STATE-READER | planned | V-M-UI-STATE-READER | planned | NO | NO | yes | yes | — | VERIFICATION_PLANNED |
| M-UPDATE-CHECKER | implemented | V-M-REF-UPDATE-CHECKER | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |
| M-VIDEO-DECODE | implemented | V-M-VIDEO-DECODE | passed | NO | NO | yes | yes | — | VERIFIED_PASSED |