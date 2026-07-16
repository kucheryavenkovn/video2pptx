# Corrected Target Optimization Discrimination

* Reference repeatability: `REFERENCE_EXACTLY_REPEATABLE`
* C1: `NOT_VIABLE_EXACT_PARITY_FAIL`; causal classification `ROOT_CAUSE_UNKNOWN_NOT_ISOLATED`; `codec_context_causal=false`; `codec_context_access=LEADING_HYPOTHESIS_NOT_PROVEN`
* C2: `NOT_VIABLE_PERFORMANCE_FAIL`; retention model `ROLLING_WINDOW_EXACT_MODEL_PROVEN` (peak 15 frames / 93,312,000 bytes; retain-all 7,471,180,800 bytes is an upper bound)
* C3: `NOT_VIABLE_PERFORMANCE_FAIL`; variants: `thread_count_1`, `thread_count_4`, `thread_count_8`
* Outcome: `PENDING` (`terminal_outcome=null`); terminal `T3` is NOT accepted while the canonical-signature provenance gate is open
* Decision status: `BLOCKED_NO_EVIDENCE_SUPPORTED_TARGET_OPTIMIZATION`
* Step 18.4C: `in_progress / blocked_on_canonical_signature_provenance`
* Step 18.5: `planned / blocked`; implementation not started
* Selected optimization: `NONE`

## Canonical signature provenance

Accepted immutable signature `8cc06c6a...`; fresh reference/candidate signature
`5a7c4538...`. These do NOT match (`match=false`).

The historical benchmark path at HEAD `acb424f` did NOT access `stream.codec_context`
in `pyav_iter_frames`, while the current production-equivalent path DOES. This is a
**proven code-path difference** and the **leading hypothesis** for the
canonical-signature change. Causality has NOT been isolated
(`ROOT_CAUSE_UNKNOWN_NOT_ISOLATED`): no controlled causal A/B matrix was run in
which ONLY the presence of `stream.codec_context` access varied, and other
HWAccel/evidence infrastructure changed together with that access. It is therefore
NOT asserted that `stream.codec_context` access is the isolated cause of the pixel
difference.

The exact-semantics gate is blocked until either (a) a controlled causal A/B probe
varying ONLY `stream.codec_context` access is performed, or (b) an architectural
decision on the production decode path is made and the immutable signature is then
explicitly, consciously re-baselined under the current code.

## C2 arithmetic (computed from raw medians)

* reference median = 290.5263571000032 s
* candidate median = 330.72188989999995 s
* median of paired differences = -46.81963299999916 s / -16.115451096192 %
* difference of medians = reference_median - candidate_median = -40.19553279999673 s / -13.835416931263438 %

`median of paired differences` and `difference of medians` are distinct quantities
and are both recorded explicitly in the child artifacts with their own definition
fields.

This report is generated directly from duplicate-key-validated child artifacts.
