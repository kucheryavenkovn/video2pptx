# Duplicate Implementations

## D-001: Qt resource branding integration

- Commits: `b1bb67b`, `2efe8a1`; inverse commit `be39359`.
- Common merge base: `142c5f7`.
- Relationship: **DUPLICATE_IMPLEMENTATION / REVERT_AND_REIMPLEMENT**.
- The seven target blobs are byte-identical at `b1bb67b` and `2efe8a1`:
  installer, PyInstaller spec, branding sync script, resource package init,
  `branding.qrc`, generated `branding_rc.py`, and branding tests.
- Stable patch IDs differ because the commits were independently applied to
  diverged parent trees.
- `be39359` exactly restores the pre-branding `43abab6` tree.
- Neither implementation actually added the claimed desktop/About runtime
  wiring. `21ba94e` is a corrective LOST_WIRING_REPAIR, and `49a077f` is the
  FINAL_ACCEPTED_VARIANT with compact header branding and canonical filenames.

## D-002: Step 18.2 evidence correction

- Commits: `b1cc67f`, `2aec742`; follow-up `6da09c0`.
- Relationship: **PARTIAL_DUPLICATE**.
- `b1cc67f` and `2aec742` produce identical result blobs for the Phase 18 report
  (`96f8d6a...`) and verification plan (`6b714fa...`) on diverged lines.
- They are not patch-equivalent. The Phase 17-context `b1cc67f` is anomalously
  broad and displaces Phase 17 verification entries; `6da09c0` restores them,
  producing verification blob `723ccc5...` while retaining the report blob.

## Other repeated claims

No additional exact stable-patch-ID duplicate groups were found among July 12
non-merge commits. The `*-clean.*` plus canonical assets were a merge-created
duplicate state, not an independently duplicated implementation commit.
