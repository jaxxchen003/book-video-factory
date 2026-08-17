"""Generate and run the bounded Phase 3C legacy V4 real-media smoke fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import wave
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw

from book_video_factory.fonts import resolve_font_path
from book_video_factory.manifests import record_approval
from book_video_factory.renderer_contracts import (
    CommandResult,
    LegacyV4Renderer,
    PortableRef,
    RenderExecutionContext,
    RenderStatus,
    RootResolver,
    collect_v4_release,
    map_v4_snapshot_to_request,
    render_result_to_dict,
    write_render_request,
)


MARKER_NAME = "SMOKE_FIXTURE.json"
FIXTURE_TYPE = "legacy-v4-real-media-smoke"
RELEASE_ID = "phase3c-smoke-release-v1"
SOURCE_VOICE_TICKS = 8_000
EXPECTED_OUTPUT_TICKS = 11_520
WIDTH = 720
HEIGHT = 960
FPS = 30


class SmokeFixtureError(RuntimeError):
    pass


def _runtime_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _write_human_report(path: Path, result: Mapping[str, Any]) -> Path:
    baseline = result["baseline"]
    facade = result["facade"]
    comparison = result["media_semantic_comparison"]
    failure = result["failure_fixture"]
    lines = [
        "# Phase 3C Real-Media Smoke Report",
        "",
        f"- Overall result: {'PASS' if result['passed'] else 'FAIL'}",
        f"- Fixture type: {result['fixture']['fixture_type']}",
        f"- Baseline exit code: {baseline['execution']['returncode']}",
        f"- Baseline output SHA-256: `{baseline['probe']['sha256']}`",
        f"- Facade status: {facade['result']['status']}",
        f"- Facade attempt: `{facade['attempt_id']}`",
        f"- Facade output SHA-256: `{facade['probe']['sha256']}`",
        f"- Media semantic comparison: {'PASS' if comparison['passed'] else 'FAIL'}",
        f"- Duration difference: {comparison['duration_difference_ticks']} ms",
        f"- Post-QC equivalence: {'PASS' if result['post_qc_comparison']['passed'] else 'FAIL'}",
        f"- Failure fixture: {'PASS' if failure['passed'] else 'FAIL'}",
        f"- Failure runner called: {str(failure['runner_called']).lower()}",
        f"- Pre-existing output preserved: {str(failure['output_preserved']).lower()}",
        "",
        "The JSON report in this directory is the authoritative machine-readable record.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def initialize_fixture_root(root: Path) -> Path:
    requested = Path(root).expanduser()
    if requested.exists() and any(requested.iterdir()):
        raise SmokeFixtureError("fixture initialization requires an empty directory")
    requested.mkdir(parents=True, exist_ok=True)
    marker = {
        "fixture": True,
        "fixture_type": FIXTURE_TYPE,
        "version": "1",
        "production_use": False,
        "generated_assets_only": True,
        "expected_output_duration_ticks": EXPECTED_OUTPUT_TICKS,
        "resolution": {"width": WIDTH, "height": HEIGHT},
        "fps": FPS,
        "visual_motif_families": 3,
        "v4_scene_assets": 12,
        "v4_script_cues": 15,
    }
    return _write_json(requested / MARKER_NAME, marker)


def validate_fixture_root(root: Path) -> dict[str, Any]:
    resolved = Path(root).expanduser().resolve()
    marker_path = resolved / MARKER_NAME
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SmokeFixtureError("fixture marker is missing or unreadable") from error
    if not isinstance(marker, dict) or marker != {
        "fixture": True,
        "fixture_type": FIXTURE_TYPE,
        "version": "1",
        "production_use": False,
        "generated_assets_only": True,
        "expected_output_duration_ticks": EXPECTED_OUTPUT_TICKS,
        "resolution": {"width": WIDTH, "height": HEIGHT},
        "fps": FPS,
        "visual_motif_families": 3,
        "v4_scene_assets": 12,
        "v4_script_cues": 15,
    }:
        raise SmokeFixtureError("fixture marker does not match the Phase 3C contract")
    if (resolved / "project.json").exists():
        raise SmokeFixtureError("fixture root must not be a production Project root")
    return marker


def _write_pcm_wave(
    path: Path,
    *,
    duration_seconds: int | Decimal,
    frequency_hz: int,
    amplitude: int,
    sample_rate: int = 48_000,
    channels: int = 2,
    three_sections: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(Decimal(str(duration_seconds)) * sample_rate)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        chunk = bytearray()
        for index in range(frame_count):
            section = (index * 3) // max(1, frame_count) if three_sections else 0
            section_frequency = frequency_hz + section * 73
            phase = 2 * math.pi * section_frequency * index / sample_rate
            sample = round(math.sin(phase) * amplitude)
            if three_sections and index % (sample_rate * 2) < sample_rate // 5:
                sample = 0
            packed = struct.pack("<h", max(-32768, min(32767, sample)))
            chunk.extend(packed * channels)
            if len(chunk) >= 256 * 1024:
                output.writeframesraw(chunk)
                chunk.clear()
        if chunk:
            output.writeframesraw(chunk)


def _generate_scene(path: Path, index: int) -> None:
    palettes = (
        ((28, 51, 76), (239, 181, 64)),
        ((63, 39, 74), (104, 211, 145)),
        ((74, 46, 34), (113, 186, 232)),
    )
    background, accent = palettes[(index - 1) % 3]
    image = Image.new("RGB", (WIDTH, HEIGHT), background)
    draw = ImageDraw.Draw(image)
    inset = 70 + index * 3
    motif = (index - 1) % 3
    if motif == 0:
        draw.ellipse((inset, 190, WIDTH - inset, 720), fill=accent, outline="white", width=8)
    elif motif == 1:
        draw.rounded_rectangle((inset, 190, WIDTH - inset, 720), radius=54, fill=accent, outline="white", width=8)
    else:
        draw.polygon(((WIDTH // 2, 160), (WIDTH - inset, 735), (inset, 735)), fill=accent, outline="white")
    draw.text((WIDTH // 2 - 22, 790), f"S{index:02d}", fill="white")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=False)


def _generate_cover(path: Path) -> None:
    image = Image.new("RGB", (360, 540), (234, 229, 215))
    draw = ImageDraw.Draw(image)
    draw.rectangle((24, 24, 336, 516), outline=(30, 30, 30), width=8)
    draw.rectangle((65, 105, 295, 330), fill=(179, 87, 54))
    draw.text((105, 385), "SMOKE BOOK", fill=(20, 20, 20))
    draw.text((130, 430), "FIXTURE", fill=(20, 20, 20))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=False)


def _encode_bgm(source: Path, target: Path) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-c:a",
        "libmp3lame",
        "-b:a",
        "128k",
        str(target),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0 or not target.is_file():
        raise SmokeFixtureError("failed to encode generated fixture BGM")
    return {"argv": command, "returncode": completed.returncode}


def _shared_assets(fixture_root: Path) -> tuple[Path, dict[str, Any]]:
    shared = fixture_root / "generated-shared-assets"
    if shared.exists():
        raise SmokeFixtureError("generated shared asset directory already exists")
    scenes = shared / "scenes"
    for index in range(1, 13):
        _generate_scene(scenes / f"S{index:02d}.png", index)
    _generate_cover(shared / "cover.png")
    _write_pcm_wave(
        shared / "narration.wav",
        duration_seconds=8,
        frequency_hz=220,
        amplitude=2600,
        three_sections=True,
    )
    _write_pcm_wave(
        shared / "h2.wav",
        duration_seconds=Decimal("0.96"),
        frequency_hz=1200,
        amplitude=1800,
    )
    _write_pcm_wave(
        shared / "bgm-source.wav",
        duration_seconds=32,
        frequency_hz=110,
        amplitude=900,
    )
    bgm_encode = _encode_bgm(shared / "bgm-source.wav", shared / "v4-smoke-original-bgm.mp3")
    lines: list[dict[str, str]] = []
    words: list[dict[str, Any]] = []
    for index in range(1, 16):
        token = f"L{index:02d}"
        start_ms = 180 + (index - 1) * 490
        end_ms = start_ms + 260
        lines.append(
            {
                "id": f"V{index:02d}",
                "role": "hook" if index == 1 else "reveal_cue" if index == 2 else "body",
                "zh": token,
                "en": f"LINE {index:02d}",
            }
        )
        words.append({"word": token, "start": start_ms / 1000, "end": end_ms / 1000})
    topics = [
        {"zh": f"T{index}", "en": f"TOPIC {index}", "scene": f"S{index:02d}"}
        for index in range(1, 9)
    ]
    _write_json(
        shared / "script.json",
        {
            "schema_version": "2.0",
            "version": "phase3c-smoke-v1",
            "project_id": "phase3c-smoke-semantic-input",
            "book": {"title": "SMOKE BOOK", "author": "FIXTURE"},
            "translation_status": "native_approved",
            "intro_topics": topics,
            "lines": lines,
        },
    )
    _write_json(
        shared / "asr.json",
        {"segments": [{"start": 0, "end": 8, "text": " ".join(item["word"] for item in words), "words": words}]},
    )
    hashes = {
        path.relative_to(shared).as_posix(): _sha256(path)
        for path in sorted(shared.rglob("*"))
        if path.is_file()
    }
    return shared, {"bgm_encode": bgm_encode, "hashes": hashes}


def _copy(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def _create_project(fixture_root: Path, shared: Path, slug: str) -> tuple[Path, dict[str, str]]:
    project = fixture_root / slug
    if project.exists():
        raise SmokeFixtureError(f"fixture project already exists: {slug}")
    project.mkdir(parents=True)
    _write_json(
        project / "project.json",
        {
            "schema_version": "1.0",
            "project_id": slug,
            "book": {"title": "SMOKE BOOK", "author": "FIXTURE"},
            "status": "fixture_initialized",
            "current_stage": "phase3c_smoke",
            "created_at": "2026-08-01T00:00:00Z",
            "reference_video": None,
            "workflow": {
                "mode": "single-book",
                "style_profile_id": "book-editorial-bilingual-v2",
                "style_display_name": "Phase 3C Fixture",
                "release_profile_id": "book-v4-bilingual-3x4",
                "generation_lane": "local-renderer",
                "execution_mode": "deterministic_local_renderer",
                "state_source": "derived_gate_evaluator",
                "status_field_role": "compatibility_cache_only",
            },
        },
    )
    script = _copy(shared / "script.json", project / "02_story_script_故事脚本/script.v2.bilingual.json")
    asr = _copy(shared / "asr.json", project / "05_voice_人声/asr-v3/v3-b-locked-master.json")
    voice = _copy(shared / "narration.wav", project / "05_voice_人声/v3-b-locked-master.wav")
    bgm = _copy(shared / "v4-smoke-original-bgm.mp3", project / "06_music_音乐/v4-smoke-original-bgm.mp3")
    sfx = _copy(shared / "h2.wav", project / "06_music_音乐/H2-用户确认原片高频音效层.wav")
    scenes = [
        _copy(shared / f"scenes/S{index:02d}.png", project / f"03_images_生成图片/approved/v4/S{index:02d}.png")
        for index in range(1, 13)
    ]
    cover = _copy(shared / "cover.png", project / "01_research_资料搜集/sources/cover/cover.png")
    cover_manifest = _write_json(
        project / "01_research_资料搜集/sources/cover/cover_manifest.json",
        {
            "schema_version": "1.1",
            "source_type": "program_generated_fixture",
            "source_url": "fixture://phase3c/generated-cover",
            "local_file": cover.relative_to(project).as_posix(),
            "content_type": "image/png",
            "dimensions": [360, 540],
            "sha256": _sha256(cover),
            "rights_status": "cleared_for_public_release",
            "rights_note": "Program-generated Phase 3C smoke asset; production use prohibited.",
        },
    )
    _write_json(
        project / "06_music_音乐/bgm_license.json",
        {
            "schema_version": "1.0",
            "asset": bgm.relative_to(project).as_posix(),
            "rights_status": "channel_owned_original",
            "generator": "python-wave-plus-local-ffmpeg",
            "production_use": False,
        },
    )
    approvals = {
        "script": [script],
        "timing": [asr],
        "visual_rights": scenes,
        "cover_rights": [cover_manifest, cover],
        "bgm_rights": [bgm],
        "sfx_rights": [sfx],
        "voice_rights": [voice],
    }
    for gate, subjects in approvals.items():
        record_approval(
            project,
            release_id=RELEASE_ID,
            gate=gate,
            decision="approved",
            reviewer="phase3c-fixture-generator",
            subjects=subjects,
            note="Program-generated, non-production smoke fixture.",
            event_id=f"phase3c-{slug}-{gate}",
            reviewed_at="2026-08-01T00:00:00+00:00",
        )
    semantic = {
        "script": _sha256(script),
        "asr": _sha256(asr),
        "voice": _sha256(voice),
        "bgm": _sha256(bgm),
        "sfx": _sha256(sfx),
        "cover": _sha256(cover),
        **{f"scene_{index:02d}": _sha256(path) for index, path in enumerate(scenes, start=1)},
    }
    return project, semantic


def _font_environment(runtime: Path) -> tuple[dict[str, str], dict[str, str]]:
    style = json.loads((runtime / "config/video_style_v2.json").read_text(encoding="utf-8"))
    fonts = style["fonts"]
    values = {
        "BOOK_VIDEO_TITLE_FONT": str(resolve_font_path(runtime, fonts, "title")),
        "BOOK_VIDEO_CHINESE_FONT": str(resolve_font_path(runtime, fonts, "chinese")),
        "BOOK_VIDEO_ENGLISH_FONT": str(resolve_font_path(runtime, fonts, "english")),
    }
    hashes = {key: _sha256(Path(value)) for key, value in values.items()}
    return values, hashes


def _run_command(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    log_dir: Path,
    label: str,
) -> dict[str, Any]:
    started_at = _utc_now()
    completed = subprocess.run(
        list(argv), cwd=cwd, env=dict(env), check=False, capture_output=True, text=True
    )
    finished_at = _utc_now()
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"{label}.stdout.log"
    stderr_path = log_dir / f"{label}.stderr.log"
    stdout_path.write_text(completed.stdout, encoding="utf-8", errors="replace")
    stderr_path.write_text(completed.stderr, encoding="utf-8", errors="replace")
    return {
        "argv": list(argv),
        "cwd": str(cwd),
        "injected_env_keys": sorted(key for key in env if key.startswith("BOOK_VIDEO_")),
        "base_environment": "inherited",
        "started_at": started_at,
        "finished_at": finished_at,
        "returncode": completed.returncode,
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
    }


def _probe(path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    streams = payload.get("streams", [])
    video_streams = [item for item in streams if item.get("codec_type") == "video"]
    audio_streams = [item for item in streams if item.get("codec_type") == "audio"]
    video = video_streams[0]
    audio = audio_streams[0]
    rotation = video.get("tags", {}).get("rotate")
    if rotation is None:
        rotation = next(
            (item.get("rotation") for item in video.get("side_data_list", []) if "rotation" in item),
            None,
        )
    return {
        "file": str(path),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "format_name": payload.get("format", {}).get("format_name"),
        "format_duration": payload.get("format", {}).get("duration"),
        "video_stream_count": len(video_streams),
        "audio_stream_count": len(audio_streams),
        "video": {
            "codec_name": video.get("codec_name"),
            "width": video.get("width"),
            "height": video.get("height"),
            "r_frame_rate": video.get("r_frame_rate"),
            "avg_frame_rate": video.get("avg_frame_rate"),
            "duration": video.get("duration"),
            "pix_fmt": video.get("pix_fmt"),
            "rotation": rotation,
            "sample_aspect_ratio": video.get("sample_aspect_ratio"),
            "display_aspect_ratio": video.get("display_aspect_ratio"),
        },
        "audio": {
            "codec_name": audio.get("codec_name"),
            "sample_rate": audio.get("sample_rate"),
            "channels": audio.get("channels"),
            "channel_layout": audio.get("channel_layout"),
            "duration": audio.get("duration"),
        },
    }


def _post_qc(
    runtime: Path,
    project: Path,
    env: Mapping[str, str],
    log_dir: Path,
    label: str,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(runtime / "scripts/v4_post_qc.py"),
        "--project",
        str(project),
        "--release-id",
        RELEASE_ID,
    ]
    execution = _run_command(command, cwd=runtime, env=env, log_dir=log_dir, label=label)
    report_path = project / "09_qc_质检/v4_release_gate.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else None
    return {"execution": execution, "report_path": str(report_path), "report": report}


def _baseline_run(
    fixture_root: Path,
    runtime: Path,
    project: Path,
    env: Mapping[str, str],
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(runtime / "scripts/build_batch_video_v3.py"),
        str(project),
        "--release-version",
        "v4",
    ]
    execution = _run_command(
        command,
        cwd=runtime,
        env=env,
        log_dir=fixture_root / "logs/baseline",
        label="renderer",
    )
    output = project / f"08_render_合成/v4/{project.name}-v4-bilingual-3x4.mp4"
    if execution["returncode"] != 0 or not output.is_file() or output.stat().st_size <= 0:
        raise SmokeFixtureError("baseline V4 renderer failed; artifacts were retained")
    probe = _probe(output)
    post_qc = _post_qc(runtime, project, env, fixture_root / "logs/baseline", "post-qc")
    if post_qc["execution"]["returncode"] != 0:
        raise SmokeFixtureError("baseline V4 Post-QC failed; artifacts were retained")
    manifest_path = project / "07_timeline_时间线/v4/render_manifest.v4.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "execution": execution,
        "output": str(output),
        "probe": probe,
        "manifest": str(manifest_path),
        "timeline_segment_count": len(manifest.get("timeline", [])),
        "line_count": len(manifest.get("lines", [])),
        "post_qc": post_qc,
    }


def _facade_post_qc(
    fixture_root: Path,
    runtime: Path,
    project: Path,
    request: Any,
    result: Any,
    resolver: RootResolver,
    env: Mapping[str, str],
) -> dict[str, Any]:
    handoff = result.qc_handoff
    if handoff is None or handoff.get("attempt_id") != result.attempt_id:
        raise SmokeFixtureError("QC handoff is missing or attempt-mismatched")
    if tuple(handoff.get("output_asset_ids", ())) != tuple(item.asset_id for item in result.output):
        raise SmokeFixtureError("QC handoff output IDs do not match this Result")
    if result.request_hash != request.request_hash or handoff.get("request_hash") != request.request_hash:
        raise SmokeFixtureError("QC handoff Request hash does not match")
    output = result.output[0]
    output_path = resolver.resolve(output.ref, require_exists=True)
    if _sha256(output_path) != output.sha256:
        raise SmokeFixtureError("QC adapter output Hash does not match Result")
    delivery = project / f"10_delivery_交付/v4/{project.name}-v4-bilingual-3x4.mp4"
    if not delivery.is_file():
        raise SmokeFixtureError("legacy delivery copy required by v4_post_qc is missing")
    post_qc = _post_qc(runtime, project, env, fixture_root / "logs/facade", "post-qc")
    post_qc["adapter"] = {
        "schema_version": "1.0",
        "source": "current_attempt_qc_handoff",
        "attempt_id": result.attempt_id,
        "request_hash": request.request_hash,
        "result_output_ref": {"root": output.ref.root, "path": output.ref.path},
        "result_output_sha256": output.sha256,
        "legacy_post_qc_project_argument": str(project),
        "legacy_delivery_mapping": delivery.relative_to(project).as_posix(),
        "directory_scan": False,
    }
    return post_qc


def _facade_run(
    fixture_root: Path,
    runtime: Path,
    project: Path,
    env: Mapping[str, str],
) -> dict[str, Any]:
    bundle = collect_v4_release(
        project,
        RELEASE_ID,
        runtime_root=runtime,
        created_at="2026-08-01T00:00:00Z",
    )
    resolver = RootResolver(bundle.root_bindings)
    snapshot_ref = PortableRef("project", bundle.snapshot_path.relative_to(project).as_posix())
    request = map_v4_snapshot_to_request(
        bundle.snapshot,
        snapshot_ref,
        resolver,
        created_at="2026-08-01T00:00:00Z",
    )
    request_path = write_render_request(request, project / "manifests/requests")
    context = RenderExecutionContext(
        resolver=resolver,
        attempts_directory=project / "08_render_合成/attempts",
        attempt_id="phase3c-real-media-001",
        environment=None,
    )
    result = LegacyV4Renderer().render(request, context)
    if result.status is not RenderStatus.SUCCEEDED:
        raise SmokeFixtureError(
            f"facade V4 renderer failed with {result.primary_error_code}; artifacts were retained"
        )
    output_path = resolver.resolve(result.output[0].ref, require_exists=True)
    probe = _probe(output_path)
    post_qc = _facade_post_qc(
        fixture_root, runtime, project, request, result, resolver, env
    )
    if post_qc["execution"]["returncode"] != 0:
        raise SmokeFixtureError("facade V4 Post-QC failed; artifacts were retained")
    manifest_path = project / "07_timeline_时间线/v4/render_manifest.v4.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result_path = context.attempts_directory / context.attempt_id / "render-result-v1.json"
    return {
        "snapshot": {
            "id": bundle.snapshot.snapshot_id,
            "hash": bundle.snapshot.snapshot_hash,
            "path": str(bundle.snapshot_path),
        },
        "request": {
            "id": request.request_id,
            "hash": request.request_hash,
            "path": str(request_path),
        },
        "attempt_id": context.attempt_id,
        "result": render_result_to_dict(result),
        "result_path": str(result_path),
        "output": str(output_path),
        "probe": probe,
        "timeline_segment_count": len(manifest.get("timeline", [])),
        "request_segment_count": len(request.timeline["segments"]),
        "line_count": len(manifest.get("lines", [])),
        "sidecar_count": len(result.sidecars),
        "post_qc": post_qc,
    }


def _duration_ticks(probe: Mapping[str, Any]) -> int:
    value = probe.get("format_duration") or probe.get("video", {}).get("duration")
    return int(Decimal(str(value)) * 1000)


def compare_probes(
    baseline: Mapping[str, Any], facade: Mapping[str, Any]
) -> dict[str, Any]:
    stable_fields = {
        "format_name": baseline.get("format_name") == facade.get("format_name"),
        "video_stream_count": baseline.get("video_stream_count") == facade.get("video_stream_count") == 1,
        "audio_stream_count": baseline.get("audio_stream_count") == facade.get("audio_stream_count") == 1,
    }
    for section, fields in {
        "video": (
            "codec_name",
            "width",
            "height",
            "r_frame_rate",
            "avg_frame_rate",
            "pix_fmt",
            "rotation",
            "sample_aspect_ratio",
            "display_aspect_ratio",
        ),
        "audio": ("codec_name", "sample_rate", "channels", "channel_layout"),
    }.items():
        for field in fields:
            stable_fields[f"{section}.{field}"] = (
                baseline.get(section, {}).get(field) == facade.get(section, {}).get(field)
            )
    baseline_ticks = _duration_ticks(baseline)
    facade_ticks = _duration_ticks(facade)
    duration_difference = abs(baseline_ticks - facade_ticks)
    duration_tolerance = (1000 + FPS - 1) // FPS
    stable_fields["duration_within_one_frame"] = duration_difference <= duration_tolerance
    return {
        "passed": all(stable_fields.values()),
        "checks": stable_fields,
        "baseline_duration_ticks": baseline_ticks,
        "facade_duration_ticks": facade_ticks,
        "duration_difference_ticks": duration_difference,
        "approved_tolerance_ticks": duration_tolerance,
        "bitwise_equality_required": False,
        "bitwise_equal": baseline.get("sha256") == facade.get("sha256"),
    }


class _NeverRunner:
    def __init__(self) -> None:
        self.called = False

    def run(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
    ) -> CommandResult:
        self.called = True
        return CommandResult(99, stderr="runner must not be called")


def _failure_run(runtime: Path, project: Path) -> dict[str, Any]:
    bundle = collect_v4_release(
        project,
        RELEASE_ID,
        runtime_root=runtime,
        created_at="2026-08-01T00:00:00Z",
    )
    resolver = RootResolver(bundle.root_bindings)
    snapshot_ref = PortableRef("project", bundle.snapshot_path.relative_to(project).as_posix())
    request = map_v4_snapshot_to_request(bundle.snapshot, snapshot_ref, resolver)
    target_ref = request.output["target"]
    target = resolver.resolve(
        PortableRef(str(target_ref["root"]), str(target_ref["path"]))
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"phase3c-preexisting-output-guard")
    before = {"bytes": target.stat().st_size, "sha256": _sha256(target)}
    runner = _NeverRunner()
    context = RenderExecutionContext(
        resolver,
        project / "08_render_合成/attempts",
        "phase3c-failure-existing-output",
        environment=None,
    )
    result = LegacyV4Renderer(runner=runner).render(request, context)
    after = {"bytes": target.stat().st_size, "sha256": _sha256(target)}
    quarantine = project / "failed-output-quarantine" / context.attempt_id
    quarantine.mkdir(parents=True, exist_ok=False)
    _write_json(
        quarantine / "QUARANTINE_NOT_TRIGGERED.json",
        {
            "schema_version": "1.0",
            "reason": "preexisting output was not created by the failed process",
            "original_path": target.relative_to(project).as_posix(),
            "before": before,
            "after": after,
            "preserved_in_place": True,
        },
    )
    return {
        "fixture_type": "fixed_output_already_exists",
        "status": result.status.value,
        "primary_error_code": result.primary_error_code,
        "runner_called": runner.called,
        "output_before": before,
        "output_after": after,
        "output_preserved": before == after,
        "attempt_id": result.attempt_id,
        "result_path": str(
            context.attempts_directory / context.attempt_id / "render-result-v1.json"
        ),
        "quarantine": {
            "triggered": False,
            "reason": "No process-created partial output; preexisting guard file retained in place.",
            "evidence_directory": str(quarantine),
        },
        "passed": (
            result.status is RenderStatus.FAILED
            and not runner.called
            and before == after
        ),
    }


def run_smoke(fixture_root: Path) -> dict[str, Any]:
    root = Path(fixture_root).expanduser().resolve()
    marker = validate_fixture_root(root)
    runtime = _runtime_root()
    shared, shared_record = _shared_assets(root)
    baseline_project, baseline_semantic = _create_project(root, shared, "fixture-copy-a-baseline")
    facade_project, facade_semantic = _create_project(root, shared, "fixture-copy-b-facade")
    failure_project, failure_semantic = _create_project(root, shared, "fixture-copy-c-failure")
    if not (baseline_semantic == facade_semantic == failure_semantic):
        raise SmokeFixtureError("fixture Project roots do not share identical semantic media inputs")
    font_env, font_hashes = _font_environment(runtime)
    environment = dict(os.environ)
    environment.update(font_env)
    baseline = _baseline_run(root, runtime, baseline_project, environment)
    facade = _facade_run(root, runtime, facade_project, environment)
    media_comparison = compare_probes(baseline["probe"], facade["probe"])
    baseline_qc = baseline["post_qc"]["report"]
    facade_qc = facade["post_qc"]["report"]
    post_qc_comparison = {
        "local_master_status_equal": baseline_qc["local_master_status"] == facade_qc["local_master_status"],
        "technical_checks_equal": baseline_qc["technical_checks"] == facade_qc["technical_checks"],
        "public_release_allowed_equal": baseline_qc["public_release_allowed"] == facade_qc["public_release_allowed"],
        "release_holds_equal": baseline_qc["release_holds"] == facade_qc["release_holds"],
    }
    post_qc_comparison["passed"] = all(post_qc_comparison.values())
    business_structure = {
        "baseline_timeline_segments": baseline["timeline_segment_count"],
        "facade_timeline_segments": facade["timeline_segment_count"],
        "request_timeline_segments": facade["request_segment_count"],
        "baseline_lines": baseline["line_count"],
        "facade_lines": facade["line_count"],
        "facade_sidecars": facade["sidecar_count"],
    }
    business_structure["passed"] = (
        business_structure["baseline_timeline_segments"]
        == business_structure["facade_timeline_segments"]
        == business_structure["request_timeline_segments"]
        == 13
        and business_structure["baseline_lines"]
        == business_structure["facade_lines"]
        == 15
        and business_structure["facade_sidecars"] >= 7
    )
    failure = _failure_run(runtime, failure_project)
    result = {
        "schema_version": "1.0",
        "fixture": marker,
        "generated_at": _utc_now(),
        "runtime_root": str(runtime),
        "shared_assets": shared_record,
        "semantic_input_hashes": baseline_semantic,
        "font_hashes": font_hashes,
        "baseline": baseline,
        "facade": facade,
        "media_semantic_comparison": media_comparison,
        "post_qc_comparison": post_qc_comparison,
        "business_structure": business_structure,
        "failure_fixture": failure,
        "passed": (
            media_comparison["passed"]
            and post_qc_comparison["passed"]
            and business_structure["passed"]
            and failure["passed"]
        ),
        "scope": {
            "provider_calls": 0,
            "network_calls": 0,
            "external_assets": 0,
            "real_commercial_projects": 0,
            "remotion": False,
            "post_qc_inside_facade": False,
        },
    }
    report_path = _write_json(root / "phase-3c-smoke-report.json", result)
    human_report_path = _write_human_report(root / "phase-3c-smoke-report.md", result)
    result["report_path"] = str(report_path)
    result["human_report_path"] = str(human_report_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 3C test-only legacy V4 real-media smoke adapter"
    )
    parser.add_argument("--fixture-dir", type=Path, required=True)
    parser.add_argument("--initialize-only", action="store_true")
    parser.add_argument("--keep-artifacts", action="store_true")
    args = parser.parse_args()
    try:
        if args.initialize_only:
            marker = initialize_fixture_root(args.fixture_dir)
            print(json.dumps({"initialized": True, "marker": str(marker)}, ensure_ascii=False))
            return 0
        result = run_smoke(args.fixture_dir)
    except SmokeFixtureError as error:
        print(json.dumps({"passed": False, "error": str(error)}, ensure_ascii=False))
        return 2
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "report": result["report_path"],
                "human_report": result["human_report_path"],
                "baseline_sha256": result["baseline"]["probe"]["sha256"],
                "facade_sha256": result["facade"]["probe"]["sha256"],
                "bitwise_equal": result["media_semantic_comparison"]["bitwise_equal"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
