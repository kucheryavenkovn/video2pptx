# Commit DAG

## Verified split and joins

```text
142c5f766bc3a81e6e1729d229e9312f4a2a3ec4
|-- Phase 17: c8699fe -> ed60d33 -> fadd1fd -> 2b1507c -> 2efe8a1
|              -> 21ba94e -> b1cc67f -> 6da09c0 -> 49a077f
`-- Phase 18: 3472e62 -> 7919dc3 -> 1c76062 -> 43abab6 -> b1bb67b
               -> be39359 -> b879f5e -> 60d6cde

f07615c = merge(49a077f, 60d6cde)
83c0d10 -> 8c5ea4e
8623cd2 = merge(49a077f, 8c5ea4e), tree identical to 8c5ea4e
81875bc = Step 18.3 evidence and OpenCV telemetry repair
```

## Proven relationships

- `merge-base(b1bb67b, 2efe8a1) = 142c5f7`; neither is ancestor of the other.
- `merge-base(3472e62, 60d6cde) = 3472e62`; the Phase 18 sequence is linear.
- `merge-base(49a077f, 60d6cde) = 142c5f7`.
- `f07615c` is the first Phase 17/18 content merge.
- `f07615c` is an ancestor of `8623cd2`.
- `git diff 8c5ea4e 8623cd2` is empty; the latter records ancestry only.

## Docs side lines

`2aec742` is the Phase 18-line docs correction, parented by `60d6cde`. `b1cc67f`
is an independent Phase 17-line correction, parented by `21ba94e`; both produce
the same report and verification-plan blobs. `6da09c0` follows `b1cc67f` and
restores Phase 17 verification blocks that the broad `b1cc67f` tree replacement
had displaced.

## Date-window inventory

The all-ref `2026-07-12 +03:00` window contains 79 objects: 77 non-merge commits
and two merge-shaped objects (`f07615c` and stash object `5942ab8`). Excluding
the two stash objects (`5942ab8`, `335f564`) leaves 77 ordinary project commits.
`8623cd2` and `81875bc` fall outside the date window but are audited endpoints.
