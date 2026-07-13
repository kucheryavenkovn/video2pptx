# Provenance Matrix

## Phase 18 runtime files

| File | Accepted Phase 18 | Integration `f07615c` | Master `8623cd2` | Perf `81875bc` | Classification |
|---|---|---|---|---|---|
| `detect_slides.py` | `1792cacf` (`60d6cde`) | `0cdd7784` | `0cdd7784` | `0cdd7784` | LOST_ACCEPTED_CHANGE: RSS lifecycle/peak and contracts. TwoPass survives. |
| `slide_detector.py` | `8e1c7488` | `3902427c` | `3902427c` | `3902427c` | LOST_ACCEPTED_CHANGE: contracts/blocks; executable score logic preserved. |
| `opencv_backend.py` | `3b818b47` | `24d726d7` | `24d726d7` | `38b6ebf5` | LOST_ACCEPTED_CHANGE, repaired only on perf. |
| `pyav_backend.py` | `9bb9443d` | `0e0924fd` | `0e0924fd` | `0e0924fd` | BENIGN_DIVERGENCE: comments/format only; executable telemetry preserved. |
| `detection_metrics.py` | `a4116cea` | `a4116cea` | `a4116cea` | `a4116cea` | Exact accepted implementation preserved. |

## detect_slides semantic sequence

| Commit | Decoder passes | RSS lifecycle/peak | Document/persistence order |
|---|---:|---|---|
| `3472e62` | 3 | no strengthened lifecycle | normal post-detection persistence |
| `7919dc3` | 2 | no strengthened lifecycle | TwoPass merge accepted |
| `43abab6` | 2 | sampler start/stop in finally | persistence outside detector try |
| `b879f5e`, `60d6cde` | 2 | peak=max(before,sampled,after) | document and persistence protected before finally/stop |
| `f07615c` through `81875bc` | 2 | sampled-only peak | stop occurs before document construction/persistence |

## Phase 17 implementation files

| Area/file | Accepted state | Integration/current state | Classification |
|---|---|---|---|
| Branding resources | `49a077f`, canonical assets and runtime wiring | wiring preserved; stale clean assets removed by `8c5ea4e` | FINAL_ACCEPTED_VARIANT with resolved stale state. |
| `build_meta.py` | source blob `7252fc0b` in both merge parents | contaminated at `f07615c`, restored by `8c5ea4e` | STALE_VARIANT_SURVIVED, resolved. |
| Installer README | present from `c8699fe` through `2b1507c` | absent from `2efe8a1` through `8623cd2` | LOST_ACCEPTED_CHANGE. |
| Installer icon directive | one at `49a077f` | duplicate at `f07615c` and `8623cd2` | STALE_VARIANT_SURVIVED. |
| Update checker | accepted at `c8699fe` | byte-identical through `8623cd2` | BENIGN_DIVERGENCE / preserved. |
| `build.ps1` | corrected blob `cd2e4c9e` | same at master | preserved. |
| `smoke-test.ps1` | corrected blob `032ae4b6` | same at master | preserved. |
| release workflow | corrected blob `c41d1ab4` | same at master | preserved. |

## Historical overlapping ownership

Sixteen files were touched by both histories, including reverted branding work.
They are listed in `overlap-files.txt`. The five GRACE documents and the
installer/resource bundle are the highest conflict-risk ownership surfaces.
