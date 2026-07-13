# PyAV HWAccel Runtime Evidence Probe Report

**Step:** 18.4A
**Evidence type:** PYAV_HWACCEL_RUNTIME_STATE
**Status:** OBSERVATION_COMPLETE

## Observations

### Observation 01
- requested_hw_device: cuda
- hwaccel_requested: True
- hwaccel_object_created: True
- container_opened: True
- container_opened_with_hwaccel: True
- runtime_hwaccel_active: True
- observation_method: stream.codec_context.is_hwaccel
- codec_name: mpeg4
- codec_long_name: MPEG-4 part 2
- hw_config_device_type: None
- hw_config_format: None
- hardware_decoder_or_device_identity: <av.codec.hwaccel.HWAccel object at 0x000001F97FCE3A70>
- software_fallback_detected: UNKNOWN_NOT_EXPOSED
- first_frame_shape: [480, 640, 3]

### Observation 02
- requested_hw_device: cuda
- hwaccel_requested: True
- hwaccel_object_created: True
- container_opened: True
- container_opened_with_hwaccel: True
- runtime_hwaccel_active: True
- observation_method: stream.codec_context.is_hwaccel
- codec_name: mpeg4
- codec_long_name: MPEG-4 part 2
- hw_config_device_type: None
- hw_config_format: None
- hardware_decoder_or_device_identity: <av.codec.hwaccel.HWAccel object at 0x000001F97FCE3A70>
- software_fallback_detected: UNKNOWN_NOT_EXPOSED
- first_frame_shape: [480, 640, 3]

## Consistency
- Observations consistent: True

## Strict Fallback Control
- supported: True
- attempted: True
- result: STRICT_PROBE_SUCCEEDED
- error_type: None

## Conclusions
- Requested HW device: cuda
- Runtime active state: True
- Fallback state: UNKNOWN_NOT_EXPOSED
- Evidence confidence: HIGH
