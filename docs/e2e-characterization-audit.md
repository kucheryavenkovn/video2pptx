# E2E Characterization Audit

Date: 2026-07-10
Branch: `test/mcp-e2e-hardening`
Scope: E2E-001 through E2E-015 before Phase-16 refactoring.

The existing scenario file is a catalog, not a trusted characterization suite. Known defects are not accepted as desired behavior. Characterization assertions compare structural invariants and normalized metadata rather than binary files byte-for-byte.

| Scenario | Current classification | Evidence / missing behavior |
| --- | --- | --- |
| E2E-001 Startup | executable but failing | Requires externally started GUI/MCP and previously lacked `repo_dir`; does not validate initial button states or startup logs. |
| E2E-002 Create Project | executable but failing | Shared mutable session project; project-name assertion was bypassed; no terminal operation wait or GUI title assertion. |
| E2E-003 Import Video | executable but failing | Fixed sleep instead of operation lifecycle; duration, timeline, and button assertions missing. |
| E2E-004 Import Subtitles | incomplete | Performs the call but has no substantive postcondition assertions. |
| E2E-005 Playback | environment-dependent | No scenario implementation. Requires multimedia capability in an interactive session. |
| E2E-006 Quick Preview | incomplete | Runner calls the service directly; no MCP/GUI route, idempotency, or no-slide side-effect assertions. |
| E2E-007 Detect | executable but failing | Existing test does not require successful terminal status and only weakly compares state views. |
| E2E-008 Align Dry Run | incomplete | Direct service call only; no before/after project and file comparison. |
| E2E-009 Align Apply | incomplete | No count/order preservation, idempotency, cue metrics, or GUI refresh assertion. |
| E2E-010 Process Notes | incomplete | Not implemented through MCP. |
| E2E-011 Slide CRUD | incomplete | No UID-based add/move/resize/frame/clear/delete sequence or persistence round-trip. |
| E2E-012 Markdown | executable but failing | Does not compare slide count or validate all image references; runner observations do not affect pass/fail. |
| E2E-013 PPTX | environment-dependent | Only ZIP signature checked; `python-pptx` reopen, slide count, media and relationships are not verified. |
| E2E-014 Save/Close/Open | executable but failing | Fixed sleep and incomplete restored-state assertions. |
| E2E-015 Auto | incomplete | No clean-project full/resume/force scenario. |

## Phase-1 characterization gates

1. Synthetic fixture is generated deterministically when absent and decodes to four visible sections.
2. Direct service and CLI Detect run in separate project directories and produce equivalent normalized slide structure.
3. Real GUI subprocess and MCP transport are controlled by a dedicated harness; every write waits for terminal operation state.
4. Project, timeline, `project.json`, and `slides.json` are compared after each mutating operation.
5. Known defects are recorded in `docs/findings.md` and receive failing regression tests; they are not frozen as contracts.

## Binary comparison policy

- Compare slide count, ordering, intervals, representative timestamps, image existence and image dimensions.
- Compare Markdown structure and normalized paths, not exact whitespace.
- Validate PPTX as Open XML and compare slide/media counts, not ZIP bytes.
- Ignore absolute output directory differences between adapters.
