# hermes-600s-f0097-instrumented-run-02

- Detect elapsed: 311.793136 s
- Video duration: 600.016667 s
- Real-time multiplier: 0.5196407913669066
- Effective backend: None
- Output signature: 8cc06c6accb055fb6fed461f2f4a96f0b288ef864b9423000b6f59d9ab56bc85

## Invariants

- features_equal_frames_sampled: PASS - features_full + features_quick == frames_sampled
- decoded_at_least_conversions: PASS - frames_decoded >= ndarray_conversions
- conversions_cover_sampled_passes: PASS - valid for current OpenCV/PyAV full-frame sampling implementations
- representative_frames_positive: PASS - representative_frames > 0
- representative_bytes_positive: PASS - representative_frame_bytes > 0 when representative frames exist
- screenshots_match_png_count: PASS - screenshots_written == PNG count (6)
- rss_peak_bounds: SKIPPED - psutil unavailable
