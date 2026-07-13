# Accepted Change Loss Register

| ID | Class | Severity | Accepted source | First missing/regressed | File/block | Accepted behavior | Later/current behavior | Recovery |
|---|---|---|---|---|---|---|---|---|
| A-001 | LOST_ACCEPTED_CHANGE | critical | `60d6cde`, blob `1792cacf` | `f07615c`, blob `0cdd7784` | `detect_slides.py/run_detect_slides` RSS lifecycle | document construction and JSON persistence remain inside protected detector lifecycle; peak is `max(before, sampled, after)` | document/persistence occur after `sampler.stop`; peak uses sampled value only; still present at `81875bc` | Restore accepted lifecycle in a recovery branch and add ordering/failure tests. |
| A-002 | LOST_ACCEPTED_CHANGE | high | `1c76062`-`60d6cde`, OpenCV blob `3b818b47` | `f07615c`, blob `24d726d7` | `opencv_iter_frames` | one successful `cap.read()` increments `frames_decoded` once | merge result increments twice; survives `8623cd2`; fixed by `81875bc`, blob `38b6ebf5` | Already repaired on perf branch; recover independently before further optimization. |
| A-003 | LOST_ACCEPTED_CHANGE | high | `60d6cde`, `slide_detector.py` blob `8e1c7488` | `f07615c`, blob `3902427c` | detection contracts and semantic blocks | ChangeEvent/detect contracts and process/debounce navigation anchors exist | load-bearing anchors removed and remain absent through `81875bc` | Restore accepted markup without changing detector behavior. |
| A-004 | LOST_ACCEPTED_CHANGE | high | `c8699fe`-`2b1507c`, installer blobs `f1ba34e6`/`94bdd721` | `2efe8a1`, blob `c5d94acd` | installer `[Files]` | installs repository `README.md` | accepted branding replay drops README; still absent at `8623cd2` | Decide whether README is required, then restore directive and installer verification. |
| A-005 | STALE_VARIANT_SURVIVED | medium | `49a077f` canonical assets | `f07615c` | `assets/branding/*-clean.*` | only canonical asset names | merge resurrects three byte-identical stale copies; removed by `8c5ea4e` | Resolved; retain anti-duplication checks. |
| A-006 | STALE_VARIANT_SURVIVED | high | both `f07615c` parents, build-meta blob `7252fc0b` | `f07615c`, blob `0a82883b` | `build_meta.py` | source defaults: empty SHA/tool, source build type | generated standalone values from `2b1507c` appear in merge tree; restored by `8c5ea4e` | Resolved; prohibit generated metadata in source commits. |
| A-007 | STALE_VARIANT_SURVIVED | medium | `49a077f` single icon directive | `f07615c` | `video2pptx.iss/[Setup]` | one `SetupIconFile` | duplicate identical directive remains at `8623cd2` | Remove duplicate in recovery branch; add static assertion. |
| A-008 | EVIDENCE_AHEAD_OF_CODE | high | `V-PERF-DETECT-BASELINE` at `60d6cde` | `f07615c` | RSS invariant | evidence claims `rss_peak_mb >= rss_before_mb` | code no longer enforces max with before/after | Reopen evidence until lifecycle is recovered and tested. |
| A-009 | EVIDENCE_AHEAD_OF_CODE | high | Phase 18 telemetry evidence | `f07615c` | OpenCV decode counter | documented decoded frame semantics imply one source frame/read | OpenCV values are doubled until `81875bc` | Keep F-0085 regression test and correct master lineage. |
| A-010 | CROSS_PHASE_OWNERSHIP | high | Phase 17 branding task | `b1bb67b` on Phase 18 line | branding/packaging/resources | Phase 17-owned implementation belongs on Phase 17 line | implementation and revert contaminate Phase 18 ancestry | Require explicit ownership packet for future cross-phase edits. |
| A-011 | CROSS_PHASE_OWNERSHIP | high | Phase 18 docs task | `b1cc67f` on Phase 17 line | Phase 18 report/verification | correction should preserve Phase 17 verification | broad replacement temporarily removes accepted Phase 17 evidence | Use merge-aware XML updates and scoped verification. |

## Tests that should have caught losses

- A deterministic RSS test asserting `start < document construction < persistence < stop`
  and `peak >= before, after`, including persistence exceptions.
- Exact OpenCV and PyAV source-frame/conversion/byte counter tests.
- A GRACE anchor-preservation lint gate for modified governed modules.
- Installer file-list tests requiring accepted payloads and unique directives.
