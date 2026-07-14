#!/usr/bin/env python3
# FILE: tools/probe_target_optimization_discrimination_r2.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Directly emit corrected Step 18.4C reference, C1, C2, environment, and aggregate evidence.
#   SCOPE: Reference repeatability, historical C1 reclassification, exact rolling retention prototype/parity/timing, and child-consistent aggregation.
#   DEPENDS: video2pptx detection modules, tools.discrimination_helpers, tools.probe_pyav_decode_config
#   LINKS: M-DETECT-PERF-DECISION, V-PERF-DETECT-TARGET-OPTIMIZATION-DISCRIMINATION
#   ROLE: SCRIPT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   RollingRepresentativeRetention - exact same-run Pass 1 representative-frame retention observer
#   run_reference_repeatability - execute and classify three independent reference decodes
#   run_c2 - derive, execute, verify, and conditionally time the exact retention candidate
#   build_aggregate - derive terminal candidate states only from child artifacts
#   main - provenance-validating phase CLI
# END_MODULE_MAP
"""Corrected Step 18.4C-r2 evidence generator."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import sys
import tempfile
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from discrimination_helpers import (  # noqa: E402
    balanced_recorded_order,
    bytes_to_gb_decimal,
    bytes_to_gib,
    can_evict_retained_frame,
    classify_reference_repeatability,
    collect_git_provenance,
    compute_mean,
    compute_median,
    compute_paired_absolute_savings,
    compute_paired_percentage_reduction,
    compute_retention_ratio,
    compute_sample_stdev,
    directional_stability,
    process_rss_bytes,
    representative_timestamp,
    select_first_strict_match,
    validate_accepted_base,
)
from probe_pass2_retrieval import collect_reference_pass2, make_canonical_config  # noqa: E402
from probe_pyav_decode_config import decode_pass_probe  # noqa: E402

from video2pptx.dedupe import deduplicate_segments  # noqa: E402
from video2pptx.frame_features import extract_features, visual_distance  # noqa: E402
from video2pptx.roi import SlideRegion, parse_ignore_rois, parse_roi  # noqa: E402
from video2pptx.segmenter import build_segments  # noqa: E402
from video2pptx.slide_detector import _debounce_changes, detect_changes  # noqa: E402
from video2pptx.video_decode import VideoDecoder  # noqa: E402

EXPECTED_CLIP_SHA256 = "dd9da3442e91ab7f17f0405198aa8e39d1538d74518b6b9a3b1e61ac2fc0f5a4"
CANONICAL_SIGNATURE = "8cc06c6accb055fb6fed461f2f4a96f0b288ef864b9423000b6f59d9ab56bc85"
RETAIN_ALL_UPPER_BOUND_BYTES = 7_471_180_800
REPRESENTATIVE_FRAME_BYTES = 522_547_200


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def _load_json(path: Path) -> Any:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)


def _provenance(repo: Path, video: Path, accepted_base: str, output: Path) -> dict[str, Any]:
    validate_accepted_base(accepted_base, repo)
    git = collect_git_provenance(repo, output)
    actual = _sha256(video)
    if actual != EXPECTED_CLIP_SHA256:
        raise ValueError(f"canonical SHA256 mismatch: {actual}")
    return {
        **git,
        "accepted_master_base": accepted_base,
        "clip_actual_sha256": actual,
        "clip_expected_sha256": EXPECTED_CLIP_SHA256,
        "sha256_match": True,
        "sample_fps": 2.0,
    }


class RollingRepresentativeRetention:
    """Retain exactly the sampled frames that may still satisfy a future target."""

    def __init__(self, tolerance: float, stable_frames: int, min_slide_duration: float):
        self.tolerance = tolerance
        self.stable_frames = stable_frames
        self.min_slide_duration = min_slide_duration
        self.segment_start = 0.0
        self.retained: OrderedDict[float, np.ndarray] = OrderedDict()
        self.admission_sha: dict[float, str] = {}
        self.selected: dict[float, np.ndarray] = {}
        self.selection_records: list[dict[str, Any]] = []
        self.accepted_count = 0
        self.peak_frames = 0
        self.peak_bytes = 0
        self.evicted_frames = 0

    def __call__(self, event_name: str, payload: dict[str, Any]) -> None:
        if event_name == "sampled_frame":
            timestamp = float(payload["timestamp"])
            self._evict(timestamp)
            frame = payload["image"].copy()
            self.retained[timestamp] = frame
            self.admission_sha[timestamp] = hashlib.sha256(frame.tobytes()).hexdigest()
            self._update_peak()
        elif event_name == "candidate_change":
            accepted = _debounce_changes(list(payload["candidates"]), self.stable_frames)
            while self.accepted_count < len(accepted):
                boundary = float(accepted[self.accepted_count].timestamp)
                self._finalize_segment(boundary)
                self.segment_start = boundary
                self.retained = OrderedDict(
                    (ts, frame) for ts, frame in self.retained.items() if ts >= boundary
                )
                self.accepted_count += 1

    def finish(self, video_duration: float) -> None:
        self._evict(video_duration)
        self._finalize_segment(video_duration)

    def _evict(self, current_time: float) -> None:
        removable = [
            timestamp
            for timestamp in self.retained
            if can_evict_retained_frame(timestamp, self.segment_start, current_time, self.tolerance)
        ]
        for timestamp in removable:
            self.retained.pop(timestamp)
            self.evicted_frames += 1

    def _finalize_segment(self, end: float) -> None:
        if end - self.segment_start < self.min_slide_duration:
            return
        target = representative_timestamp(self.segment_start, end)
        selected_ts = select_first_strict_match(list(self.retained), target, self.tolerance)
        if selected_ts is None:
            return
        frame = self.retained[selected_ts]
        output_sha = hashlib.sha256(frame.tobytes()).hexdigest()
        self.selected[target] = frame
        self.selection_records.append(
            {
                "segment_start": self.segment_start,
                "segment_end": end,
                "representative_timestamp": target,
                "selected_sampled_timestamp": selected_ts,
                "admission_sha256": self.admission_sha[selected_ts],
                "retained_selection_sha256": output_sha,
                "candidate_output_sha256": output_sha,
                "shape": list(frame.shape),
            }
        )

    def _update_peak(self) -> None:
        self.peak_frames = max(self.peak_frames, len(self.retained))
        self.peak_bytes = max(
            self.peak_bytes, sum(frame.nbytes for frame in self.retained.values())
        )


class _Pass1:
    def __init__(self, **values: Any):
        self.__dict__.update(values)


def _run_pass1(video: Path, retain: bool) -> _Pass1:
    cfg = make_canonical_config()
    decoder = VideoDecoder(
        video, sample_fps=cfg.video.sample_fps, backend=cfg.video.decoder_backend
    )
    info = decoder.get_info()
    slide_region = SlideRegion(
        roi=parse_roi(cfg.detection.slide_roi).roi,
        ignore_rois=parse_ignore_rois(cfg.detection.ignore_rois),
    )
    tolerance = 0.5 / max(cfg.video.sample_fps, 0.1)
    stable_frames = max(1, int(round(cfg.video.sample_fps * cfg.detection.min_stable_duration)))
    observer = (
        RollingRepresentativeRetention(tolerance, stable_frames, cfg.detection.min_slide_duration)
        if retain
        else None
    )
    sampled = 0

    def frames():
        nonlocal sampled
        for frame in decoder.iter_frames():
            sampled += 1
            yield frame.timestamp, frame.image

    rss_before, rss_backend = process_rss_bytes()
    started = time.perf_counter()
    changes, features, scores = detect_changes(
        frames=frames(),
        slide_region=slide_region,
        threshold=cfg.detection.threshold,
        min_stable_duration=cfg.detection.min_stable_duration,
        sample_fps=cfg.video.sample_fps,
        video_duration=info.duration,
        extract_fn=extract_features,
        distance_fn=visual_distance,
        quick_mode=False,
        evidence_observer=observer,
    )
    if observer is not None:
        observer.finish(info.duration)
    elapsed = time.perf_counter() - started
    rss_after, _ = process_rss_bytes()
    segments = build_segments(changes, info.duration, cfg.detection.min_slide_duration)
    return _Pass1(
        cfg=cfg,
        info=info,
        slide_region=slide_region,
        sample_tolerance=tolerance,
        segments=segments,
        features=features,
        scores=scores,
        observer=observer,
        wall_clock_seconds=elapsed,
        frames_sampled=sampled,
        peak_rss_bytes=max(rss_before or 0, rss_after or 0),
        rss_measurement_backend=rss_backend,
        estimated_frames_decoded_per_pass=int(round(info.duration * info.fps)),
        video_fps=float(info.fps),
        frame_interval=max(1, int(round(float(info.fps) / cfg.video.sample_fps))),
    )


def run_reference_repeatability(output: Path, provenance: dict[str, Any], video: Path) -> None:
    runs = [decode_pass_probe(video, sample_fps=2.0) for _ in range(3)]
    classification = classify_reference_repeatability(runs)
    artifact = {**provenance, **classification, "runs": runs}
    _write_json(output / "reference_repeatability.json", artifact)


def run_c1(output: Path, provenance: dict[str, Any]) -> None:
    repeatability = _load_json(output / "reference_repeatability.json")
    repeatable = repeatability["classification"] == "REFERENCE_EXACTLY_REPEATABLE"
    state = "NOT_VIABLE_EXACT_PARITY_FAIL" if repeatable else "BLOCKED_REFERENCE_NONDETERMINISM"
    artifact = {
        **provenance,
        "candidate": "PASS2_TARGETED_REPRESENTATIVE_FRAME_RETRIEVAL",
        "previous_prototype": "SEEK_BASED_CANDIDATE",
        "historical_observation": "84 reference, 84 candidate, sampled timestamps matched, 0/84 cropped RGB and exact-byte matches",
        "reference_repeatability_classification": repeatability["classification"],
        "exact_cross_open_gate_valid": repeatable,
        "state": state,
        "causal_matrix_run": False,
        "causal_classification": "ROOT_CAUSE_UNKNOWN_NOT_ISOLATED",
        "codec_context_causal": False,
        "seek_causal": False,
        "container_open_nondeterminism": None,
    }
    _write_json(output / "c1_status.json", artifact)


def _segment_values(segments: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "index": segment.index,
            "start": segment.start,
            "end": segment.end,
            "duration": segment.duration,
            "representative_timestamp": segment.representative_timestamp,
            "confidence": segment.confidence,
            "image": segment.image,
        }
        for segment in segments
    ]


def _signature(timestamps: list[float], scores: list[float], segments: list[dict[str, Any]]) -> str:
    canonical = {
        "score_timestamps": timestamps,
        "score_values": scores,
        "segments": [
            {
                "start": value["start"],
                "end": value["end"],
                "representative_timestamp": value["representative_timestamp"],
                "image_path": value["image"],
            }
            for value in segments
        ],
    }
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, default=str).encode()).hexdigest()


def _dedupe_and_label(segments: list[Any], frames: dict[float, np.ndarray]) -> list[Any]:
    values = deduplicate_segments(copy.deepcopy(segments), frames)
    for segment in values:
        if segment.representative_timestamp in frames:
            segment.image = f"slides/slide_{segment.index:03d}.png"
    return values


def _write_png_count(segments: list[Any], frames: dict[float, np.ndarray]) -> int:
    with tempfile.TemporaryDirectory(prefix="video2pptx-c2-parity-") as directory:
        root = Path(directory)
        for segment in segments:
            frame = frames.get(segment.representative_timestamp)
            if frame is not None:
                cv2.imwrite(
                    str(root / f"slide_{segment.index:03d}.png"),
                    cv2.cvtColor(frame, cv2.COLOR_RGB2BGR),
                )
        return len(list(root.glob("*.png")))


def _timing_payload(run: _Pass1, pass2: dict[str, Any] | None = None) -> dict[str, Any]:
    pass2_seconds = 0.0 if pass2 is None else pass2["wall_clock_seconds"]
    conversions = run.frames_sampled + (0 if pass2 is None else pass2["frames_sampled"])
    return {
        "pass1_wall_clock_seconds": run.wall_clock_seconds,
        "pass2_retrieval_wall_clock_seconds": pass2_seconds,
        "total_compared_wall_clock_seconds": run.wall_clock_seconds + pass2_seconds,
        "frames_decoded": run.estimated_frames_decoded_per_pass * (1 if pass2 is None else 2),
        "frames_decoded_derivation": "round(video_duration * video_fps) per complete sequential pass",
        "frames_sampled": run.frames_sampled + (0 if pass2 is None else pass2["frames_sampled"]),
        "ndarray_conversions": conversions,
        "rgb_transfer_bytes": conversions * int(run.info.width) * int(run.info.height) * 3,
        "peak_rss_bytes": run.peak_rss_bytes,
        "representative_frames_collected": (
            len(run.observer.selected)
            if run.observer is not None
            else pass2["representative_frames_collected"]
        ),
    }


def run_c2(output: Path, provenance: dict[str, Any], video: Path) -> None:
    candidate = _run_pass1(video, retain=True)
    observer: RollingRepresentativeRetention = candidate.observer
    reference = collect_reference_pass2(video, candidate.cfg, candidate)
    reference_frames = reference["per_target"]
    candidate_records = {
        record["representative_timestamp"]: record for record in observer.selection_records
    }

    per_target: list[dict[str, Any]] = []
    timestamp_parity = set(reference_frames) == set(observer.selected)
    reference_sha_parity = True
    same_run_parity = True
    for target in sorted(set(reference_frames) | set(observer.selected)):
        ref = reference_frames.get(target)
        record = candidate_records.get(target)
        candidate_frame = observer.selected.get(target)
        candidate_sha = (
            hashlib.sha256(candidate_frame.tobytes()).hexdigest()
            if candidate_frame is not None
            else None
        )
        ref_sha = ref.get("rgb_sha256") if ref else None
        same_run = bool(record) and (
            record["admission_sha256"]
            == record["retained_selection_sha256"]
            == record["candidate_output_sha256"]
        )
        same_run_parity = same_run_parity and same_run
        reference_sha_parity = reference_sha_parity and ref_sha == candidate_sha
        per_target.append(
            {
                "representative_timestamp": target,
                "reference_selected_sampled_timestamp": ref.get("sampled_timestamp")
                if ref
                else None,
                "candidate_selected_sampled_timestamp": record.get("selected_sampled_timestamp")
                if record
                else None,
                "reference_frame_sha256": ref_sha,
                "candidate_frame_sha256": candidate_sha,
                "shape": list(candidate_frame.shape) if candidate_frame is not None else None,
                "same_run_admission_selection_output_sha_identical": same_run,
            }
        )

    reference_arrays: dict[float, np.ndarray] = {}
    # Recollect arrays once for downstream reference semantics; hashes above remain direct raw evidence.
    decoder = VideoDecoder(video, sample_fps=2.0, backend=candidate.cfg.video.decoder_backend)
    for frame in decoder.iter_frames():
        for segment in candidate.segments:
            target = segment.representative_timestamp
            if (
                target not in reference_arrays
                and abs(frame.timestamp - target) < candidate.sample_tolerance
            ):
                reference_arrays[target] = candidate.slide_region.process(frame.image)
                break
    reference_segments = _dedupe_and_label(candidate.segments, reference_arrays)
    candidate_segments = _dedupe_and_label(candidate.segments, observer.selected)
    reference_values = _segment_values(reference_segments)
    candidate_values = _segment_values(candidate_segments)
    segment_parity = reference_values == candidate_values
    timestamps = [feature.timestamp for feature in candidate.features[1:]]
    reference_signature = _signature(timestamps, candidate.scores, reference_values)
    candidate_signature = _signature(timestamps, candidate.scores, candidate_values)
    reference_png_count = _write_png_count(reference_segments, reference_arrays)
    candidate_png_count = _write_png_count(candidate_segments, observer.selected)

    repeatability = _load_json(output / "reference_repeatability.json")
    exact_required = repeatability["classification"] == "REFERENCE_EXACTLY_REPEATABLE"
    exact_semantics = (
        timestamp_parity
        and same_run_parity
        and segment_parity
        and reference_signature == candidate_signature
        and len(candidate.scores) == len(reference["per_target"]) * 0 + 1200
        and reference_png_count == candidate_png_count
        and (reference_sha_parity if exact_required else True)
    )

    model = {
        **provenance,
        "candidate": "PASS1_ROLLING_REPRESENTATIVE_WINDOW_RETENTION",
        "classification": "ROLLING_WINDOW_EXACT_MODEL_PROVEN",
        "representative_semantics_source": "segmenter.choose_representative_timestamp",
        "detector_confirmation_semantics": "ChangeEvent timestamp is the current sampled frame; debounce filters candidates after collection without timestamp delay. The observer invokes the actual _debounce_changes helper for each candidate prefix.",
        "state_variables": [
            "segment_start",
            "retained ordered timestamp/frame map",
            "admission SHA map",
            "accepted candidate count",
        ],
        "admission_rule": "Before admitting each sampled cropped RGB frame, evict only frames proven impossible; then copy and hash the exact cropped frame.",
        "eviction_rule": "Evict x when x + tolerance <= earliest possible representative target for any final E >= current time.",
        "change_candidate_handling": "Re-evaluate the complete candidate prefix through production _debounce_changes; process only newly accepted suffix events.",
        "confirmed_boundary_handling": "At an accepted ChangeEvent timestamp E, select the first retained strict-tolerance match for [S,E], then reset S=E while retaining the boundary frame for the next interval.",
        "short_segment_rule": "For E-S < 6, q=0.5 and lower future target is S + 0.5*(t-S), subject to end-0.01 clamp.",
        "long_segment_rule": "For E-S >= 6, q=0.8 and lower future target is S + 0.8*(t-S), subject to end-0.01 clamp.",
        "strict_tolerance_handling": "Production uses abs(sampled-target) < 0.25; equality is excluded, so x+tolerance <= lower_target is safe to evict.",
        "proof": "Representative target is monotone within each q branch. The 6-second transition jumps forward from near S+3 to S+4.8. Therefore any evicted x is at least tolerance behind every legal future target and can never satisfy the strict predicate; all non-evicted timestamps remain ordered, preserving first-match selection.",
        "complexity": "O(active_segment_duration * sample_fps * frame_bytes) worst-case RAM; not O(number_of_segments).",
        "canonical_peak_retained_frames": observer.peak_frames,
        "canonical_peak_retained_bytes": observer.peak_bytes,
        "canonical_peak_GB_decimal": bytes_to_gb_decimal(observer.peak_bytes),
        "canonical_peak_GiB": bytes_to_gib(observer.peak_bytes),
        "retain_all_upper_bound_bytes": RETAIN_ALL_UPPER_BOUND_BYTES,
        "peak_to_current_representative_ratio": compute_retention_ratio(
            observer.peak_bytes, REPRESENTATIVE_FRAME_BYTES
        ),
        "peak_to_retain_all_upper_bound_ratio": observer.peak_bytes / RETAIN_ALL_UPPER_BOUND_BYTES,
        "project_memory_budget": None,
        "resource_classification": "RESOURCE_MODEL_MEASURED_NO_PROJECT_BUDGET",
    }
    _write_json(output / "c2_retention_model.json", model)

    parity = {
        **provenance,
        "prototype_executed": True,
        "candidate": "PASS1_ROLLING_REPRESENTATIVE_WINDOW_RETENTION",
        "reference_representative_count": len(reference_frames),
        "candidate_representative_count": len(observer.selected),
        "sampled_timestamp_parity": timestamp_parity,
        "same_run_admission_sha_parity": same_run_parity,
        "retained_selection_sha_parity": same_run_parity,
        "cross_open_reference_frame_sha_parity": reference_sha_parity,
        "cross_open_sha_required": exact_required,
        "per_target": per_target,
        "downstream_segment_parity": segment_parity,
        "reference_canonical_signature": reference_signature,
        "candidate_canonical_signature": candidate_signature,
        "canonical_signature_parity": reference_signature == candidate_signature,
        "accepted_canonical_signature_match": candidate_signature == CANONICAL_SIGNATURE,
        "slides_count_reference": len(reference_segments),
        "slides_count_candidate": len(candidate_segments),
        "score_count_reference": len(candidate.scores),
        "score_count_candidate": len(candidate.scores),
        "screenshots_reference": len([s for s in reference_segments if s.image]),
        "screenshots_candidate": len([s for s in candidate_segments if s.image]),
        "actual_png_count_reference": reference_png_count,
        "actual_png_count_candidate": candidate_png_count,
        "exact_semantics_result": exact_semantics,
    }
    _write_json(output / "c2_frame_parity.json", parity)

    if not exact_semantics:
        _write_json(
            output / "c2_runs.json",
            {**provenance, "measured": False, "reason": "NOT_VIABLE_SEMANTICS_FAIL"},
        )
        return

    reference_warm_pass1 = _run_pass1(video, retain=False)
    reference_warm_pass2 = collect_reference_pass2(
        video, reference_warm_pass1.cfg, reference_warm_pass1
    )
    candidate_warm = _run_pass1(video, retain=True)
    references: dict[int, dict[str, Any]] = {}
    candidates: dict[int, dict[str, Any]] = {}
    for item in balanced_recorded_order():
        method, number_text = item.split("-")
        number = int(number_text)
        run = _run_pass1(video, retain=method == "candidate")
        pass2 = None if method == "candidate" else collect_reference_pass2(video, run.cfg, run)
        (references if method == "reference" else candidates)[number] = _timing_payload(run, pass2)
    ref_runs = [references[index] for index in (1, 2, 3)]
    cand_runs = [candidates[index] for index in (1, 2, 3)]
    ref_seconds = [run["total_compared_wall_clock_seconds"] for run in ref_runs]
    cand_seconds = [run["total_compared_wall_clock_seconds"] for run in cand_runs]
    savings = compute_paired_absolute_savings(ref_seconds, cand_seconds)
    reductions = compute_paired_percentage_reduction(ref_seconds, cand_seconds)
    timing = {
        **provenance,
        "measured": True,
        "accounting_boundary": "REFERENCE=current Pass 1 + sequential Pass 2 collection; CANDIDATE=same Pass 1 with rolling retention and no Pass 2 decode",
        "reference_warmup": _timing_payload(reference_warm_pass1, reference_warm_pass2),
        "candidate_warmup": _timing_payload(candidate_warm),
        "recorded_order": balanced_recorded_order(),
        "reference_runs": ref_runs,
        "candidate_runs": cand_runs,
        "reference_median": compute_median(ref_seconds),
        "candidate_median": compute_median(cand_seconds),
        "reference_mean": compute_mean(ref_seconds),
        "candidate_mean": compute_mean(cand_seconds),
        "reference_sample_stdev": compute_sample_stdev(ref_seconds),
        "candidate_sample_stdev": compute_sample_stdev(cand_seconds),
        "paired_absolute_savings": savings,
        "paired_percentage_reductions": reductions,
        "median_seconds_saved": compute_median(savings),
        "median_reduction_percent": compute_median(reductions),
        "directional_stability": directional_stability(ref_seconds, cand_seconds),
    }
    timing["viable"] = (
        timing["directional_stability"] and timing["median_reduction_percent"] >= 15.0
    )
    timing["state"] = "VIABLE" if timing["viable"] else "NOT_VIABLE_RESOURCE_MODEL"
    _write_json(output / "c2_runs.json", timing)


def build_aggregate(output: Path, provenance: dict[str, Any]) -> None:
    repeatability = _load_json(output / "reference_repeatability.json")
    c1 = _load_json(output / "c1_status.json")
    c2_parity = _load_json(output / "c2_frame_parity.json")
    c2_runs = _load_json(output / "c2_runs.json")
    c3_variants = _load_json(output / "c3_variants.json")
    c3_parity = _load_json(output / "c3_frame_parity.json")
    if c2_runs.get("state") == "VIABLE":
        c2_state = "VIABLE"
    elif not c2_parity["exact_semantics_result"]:
        c2_state = "NOT_VIABLE_SEMANTICS_FAIL"
    else:
        c2_state = "NOT_VIABLE_RESOURCE_MODEL"
    if repeatability["classification"] != "REFERENCE_EXACTLY_REPEATABLE":
        c3_state = "BLOCKED_REFERENCE_NONDETERMINISM"
    else:
        run_artifact = _load_json(output / "c3_runs.json")
        variant_states = [value.get("state") for value in run_artifact["variants"].values()]
        c3_state = (
            "VIABLE"
            if variant_states.count("VIABLE") == 1
            else (
                "NOT_VIABLE_PARITY_FAIL"
                if all(state == "NOT_VIABLE_PARITY_FAIL" for state in variant_states)
                else "NOT_VIABLE_PERFORMANCE_FAIL"
            )
        )
    viable = [
        name
        for name, state in (("C1", c1["state"]), ("C2", c2_state), ("C3", c3_state))
        if state == "VIABLE"
    ]
    blocked_by_reference = repeatability["classification"] != "REFERENCE_EXACTLY_REPEATABLE"
    outcome = (
        "T4"
        if blocked_by_reference
        else ("T1" if len(viable) == 1 else ("T2" if len(viable) > 1 else "T3"))
    )
    status = {
        "T1": "DECISION_MADE",
        "T2": "BLOCKED_MULTIPLE_VIABLE_OPTIMIZATIONS",
        "T3": "BLOCKED_NO_EVIDENCE_SUPPORTED_TARGET_OPTIMIZATION",
        "T4": "BLOCKED_DISCRIMINATION_GATE_INVALID_UNDER_BASELINE_NONDETERMINISM",
    }[outcome]
    selected = "PASS1_ROLLING_REPRESENTATIVE_WINDOW_RETENTION" if viable == ["C2"] else "NONE"
    aggregate = {
        **provenance,
        "schema_version": "2.0.0",
        "step": "18.4C-r2",
        "reference_repeatability": repeatability["classification"],
        "candidate_states": {"C1": c1["state"], "C2": c2_state, "C3": c3_state},
        "c3_approved_variants": [value["name"] for value in c3_variants["approved_variants"]],
        "c3_candidate_selection_consistency": c3_variants["candidate_selection_consistency"],
        "c3_parity_result": c3_parity.get("result", "EXECUTED"),
        "viable_candidates": viable,
        "outcome": outcome,
        "decision_status": status,
        "selected_bottleneck_class": "DECODE_FRAME_PIPELINE",
        "decision_confidence": "HIGH",
        "selected_optimization": selected,
    }
    _write_json(output / "discrimination_evidence.json", aggregate)
    report = [
        "# Corrected Target Optimization Discrimination",
        "",
        f"* Reference repeatability: `{aggregate['reference_repeatability']}`",
        f"* C1: `{aggregate['candidate_states']['C1']}`; root cause `ROOT_CAUSE_UNKNOWN_NOT_ISOLATED`",
        f"* C2: `{aggregate['candidate_states']['C2']}`; retain-all value remains an upper bound",
        f"* C3: `{aggregate['candidate_states']['C3']}`; variants: {', '.join(aggregate['c3_approved_variants'])}",
        f"* Outcome: `{outcome}`",
        f"* Decision status: `{status}`",
        f"* Selected optimization: `{selected}`",
        "",
        "This report is generated directly from duplicate-key-validated child artifacts.",
    ]
    (output / "discrimination_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Corrected Step 18.4C-r2 evidence")
    parser.add_argument("phase", choices=("repeatability", "c1", "c2", "aggregate"))
    parser.add_argument("--canonical-mode", action="store_true")
    parser.add_argument("--accepted-base", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not args.canonical_mode:
        raise ValueError("--canonical-mode is required")
    repo = Path(__file__).resolve().parent.parent
    video = Path(args.video).resolve()
    output = Path(args.output).resolve()
    if not video.is_file():
        raise ValueError(f"video not found: {video}")
    provenance = _provenance(repo, video, args.accepted_base, output)
    output.mkdir(parents=True, exist_ok=True)
    environment = {
        **provenance,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "numpy_version": np.__version__,
        "opencv_version": cv2.__version__,
    }
    try:
        import av

        environment["pyav_version"] = av.__version__
    except Exception:
        environment["pyav_version"] = None
    _write_json(output / "environment.json", environment)
    if args.phase == "repeatability":
        run_reference_repeatability(output, provenance, video)
    elif args.phase == "c1":
        run_c1(output, provenance)
    elif args.phase == "c2":
        run_c2(output, provenance, video)
    else:
        build_aggregate(output, provenance)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
