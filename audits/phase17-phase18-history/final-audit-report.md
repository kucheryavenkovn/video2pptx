# Phase 17 / Phase 18 Historical Implementation Forensic Audit

## Scope

- Date window: `2026-07-12 00:00:00` to `2026-07-13 00:00:00 +03:00`.
- All local/remote refs after `git fetch --all --prune`; all 28 requested SHAs exist.
- 79 all-ref objects inventoried, 77 ordinary project commits after excluding two stash objects.
- Relevant named Phase 17 candidate set: 16 commits (including the shared base and
  cross-line branding/revert commits). Complete-window changed-file classification
  finds 15 Phase 17 commits, 7 Phase 18 commits, and one cross-phase production commit
  (`43abab6`, detection metrics plus branding asset deletions). Five
  integration/revert/fixup endpoints were audited.
- 23 detached clean worktrees were created under an approved local temp root.

## Reconstructed history

Phase 17 and Phase 18 diverged at `142c5f7`. Phase 18 is linear from `3472e62`
through `60d6cde`, except the independently applied/reverted Phase 17 branding
payload. Phase 17 reaches `49a077f` through its own packaging/branding line and
two Phase 18 docs commits. `f07615c` merges the two accepted tips and is the first
semantic loss point. `8623cd2` is an ancestry-only merge whose tree exactly equals
`8c5ea4e`; it introduces no new content loss.

## Duplicate implementation groups

1. D-001 Qt resource branding: `b1bb67b` and `2efe8a1`, duplicate target blobs on
   divergent histories; `be39359` reverts A; `21ba94e` repairs omitted wiring.
2. D-002 Step 18.2 docs: `b1cc67f` and `2aec742` produce duplicate result state;
   `6da09c0` is a necessary fixup, not an identical duplicate.

## Overlapping file ownership

Sixteen files were historically touched by both lines. The full list is in
`overlap-files.txt`. Shared GRACE XML, installer/spec, generated Qt resources,
branding tests/assets, and Phase 18 report are the conflict-heavy surfaces.

## Confirmed LOST_ACCEPTED_CHANGE

- **A-001, critical:** accepted complete RSS lifecycle and peak invariant from
  `60d6cde:detect_slides.py` blob `1792cacf` regress at `f07615c` blob `0cdd7784`.
- **A-002, high:** accepted one-read/one-count OpenCV telemetry (`3b818b47`) becomes
  duplicate-count telemetry at `f07615c` (`24d726d7`), surviving master and fixed
  only by `81875bc` (`38b6ebf5`).
- **A-003, high:** accepted detection contracts/semantic blocks (`8e1c7488`) are
  stripped by `f07615c` (`3902427c`) and remain absent.
- **A-004, high:** accepted installer README payload is dropped by the divergent
  branding replay `2efe8a1` and remains absent on master.

## Confirmed STALE_VARIANT_SURVIVED

- **A-005:** `f07615c` resurrects three obsolete `*-clean.*` assets beside canonical
  names; resolved by `8c5ea4e`.
- **A-006:** `f07615c` synthesizes generated standalone build metadata although both
  parents contain clean source defaults; resolved by `8c5ea4e`.
- **A-007:** duplicate `SetupIconFile` survives at current master.

## Confirmed EVIDENCE_AHEAD_OF_CODE

- **A-008:** RSS evidence claims peak bounds after code loses the max invariant.
- **A-009:** telemetry evidence remains accepted while OpenCV decoded count is 2x.

## CROSS_PHASE_OWNERSHIP

- **A-010:** Phase 17 branding implementation/revert occurred on the Phase 18 line.
- **A-011:** Phase 18 evidence was independently applied on the Phase 17 line and
  initially displaced accepted Phase 17 verification content.

## TEST_GAP

Seven properties are unprotected or historically unprotected: RSS ordering,
RSS deterministic peak bounds, exact OpenCV counters, exact PyAV counters/bytes,
installer payload uniqueness/completeness, runtime branding wiring, and semantic
anchor preservation. See `test-gap-register.md`.

## BENIGN_DIVERGENCE

- PyAV accepted executable decode/hwaccel/counter/conversion behavior survives;
  its blob difference at integration is comments/formatting only.
- Update checker/service/provider/controller behavior is byte-identical through master.
- `8623cd2` is a content-identical ancestry merge of `8c5ea4e`.

## Current master risk

Master `8623cd2` still has A-001 (RSS lifecycle/peak), A-002 (OpenCV 2x counter),
A-003 (missing semantic structure), A-004 (installer README loss), A-007 (duplicate
installer directive), A-008/A-009 evidence drift, and the associated test gaps.

## Current perf branch risk

Perf `81875bc` fixes A-002 and adds its focused test. It still has A-001, A-003,
A-004, A-007, RSS evidence drift, absent exact PyAV telemetry tests, and an accepted
benchmark whose effective backend is PyAV. PyAV executable behavior itself was not
lost, but further optimization should wait for recovery and evidence revalidation.

## Recommended recovery order

1. Restore accepted `detect_slides.py` RSS lifecycle/peak semantics and add deterministic
   success/failure ordering tests.
2. Port the `81875bc` OpenCV counter fix/test onto the recovery lineage independently.
3. Add exact PyAV decoded/conversion/transfer telemetry tests before trusting new profiles.
4. Restore accepted detection contracts/semantic anchors and run scoped GRACE review.
5. Resolve installer README intent and duplicate icon directive with packaging tests.
6. Reconcile verification status/evidence only after code and tests pass.
7. Re-run the immutable short benchmark before any optimization decision proceeds.

## Stop/go decision

**HISTORICAL_RECOVERY_REQUIRED**

No product code, tests, GRACE status, or historical worktree was changed by this audit.
