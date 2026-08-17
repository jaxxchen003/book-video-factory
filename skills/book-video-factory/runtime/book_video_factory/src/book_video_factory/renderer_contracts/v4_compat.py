"""Freeze legacy V4 inputs and map them to Renderer Contract v1."""

from __future__ import annotations

import difflib
import hashlib
import json
import mimetypes
import re
import wave
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Mapping

from book_video_factory.contracts import ReleaseProfile
from book_video_factory.fonts import resolve_font_path
from book_video_factory.gates import approval_covers_path, approval_is_current
from book_video_factory.scene_contract import V4_SCENE_LINE_CONTRACT, V4_TIMELINE_SCENES
from book_video_factory.style_profiles import StyleProfile

from .canonical import canonical_sha256, request_id_from_hash, semantic_request_hash
from .enums import RendererErrorCode
from .errors import ContractValidationError, RenderIssue
from .models import ArtifactBinding, PortableRef, ReleaseSnapshot, RenderRequest
from .paths import RootResolver, normalize_portable_path
from .persistence import write_canonical_once
from .release_snapshot import create_release_snapshot, write_release_snapshot
from .serialization import (
    capabilities_from_dict,
    render_request_from_dict,
)
from .validation import (
    validate_capabilities,
    validate_release_snapshot,
    validate_render_request,
    validate_request_capabilities,
    validate_request_hash,
    validate_snapshot_hash,
)


LEGACY_RENDERER_ID = "org.book-video-factory.legacy-v4"
LEGACY_RENDERER_VERSION = "1.0.0"
LEGACY_EXTENSION = LEGACY_RENDERER_ID
V4_STYLE_ID = "book-editorial-bilingual-v2"
V4_PROFILE_ID = "book-v4-bilingual-3x4"
MONTAGE_TICKS = 960
OUTRO_TICKS = 2_500
PAUSE_REMOVED_TICKS = 20
PAUSE_INSERTED_TICKS = 1_040
PAUSE_DELTA_TICKS = PAUSE_INSERTED_TICKS - PAUSE_REMOVED_TICKS
PRE_RENDER_GATES = (
    "script",
    "timing",
    "visual_rights",
    "cover_rights",
    "bgm_rights",
    "sfx_rights",
    "voice_rights",
)


@dataclass(frozen=True)
class V4CompatibilityBundle:
    snapshot: ReleaseSnapshot
    snapshot_path: Path
    evidence_path: Path
    root_bindings: Mapping[str, Path]


@dataclass(frozen=True)
class _AlignedLine:
    line_id: str
    role: str
    zh: str
    en: str
    start_tick: int
    end_tick: int


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _fail(
    code: RendererErrorCode,
    message: str,
    field: str,
    *,
    stage: str = "validate",
    details: Mapping[str, Any] | None = None,
) -> None:
    raise ContractValidationError(
        (RenderIssue(code, message, field, details or {}, stage),)
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, *, field: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        _fail(
            RendererErrorCode.RENDER_INPUT_INVALID,
            "Required JSON input is unreadable.",
            field,
            details={"filename": path.name},
        )
        raise AssertionError from error
    if not isinstance(payload, dict):
        _fail(
            RendererErrorCode.RENDER_INPUT_INVALID,
            "Required JSON input must contain an object.",
            field,
        )
    return payload


def _require_project_file(project: Path, relative: str, *, field: str) -> Path:
    portable = normalize_portable_path(relative)
    candidate = project.joinpath(*portable.split("/")).resolve(strict=False)
    try:
        candidate.relative_to(project)
    except ValueError:
        _fail(
            RendererErrorCode.RENDER_INPUT_INVALID,
            "Input path escapes the project root.",
            field,
        )
    if not candidate.is_file():
        _fail(
            RendererErrorCode.RENDER_ASSET_MISSING,
            "Required V4 input is missing.",
            field,
            details={"path": portable},
        )
    return candidate


def _runtime_ref(runtime: Path, path: Path) -> PortableRef:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(runtime)
    except ValueError:
        _fail(
            RendererErrorCode.RENDER_INPUT_INVALID,
            "Runtime source is outside the runtime root.",
            "$.runtime",
        )
    return PortableRef("runtime", relative.as_posix())


def _project_ref(project: Path, path: Path) -> PortableRef:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(project)
    except ValueError:
        _fail(
            RendererErrorCode.RENDER_INPUT_INVALID,
            "Project source is outside the project root.",
            "$.project",
        )
    return PortableRef("project", relative.as_posix())


def _media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    explicit = {
        ".json": "application/json",
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".ttf": "font/ttf",
        ".ttc": "font/collection",
        ".otf": "font/otf",
        ".py": "text/x-python",
    }
    return explicit.get(suffix) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def _artifact(
    asset_id: str,
    role: str,
    ref: PortableRef,
    path: Path,
    rights_ref: str,
) -> ArtifactBinding:
    return ArtifactBinding(
        asset_id=asset_id,
        role=role,
        ref=ref,
        bytes=path.stat().st_size,
        sha256=_sha256_file(path),
        media_type=_media_type(path),
        source_manifest_artifact_id=f"v4-compat:{asset_id}",
        rights_ref=rights_ref,
    )


def _source_binding(
    identifier: str,
    version: str,
    ref: PortableRef,
    path: Path,
) -> dict[str, Any]:
    return {
        "id": identifier,
        "version": version,
        "ref": {"root": ref.root, "path": ref.path},
        "sha256": _sha256_file(path),
    }


def _ticks(value: Any, *, field: str) -> int:
    if isinstance(value, bool):
        _fail(RendererErrorCode.RENDER_INPUT_INVALID, "Timing value is invalid.", field)
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError):
        _fail(RendererErrorCode.RENDER_INPUT_INVALID, "Timing value is invalid.", field)
        raise AssertionError
    if not decimal.is_finite() or decimal < 0:
        _fail(RendererErrorCode.RENDER_INPUT_INVALID, "Timing value is invalid.", field)
    return int((decimal * 1000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _midpoint(left: int, right: int) -> int:
    return (left + right + 1) // 2


def _normalize(text: str) -> str:
    return "".join(re.findall(r"[\u3400-\u9fffA-Za-z0-9]", text))


def _asr_words(asr: Mapping[str, Any]) -> list[dict[str, Any]]:
    segments = asr.get("segments")
    if not isinstance(segments, list) or not segments:
        _fail(
            RendererErrorCode.RENDER_CAPTION_INVALID,
            "ASR requires non-empty segments.",
            "$.asr.segments",
        )
    words: list[dict[str, Any]] = []
    for segment_index, segment in enumerate(segments):
        if not isinstance(segment, Mapping):
            _fail(
                RendererErrorCode.RENDER_CAPTION_INVALID,
                "ASR segment must be an object.",
                f"$.asr.segments[{segment_index}]",
            )
        raw_words = segment.get("words")
        if not isinstance(raw_words, list):
            continue
        for word_index, word in enumerate(raw_words):
            field = f"$.asr.segments[{segment_index}].words[{word_index}]"
            if not isinstance(word, Mapping) or not isinstance(word.get("word"), str):
                _fail(RendererErrorCode.RENDER_CAPTION_INVALID, "ASR word is invalid.", field)
            start = _ticks(word.get("start"), field=f"{field}.start")
            end = _ticks(word.get("end"), field=f"{field}.end")
            if end <= start:
                _fail(
                    RendererErrorCode.RENDER_CAPTION_INVALID,
                    "ASR word timing must have positive duration.",
                    field,
                )
            words.append({"word": str(word["word"]), "start_tick": start, "end_tick": end})
    if not words:
        _fail(
            RendererErrorCode.RENDER_CAPTION_INVALID,
            "ASR does not contain word timing.",
            "$.asr.segments",
        )
    return words


def _word_normalized(words: list[dict[str, Any]], index: int) -> str:
    value = _normalize(str(words[index]["word"]))
    next_value = _normalize(str(words[index + 1]["word"])) if index + 1 < len(words) else ""
    if value in {"情", "秦"} and next_value == "山":
        return "晴"
    return value


def _script_lines(script: Mapping[str, Any]) -> list[dict[str, str]]:
    raw = script.get("lines")
    if not isinstance(raw, list) or len(raw) != 15:
        _fail(
            RendererErrorCode.RENDER_CAPTION_INVALID,
            "V4 requires exactly 15 script lines.",
            "$.script.lines",
        )
    lines: list[dict[str, str]] = []
    expected_ids = [f"V{index:02d}" for index in range(1, 16)]
    for index, item in enumerate(raw):
        field = f"$.script.lines[{index}]"
        if not isinstance(item, Mapping):
            _fail(RendererErrorCode.RENDER_CAPTION_INVALID, "Script line must be an object.", field)
        values = {key: str(item.get(key, "")).strip() for key in ("id", "role", "zh", "en")}
        if values["id"] != expected_ids[index] or not all(values.values()):
            _fail(
                RendererErrorCode.RENDER_CAPTION_INVALID,
                "V4 script lines require ordered V01-V15 IDs and non-empty role/zh/en text.",
                field,
            )
        lines.append(values)
    return lines


def _proportional_alignment(
    lines: list[dict[str, str]], words: list[dict[str, Any]]
) -> list[_AlignedLine]:
    duration = max(int(word["end_tick"]) for word in words)
    weights = [max(1, len(_normalize(line["zh"]))) for line in lines]
    total = sum(weights)
    cursor = 0
    aligned: list[_AlignedLine] = []
    accumulated = 0
    for index, (line, weight) in enumerate(zip(lines, weights, strict=True)):
        accumulated += weight
        end = duration if index == len(lines) - 1 else (duration * accumulated * 2 + total) // (2 * total)
        aligned.append(
            _AlignedLine(line["id"], line["role"], line["zh"], line["en"], cursor, end)
        )
        cursor = end
    return aligned


def _align_lines(
    lines: list[dict[str, str]], words: list[dict[str, Any]]
) -> tuple[list[_AlignedLine], str]:
    characters: list[str] = []
    character_to_word: list[int] = []
    for index in range(len(words)):
        for character in _word_normalized(words, index):
            characters.append(character)
            character_to_word.append(index)
    transcript = "".join(characters)
    cursor = 0
    aligned: list[_AlignedLine] = []
    exact = True
    for line in lines:
        target = _normalize(line["zh"])
        position = transcript.find(target, cursor)
        if position < 0:
            exact = False
            break
        start_word = words[character_to_word[position]]
        end_word = words[character_to_word[position + len(target) - 1]]
        aligned.append(
            _AlignedLine(
                line["id"],
                line["role"],
                line["zh"],
                line["en"],
                int(start_word["start_tick"]),
                int(end_word["end_tick"]),
            )
        )
        cursor = position + len(target)
    if exact:
        return aligned, "exact_v2"

    cursor = 0
    aligned = []
    for line in lines:
        target = _normalize(line["zh"])
        best: tuple[float, int, int] | None = None
        minimum = max(1, len(target) - 7)
        maximum = len(target) + 9
        for start in range(cursor, min(len(transcript), cursor + 40) + 1):
            for length in range(minimum, maximum + 1):
                end = start + length
                if end > len(transcript):
                    break
                ratio = difflib.SequenceMatcher(
                    a=target, b=transcript[start:end], autojunk=False
                ).ratio()
                score = ratio - abs(length - len(target)) * 0.006
                if best is None or score > best[0]:
                    best = (score, start, end)
        if best is None or best[0] < 0.45 or best[2] <= best[1]:
            return _proportional_alignment(lines, words), "proportional_v3"
        _, start, end = best
        start_word = words[character_to_word[start]]
        end_word = words[character_to_word[end - 1]]
        aligned.append(
            _AlignedLine(
                line["id"],
                line["role"],
                line["zh"],
                line["en"],
                int(start_word["start_tick"]),
                int(end_word["end_tick"]),
            )
        )
        cursor = end
    return aligned, "ordered_fuzzy_v3"


def _apply_intro_pause(
    lines: list[dict[str, str]], words: list[dict[str, Any]]
) -> tuple[list[_AlignedLine], str, int]:
    original, _ = _align_lines(lines, words)
    cue_end = next(line.end_tick for line in original if line.line_id == "V02")
    shifted: list[dict[str, Any]] = []
    for word in words:
        start = int(word["start_tick"])
        end = int(word["end_tick"])
        if start >= cue_end:
            start += PAUSE_DELTA_TICKS
            end += PAUSE_DELTA_TICKS
        elif end > cue_end:
            end = cue_end
        shifted.append({"word": word["word"], "start_tick": start, "end_tick": end})
    aligned, mode = _align_lines(lines, shifted)
    montage_start = next(line.end_tick for line in aligned if line.line_id == "V02") + 40
    montage_end = montage_start + MONTAGE_TICKS
    adjusted = [
        _AlignedLine(
            line.line_id,
            line.role,
            line.zh,
            line.en,
            max(line.start_tick, montage_end) if line.line_id == "V03" else line.start_tick,
            line.end_tick,
        )
        for line in aligned
    ]
    if any(line.end_tick <= line.start_tick for line in adjusted):
        _fail(
            RendererErrorCode.RENDER_TIMELINE_INVALID,
            "Intro pause produced a non-positive script cue.",
            "$.timing.lines",
        )
    return adjusted, mode, cue_end


def _wave_duration_ticks(path: Path) -> int:
    try:
        with wave.open(str(path), "rb") as source:
            frames = source.getnframes()
            rate = source.getframerate()
    except (OSError, EOFError, wave.Error) as error:
        _fail(
            RendererErrorCode.RENDER_AUDIO_INVALID,
            "Narration must be a readable WAV file for compatibility freezing.",
            "$.assets.narration",
        )
        raise AssertionError from error
    if frames <= 0 or rate <= 0:
        _fail(
            RendererErrorCode.RENDER_AUDIO_INVALID,
            "Narration WAV has no usable duration.",
            "$.assets.narration",
        )
    return (frames * 1000 * 2 + rate) // (2 * rate)


def _timeline(
    aligned: list[_AlignedLine],
    voice_duration_ticks: int,
    scene_asset_ids: Mapping[str, str],
    cover_asset_id: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    by_id = {line.line_id: line for line in aligned}
    total_duration = voice_duration_ticks + OUTRO_TICKS
    montage_start = by_id["V02"].end_tick + 40
    montage_end = montage_start + MONTAGE_TICKS
    segment_for_line: dict[str, str] = {}
    segments: list[dict[str, Any]] = []
    groups = list(V4_TIMELINE_SCENES)
    cursor = 0
    for index, (timeline_id, scene_id) in enumerate(groups):
        line_ids = list(V4_SCENE_LINE_CONTRACT[scene_id])
        if timeline_id == "HOOK":
            end = montage_start
        elif timeline_id == "BOOK":
            end = min(by_id[item].start_tick for item in V4_SCENE_LINE_CONTRACT[groups[index + 1][1]])
        elif index == len(groups) - 1:
            end = total_duration
        else:
            current_end = max(by_id[item].end_tick for item in line_ids)
            next_ids = V4_SCENE_LINE_CONTRACT[groups[index + 1][1]]
            next_start = min(by_id[item].start_tick for item in next_ids)
            end = _midpoint(current_end, next_start)
        if end <= cursor:
            _fail(
                RendererErrorCode.RENDER_TIMELINE_INVALID,
                "V4 scene ordering cannot form a continuous timeline.",
                "$.timeline.segments",
                details={"segment_id": timeline_id},
            )
        visual_ids = [scene_asset_ids[scene_id]]
        visual_kind = "still"
        motion = "legacy_zoompan_v1"
        if timeline_id == "BOOK":
            visual_ids.append(cover_asset_id)
            visual_kind = "sequence"
            motion = "legacy_cover_composite_v1"
        caption_ids = [
            item
            for line_id in line_ids
            for item in (f"caption-zh-{line_id}", f"caption-en-{line_id}")
        ]
        audio_ids = [f"narration-{line_id}" for line_id in line_ids]
        overlay_ids = ["overlay-brand"]
        if end > montage_end:
            overlay_ids.append("overlay-title")
        segments.append(
            {
                "segment_id": timeline_id,
                "start_tick": cursor,
                "end_tick": end,
                "narration": {"cue_ids": audio_ids},
                "visual": {"kind": visual_kind, "asset_ids": visual_ids, "motion": motion},
                "caption_cue_ids": caption_ids,
                "overlay_ids": overlay_ids,
                "transition": {"in": "cut", "out": "cut"},
                "metadata": {"script_line_ids": line_ids, "scene_ids": [scene_id]},
            }
        )
        for line_id in line_ids:
            segment_for_line[line_id] = timeline_id
        cursor = end
        if timeline_id == "HOOK":
            segments.append(
                {
                    "segment_id": "MONTAGE",
                    "start_tick": cursor,
                    "end_tick": montage_end,
                    "narration": None,
                    "visual": {
                        "kind": "sequence",
                        "asset_ids": [scene_asset_ids[f"S{item:02d}"] for item in range(1, 9)],
                        "motion": "legacy_topic_cards_v1",
                    },
                    "caption_cue_ids": [],
                    "overlay_ids": ["overlay-brand"],
                    "transition": {"in": "cut", "out": "cut"},
                    "metadata": {"script_line_ids": [], "scene_ids": []},
                }
            )
            cursor = montage_end
    if cursor != total_duration:
        _fail(
            RendererErrorCode.RENDER_TIMELINE_INVALID,
            "V4 timeline does not cover the requested duration.",
            "$.timeline.duration_ticks",
        )
    return (
        {
            "model": "narration_segments_v1",
            "timebase": {"ticks_per_second": 1000},
            "frame_rounding": "integer_round_half_up_v1",
            "duration_ticks": total_duration,
            "segments": segments,
        },
        segment_for_line,
    )


def _captions(
    aligned: list[_AlignedLine],
    segment_for_line: Mapping[str, str],
    script_asset_id: str,
    asr_asset_id: str,
    font_assets: Mapping[str, str],
) -> dict[str, Any]:
    tracks: list[dict[str, Any]] = []
    for language, field, font_role, font_asset_id, margin in (
        ("zh-CN", "zh", "chinese", font_assets["chinese"], 18),
        ("en", "en", "english", font_assets["english"], 55),
    ):
        cues = []
        for line in aligned:
            cues.append(
                {
                    "cue_id": f"caption-{'zh' if field == 'zh' else 'en'}-{line.line_id}",
                    "segment_id": segment_for_line[line.line_id],
                    "start_tick": line.start_tick,
                    "end_tick": line.end_tick,
                    "text": getattr(line, field),
                    "granularity": "sentence",
                    "words": [],
                    "highlight": None,
                }
            )
        tracks.append(
            {
                "track_id": f"legacy-v4-{language}",
                "language": language,
                "text_source_asset_id": script_asset_id,
                "timing_source_asset_id": asr_asset_id,
                "alignment_revision": 1,
                "cues": cues,
                "style": {
                    "font_role": font_role,
                    "font_asset_id": font_asset_id,
                    "safe_area": {"left_px": margin, "right_px": margin, "bottom_px": 28},
                    "max_lines": 3,
                    "line_break_policy": "legacy-v4-width-wrap-v1",
                    "overflow_policy": "fail",
                    "highlight_tokens": {},
                },
            }
        )
    return {"tracks": tracks}


def _overlays(
    book: Mapping[str, Any],
    montage_end: int,
    voice_duration_ticks: int,
    total_duration_ticks: int,
    font_assets: Mapping[str, str],
) -> list[dict[str, Any]]:
    title = str(book.get("title", "")).strip()
    author = str(book.get("author", "")).strip()
    if not title or not author:
        _fail(
            RendererErrorCode.RENDER_INPUT_INVALID,
            "Script book title and author are required.",
            "$.script.book",
        )
    return [
        {
            "overlay_id": "overlay-title",
            "kind": "book_title",
            "start_tick": montage_end,
            "end_tick": voice_duration_ticks,
            "content": {
                "text": f"《{title}》\n{author}／著",
                "font_role": "title",
                "font_asset_id": font_assets["title"],
                "layout_token": "legacy-v4-title-v1",
            },
            "overflow_policy": "fail",
        },
        {
            "overlay_id": "overlay-brand",
            "kind": "brand_label",
            "start_tick": 0,
            "end_tick": total_duration_ticks,
            "content": {
                "text": "JAXXMIND · BOOK NOTES",
                "font_role": "english",
                "font_asset_id": font_assets["english"],
                "layout_token": "legacy-v4-brand-v1",
            },
            "overflow_policy": "fail",
        },
    ]


def _load_current_approval_records(
    project: Path, release_id: str
) -> dict[str, tuple[dict[str, Any], Path]]:
    directory = project / "logs" / "approval_events"
    candidates: dict[str, list[tuple[dict[str, Any], Path]]] = {}
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else []:
        payload = _read_json(path, field="$.approval_events")
        if payload.get("project_id") != project.name or payload.get("release_id") != release_id:
            continue
        gate = payload.get("gate")
        if isinstance(gate, str) and gate:
            candidates.setdefault(gate, []).append((payload, path))
    current: dict[str, tuple[dict[str, Any], Path]] = {}
    for gate, records in candidates.items():
        latest = max(str(payload.get("reviewed_at", "")) for payload, _ in records)
        newest = [record for record in records if str(record[0].get("reviewed_at", "")) == latest]
        if len(newest) == 1 and approval_is_current(project, newest[0][0]):
            current[gate] = newest[0]
    return current


def _approval_snapshot(
    project: Path,
    release_id: str,
    required_subjects: Mapping[str, tuple[Path, ...]],
) -> tuple[list[str], str, list[ArtifactBinding], list[dict[str, Any]]]:
    current = _load_current_approval_records(project, release_id)
    issues: list[RenderIssue] = []
    records: list[dict[str, Any]] = []
    event_artifacts: list[ArtifactBinding] = []
    event_ids: list[str] = []
    for gate in PRE_RENDER_GATES:
        record = current.get(gate)
        if record is None:
            issues.append(
                RenderIssue(
                    RendererErrorCode.RENDER_GATE_BLOCKED,
                    "A current release-scoped approval is missing.",
                    f"$.approvals.{gate}",
                    {"release_id": release_id},
                    "preflight",
                )
            )
            continue
        event, path = record
        missing = [
            subject
            for subject in required_subjects[gate]
            if not approval_covers_path(project, event, subject)
        ]
        if missing:
            issues.append(
                RenderIssue(
                    RendererErrorCode.RENDER_RIGHTS_BLOCKED,
                    "Approval does not cover every required frozen subject.",
                    f"$.approvals.{gate}.subjects",
                    {"missing_count": len(missing)},
                    "preflight",
                )
            )
            continue
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            issues.append(
                RenderIssue(
                    RendererErrorCode.RENDER_GATE_BLOCKED,
                    "Approval event_id is missing.",
                    f"$.approvals.{gate}.event_id",
                    {},
                    "preflight",
                )
            )
            continue
        digest = _sha256_file(path)
        event_ids.append(event_id)
        records.append({"gate": gate, "event_id": event_id, "sha256": digest})
        event_artifacts.append(
            _artifact(
                f"approval-{gate}",
                "approval_event",
                _project_ref(project, path),
                path,
                "workflow-governance-v1",
            )
        )
    if issues:
        raise ContractValidationError(tuple(issues))
    if len(set(event_ids)) != len(event_ids):
        _fail(
            RendererErrorCode.RENDER_GATE_BLOCKED,
            "Pre-render gates must bind distinct approval event IDs.",
            "$.approvals.event_ids",
            stage="preflight",
        )
    return event_ids, canonical_sha256(records), event_artifacts, records


def _font_bindings(
    runtime: Path,
    project: Path,
    style: Mapping[str, Any],
    supplied: Mapping[str, Path] | None,
) -> tuple[list[ArtifactBinding], dict[str, str], dict[str, Path]]:
    fonts = style.get("fonts")
    if not isinstance(fonts, Mapping):
        _fail(RendererErrorCode.RENDER_FONT_UNAVAILABLE, "V4 font configuration is missing.", "$.style.fonts")
    assets: list[ArtifactBinding] = []
    ids: dict[str, str] = {}
    roots: dict[str, Path] = {"project": project, "runtime": runtime}
    for role in ("title", "chinese", "english"):
        path = (
            Path(supplied[role]).expanduser().resolve()
            if supplied is not None and role in supplied
            else resolve_font_path(runtime, fonts, role).resolve()
        )
        if not path.is_file():
            _fail(
                RendererErrorCode.RENDER_FONT_UNAVAILABLE,
                "Bound font asset is unavailable.",
                f"$.fonts.{role}",
            )
        try:
            ref = _project_ref(project, path)
        except ContractValidationError:
            try:
                ref = _runtime_ref(runtime, path)
            except ContractValidationError:
                root_name = f"font_{role}_resources"
                roots[root_name] = path.parent
                ref = PortableRef(root_name, path.name)
        asset_id = f"font-{role}"
        assets.append(_artifact(asset_id, f"font_{role}", ref, path, "runtime-font-contract-v1"))
        ids[role] = asset_id
    return assets, ids, roots


def _font_ref_for_path(
    project: Path, runtime: Path, roots: Mapping[str, Path], path: Path
) -> PortableRef:
    for root_name, root_path in roots.items():
        try:
            relative = path.resolve().relative_to(root_path.resolve())
        except ValueError:
            continue
        return PortableRef(root_name, relative.as_posix())
    _fail(RendererErrorCode.RENDER_FONT_UNAVAILABLE, "Font root binding is missing.", "$.fonts")
    raise AssertionError


def collect_v4_release(
    project: Path,
    release_id: str,
    *,
    runtime_root: Path | None = None,
    font_paths: Mapping[str, Path] | None = None,
    created_at: str | None = None,
    snapshot_directory: Path | None = None,
) -> V4CompatibilityBundle:
    """Freeze one explicit V4 release without running media tools or providers."""
    if not isinstance(release_id, str) or not release_id.strip():
        _fail(RendererErrorCode.RENDER_INPUT_INVALID, "release_id is required.", "$.release_id")
    project_root = Path(project).expanduser().resolve()
    runtime = (
        Path(runtime_root).expanduser().resolve()
        if runtime_root is not None
        else Path(__file__).resolve().parents[3]
    )
    project_path = _require_project_file(project_root, "project.json", field="$.project")
    project_payload = _read_json(project_path, field="$.project")
    project_id = project_payload.get("project_id")
    if project_id != project_root.name:
        _fail(
            RendererErrorCode.RENDER_INPUT_INVALID,
            "Project manifest ID must match the project directory.",
            "$.project.project_id",
        )
    workflow = project_payload.get("workflow")
    if not isinstance(workflow, Mapping):
        _fail(RendererErrorCode.RENDER_INPUT_INVALID, "Project workflow is missing.", "$.project.workflow")
    if workflow.get("style_profile_id") != V4_STYLE_ID or workflow.get("release_profile_id") != V4_PROFILE_ID:
        _fail(
            RendererErrorCode.RENDER_INPUT_INVALID,
            "Project workflow is not aligned to the locked V4 Style/Release Profile.",
            "$.project.workflow",
        )

    release_profile_path = runtime / f"config/release_profiles/{V4_PROFILE_ID}.json"
    style_profile_path = runtime / f"config/style_profiles/{V4_STYLE_ID}.json"
    video_style_path = runtime / "config/video_style_v2.json"
    release_profile = ReleaseProfile.load(release_profile_path)
    style_profile = StyleProfile.load(style_profile_path)
    video_style = _read_json(video_style_path, field="$.video_style")
    if (
        release_profile.profile_id != V4_PROFILE_ID
        or release_profile.renderer != "build_batch_video_v3"
        or style_profile.release_profile_id != release_profile.profile_id
    ):
        _fail(RendererErrorCode.RENDER_INPUT_INVALID, "V4 Profile identities diverge.", "$.profile")
    canvas = release_profile.payload["canvas"]
    local_master = style_profile.payload["output"]["local_master"]
    if any(local_master[key] != canvas[key] for key in ("width", "height", "fps")):
        _fail(RendererErrorCode.RENDER_INPUT_INVALID, "Style and Release output Profiles diverge.", "$.profile.canvas")
    intro = video_style.get("intro", {})
    if _ticks(intro.get("montage_duration_seconds"), field="$.video_style.intro.montage_duration_seconds") != MONTAGE_TICKS:
        _fail(RendererErrorCode.RENDER_INPUT_INVALID, "V4 montage policy changed.", "$.video_style.intro.montage_duration_seconds")

    script_path = _require_project_file(project_root, "02_story_script_故事脚本/script.v2.bilingual.json", field="$.assets.script")
    voice_path = _require_project_file(project_root, "05_voice_人声/v3-b-locked-master.wav", field="$.assets.voice")
    asr_path = _require_project_file(project_root, "05_voice_人声/asr-v3/v3-b-locked-master.json", field="$.assets.asr")
    h2_path = _require_project_file(project_root, "06_music_音乐/H2-用户确认原片高频音效层.wav", field="$.assets.sfx")
    bgm_candidates = sorted((project_root / "06_music_音乐").glob("v4-*-original-bgm.mp3"))
    if len(bgm_candidates) != 1 or not bgm_candidates[0].is_file():
        _fail(
            RendererErrorCode.RENDER_ASSET_MISSING,
            "V4 requires exactly one project-specific BGM.",
            "$.assets.bgm",
            details={"candidate_count": len(bgm_candidates)},
        )
    bgm_path = bgm_candidates[0].resolve()
    cover_manifest_path = _require_project_file(project_root, "01_research_资料搜集/sources/cover/cover_manifest.json", field="$.assets.cover_manifest")
    cover_manifest = _read_json(cover_manifest_path, field="$.cover_manifest")
    local_cover = cover_manifest.get("local_file")
    if not isinstance(local_cover, str):
        _fail(RendererErrorCode.RENDER_INPUT_INVALID, "Cover manifest local_file is required.", "$.cover_manifest.local_file")
    cover_path = _require_project_file(project_root, local_cover, field="$.assets.cover")
    recorded_cover_hash = cover_manifest.get("sha256")
    if isinstance(recorded_cover_hash, str) and recorded_cover_hash != _sha256_file(cover_path):
        _fail(RendererErrorCode.RENDER_HASH_MISMATCH, "Cover hash does not match its manifest.", "$.cover_manifest.sha256")
    cover_dir = project_root / "01_research_资料搜集/sources/cover"
    legacy_cover = cover_dir / "cover.jpg"
    if not legacy_cover.is_file():
        choices = sorted(path for path in cover_dir.glob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
        legacy_cover = choices[0] if choices else legacy_cover
    if legacy_cover.resolve(strict=False) != cover_path:
        _fail(
            RendererErrorCode.RENDER_INPUT_INVALID,
            "Cover manifest and legacy V4 cover selection disagree.",
            "$.cover_manifest.local_file",
        )

    scene_paths = {
        f"S{index:02d}": _require_project_file(
            project_root,
            f"03_images_生成图片/approved/v4/S{index:02d}.png",
            field=f"$.assets.scenes[{index - 1}]",
        )
        for index in range(1, 13)
    }
    scene_hashes = [_sha256_file(path) for path in scene_paths.values()]
    if len(set(scene_hashes)) != 12:
        _fail(
            RendererErrorCode.RENDER_INPUT_INVALID,
            "V4 requires 12 unique scene-image byte streams.",
            "$.assets.scenes",
        )

    script = _read_json(script_path, field="$.script")
    lines = _script_lines(script)
    asr = _read_json(asr_path, field="$.asr")
    words = _asr_words(asr)
    aligned, alignment_mode, pause_cut_tick = _apply_intro_pause(lines, words)
    source_voice_duration = _wave_duration_ticks(voice_path)
    prepared_voice_duration = source_voice_duration + PAUSE_DELTA_TICKS
    if max(line.end_tick for line in aligned) > prepared_voice_duration:
        _fail(
            RendererErrorCode.RENDER_AUDIO_INVALID,
            "Aligned captions exceed the prepared narration duration.",
            "$.timing.lines",
        )

    font_artifacts, font_asset_ids, root_bindings = _font_bindings(runtime, project_root, video_style, font_paths)
    for index, font_artifact in enumerate(font_artifacts):
        font_path = Path(font_paths[("title", "chinese", "english")[index]]).expanduser().resolve() if font_paths is not None and ("title", "chinese", "english")[index] in font_paths else None
        if font_path is not None:
            corrected_ref = _font_ref_for_path(project_root, runtime, root_bindings, font_path)
            font_artifacts[index] = ArtifactBinding(
                font_artifact.asset_id,
                font_artifact.role,
                corrected_ref,
                font_artifact.bytes,
                font_artifact.sha256,
                font_artifact.media_type,
                font_artifact.source_manifest_artifact_id,
                font_artifact.rights_ref,
            )

    scene_asset_ids = {scene_id: f"scene-{scene_id}" for scene_id in scene_paths}
    timeline, segment_for_line = _timeline(
        aligned,
        prepared_voice_duration,
        scene_asset_ids,
        "cover-source",
    )
    captions = _captions(aligned, segment_for_line, "approved-script", "asr-timing", font_asset_ids)
    montage_end = next(line.end_tick for line in aligned if line.line_id == "V02") + 40 + MONTAGE_TICKS
    overlays = _overlays(
        script.get("book") if isinstance(script.get("book"), Mapping) else {},
        montage_end,
        prepared_voice_duration,
        int(timeline["duration_ticks"]),
        font_asset_ids,
    )

    required_subjects = {
        "script": (script_path,),
        "timing": (asr_path,),
        "visual_rights": tuple(scene_paths.values()),
        "cover_rights": (cover_manifest_path, cover_path),
        "bgm_rights": (bgm_path,),
        "sfx_rights": (h2_path,),
        "voice_rights": (voice_path,),
    }
    event_ids, approval_hash, approval_artifacts, approval_records = _approval_snapshot(
        project_root, release_id, required_subjects
    )

    artifacts: list[ArtifactBinding] = [
        _artifact("project-manifest", "project_manifest", _project_ref(project_root, project_path), project_path, "workflow-governance-v1"),
        _artifact("approved-script", "approved_script", _project_ref(project_root, script_path), script_path, "approval:script"),
        _artifact("asr-timing", "caption_timing_source", _project_ref(project_root, asr_path), asr_path, "approval:timing"),
        _artifact("narration", "narration_stem", _project_ref(project_root, voice_path), voice_path, "approval:voice_rights"),
        _artifact("bgm", "bgm_stem", _project_ref(project_root, bgm_path), bgm_path, "approval:bgm_rights"),
        _artifact("sfx-h2", "sfx_stem", _project_ref(project_root, h2_path), h2_path, "approval:sfx_rights"),
        _artifact("cover-manifest", "cover_source_manifest", _project_ref(project_root, cover_manifest_path), cover_manifest_path, "approval:cover_rights"),
        _artifact("cover-source", "cover_source", _project_ref(project_root, cover_path), cover_path, "approval:cover_rights"),
    ]
    artifacts.extend(
        _artifact(scene_asset_ids[scene_id], "scene_visual", _project_ref(project_root, path), path, "approval:visual_rights")
        for scene_id, path in scene_paths.items()
    )
    artifacts.extend(font_artifacts)
    artifacts.extend(approval_artifacts)
    artifacts = sorted(artifacts, key=lambda item: item.asset_id)

    legacy_sources = [
        _source_binding("legacy-v4-entrypoint", "1", _runtime_ref(runtime, runtime / "scripts/build_batch_video_v3.py"), runtime / "scripts/build_batch_video_v3.py"),
        _source_binding("legacy-v2-render-core", "1", _runtime_ref(runtime, runtime / "scripts/build_final_video_v2.py"), runtime / "scripts/build_final_video_v2.py"),
        _source_binding("v4-scene-contract", "1", _runtime_ref(runtime, runtime / "src/book_video_factory/scene_contract.py"), runtime / "src/book_video_factory/scene_contract.py"),
    ]
    profile_binding = _source_binding(
        release_profile.profile_id,
        str(release_profile.payload.get("profile_revision", 1)),
        _runtime_ref(runtime, release_profile_path),
        release_profile_path,
    )
    source_manifests = [
        _source_binding("project-manifest", str(project_payload.get("schema_version", "1.0")), _project_ref(project_root, project_path), project_path),
        _source_binding(style_profile.style_id, str(style_profile.payload.get("schema_version", "1.0")), _runtime_ref(runtime, style_profile_path), style_profile_path),
        _source_binding("video-style-v2", str(video_style.get("schema_version", "2.0")), _runtime_ref(runtime, video_style_path), video_style_path),
        *legacy_sources,
    ]

    audio_style = video_style.get("audio") if isinstance(video_style.get("audio"), Mapping) else {}
    output_path = f"08_render_合成/v4/{project_id}-v4-bilingual-3x4.mp4"
    sidecars = [
        {"asset_id": "legacy-render-manifest", "role": "legacy_render_manifest", "ref": {"root": "project", "path": "07_timeline_时间线/v4/render_manifest.v4.json"}, "media_type": "application/json"},
        {"asset_id": "legacy-renderer-qc", "role": "legacy_renderer_qc", "ref": {"root": "project", "path": "09_qc_质检/qc_report.v4.json"}, "media_type": "application/json"},
        {"asset_id": "subtitle-zh", "role": "subtitle_zh", "ref": {"root": "project", "path": "07_timeline_时间线/v4/subtitles.v2.zh-CN.srt"}, "media_type": "application/x-subrip"},
        {"asset_id": "subtitle-en", "role": "subtitle_en", "ref": {"root": "project", "path": "07_timeline_时间线/v4/subtitles.v2.en.srt"}, "media_type": "application/x-subrip"},
        {"asset_id": "subtitle-bilingual", "role": "subtitle_bilingual", "ref": {"root": "project", "path": "07_timeline_时间线/v4/subtitles.v2.bilingual.srt"}, "media_type": "application/x-subrip"},
        {"asset_id": "title-layout", "role": "title_layout", "ref": {"root": "project", "path": "07_timeline_时间线/v4/overlays/bilingual-3x4/title.layout.json"}, "media_type": "application/json"},
    ]
    legacy_extension = {
        "schema_version": "1.0",
        "release_version": "v4",
        "entrypoint": legacy_sources[0],
        "legacy_code": legacy_sources,
        "alignment": {
            "algorithm": alignment_mode,
            "pause_cut_tick": pause_cut_tick,
            "removed_ticks": PAUSE_REMOVED_TICKS,
            "inserted_silence_ticks": PAUSE_INSERTED_TICKS,
            "shift_ticks": PAUSE_DELTA_TICKS,
            "montage_duration_ticks": MONTAGE_TICKS,
            "outro_duration_ticks": OUTRO_TICKS,
        },
        "audio_mix": {
            "narration_asset_id": "narration",
            "bgm_asset_id": "bgm",
            "sfx_asset_id": "sfx-h2",
            "bgm_start_offset_ticks": _ticks(audio_style.get("bgm_start_offset_seconds"), field="$.video_style.audio.bgm_start_offset_seconds"),
            "bgm_target_millilufs": int(Decimal(str(audio_style.get("bgm_target_lufs"))) * 1000),
            "body_duck_millidecibels": int(Decimal(str(audio_style.get("body_duck_db"))) * 1000),
            "montage_boost_millidecibels": int(Decimal(str(audio_style.get("montage_boost_db"))) * 1000),
            "final_target_millilufs": int(Decimal(str(audio_style.get("final_target_lufs"))) * 1000),
            "true_peak_millidecibels": int(Decimal(str(audio_style.get("true_peak_dbfs"))) * 1000),
            "approval_event_ids": [
                approval_records[PRE_RENDER_GATES.index(gate)]["event_id"]
                for gate in ("bgm_rights", "sfx_rights", "voice_rights")
            ],
        },
        "font_asset_ids": font_asset_ids,
        "expected_output": {"root": "project", "path": output_path},
        "expected_sidecars": sidecars,
        "post_qc_entrypoint": None,
    }
    renderer_input_ids = [
        "approved-script",
        "asr-timing",
        "narration",
        "bgm",
        "sfx-h2",
        "cover-manifest",
        "cover-source",
        *scene_asset_ids.values(),
        *font_asset_ids.values(),
    ]
    evidence = {
        "schema_version": "1.0",
        "kind": "v4_compatibility_release_evidence",
        "project_id": project_id,
        "release_id": release_id,
        "profile_id": release_profile.profile_id,
        "profile_revision": int(release_profile.payload.get("profile_revision", 1)),
        "artifact_hashes": {item.asset_id: item.sha256 for item in artifacts},
        "renderer_input_asset_ids": renderer_input_ids,
        "pre_render_gate_ids": list(PRE_RENDER_GATES),
        "approval_event_ids": event_ids,
        "approval_records": approval_records,
        "approval_snapshot_sha256": approval_hash,
        "timing": {
            "source_voice_duration_ticks": source_voice_duration,
            "prepared_voice_duration_ticks": prepared_voice_duration,
            "lines": [
                {
                    "line_id": line.line_id,
                    "role": line.role,
                    "start_tick": line.start_tick,
                    "end_tick": line.end_tick,
                }
                for line in aligned
            ],
        },
        "output_spec": {
            "width": int(canvas["width"]),
            "height": int(canvas["height"]),
            "fps": {"numerator": int(canvas["fps"]), "denominator": 1},
            "pixel_format": "yuv420p",
            "container": "mp4",
            "video": {"codec": "h264", "encoding_policy": "legacy-v4-libx264-v1"},
            "audio": {"codec": "aac", "sample_rate": 48000, "channels": 2},
            "duration_ticks": int(timeline["duration_ticks"]),
            "artifact_role": "local_master",
        },
        "output": {
            "artifact_id": "local-master",
            "role": "local_master",
            "target": {"root": "project", "path": output_path},
            "overwrite_policy": "fail_if_exists",
        },
        "timeline": timeline,
        "captions": captions,
        "overlays": overlays,
        "audio": {
            "final_mix_asset_id": None,
            "stem_asset_ids": ["narration", "bgm", "sfx-h2"],
            "stem_usage": "legacy_audio_mixing",
            "cues": [
                {
                    "cue_id": f"narration-{line.line_id}",
                    "asset_id": "narration",
                    "start_tick": line.start_tick,
                    "end_tick": line.end_tick,
                }
                for line in aligned
            ],
            "sync_policy": "timeline_zero_locked",
            "mix_policy_id": "legacy-v4-mix-v1",
        },
        "legacy_extension": legacy_extension,
    }
    evidence_hash = canonical_sha256(evidence)
    release_key = hashlib.sha256(release_id.encode("utf-8")).hexdigest()[:16]
    evidence_directory = project_root / "manifests" / "releases" / release_key / "v4-compatibility"
    evidence_path = write_canonical_once(
        evidence_directory / f"v4-compatibility-evidence-{evidence_hash}.json",
        evidence,
    )
    evidence_ref = _project_ref(project_root, evidence_path)
    evidence_binding = _source_binding("v4-compatibility-evidence", "1.0", evidence_ref, evidence_path)
    timestamp = created_at or _utc_now()
    snapshot = create_release_snapshot(
        project_id=str(project_id),
        release_id=release_id,
        created_at=timestamp,
        profile=profile_binding,
        artifacts=artifacts,
        timeline_source=evidence_binding,
        audio_source=evidence_binding,
        caption_source=evidence_binding,
        rights={
            "status": "allowed",
            "policy_version": "v4-compatibility-pre-render-rights-v1",
            "snapshot_ref": {"root": evidence_ref.root, "path": evidence_ref.path},
            "snapshot_sha256": evidence_hash,
        },
        approvals={"status": "approved", "event_ids": event_ids, "snapshot_sha256": approval_hash},
        release_gates={"status": "passed", "gate_ids": list(PRE_RENDER_GATES), "policy_version": "v4-compatibility-pre-render-gates-v1"},
        source_manifests=source_manifests,
        metadata={"created_by": "v4-compatibility-collector-v1", "notes": "Legacy V4 compatibility snapshot; not render_manifest.v4.json."},
    )
    snapshot_dir = Path(snapshot_directory) if snapshot_directory is not None else evidence_directory / "snapshots"
    snapshot_path = write_release_snapshot(snapshot, snapshot_dir)
    return V4CompatibilityBundle(snapshot, snapshot_path, evidence_path, root_bindings)


def _load_evidence(snapshot: ReleaseSnapshot, resolver: RootResolver) -> tuple[dict[str, Any], PortableRef]:
    binding = snapshot.timeline_source
    ref_payload = binding.get("ref")
    if not isinstance(ref_payload, Mapping):
        _fail(RendererErrorCode.RENDER_INPUT_INVALID, "Snapshot evidence ref is invalid.", "$.timeline_source.ref")
    ref = PortableRef(str(ref_payload.get("root", "")), str(ref_payload.get("path", "")))
    try:
        path = resolver.resolve(ref, require_exists=True)
    except (ValueError, FileNotFoundError) as error:
        _fail(RendererErrorCode.RENDER_ASSET_MISSING, "Frozen compatibility evidence is unavailable.", "$.timeline_source.ref")
        raise AssertionError from error
    digest = _sha256_file(path)
    if digest != binding.get("sha256"):
        _fail(RendererErrorCode.RENDER_HASH_MISMATCH, "Compatibility evidence hash changed.", "$.timeline_source.sha256")
    evidence = _read_json(path, field="$.compatibility_evidence")
    if canonical_sha256(evidence) != digest:
        _fail(RendererErrorCode.RENDER_HASH_MISMATCH, "Compatibility evidence is not canonical-hash bound.", "$.timeline_source.sha256")
    return evidence, ref


def map_v4_snapshot_to_request(
    snapshot: ReleaseSnapshot,
    snapshot_ref: PortableRef,
    resolver: RootResolver,
    *,
    capability_ref: PortableRef = PortableRef("runtime", "config/renderers/legacy-v4.capabilities.json"),
    created_at: str | None = None,
) -> RenderRequest:
    """Map only frozen Snapshot/evidence data; never glob or guess project inputs."""
    snapshot_issues = (*validate_release_snapshot(snapshot), *validate_snapshot_hash(snapshot))
    if snapshot_issues:
        raise ContractValidationError(snapshot_issues)
    evidence, evidence_ref = _load_evidence(snapshot, resolver)
    if evidence.get("project_id") != snapshot.project_id or evidence.get("release_id") != snapshot.release_id:
        _fail(RendererErrorCode.RENDER_INPUT_INVALID, "Compatibility evidence scope does not match Snapshot.", "$.release")
    if evidence.get("profile_id") != snapshot.profile.get("id"):
        _fail(RendererErrorCode.RENDER_INPUT_INVALID, "Compatibility evidence Profile does not match Snapshot.", "$.profile")
    snapshot_hashes = {item.asset_id: item.sha256 for item in snapshot.artifacts}
    if evidence.get("artifact_hashes") != snapshot_hashes:
        _fail(RendererErrorCode.RENDER_HASH_MISMATCH, "Compatibility evidence asset index does not match Snapshot.", "$.artifact_hashes")
    for index, artifact in enumerate(snapshot.artifacts):
        try:
            path = resolver.resolve(artifact.ref, require_exists=True)
        except (ValueError, FileNotFoundError) as error:
            _fail(RendererErrorCode.RENDER_ASSET_MISSING, "Frozen Snapshot asset is unavailable.", f"$.artifacts[{index}]")
            raise AssertionError from error
        if path.stat().st_size != artifact.bytes or _sha256_file(path) != artifact.sha256:
            _fail(RendererErrorCode.RENDER_HASH_MISMATCH, "Frozen Snapshot asset bytes changed.", f"$.artifacts[{index}]")

    try:
        capability_path = resolver.resolve(capability_ref, require_exists=True)
    except (ValueError, FileNotFoundError) as error:
        _fail(RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED, "Legacy V4 Capability document is unavailable.", "$.renderer.capability_document_ref", stage="negotiate")
        raise AssertionError from error
    capability_payload = _read_json(capability_path, field="$.renderer.capabilities")
    capabilities = capabilities_from_dict(capability_payload)
    capability_issues = validate_capabilities(capabilities)
    if capability_issues:
        raise ContractValidationError(capability_issues)
    if capabilities.renderer.id != LEGACY_RENDERER_ID or capabilities.renderer.version != LEGACY_RENDERER_VERSION:
        _fail(RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED, "Legacy V4 Capability identity is invalid.", "$.renderer", stage="negotiate")
    capability_hash = _sha256_file(capability_path)

    input_ids = evidence.get("renderer_input_asset_ids")
    if not isinstance(input_ids, list) or not all(isinstance(item, str) for item in input_ids):
        _fail(RendererErrorCode.RENDER_INPUT_INVALID, "Compatibility evidence input IDs are invalid.", "$.renderer_input_asset_ids")
    artifact_map = {item.asset_id: item for item in snapshot.artifacts}
    try:
        request_artifacts = [artifact_map[item] for item in input_ids]
    except KeyError as error:
        _fail(RendererErrorCode.RENDER_ASSET_MISSING, "Compatibility evidence references an unknown Snapshot asset.", "$.renderer_input_asset_ids")
        raise AssertionError from error
    project_artifact = artifact_map.get("project-manifest")
    if project_artifact is None:
        _fail(RendererErrorCode.RENDER_ASSET_MISSING, "Snapshot lacks the Project Manifest binding.", "$.project")

    root_names = {artifact.ref.root for artifact in request_artifacts}
    root_names.update({snapshot_ref.root, capability_ref.root, evidence_ref.root, project_artifact.ref.root})
    roots: dict[str, dict[str, str]] = {}
    for root_name in sorted(root_names):
        if root_name == "project":
            kind = "project"
            output_access = "request_targets_only"
        elif root_name == "runtime":
            kind = "runtime"
            output_access = "none"
        elif root_name.startswith("font_"):
            kind = "font_resources"
            output_access = "none"
        else:
            kind = "artifact"
            output_access = "none"
        roots[root_name] = {"kind": kind, "input_access": "read_only", "output_access": output_access}

    extension = evidence.get("legacy_extension")
    if not isinstance(extension, Mapping):
        _fail(RendererErrorCode.RENDER_INPUT_INVALID, "Legacy V4 extension is missing from frozen evidence.", "$.extensions")
    extension_payload = dict(extension)
    extension_payload["release_snapshot_id"] = snapshot.snapshot_id
    required_capabilities = [
        "still_images",
        "layered_images",
        "captions",
        "camera_motion",
        "audio_mixing",
        "transitions",
        "deterministic_render",
    ]
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "request_id": "pending",
        "request_hash": "0" * 64,
        "project": {
            "id": snapshot.project_id,
            "manifest_ref": {"root": project_artifact.ref.root, "path": project_artifact.ref.path},
            "manifest_sha256": project_artifact.sha256,
        },
        "release": {
            "id": snapshot.release_id,
            "manifest_id": snapshot.snapshot_id,
            "manifest_version": "release-snapshot-v1",
            "manifest_ref": {"root": snapshot_ref.root, "path": snapshot_ref.path},
            "manifest_sha256": snapshot.snapshot_hash,
        },
        "render_mode": "final",
        "renderer": {
            "id": LEGACY_RENDERER_ID,
            "version": LEGACY_RENDERER_VERSION,
            "capability_document_ref": {"root": capability_ref.root, "path": capability_ref.path},
            "capability_document_sha256": capability_hash,
            "required_capabilities": required_capabilities,
        },
        "profile": {
            "id": str(snapshot.profile["id"]),
            "revision": int(evidence["profile_revision"]),
            "ref": dict(snapshot.profile["ref"]),
            "sha256": str(snapshot.profile["sha256"]),
        },
        "roots": roots,
        "output_spec": evidence["output_spec"],
        "output": evidence["output"],
        "timeline": evidence["timeline"],
        "audio": {
            "manifest_ref": {"root": evidence_ref.root, "path": evidence_ref.path},
            "manifest_sha256": str(snapshot.audio_source["sha256"]),
            **dict(evidence["audio"]),
        },
        "captions": evidence["captions"],
        "assets": [
            {
                "asset_id": item.asset_id,
                "role": item.role,
                "ref": {"root": item.ref.root, "path": item.ref.path},
                "bytes": item.bytes,
                "sha256": item.sha256,
                "media_type": item.media_type,
                "source_manifest_artifact_id": item.source_manifest_artifact_id,
                "rights_ref": item.rights_ref,
            }
            for item in request_artifacts
        ],
        "overlays": evidence["overlays"],
        "rights": {
            "policy_version": str(snapshot.rights["policy_version"]),
            "snapshot_ref": dict(snapshot.rights["snapshot_ref"]),
            "snapshot_sha256": str(snapshot.rights["snapshot_sha256"]),
            "status": "allowed",
            "scope": "final",
        },
        "approvals": {
            "required_gate_ids": list(evidence["pre_render_gate_ids"]),
            "satisfied_event_ids": list(evidence["approval_event_ids"]),
            "snapshot_sha256": str(snapshot.approvals["snapshot_sha256"]),
        },
        "determinism": {
            "canonicalization": "canonical-json-v1",
            "timeline_rounding": "integer_round_half_up_v1",
            "random_seed": None,
            "locale": "zh-CN",
            "timezone": "UTC",
            "required_level": "semantic",
        },
        "extensions": {LEGACY_EXTENSION: extension_payload},
        "metadata": {
            "created_at": created_at or _utc_now(),
            "created_by": "v4-to-render-request-mapper-v1",
            "notes": "Mapped only from immutable V4 compatibility evidence.",
        },
    }
    digest = semantic_request_hash(payload)
    payload["request_hash"] = digest
    payload["request_id"] = request_id_from_hash(digest)
    request = render_request_from_dict(payload)
    issues = (
        *validate_render_request(request),
        *validate_request_hash(request),
        *validate_request_capabilities(request, capabilities),
    )
    if issues:
        raise ContractValidationError(issues)
    return request


__all__ = [
    "LEGACY_EXTENSION",
    "LEGACY_RENDERER_ID",
    "LEGACY_RENDERER_VERSION",
    "PRE_RENDER_GATES",
    "V4CompatibilityBundle",
    "collect_v4_release",
    "map_v4_snapshot_to_request",
]
