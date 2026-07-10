# E2E Characterization Audit

Date: 2026-07-10
Branch: `test/mcp-e2e-hardening`
Scope: E2E-001 through E2E-015 before Phase-16 refactoring.

The existing scenario file is a catalog, not a trusted characterization suite. Known defects are not accepted as desired behavior. Characterization assertions compare structural invariants and normalized metadata rather than binary files byte-for-byte.

| Scenario | Current classification | Evidence / missing behavior |
| --- | --- | --- |
| E2E-001 Startup | executable and passing | Dedicated subprocess harness verifies owned PID/instance, health, initialize, tools/list, initial UI state, logs, and cleanup. |
| E2E-002 Create Project | executable and passing | Real MCP operation is awaited; project name/path, model state, window title, save button, and disk artifact are asserted. |
| E2E-003 Import Video | executable and passing | Real GUI+MCP test verifies video path in project, subtitle auto-detection, Detect/Preview button enablement. |
| E2E-004 Import Subtitles | executable and passing | Real GUI+MCP test verifies subtitle path, four monotonic subtitle clips in timeline with correct boundaries. |
| E2E-005 Playback | environment-dependent and blocked | Video transport MCP tools route to ProjectModel which lacks seek/play/pause methods (F-0058). Also requires multimedia backend in offscreen Qt. Deferred to Phase 8. |
| E2E-006 Quick Preview | executable and passing | Real GUI+MCP test runs twice, verifies waveform replacement and absence of slide/export artifacts. CLI adapter remains missing (F-0046). |
| E2E-007 Detect | executable and passing | Real GUI+MCP test verifies terminal status and synchronized project/timeline/disk/UI views without reopen. |
| E2E-008 Align Dry Run | executable and passing | Real GUI+MCP test verifies no confirmation requirement, byte-identical project/slides files, unchanged timeline/state, and no report artifact. |
| E2E-009 Align Apply | executable and passing | Real GUI+MCP test verifies terminal synchronization, interval invariants, count/order preservation, report creation, pipeline state, and idempotent second apply. |
| E2E-010 Process Notes | executable and passing | Real GUI+MCP test verifies transcript enrichment, atomic slides.json update, and pipeline state after process_notes. |
| E2E-011 Slide CRUD | executable and passing | Real GUI+MCP test covers UID-based add/get/resize/move/set-frame/clear/delete and compares project, timeline, `project.json`, and `slides.json`. |
| E2E-012 Markdown | executable and passing | Real GUI+MCP test validates project title, Marp metadata, slide/image/timecode counts, normalized paths, existing references, artifact path, and pipeline state. |
| E2E-013 PPTX | executable and passing | Real GUI+MCP test reopens through `python-pptx`, verifies title, source slide count, embedded picture per slide, notes, artifact path, and pipeline state. |
| E2E-014 Save/Close/Open | executable and passing | Real GUI+MCP test compares project, normalized timeline, pipeline state, persisted UID/order/intervals/images, score waveform, and both JSON files across close/open. |
| E2E-015 Auto | executable and passing | Real GUI+MCP test verifies detect+align+notes+export pipeline, all pipeline flags, all artifacts, and slide count in a single clean project. |

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
