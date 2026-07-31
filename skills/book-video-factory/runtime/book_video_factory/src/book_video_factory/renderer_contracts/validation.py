"""Layered validators for Renderer Contract v1."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from .canonical import (
    semantic_request_hash,
    semantic_snapshot_hash,
    snapshot_id_from_hash,
)
from .enums import (
    CaptionTimingLevel,
    RenderMode,
    RendererCapability,
    RendererErrorCode,
    RenderStatus,
    TimelineAssetKind,
)
from .errors import RenderIssue
from .models import (
    ArtifactBinding,
    PortableRef,
    ReleaseSnapshot,
    RenderRequest,
    RendererCapabilities,
    RenderResult,
)
from .paths import PortablePathError, RootResolver, normalize_portable_path
from .serialization import release_snapshot_to_dict, render_request_to_dict


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXTENSION_RE = re.compile(
    r"^[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+$"
)

_ERROR_PRIORITY = {
    RendererErrorCode.RENDER_INPUT_INVALID: 10,
    RendererErrorCode.RENDER_GATE_BLOCKED: 20,
    RendererErrorCode.RENDER_RIGHTS_BLOCKED: 21,
    RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED: 30,
    RendererErrorCode.RENDER_ASSET_MISSING: 40,
    RendererErrorCode.RENDER_HASH_MISMATCH: 41,
    RendererErrorCode.RENDER_FONT_UNAVAILABLE: 42,
    RendererErrorCode.RENDER_TIMELINE_INVALID: 50,
    RendererErrorCode.RENDER_AUDIO_INVALID: 51,
    RendererErrorCode.RENDER_CAPTION_INVALID: 52,
    RendererErrorCode.RENDER_PROCESS_FAILED: 60,
    RendererErrorCode.RENDER_OUTPUT_MISSING: 61,
    RendererErrorCode.RENDER_PROBE_FAILED: 62,
    RendererErrorCode.RENDER_CANCELLED: 70,
}


def _issue(
    code: RendererErrorCode,
    message: str,
    field: str,
    *,
    details: Mapping[str, Any] | None = None,
    stage: str = "validate",
) -> RenderIssue:
    return RenderIssue(code, message, field, details or {}, stage)


def stable_issues(issues: Iterable[RenderIssue]) -> tuple[RenderIssue, ...]:
    return tuple(
        sorted(
            issues,
            key=lambda item: (
                _ERROR_PRIORITY[item.code],
                item.field,
                item.code.value,
                item.message,
            ),
        )
    )


def _sha_issue(value: Any, field: str) -> RenderIssue | None:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        return _issue(
            RendererErrorCode.RENDER_INPUT_INVALID,
            "SHA-256 must be 64 lowercase hexadecimal characters.",
            field,
        )
    return None


def _portable_ref_issues(
    ref: PortableRef,
    field: str,
    declared_roots: set[str] | None = None,
) -> list[RenderIssue]:
    issues: list[RenderIssue] = []
    if declared_roots is not None and ref.root not in declared_roots:
        issues.append(
            _issue(
                RendererErrorCode.RENDER_INPUT_INVALID,
                "Portable ref uses an undeclared root.",
                f"{field}.root",
                details={"root": ref.root},
            )
        )
    try:
        normalize_portable_path(ref.path)
    except PortablePathError as error:
        issues.append(
            _issue(
                RendererErrorCode.RENDER_INPUT_INVALID,
                str(error),
                f"{field}.path",
            )
        )
    return issues


def _shape_issues(
    value: Any,
    *,
    required: Iterable[str],
    optional: Iterable[str] = (),
    field: str,
    code: RendererErrorCode = RendererErrorCode.RENDER_INPUT_INVALID,
) -> list[RenderIssue]:
    if not isinstance(value, Mapping):
        return [_issue(code, "Expected an object.", field)]
    required_set = set(required)
    allowed = required_set | set(optional)
    issues: list[RenderIssue] = []
    for key in sorted(required_set - value.keys()):
        issues.append(_issue(code, "Required field is missing.", f"{field}.{key}"))
    for key in sorted(value.keys() - allowed):
        issues.append(_issue(code, "Unknown field is not allowed.", f"{field}.{key}"))
    return issues


def _request_shape_issues(request: RenderRequest) -> list[RenderIssue]:
    issues: list[RenderIssue] = []
    for name, declaration in request.roots.items():
        field = f"$.roots.{name}"
        issues.extend(_shape_issues(declaration, required=("kind", "input_access", "output_access"), field=field))
        if isinstance(declaration, Mapping):
            if declaration.get("kind") not in {"workspace", "project", "release", "artifact", "output", "runtime", "font_resources"}:
                issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Unknown root kind.", f"{field}.kind"))
            if declaration.get("input_access") not in {"read_only", "none"}:
                issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Unknown input access policy.", f"{field}.input_access"))
            if declaration.get("output_access") not in {"request_targets_only", "none"}:
                issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Unknown output access policy.", f"{field}.output_access"))
    issues.extend(_shape_issues(request.output_spec, required=("width", "height", "fps", "pixel_format", "container", "video", "audio", "duration_ticks", "artifact_role"), field="$.output_spec"))
    fps = request.output_spec.get("fps")
    issues.extend(_shape_issues(fps, required=("numerator", "denominator"), field="$.output_spec.fps"))
    video = request.output_spec.get("video")
    issues.extend(_shape_issues(video, required=("codec", "encoding_policy"), field="$.output_spec.video"))
    output_audio = request.output_spec.get("audio")
    issues.extend(_shape_issues(output_audio, required=("codec", "sample_rate", "channels"), field="$.output_spec.audio"))
    issues.extend(_shape_issues(request.output, required=("artifact_id", "role", "target", "overwrite_policy"), field="$.output"))
    issues.extend(_shape_issues(request.timeline, required=("model", "timebase", "frame_rounding", "duration_ticks", "segments"), field="$.timeline", code=RendererErrorCode.RENDER_TIMELINE_INVALID))
    issues.extend(_shape_issues(request.timeline.get("timebase"), required=("ticks_per_second",), field="$.timeline.timebase", code=RendererErrorCode.RENDER_TIMELINE_INVALID))
    segments = request.timeline.get("segments", ())
    if isinstance(segments, tuple):
        for index, segment in enumerate(segments):
            field = f"$.timeline.segments[{index}]"
            issues.extend(_shape_issues(segment, required=("segment_id", "start_tick", "end_tick", "narration", "visual", "caption_cue_ids", "overlay_ids", "transition", "metadata"), field=field, code=RendererErrorCode.RENDER_TIMELINE_INVALID))
            if isinstance(segment, Mapping):
                narration = segment.get("narration")
                if narration is not None:
                    issues.extend(_shape_issues(narration, required=("cue_ids",), field=f"{field}.narration", code=RendererErrorCode.RENDER_TIMELINE_INVALID))
                issues.extend(_shape_issues(segment.get("visual"), required=("kind", "asset_ids", "motion"), field=f"{field}.visual", code=RendererErrorCode.RENDER_TIMELINE_INVALID))
                issues.extend(_shape_issues(segment.get("transition"), required=("in", "out"), field=f"{field}.transition", code=RendererErrorCode.RENDER_TIMELINE_INVALID))
                issues.extend(_shape_issues(segment.get("metadata"), required=("script_line_ids", "scene_ids"), field=f"{field}.metadata", code=RendererErrorCode.RENDER_TIMELINE_INVALID))
    issues.extend(_shape_issues(request.audio, required=("manifest_ref", "manifest_sha256", "final_mix_asset_id", "stem_asset_ids", "stem_usage", "cues", "sync_policy", "mix_policy_id"), field="$.audio", code=RendererErrorCode.RENDER_AUDIO_INVALID))
    cues = request.audio.get("cues", ())
    if isinstance(cues, tuple):
        for index, cue in enumerate(cues):
            issues.extend(_shape_issues(cue, required=("cue_id", "asset_id", "start_tick", "end_tick"), field=f"$.audio.cues[{index}]", code=RendererErrorCode.RENDER_AUDIO_INVALID))
    issues.extend(_shape_issues(request.captions, required=("tracks",), field="$.captions", code=RendererErrorCode.RENDER_CAPTION_INVALID))
    tracks = request.captions.get("tracks", ())
    if isinstance(tracks, tuple):
        for track_index, track in enumerate(tracks):
            field = f"$.captions.tracks[{track_index}]"
            issues.extend(_shape_issues(track, required=("track_id", "language", "text_source_asset_id", "timing_source_asset_id", "alignment_revision", "cues", "style"), field=field, code=RendererErrorCode.RENDER_CAPTION_INVALID))
            if not isinstance(track, Mapping):
                continue
            style = track.get("style")
            issues.extend(_shape_issues(style, required=("font_role", "font_asset_id", "safe_area", "max_lines", "line_break_policy", "overflow_policy", "highlight_tokens"), field=f"{field}.style", code=RendererErrorCode.RENDER_CAPTION_INVALID))
            if isinstance(style, Mapping):
                issues.extend(_shape_issues(style.get("safe_area"), required=("left_px", "right_px", "bottom_px"), optional=("top_px",), field=f"{field}.style.safe_area", code=RendererErrorCode.RENDER_CAPTION_INVALID))
            track_cues = track.get("cues", ())
            if isinstance(track_cues, tuple):
                for cue_index, cue in enumerate(track_cues):
                    cue_field = f"{field}.cues[{cue_index}]"
                    issues.extend(_shape_issues(cue, required=("cue_id", "segment_id", "start_tick", "end_tick", "text", "granularity", "words", "highlight"), field=cue_field, code=RendererErrorCode.RENDER_CAPTION_INVALID))
                    if isinstance(cue, Mapping):
                        words = cue.get("words", ())
                        if isinstance(words, tuple):
                            for word_index, word in enumerate(words):
                                issues.extend(_shape_issues(word, required=("word_id", "text", "start_tick", "end_tick"), field=f"{cue_field}.words[{word_index}]", code=RendererErrorCode.RENDER_CAPTION_INVALID))
                        highlight = cue.get("highlight")
                        if highlight is not None:
                            issues.extend(_shape_issues(highlight, required=("mode", "states"), field=f"{cue_field}.highlight", code=RendererErrorCode.RENDER_CAPTION_INVALID))
    for index, overlay in enumerate(request.overlays):
        field = f"$.overlays[{index}]"
        issues.extend(_shape_issues(overlay, required=("overlay_id", "kind", "start_tick", "end_tick", "content", "overflow_policy"), field=field))
        if isinstance(overlay, Mapping):
            issues.extend(_shape_issues(overlay.get("content"), required=("text", "font_role", "font_asset_id", "layout_token"), field=f"{field}.content"))
    issues.extend(_shape_issues(request.rights, required=("policy_version", "snapshot_ref", "snapshot_sha256", "status", "scope"), field="$.rights"))
    issues.extend(_shape_issues(request.approvals, required=("required_gate_ids", "satisfied_event_ids", "snapshot_sha256"), field="$.approvals"))
    issues.extend(_shape_issues(request.determinism, required=("canonicalization", "timeline_rounding", "random_seed", "locale", "timezone", "required_level"), field="$.determinism"))
    if request.metadata is not None:
        issues.extend(_shape_issues(request.metadata, required=(), optional=("created_at", "created_by", "notes"), field="$.metadata"))
    return issues


def validate_extensions(extensions: Mapping[str, Any]) -> tuple[RenderIssue, ...]:
    issues: list[RenderIssue] = []
    for namespace, value in extensions.items():
        field = f"$.extensions.{namespace}"
        if EXTENSION_RE.fullmatch(namespace) is None:
            issues.append(
                _issue(
                    RendererErrorCode.RENDER_INPUT_INVALID,
                    "Extension key must use a reverse-DNS namespace.",
                    field,
                )
            )
        if not isinstance(value, Mapping):
            issues.append(
                _issue(
                    RendererErrorCode.RENDER_INPUT_INVALID,
                    "Extension value must be an object.",
                    field,
                )
            )
        elif not isinstance(value.get("schema_version"), str):
            issues.append(
                _issue(
                    RendererErrorCode.RENDER_INPUT_INVALID,
                    "Extension object requires schema_version.",
                    f"{field}.schema_version",
                )
            )
    return stable_issues(issues)


def validate_capabilities(
    document: RendererCapabilities,
) -> tuple[RenderIssue, ...]:
    issues: list[RenderIssue] = []
    if document.schema_version != "1.0":
        issues.append(
            _issue(
                RendererErrorCode.RENDER_INPUT_INVALID,
                "Unsupported capability schema_version.",
                "$.schema_version",
            )
        )
    if "1.0" not in document.supported_contract_versions:
        issues.append(
            _issue(
                RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED,
                "Renderer does not declare Renderer Contract v1 support.",
                "$.supported_contract_versions",
            )
        )
    known = {item.value for item in RendererCapability}
    for name, definition in document.capabilities.items():
        if name not in known:
            issues.append(
                _issue(
                    RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED,
                    "Unknown capability is not accepted.",
                    f"$.capabilities.{name}",
                )
            )
        if definition.determinism not in {"deterministic", "seeded", "best_effort"}:
            issues.append(
                _issue(
                    RendererErrorCode.RENDER_INPUT_INVALID,
                    "Unknown capability determinism value.",
                    f"$.capabilities.{name}.determinism",
                )
            )
    for namespace, value in document.supported_extensions.items():
        if EXTENSION_RE.fullmatch(namespace) is None or not isinstance(value, Mapping):
            issues.append(
                _issue(
                    RendererErrorCode.RENDER_INPUT_INVALID,
                    "Invalid supported extension declaration.",
                    f"$.supported_extensions.{namespace}",
                )
            )
    return stable_issues(issues)


def compare_capabilities(
    required: Iterable[str | RendererCapability],
    document: RendererCapabilities,
) -> tuple[RenderIssue, ...]:
    issues: list[RenderIssue] = []
    known = {item.value for item in RendererCapability}
    for index, required_value in enumerate(required):
        name = required_value.value if isinstance(required_value, RendererCapability) else required_value
        field = f"$.renderer.required_capabilities[{index}]"
        if name not in known:
            issues.append(
                _issue(
                    RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED,
                    "Request names an unknown capability.",
                    field,
                    details={"capability": name},
                    stage="negotiate",
                )
            )
            continue
        definition = document.capabilities.get(name)
        if definition is None or not definition.supported:
            issues.append(
                _issue(
                    RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED,
                    "Renderer does not support a required capability.",
                    field,
                    details={"capability": name},
                    stage="negotiate",
                )
            )
    return stable_issues(issues)


def validate_request_capabilities(
    request: RenderRequest,
    document: RendererCapabilities,
) -> tuple[RenderIssue, ...]:
    """Purely compare a frozen request with a capability document."""
    issues: list[RenderIssue] = list(
        compare_capabilities(request.renderer.required_capabilities, document)
    )
    if request.renderer.id != document.renderer.id or request.renderer.version != document.renderer.version:
        issues.append(
            _issue(
                RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED,
                "Capability document renderer identity does not match the request.",
                "$.renderer",
                stage="negotiate",
            )
        )
    for namespace, extension in request.extensions.items():
        declaration = document.supported_extensions.get(namespace)
        version = extension.get("schema_version") if isinstance(extension, Mapping) else None
        versions = declaration.get("schema_versions") if isinstance(declaration, Mapping) else None
        if not isinstance(versions, tuple) or version not in versions:
            issues.append(
                _issue(
                    RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED,
                    "Renderer does not support the requested extension namespace/version.",
                    f"$.extensions.{namespace}",
                    stage="negotiate",
                )
            )
    plan = request.renderer.degradation_plan
    if plan is not None:
        for key in ("schema_version", "plan_id", "approval_event_id"):
            if not isinstance(plan.get(key), str) or not plan.get(key):
                issues.append(
                    _issue(
                        RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED,
                        "Degradation plan must be named and approval-bound.",
                        f"$.renderer.degradation_plan.{key}",
                        stage="negotiate",
                    )
                )
    return stable_issues(issues)


def validate_gate_rights(request: RenderRequest) -> tuple[RenderIssue, ...]:
    issues: list[RenderIssue] = []
    status = request.rights.get("status")
    if status != "allowed":
        issues.append(
            _issue(
                RendererErrorCode.RENDER_RIGHTS_BLOCKED,
                "Rights snapshot does not allow this render.",
                "$.rights.status",
                stage="preflight",
            )
        )
    scope = request.rights.get("scope")
    if scope != request.render_mode.value:
        issues.append(
            _issue(
                RendererErrorCode.RENDER_RIGHTS_BLOCKED,
                "Rights scope does not match render_mode.",
                "$.rights.scope",
                stage="preflight",
            )
        )
    required = request.approvals.get("required_gate_ids")
    satisfied = request.approvals.get("satisfied_event_ids")
    if not isinstance(required, tuple) or not all(isinstance(item, str) for item in required):
        issues.append(
            _issue(
                RendererErrorCode.RENDER_GATE_BLOCKED,
                "required_gate_ids must be an explicit array.",
                "$.approvals.required_gate_ids",
                stage="preflight",
            )
        )
    if not isinstance(satisfied, tuple) or not all(isinstance(item, str) for item in satisfied):
        issues.append(
            _issue(
                RendererErrorCode.RENDER_GATE_BLOCKED,
                "satisfied_event_ids must be an explicit array.",
                "$.approvals.satisfied_event_ids",
                stage="preflight",
            )
        )
    elif isinstance(required, tuple) and required and not satisfied:
        issues.append(
            _issue(
                RendererErrorCode.RENDER_GATE_BLOCKED,
                "Required gates have no approval events.",
                "$.approvals.satisfied_event_ids",
                stage="preflight",
            )
        )
    snapshot_error = _sha_issue(request.approvals.get("snapshot_sha256"), "$.approvals.snapshot_sha256")
    if snapshot_error is not None:
        issues.append(snapshot_error)
    rights_hash_error = _sha_issue(request.rights.get("snapshot_sha256"), "$.rights.snapshot_sha256")
    if rights_hash_error is not None:
        issues.append(rights_hash_error)
    return stable_issues(issues)


def _timeline_issues(request: RenderRequest, asset_ids: set[str]) -> list[RenderIssue]:
    issues: list[RenderIssue] = []
    timeline = request.timeline
    if timeline.get("model") != "narration_segments_v1":
        issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, "Unsupported timeline model.", "$.timeline.model"))
    timebase = timeline.get("timebase")
    if not isinstance(timebase, Mapping) or timebase.get("ticks_per_second") != 1000:
        issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, "Timeline must use 1000 ticks per second.", "$.timeline.timebase.ticks_per_second"))
    if timeline.get("frame_rounding") != "integer_round_half_up_v1":
        issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, "Unsupported frame rounding policy.", "$.timeline.frame_rounding"))
    duration = timeline.get("duration_ticks")
    if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
        issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, "duration_ticks must be a positive integer.", "$.timeline.duration_ticks"))
        duration = 0
    segments = timeline.get("segments")
    if not isinstance(segments, tuple) or not segments:
        issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, "Timeline requires at least one segment.", "$.timeline.segments"))
        return issues
    previous_end = 0
    segment_ids: set[str] = set()
    caption_refs: set[str] = set()
    overlay_refs: set[str] = set()
    audio_refs: set[str] = set()
    for index, segment in enumerate(segments):
        field = f"$.timeline.segments[{index}]"
        if not isinstance(segment, Mapping):
            issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, "Segment must be an object.", field))
            continue
        segment_id = segment.get("segment_id")
        if not isinstance(segment_id, str) or not segment_id or segment_id in segment_ids:
            issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, "segment_id must be non-empty and unique.", f"{field}.segment_id"))
        else:
            segment_ids.add(segment_id)
        start = segment.get("start_tick")
        end = segment.get("end_tick")
        if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool) or end <= start:
            issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, "Segment interval must have integer end_tick > start_tick.", field))
            continue
        if start != previous_end:
            issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, "Segments must be sorted, contiguous and non-overlapping.", f"{field}.start_tick"))
        previous_end = end
        visual = segment.get("visual")
        if not isinstance(visual, Mapping):
            issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, "Segment visual must be an object.", f"{field}.visual"))
        else:
            kind = visual.get("kind")
            if kind not in {item.value for item in TimelineAssetKind}:
                issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, "Unknown visual kind.", f"{field}.visual.kind"))
            if index == 0 and kind == TimelineAssetKind.HOLD.value:
                issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, "The first segment cannot hold a previous visual.", f"{field}.visual.kind"))
            visual_assets = visual.get("asset_ids")
            if not isinstance(visual_assets, tuple):
                issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, "visual.asset_ids must be an array.", f"{field}.visual.asset_ids"))
            else:
                for asset_id in visual_assets:
                    if asset_id not in asset_ids:
                        issues.append(_issue(RendererErrorCode.RENDER_ASSET_MISSING, "Timeline references an unknown visual asset.", f"{field}.visual.asset_ids", details={"asset_id": asset_id}))
        for key, target in (("caption_cue_ids", caption_refs), ("overlay_ids", overlay_refs)):
            values = segment.get(key)
            if not isinstance(values, tuple):
                issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, f"{key} must be an array.", f"{field}.{key}"))
            else:
                target.update(item for item in values if isinstance(item, str))
        narration = segment.get("narration")
        if narration is not None:
            if not isinstance(narration, Mapping) or not isinstance(narration.get("cue_ids"), tuple):
                issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, "narration must be null or contain cue_ids.", f"{field}.narration"))
            else:
                audio_refs.update(item for item in narration["cue_ids"] if isinstance(item, str))
    if previous_end != duration:
        issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, "Segments must cover exactly duration_ticks.", "$.timeline.segments"))
    output_duration = request.output_spec.get("duration_ticks")
    if output_duration != duration:
        issues.append(_issue(RendererErrorCode.RENDER_TIMELINE_INVALID, "Timeline duration must equal output_spec duration.", "$.output_spec.duration_ticks"))

    audio_cues = request.audio.get("cues")
    declared_audio = {
        cue.get("cue_id") for cue in audio_cues if isinstance(cue, Mapping)
    } if isinstance(audio_cues, tuple) else set()
    for cue_id in sorted(audio_refs - declared_audio):
        issues.append(_issue(RendererErrorCode.RENDER_AUDIO_INVALID, "Narration references an unknown audio cue.", "$.timeline.segments", details={"cue_id": cue_id}))
    caption_ids: set[str] = set()
    tracks = request.captions.get("tracks")
    if isinstance(tracks, tuple):
        for track in tracks:
            if isinstance(track, Mapping) and isinstance(track.get("cues"), tuple):
                caption_ids.update(cue.get("cue_id") for cue in track["cues"] if isinstance(cue, Mapping) and isinstance(cue.get("cue_id"), str))
    for cue_id in sorted(caption_refs - caption_ids):
        issues.append(_issue(RendererErrorCode.RENDER_CAPTION_INVALID, "Timeline references an unknown caption cue.", "$.timeline.segments", details={"cue_id": cue_id}))
    overlay_ids = {item.get("overlay_id") for item in request.overlays if isinstance(item.get("overlay_id"), str)}
    for overlay_id in sorted(overlay_refs - overlay_ids):
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Timeline references an unknown overlay.", "$.timeline.segments", details={"overlay_id": overlay_id}))
    return issues


def _audio_issues(request: RenderRequest, assets: Mapping[str, ArtifactBinding]) -> list[RenderIssue]:
    issues: list[RenderIssue] = []
    final_mix_id = request.audio.get("final_mix_asset_id")
    if not isinstance(final_mix_id, str) or final_mix_id not in assets:
        issues.append(_issue(RendererErrorCode.RENDER_AUDIO_INVALID, "Audio requires an existing final mix asset.", "$.audio.final_mix_asset_id"))
    elif assets[final_mix_id].role != "final_audio_mix":
        issues.append(_issue(RendererErrorCode.RENDER_AUDIO_INVALID, "final_mix_asset_id must reference role final_audio_mix.", "$.audio.final_mix_asset_id"))
    if request.audio.get("sync_policy") != "timeline_zero_locked":
        issues.append(_issue(RendererErrorCode.RENDER_AUDIO_INVALID, "Audio must be locked to timeline tick zero.", "$.audio.sync_policy"))
    cues = request.audio.get("cues")
    duration = request.timeline.get("duration_ticks", 0)
    cue_ids: set[str] = set()
    if not isinstance(cues, tuple):
        issues.append(_issue(RendererErrorCode.RENDER_AUDIO_INVALID, "audio.cues must be an array.", "$.audio.cues"))
    else:
        for index, cue in enumerate(cues):
            field = f"$.audio.cues[{index}]"
            if not isinstance(cue, Mapping):
                issues.append(_issue(RendererErrorCode.RENDER_AUDIO_INVALID, "Audio cue must be an object.", field))
                continue
            cue_id = cue.get("cue_id")
            if not isinstance(cue_id, str) or cue_id in cue_ids:
                issues.append(_issue(RendererErrorCode.RENDER_AUDIO_INVALID, "cue_id must be non-empty and unique.", f"{field}.cue_id"))
            else:
                cue_ids.add(cue_id)
            asset_id = cue.get("asset_id")
            if asset_id not in assets:
                issues.append(_issue(RendererErrorCode.RENDER_ASSET_MISSING, "Audio cue references an unknown asset.", f"{field}.asset_id"))
            start, end = cue.get("start_tick"), cue.get("end_tick")
            if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool) or start < 0 or end <= start or end > duration:
                issues.append(_issue(RendererErrorCode.RENDER_AUDIO_INVALID, "Audio cue interval is outside the timeline.", field))
    return issues


def _caption_issues(request: RenderRequest, assets: Mapping[str, ArtifactBinding]) -> list[RenderIssue]:
    issues: list[RenderIssue] = []
    tracks = request.captions.get("tracks")
    if not isinstance(tracks, tuple):
        return [_issue(RendererErrorCode.RENDER_CAPTION_INVALID, "captions.tracks must be an array.", "$.captions.tracks")]
    segments = {
        item.get("segment_id"): (item.get("start_tick"), item.get("end_tick"))
        for item in request.timeline.get("segments", ())
        if isinstance(item, Mapping)
    }
    cue_ids: set[str] = set()
    for track_index, track in enumerate(tracks):
        field = f"$.captions.tracks[{track_index}]"
        if not isinstance(track, Mapping):
            issues.append(_issue(RendererErrorCode.RENDER_CAPTION_INVALID, "Caption track must be an object.", field))
            continue
        for source_key in ("text_source_asset_id", "timing_source_asset_id"):
            if track.get(source_key) not in assets:
                issues.append(_issue(RendererErrorCode.RENDER_ASSET_MISSING, "Caption source references an unknown asset.", f"{field}.{source_key}"))
        style = track.get("style")
        if not isinstance(style, Mapping):
            issues.append(_issue(RendererErrorCode.RENDER_CAPTION_INVALID, "Caption style must be an object.", f"{field}.style"))
        else:
            font_id = style.get("font_asset_id")
            if font_id not in assets or not assets[font_id].role.startswith("font_"):
                issues.append(_issue(RendererErrorCode.RENDER_FONT_UNAVAILABLE, "Caption font asset is unavailable.", f"{field}.style.font_asset_id"))
            if not isinstance(style.get("max_lines"), int) or isinstance(style.get("max_lines"), bool) or style.get("max_lines", 0) <= 0:
                issues.append(_issue(RendererErrorCode.RENDER_CAPTION_INVALID, "max_lines must be a positive integer.", f"{field}.style.max_lines"))
            if style.get("overflow_policy") != "fail":
                issues.append(_issue(RendererErrorCode.RENDER_CAPTION_INVALID, "Caption overflow_policy must fail closed.", f"{field}.style.overflow_policy"))
        cues = track.get("cues")
        if not isinstance(cues, tuple):
            issues.append(_issue(RendererErrorCode.RENDER_CAPTION_INVALID, "Caption cues must be an array.", f"{field}.cues"))
            continue
        for cue_index, cue in enumerate(cues):
            cue_field = f"{field}.cues[{cue_index}]"
            if not isinstance(cue, Mapping):
                issues.append(_issue(RendererErrorCode.RENDER_CAPTION_INVALID, "Caption cue must be an object.", cue_field))
                continue
            cue_id = cue.get("cue_id")
            if not isinstance(cue_id, str) or cue_id in cue_ids:
                issues.append(_issue(RendererErrorCode.RENDER_CAPTION_INVALID, "Caption cue_id must be non-empty and unique.", f"{cue_field}.cue_id"))
            else:
                cue_ids.add(cue_id)
            segment_id = cue.get("segment_id")
            interval = segments.get(segment_id)
            start, end = cue.get("start_tick"), cue.get("end_tick")
            if interval is None or not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool) or start < interval[0] or end > interval[1] or end <= start:
                issues.append(_issue(RendererErrorCode.RENDER_CAPTION_INVALID, "Caption cue must fit its referenced segment.", cue_field))
                continue
            granularity = cue.get("granularity")
            if granularity not in {item.value for item in CaptionTimingLevel if item is not CaptionTimingLevel.WORD}:
                issues.append(_issue(RendererErrorCode.RENDER_CAPTION_INVALID, "Caption granularity must be phrase or sentence.", f"{cue_field}.granularity"))
            words = cue.get("words")
            if not isinstance(words, tuple):
                issues.append(_issue(RendererErrorCode.RENDER_CAPTION_INVALID, "Caption words must be an array.", f"{cue_field}.words"))
            else:
                previous = start
                for word_index, word in enumerate(words):
                    word_field = f"{cue_field}.words[{word_index}]"
                    if not isinstance(word, Mapping):
                        issues.append(_issue(RendererErrorCode.RENDER_CAPTION_INVALID, "Caption word must be an object.", word_field))
                        continue
                    word_start, word_end = word.get("start_tick"), word.get("end_tick")
                    if not isinstance(word_start, int) or isinstance(word_start, bool) or not isinstance(word_end, int) or isinstance(word_end, bool) or word_start < previous or word_end <= word_start or word_end > end:
                        issues.append(_issue(RendererErrorCode.RENDER_CAPTION_INVALID, "Word timing must be ordered and inside its cue.", word_field))
                    else:
                        previous = word_end
                highlight = cue.get("highlight")
                if isinstance(highlight, Mapping) and highlight.get("mode") == "word" and not words:
                    issues.append(_issue(RendererErrorCode.RENDER_CAPTION_INVALID, "Word highlight requires word timing.", f"{cue_field}.highlight"))
    return issues


def validate_render_request(request: RenderRequest) -> tuple[RenderIssue, ...]:
    """Validate Request structure semantics, portable refs, rights and gates.

    Stored request hash integrity is deliberately a separate layer exposed by
    :func:`validate_request_hash`.
    """
    issues: list[RenderIssue] = _request_shape_issues(request)
    if request.schema_version != "1.0":
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Unsupported request schema_version.", "$.schema_version"))
    for value, field in (
        (request.request_hash, "$.request_hash"),
        (request.project.manifest_sha256, "$.project.manifest_sha256"),
        (request.release.manifest_sha256, "$.release.manifest_sha256"),
        (request.profile.sha256, "$.profile.sha256"),
        (request.renderer.capability_document_sha256, "$.renderer.capability_document_sha256"),
    ):
        error = _sha_issue(value, field)
        if error is not None:
            issues.append(error)
    roots = set(request.roots.keys())
    if not roots:
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "At least one logical root is required.", "$.roots"))
    refs = (
        (request.project.manifest_ref, "$.project.manifest_ref"),
        (request.release.manifest_ref, "$.release.manifest_ref"),
        (request.profile.ref, "$.profile.ref"),
    )
    for ref, field in refs:
        issues.extend(_portable_ref_issues(ref, field, roots))
    if request.renderer.capability_document_ref is None:
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Renderer capability_document_ref is required.", "$.renderer.capability_document_ref"))
    else:
        issues.extend(_portable_ref_issues(request.renderer.capability_document_ref, "$.renderer.capability_document_ref", roots))
    for mapping, field in ((request.audio, "$.audio"), (request.rights, "$.rights")):
        ref = mapping.get("manifest_ref" if field == "$.audio" else "snapshot_ref")
        if isinstance(ref, Mapping):
            issues.extend(_portable_ref_issues(PortableRef(str(ref.get("root", "")), str(ref.get("path", ""))), f"{field}.{'manifest_ref' if field == '$.audio' else 'snapshot_ref'}", roots))
    known_capabilities = {item.value for item in RendererCapability}
    for index, capability in enumerate(request.renderer.required_capabilities):
        if capability not in known_capabilities:
            issues.append(_issue(RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED, "Unknown required capability.", f"$.renderer.required_capabilities[{index}]", stage="negotiate"))
    if request.render_mode is RenderMode.FINAL and any(token in request.renderer.version for token in ("*", "<", ">", "^", "~")):
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Final render requires an exact renderer version.", "$.renderer.version"))
    asset_map: dict[str, ArtifactBinding] = {}
    for index, asset in enumerate(request.assets):
        field = f"$.assets[{index}]"
        if not asset.asset_id or asset.asset_id in asset_map:
            issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "asset_id must be non-empty and unique.", f"{field}.asset_id"))
        else:
            asset_map[asset.asset_id] = asset
        if asset.bytes <= 0:
            issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Asset bytes must be positive.", f"{field}.bytes"))
        error = _sha_issue(asset.sha256, f"{field}.sha256")
        if error is not None:
            issues.append(error)
        issues.extend(_portable_ref_issues(asset.ref, f"{field}.ref", roots))
    target = request.output.get("target")
    if isinstance(target, Mapping):
        target_ref = PortableRef(str(target.get("root", "")), str(target.get("path", "")))
        issues.extend(_portable_ref_issues(target_ref, "$.output.target", roots))
        root_policy = request.roots.get(target_ref.root)
        if not isinstance(root_policy, Mapping) or root_policy.get("output_access") != "request_targets_only":
            issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Output target root is not authorized for request targets.", "$.output.target.root"))
    else:
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Output target must be a portable ref.", "$.output.target"))
    if request.output.get("overwrite_policy") != "fail_if_exists":
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Persistent output must use fail_if_exists.", "$.output.overwrite_policy"))
    issues.extend(_timeline_issues(request, set(asset_map)))
    issues.extend(_audio_issues(request, asset_map))
    issues.extend(_caption_issues(request, asset_map))
    issues.extend(validate_gate_rights(request))
    issues.extend(validate_extensions(request.extensions))
    determinism = request.determinism
    expected = {
        "canonicalization": "canonical-json-v1",
        "timeline_rounding": "integer_round_half_up_v1",
        "timezone": "UTC",
    }
    for key, value in expected.items():
        if determinism.get(key) != value:
            issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, f"determinism.{key} must be {value}.", f"$.determinism.{key}"))
    if determinism.get("required_level") not in {"semantic", "bitwise"}:
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Unknown determinism required_level.", "$.determinism.required_level"))
    if not isinstance(determinism.get("locale"), str):
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Determinism locale must be explicit.", "$.determinism.locale"))
    return stable_issues(issues)


def validate_request_hash(request: RenderRequest) -> tuple[RenderIssue, ...]:
    actual = semantic_request_hash(render_request_to_dict(request))
    if actual == request.request_hash:
        return ()
    return (
        _issue(
            RendererErrorCode.RENDER_HASH_MISMATCH,
            "Stored request_hash does not match canonical semantic payload.",
            "$.request_hash",
            details={"actual_sha256": actual},
        ),
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_request_filesystem(
    request: RenderRequest,
    resolver: RootResolver,
) -> tuple[RenderIssue, ...]:
    issues: list[RenderIssue] = []
    for index, asset in enumerate(request.assets):
        field = f"$.assets[{index}]"
        try:
            path = resolver.resolve(asset.ref, require_exists=True)
        except FileNotFoundError:
            code = RendererErrorCode.RENDER_FONT_UNAVAILABLE if asset.role.startswith("font_") else RendererErrorCode.RENDER_ASSET_MISSING
            issues.append(_issue(code, "Declared asset is unavailable.", f"{field}.ref"))
            continue
        except PortablePathError as error:
            issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, str(error), f"{field}.ref"))
            continue
        if not path.is_file():
            issues.append(_issue(RendererErrorCode.RENDER_ASSET_MISSING, "Declared asset is not a regular file.", f"{field}.ref"))
            continue
        if path.stat().st_size != asset.bytes:
            issues.append(_issue(RendererErrorCode.RENDER_HASH_MISMATCH, "Asset byte length does not match its binding.", f"{field}.bytes"))
        if _sha256_file(path) != asset.sha256:
            issues.append(_issue(RendererErrorCode.RENDER_HASH_MISMATCH, "Asset SHA-256 does not match its binding.", f"{field}.sha256"))
    return stable_issues(issues)


def _valid_utc(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def validate_render_result(result: RenderResult) -> tuple[RenderIssue, ...]:
    issues: list[RenderIssue] = []
    if result.schema_version != "1.0":
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Unsupported result schema_version.", "$.schema_version"))
    for value, field in ((result.request_hash, "$.request_hash"), (result.renderer.capability_document_sha256, "$.renderer.capability_document_sha256")):
        error = _sha_issue(value, field)
        if error is not None:
            issues.append(error)
    terminal = result.status in {RenderStatus.SUCCEEDED, RenderStatus.FAILED, RenderStatus.BLOCKED, RenderStatus.CANCELLED}
    if result.status is not RenderStatus.PENDING and not _valid_utc(result.started_at):
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "started_at must be UTC for running or terminal status.", "$.started_at"))
    if terminal and not _valid_utc(result.finished_at):
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Terminal result requires UTC finished_at.", "$.finished_at"))
    if not terminal and result.finished_at is not None:
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Non-terminal result must not have finished_at.", "$.finished_at"))
    if result.status is RenderStatus.SUCCEEDED:
        if not result.output:
            issues.append(_issue(RendererErrorCode.RENDER_OUTPUT_MISSING, "Succeeded result requires output.", "$.output", stage="collect"))
        if result.media_probe is None:
            issues.append(_issue(RendererErrorCode.RENDER_PROBE_FAILED, "Succeeded result requires media_probe.", "$.media_probe", stage="probe"))
        if result.qc_handoff is None:
            issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Succeeded result requires qc_handoff.", "$.qc_handoff"))
        if result.errors or result.primary_error_code is not None:
            issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Succeeded result cannot contain errors.", "$.errors"))
    elif result.status in {RenderStatus.FAILED, RenderStatus.BLOCKED, RenderStatus.CANCELLED}:
        if not result.errors or result.primary_error_code is None:
            issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Failed, blocked or cancelled result requires structured errors and primary_error_code.", "$.errors"))
    elif result.output:
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Pending or running result cannot register terminal output.", "$.output"))
    artifacts = (*result.output, *result.sidecars)
    expected_hashes: dict[str, str] = {}
    for index, artifact in enumerate(artifacts):
        field = "$.output" if index < len(result.output) else "$.sidecars"
        expected_hashes[artifact.asset_id] = artifact.sha256
        error = _sha_issue(artifact.sha256, f"{field}[{index if index < len(result.output) else index - len(result.output)}].sha256")
        if error is not None:
            issues.append(error)
        issues.extend(_portable_ref_issues(artifact.ref, field))
    if dict(result.output_hashes) != expected_hashes:
        issues.append(_issue(RendererErrorCode.RENDER_HASH_MISMATCH, "output_hashes must exactly match output and sidecar artifacts.", "$.output_hashes", stage="collect"))
    for index, log in enumerate(result.logs):
        ref = log.get("ref")
        if not isinstance(ref, Mapping):
            issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Log requires a portable ref.", f"$.logs[{index}].ref"))
        else:
            issues.extend(_portable_ref_issues(PortableRef(str(ref.get("root", "")), str(ref.get("path", ""))), f"$.logs[{index}].ref"))
    issues.extend(validate_extensions(result.extensions))
    return stable_issues(issues)


def validate_release_snapshot(snapshot: ReleaseSnapshot) -> tuple[RenderIssue, ...]:
    issues: list[RenderIssue] = []
    if snapshot.schema_version != "1.0":
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Unsupported snapshot schema_version.", "$.schema_version"))
    error = _sha_issue(snapshot.snapshot_hash, "$.snapshot_hash")
    if error is not None:
        issues.append(error)
    elif snapshot.snapshot_id != snapshot_id_from_hash(snapshot.snapshot_hash):
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "snapshot_id must be derived from snapshot_hash.", "$.snapshot_id"))
    if not snapshot.project_id:
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "project_id is required.", "$.project_id"))
    if not snapshot.release_id:
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "release_id is required.", "$.release_id"))
    if not _valid_utc(snapshot.created_at):
        issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "created_at must be an explicit UTC timestamp.", "$.created_at"))
    artifact_ids: set[str] = set()
    expected_hashes: dict[str, str] = {}
    for index, artifact in enumerate(snapshot.artifacts):
        field = f"$.artifacts[{index}]"
        if artifact.asset_id in artifact_ids:
            issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Snapshot asset_id must be unique.", f"{field}.asset_id"))
        artifact_ids.add(artifact.asset_id)
        expected_hashes[artifact.asset_id] = artifact.sha256
        hash_error = _sha_issue(artifact.sha256, f"{field}.sha256")
        if hash_error is not None:
            issues.append(hash_error)
        issues.extend(_portable_ref_issues(artifact.ref, f"{field}.ref"))
        if not artifact.source_manifest_artifact_id:
            issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Snapshot artifact requires source_manifest_artifact_id.", f"{field}.source_manifest_artifact_id"))
        if not artifact.rights_ref:
            issues.append(_issue(RendererErrorCode.RENDER_RIGHTS_BLOCKED, "Snapshot artifact requires rights_ref.", f"{field}.rights_ref", stage="preflight"))
    if dict(snapshot.artifact_hashes) != expected_hashes:
        issues.append(_issue(RendererErrorCode.RENDER_HASH_MISMATCH, "artifact_hashes must exactly match snapshot artifacts.", "$.artifact_hashes"))
    if snapshot.rights.get("status") != "allowed":
        issues.append(_issue(RendererErrorCode.RENDER_RIGHTS_BLOCKED, "Snapshot rights are not allowed.", "$.rights.status", stage="preflight"))
    if snapshot.approvals.get("status") != "approved":
        issues.append(_issue(RendererErrorCode.RENDER_GATE_BLOCKED, "Snapshot approvals are not approved.", "$.approvals.status", stage="preflight"))
    if snapshot.release_gates.get("status") != "passed":
        issues.append(_issue(RendererErrorCode.RENDER_GATE_BLOCKED, "Snapshot release gates have not passed.", "$.release_gates.status", stage="preflight"))
    source_bindings = (
        (snapshot.profile, "$.profile"),
        (snapshot.timeline_source, "$.timeline_source"),
        (snapshot.audio_source, "$.audio_source"),
        (snapshot.caption_source, "$.caption_source"),
        *((item, f"$.source_manifests[{index}]") for index, item in enumerate(snapshot.source_manifests)),
    )
    for binding, field in source_bindings:
        for key in ("id", "version"):
            if not isinstance(binding.get(key), str) or not binding.get(key):
                issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, f"Source binding requires {key}.", f"{field}.{key}"))
        ref = binding.get("ref")
        if not isinstance(ref, Mapping):
            issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Source binding requires a portable ref.", f"{field}.ref"))
        else:
            issues.extend(_portable_ref_issues(PortableRef(str(ref.get("root", "")), str(ref.get("path", ""))), f"{field}.ref"))
        hash_error = _sha_issue(binding.get("sha256"), f"{field}.sha256")
        if hash_error is not None:
            issues.append(hash_error)
    for mapping, field in ((snapshot.rights, "$.rights"), (snapshot.approvals, "$.approvals")):
        hash_error = _sha_issue(mapping.get("snapshot_sha256"), f"{field}.snapshot_sha256")
        if hash_error is not None:
            issues.append(hash_error)
    return stable_issues(issues)


def validate_snapshot_hash(snapshot: ReleaseSnapshot) -> tuple[RenderIssue, ...]:
    actual = semantic_snapshot_hash(release_snapshot_to_dict(snapshot))
    if actual == snapshot.snapshot_hash:
        return ()
    return (
        _issue(
            RendererErrorCode.RENDER_HASH_MISMATCH,
            "Stored snapshot_hash does not match canonical semantic payload.",
            "$.snapshot_hash",
            details={"actual_sha256": actual},
        ),
    )
