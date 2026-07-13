# GRACE / Code Consistency

## Result: FAIL

1. At `f07615c` and current endpoints, verification evidence claims an RSS peak
   invariant that the weaker sampled-only calculation does not guarantee.
2. OpenCV telemetry evidence remained accepted while the merge-created duplicate
   increment doubled decoded-frame counts through `8623cd2`.
3. Accepted `slide_detector.py` contracts and semantic blocks from `60d6cde`
   disappeared at `f07615c`, while shared Phase 18 status/evidence remained accepted.
4. `b1cc67f` demonstrates non-merge-aware shared-artifact replacement: it added
   Phase 18 evidence on the Phase 17 line while removing Phase 17 verification
   blocks; `6da09c0` had to restore them.
5. Phase 18 parity tests cover detector output but not telemetry exactness,
   resource lifecycle boundaries, or semantic markup preservation.

The audit does not alter GRACE status. Proposed recovery findings are A-001
through A-011 and must be registered on a dedicated recovery branch after review.
