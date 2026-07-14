# PyAV Strict No-Software-Fallback Control Report (Step 18.4B)

**Step:** 18.4B
**Evidence type:** PYAV_STRICT_NO_SOFTWARE_FALLBACK_CONTROL
**Status:** OBSERVATION_COMPLETE
**Mode:** strict_only
**Clip SHA256 match:** True
**Canonical runtime evidence commit:** 9b4cc54949537b2a36e70a0f98f1cb732d6688b2

## Corrected Strict Control
- control_name: STRICT_NO_SOFTWARE_FALLBACK
- primary_evidence: False
- requested_hw_device: cuda
- allow_software_fallback: False
- result: FIRST_FRAME_DECODED
- result_stage: first_frame_decoded
- packets_examined: 3
- packets_with_decoded_frames: 1
- frames_decoded: 1
- frames_converted: 1
- first_frame_timestamp: 0.033
- first_frame_shape: [1080, 1920, 3]
- codec_name: h264
- codec_long_name: H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
- container_opened: True
- container_closed: True
- error_type: None
- error_message: None
- evidence_code_head: 04c0dc1f21cd8f37a9c82925e9c1470a40759553
- evidence_code_tree: b93329dde6740d2f7f0283e6c7fb2235f0245bb3
- accepted_master_base: 547dc06ef6bfe331daf60018ac45bd342f0d3dfd

## Interpretation
With HWAccel('cuda', 0) and allow_software_fallback=false, the canonical H.264 stream produced at least one decoded and RGB-converted frame. This directly supports that a strict no-software-fallback CUDA-configured decode path is operational in this PyAV/FFmpeg/runtime environment. Supporting evidence only: does NOT prove every production benchmark frame used hardware decode, does NOT prove the production fallback-enabled path never used software fallback, and does NOT measure throughput.

## Confidence dimensions
- strict_control_execution_completeness_confidence: HIGH
- strict_control_runtime_interpretation_confidence: HIGH

## Limitations
- Supporting control only; not primary evidence.
- Probes only the first decoded frame; does not prove full-stream hardware decodability.
- Does not measure decode throughput or infer any speedup.
- A successful first frame does not prove the production fallback-enabled path never used software fallback.
