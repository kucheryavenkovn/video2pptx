# Phase 18 Short Benchmark: hermes-600s-20260713-8623cd2

## Protocol

Fixed Hermes interval 00:00:00 to 00:10:00, stream-copied without re-encoding. One warm-up preceded three recorded DetectionService runs; cProfile was separate.

- Median detect elapsed: 245.960049 s
- Min / max: 242.126841 s / 247.533700 s
- Real-time multiplier: 0.409922
- Processing x realtime: 2.439488
- Signature: `8cc06c6accb055fb6fed461f2f4a96f0b288ef864b9423000b6f59d9ab56bc85` (identical in all runs)

## Ranked Bottlenecks

| Rank | Stage | Seconds | % median detect | Measurement | Notes |
|---:|---|---:|---:|---|---|
| 1 | unattributed_residual | 96.728170 | 39.327% | derived residual | not a measured timer; includes decode/open/service/persistence |
| 2 | extract_features | 88.616671 | 36.029% | median accumulated stage timer | median across three recorded runs |
| 3 | pass2_collect | 53.669377 | 21.820% | median accumulated stage timer | median across three recorded runs |
| 4 | pass2_dedupe | 6.235529 | 2.535% | median accumulated stage timer | median across three recorded runs |
| 5 | roi | 0.253670 | 0.103% | median accumulated stage timer | median across three recorded runs |
| 6 | visual_distance | 0.241787 | 0.098% | median accumulated stage timer | median across three recorded runs |
| 7 | threshold | 0.127240 | 0.052% | median accumulated stage timer | median across three recorded runs |
| 8 | pass2_screenshots | 0.085710 | 0.035% | median accumulated stage timer | median across three recorded runs |
| 9 | debounce | 0.001895 | 0.001% | median accumulated stage timer | median across three recorded runs |

## Decision

**DECODE_PROFILE** -> `perf/phase18-decode-profile`

Median unattributed residual is a material share of detect elapsed; profile packet.decode cumulative time exceeds feature extraction, while decoded-frame and RGB-transfer volumes are high.

Threshold is not material. Feature extraction is substantial, but decode is the stronger next profiling hypothesis because decode cumulative time plus the uninstrumented residual and transfer volume indicate producer-side cost. No optimization is implemented here.

Full-Hermes acceptance remains pending; no short-clip speedup percentage or accepted full-run projection is claimed.
