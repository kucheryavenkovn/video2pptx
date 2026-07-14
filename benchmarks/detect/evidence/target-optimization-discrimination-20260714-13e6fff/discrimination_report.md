# Step 18.4C Target Optimization Discrimination Report

**Date:** 2026-07-14  
**Branch:** perf/phase18-target-optimization-discrimination  
**Evidence code HEAD:** 142da834b1a9c16416e2386d99f22ae54d692d27  
**Evidence code tree:** 52624e512e8b7a5d48963c538b3406ba3918c79c  
**Accepted master base:** 95f5794f46ce5e313c6b2548cb8dbfcfe917555a  
**Canonical runtime evidence commit:** 9b4cc54949537b2a36e70a0f98f1cb732d6688b2  
**Strict-control evidence commit:** ef589a12187c299f4bd086dc690a38b3f7095982  
**Canonical clip SHA256:** dd9da3442e91ab7f17f0405198aa8e39d1538d74518b6b9a3b1e61ac2fc0f5a4  

## Outcome: T3 — BLOCKED_NO_EVIDENCE_SUPPORTED_TARGET_OPTIMIZATION

No candidate satisfies exact parity, bounded intervention, resource safety, and measured-benefit requirements.

## C1 — PASS2_TARGETED_REPRESENTATIVE_FRAME_RETRIEVAL

**Viability: NOT VIABLE — exact parity FAIL**

### Parity Evidence
- Shared Pass 1: 175.53996180000104s, 106 segments
- Reference sequential Pass 2: 55.34686800000054s, 1201 frames sampled
- Candidate targeted retrieval: 24.844641000001502s, 12396 frames decoded
- Representative frames collected: reference=84, candidate=84
- **Exact frame parity: FAIL (0/84 targets passed)**

### Root Cause
The production decode path (`pyav_iter_frames`) accesses `stream.codec_context`, which triggers
different HW decode initialization than a direct `av.open + demux + decode` path. This causes
systematically different pixel values for the same video frame across different decode paths.
The candidate's seek-based retrieval uses a different container open path and cannot reproduce
the exact production pixels.

### Rejection Reason
EXACT_PARITY_FAIL — all 84 representative frames differ in cropped RGB SHA256. This is a
HW decode environment-specific behavior (PyAV 18.0.0 / NVDEC / CUDA), not a fixable bug.

## C2 — PASS1_SAMPLE_FRAME_RETENTION

**Viability: NOT VIABLE — no bounded resource model**

### Resource Analysis
- Sampled frames: 1201
- Full RGB retention: 7,471,180,800 bytes (7.4712 GB / 6.9581 GiB)
- ROI retention (auto = full frame): 7,471,180,800 bytes
- Current representative frame bytes: 522,547,200
- Retention/representative ratio: 14.30x

### Streaming Analysis
representative_timestamp depends on final segment start AND end. When a frame passes through
Pass 1, the final segment end is unknown. Bounded O(number_of_segments) retention is impossible
without changing representative timestamp semantics. Total retention is O(frames_sampled).

### Rejection Reason
UNBOUNDED_RETENTION_NO_RESOURCE_BUDGET — ~7.47 GB retention required, no bounded model,
no project memory budget defined.

## C3 — PYAV_DECODE_CONFIGURATION_TUNING

**Viability: NOT VIABLE — no evidence-supported variant**

### API Inspection (PyAV 18.0.0)
- HW device: cuda
- Codec: h264
- Writable potentially-parity-preserving: thread_count, thread_type
- NOT_AVAILABLE: low_delay, skip_loop_filter, skip_non_ref, skip_idct
- SEMANTICS_CHANGE_FRAME_SEQUENCE: skip_frame

### Variant Assessment
thread_count and thread_type are software decoder threading options. With NVDEC hardware
decode, the hardware decoder handles its own parallelism; software thread settings have no
mechanism to reduce HW decode cost. No evidence-supported variant exists.

### Rejection Reason
NO_EVIDENCE_SUPPORTED_CONFIGURATION_VARIANT

## Decision

- **Outcome:** T3 (no viable candidate)
- **Decision status:** BLOCKED_NO_EVIDENCE_SUPPORTED_TARGET_OPTIMIZATION
- **Selected bottleneck:** DECODE_FRAME_PIPELINE (unchanged, HIGH confidence)
- **Selected optimization:** NONE
- **Step 18.4:** in_progress
- **Step 18.5:** planned / blocked
- **New finding:** F-0102

DECODE_FRAME_PIPELINE remains the accepted primary bottleneck, but C1/C2/C3 discrimination
found no exact-parity, bounded, evidence-supported optimization satisfying the Step 18.4
selection contract.
