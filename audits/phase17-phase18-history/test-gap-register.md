# Test Gap Register

| ID | Class | Property not protected | Consequence | Current state |
|---|---|---|---|---|
| T-001 | TEST_GAP | RSS sampler ordering through document construction and JSON persistence | `f07615c` moved stop before persistence | Open at `81875bc`. |
| T-002 | TEST_GAP | `rss_peak_mb` deterministically bounds before and after RSS | weaker sampled-only peak survived | Open. |
| T-003 | TEST_GAP | one OpenCV source read equals one decoded-frame count | 2x counter survived to master | Added at `81875bc`, absent on master. |
| T-004 | TEST_GAP | exact PyAV decoded/conversion/transfer semantics | current benchmark depends on unguarded PyAV telemetry | Open. |
| T-005 | TEST_GAP | accepted installer payload includes README and directives are unique | README loss and duplicate icon directive survived | Open. |
| T-006 | TEST_GAP | branding task tests runtime desktop/About imports, not only resources | both initial implementations omitted claimed wiring | Partially repaired by later tests; historical gap confirmed. |
| T-007 | TEST_GAP | semantic anchors/contracts survive conflict resolution | `f07615c` stripped accepted detection anchors | Open. |

Historical tests were inspected selectively. No historical worktree was modified,
and no current tests were copied into old trees as purported contemporaneous evidence.
