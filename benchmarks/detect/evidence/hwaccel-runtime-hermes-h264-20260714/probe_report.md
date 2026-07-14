# PyAV HWAccel Runtime Evidence Probe Report

**Step:** 18.4A
**Evidence type:** PYAV_HWACCEL_RUNTIME_STATE
**Status:** OBSERVATION_COMPLETE
**Clip SHA256 match:** True

## Observation 01
- requested_hw_device: cuda
- hwaccel_requested: True
- hwaccel_object_created: True
- hwaccel_creation_error_type: None
- container_opened_with_hwaccel: True
- codec_context_is_hwaccel: True
- codec_context_hwaccel_present: True
- hw_config_present: False
- hw_config_device_type: None
- hw_config_format: None
- actual_hardware_decode_active: UNKNOWN_NOT_PROVEN
- codec_name: h264
- codec_long_name: H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
- software_fallback_detected: UNKNOWN_NOT_PROVEN
- first_frame_shape: [1080, 1920, 3]
- generator explicitly closed: true

## Observation 02
- requested_hw_device: cuda
- hwaccel_requested: True
- hwaccel_object_created: True
- hwaccel_creation_error_type: None
- container_opened_with_hwaccel: True
- codec_context_is_hwaccel: True
- codec_context_hwaccel_present: True
- hw_config_present: False
- hw_config_device_type: None
- hw_config_format: None
- actual_hardware_decode_active: UNKNOWN_NOT_PROVEN
- codec_name: h264
- codec_long_name: H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
- software_fallback_detected: UNKNOWN_NOT_PROVEN
- first_frame_shape: [1080, 1920, 3]
- generator explicitly closed: true

## Consistency
- Observations consistent: True

## Strict Fallback Control
- supported: True
- attempted: True
- result: STRICT_PROBE_NO_FRAME

## Conclusions
- Requested HW device: cuda
- codec_context_is_hwaccel: True
- actual_hardware_decode_active: UNKNOWN_NOT_PROVEN
- Fallback state: UNKNOWN_NOT_PROVEN
- Evidence confidence: HIGH
