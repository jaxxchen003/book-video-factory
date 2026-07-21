from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .content_bridge import content_system_status
from .contracts import ReleaseProfile
from .style_profiles import StyleProfile, project_workflow


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def approval_is_current(project: Path, event: dict[str, Any]) -> bool:
    if event.get("decision") != "approved":
        return False
    root = project.resolve()
    if event.get("schema_version") != "1.0" or event.get("project_id") != root.name:
        return False
    if not isinstance(event.get("release_id"), str) or not event["release_id"].strip():
        return False
    subjects = event.get("subjects")
    if not isinstance(subjects, list) or not subjects:
        return False
    for subject in subjects:
        try:
            path = (root / str(subject["path"])).resolve()
            path.relative_to(root)
        except (KeyError, ValueError):
            return False
        if not path.is_file() or _sha256(path) != subject.get("sha256"):
            return False
    return True


def load_approval_events(project: Path) -> list[dict[str, Any]]:
    root = project.resolve()
    directory = root / "logs" / "approval_events"
    events: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else []:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            isinstance(payload, dict)
            and payload.get("schema_version") == "1.0"
            and payload.get("project_id") == root.name
            and isinstance(payload.get("release_id"), str)
            and payload["release_id"].strip()
        ):
            events.append(payload)
    return events


def current_approvals(
    project: Path, release_id: str | None = None
) -> dict[str, dict[str, Any]]:
    candidates: dict[str, list[dict[str, Any]]] = {}
    for event in load_approval_events(project):
        if release_id is not None and event.get("release_id") != release_id:
            continue
        gate = str(event.get("gate", ""))
        if gate:
            candidates.setdefault(gate, []).append(event)
    latest: dict[str, dict[str, Any]] = {}
    for gate, events in candidates.items():
        latest_timestamp = max(str(event.get("reviewed_at", "")) for event in events)
        newest = [
            event
            for event in events
            if str(event.get("reviewed_at", "")) == latest_timestamp
        ]
        # Old second-resolution logs can contain conflicting decisions with the
        # same timestamp. Do not use UUID filename ordering to guess intent.
        if len(newest) == 1:
            latest[gate] = newest[0]
    return {
        gate: event
        for gate, event in latest.items()
        if approval_is_current(project, event)
    }


def approval_covers_path(project: Path, event: dict[str, Any], path: Path) -> bool:
    root = project.resolve()
    try:
        expected = path.resolve().relative_to(root).as_posix()
    except ValueError:
        return False
    return any(
        isinstance(subject, dict) and subject.get("path") == expected
        for subject in event.get("subjects", [])
    )


def _script_path(project: Path) -> Path:
    return project / "02_story_script_故事脚本" / "script.v2.bilingual.json"


def _script_has_lines(path: Path, *, expected: int | None = None) -> bool:
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    lines = payload.get("lines")
    if not isinstance(lines, list) or not lines:
        return False
    return expected is None or len(lines) == expected


def _legacy_asset_checks(project: Path, profile: ReleaseProfile) -> dict[str, bool]:
    scenes = project / "03_images_生成图片" / "approved" / "v4"
    scene_paths = [
        scenes / f"S{index:02d}.png" for index in range(1, profile.scene_count + 1)
    ]
    hashes = [_sha256(path) for path in scene_paths if path.is_file()]
    return {
        "script_contract": _script_has_lines(
            _script_path(project), expected=profile.line_count
        ),
        "unique_scenes": (
            len(hashes) == profile.scene_count
            and len(set(hashes)) == profile.scene_count
        ),
        "cover_manifest": (
            project
            / "01_research_资料搜集/sources/cover/cover_manifest.json"
        ).is_file(),
        "voice": (project / "05_voice_人声/v3-b-locked-master.wav").is_file(),
        "asr": (
            project / "05_voice_人声/asr-v3/v3-b-locked-master.json"
        ).is_file(),
        "bgm": len(
            list((project / "06_music_音乐").glob("v4-*-original-bgm.mp3"))
        )
        == 1,
        "sfx": (
            project / "06_music_音乐/H2-用户确认原片高频音效层.wav"
        ).is_file(),
    }


def _vox_asset_checks(project: Path, profile: ReleaseProfile) -> dict[str, bool]:
    manifest_relative = profile.asset_manifest
    manifest_path = project / str(manifest_relative or "")
    checks = {
        "script_contract": _script_has_lines(_script_path(project)),
        "clip_manifest": False,
        "clips_present": False,
        "unique_clips": False,
        "clip_hashes": False,
        "clip_qa": False,
        "silent_clip_contract": False,
        "voice": any((project / "05_voice_人声").glob("*master*.wav")),
        "asr": any((project / "05_voice_人声").glob("asr-*/*.json")),
    }
    if not manifest_path.is_file():
        return checks
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return checks
    assets = payload.get("assets")
    if not isinstance(assets, list) or not assets:
        return checks
    checks["clip_manifest"] = True
    resolved_paths: list[Path] = []
    hashes: list[str] = []
    scene_ids: list[str] = []
    hashes_match = True
    qa_passed = True
    for asset in assets:
        if not isinstance(asset, dict):
            hashes_match = False
            qa_passed = False
            continue
        relative = asset.get("path")
        scene_id = asset.get("scene_id")
        if not isinstance(relative, str) or not isinstance(scene_id, str):
            hashes_match = False
            qa_passed = False
            continue
        path = (manifest_path.parent / relative).resolve()
        try:
            path.relative_to(project.resolve())
        except ValueError:
            hashes_match = False
            qa_passed = False
            continue
        resolved_paths.append(path)
        scene_ids.append(scene_id)
        if not path.is_file():
            hashes_match = False
            continue
        digest = _sha256(path)
        hashes.append(digest)
        if digest != asset.get("sha256"):
            hashes_match = False
        if not str(asset.get("qa", "")).startswith("pass"):
            qa_passed = False
    checks["clips_present"] = len(resolved_paths) == len(assets) and all(
        path.is_file() for path in resolved_paths
    )
    checks["unique_clips"] = (
        len(scene_ids) == len(assets)
        and len(set(scene_ids)) == len(scene_ids)
        and len(hashes) == len(assets)
        and len(set(hashes)) == len(hashes)
    )
    checks["clip_hashes"] = hashes_match and len(hashes) == len(assets)
    checks["clip_qa"] = qa_passed
    delivery_spec = payload.get("delivery_spec")
    checks["silent_clip_contract"] = bool(
        isinstance(delivery_spec, dict)
        and delivery_spec.get("audio_stream") is False
        and delivery_spec.get("width") == profile.payload["canvas"]["width"]
        and delivery_spec.get("height") == profile.payload["canvas"]["height"]
    )
    return checks


def _asset_checks(project: Path, profile: ReleaseProfile) -> dict[str, bool]:
    if profile.renderer == "external_clip_timeline_v1":
        return _vox_asset_checks(project, profile)
    return _legacy_asset_checks(project, profile)


def _delivery_manifests(project: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    directory = project / "10_delivery_交付"
    for path in sorted(directory.glob("**/delivery-manifest.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            results.append(payload)
    return results


def _delivery_manifest_for_release(
    project: Path, release_id: str | None
) -> dict[str, Any] | None:
    if release_id is None:
        return None
    matches = [
        payload
        for payload in _delivery_manifests(project)
        if payload.get("release_id") == release_id
    ]
    return matches[-1] if matches else None


def _qc_passed(
    project: Path, profile: ReleaseProfile, release_id: str | None
) -> bool:
    if release_id is None:
        return False
    if profile.renderer == "build_batch_video_v3":
        qc_path = project / "09_qc_质检/v4_release_gate.json"
        if not qc_path.is_file():
            return False
        try:
            qc = json.loads(qc_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        return bool(
            qc.get("release_id") == release_id
            and qc.get("local_master_status") == "pass"
        )

    for name in ("release-gate.json", "qc-report.json"):
        path = project / "09_qc_质检" / release_id / name
        if not path.is_file():
            continue
        try:
            qc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if qc.get("release_id") == release_id and qc.get(
            "local_master_status"
        ) == "pass":
            return True

    delivery = _delivery_manifest_for_release(project, release_id)
    if delivery is None:
        return False
    qc = delivery.get("qc")
    local_master = delivery.get("local_master")
    if not isinstance(qc, dict) or not str(qc.get("status", "")).startswith("pass"):
        return False
    if not isinstance(local_master, dict) or not isinstance(local_master.get("path"), str):
        return False
    master_path = (project / local_master["path"]).resolve()
    try:
        master_path.relative_to(project.resolve())
    except ValueError:
        return False
    return bool(
        master_path.is_file()
        and _sha256(master_path) == local_master.get("sha256")
    )


def _english_is_delivered(project: Path) -> bool:
    path = _script_path(project)
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        lines = payload.get("lines", [])
        if isinstance(lines, list) and any(
            isinstance(line, dict) and str(line.get("en", "")).strip()
            for line in lines
        ):
            return True
    return any((project / "10_delivery_交付").glob("**/*en*.srt"))


def _real_cover_is_used(project: Path) -> bool:
    cover_manifest = (
        project / "01_research_资料搜集/sources/cover/cover_manifest.json"
    )
    if cover_manifest.is_file():
        return True
    return any(
        path.is_file()
        for path in (project / "03_images_生成图片").glob("**/*book-cover*")
    )


def _conditional_approval_status(
    project: Path, style: StyleProfile, approvals: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for gate, condition in style.conditional_publish_approvals.items():
        triggered = False
        if gate == "cover_rights":
            triggered = _real_cover_is_used(project)
        elif gate == "english_native":
            triggered = _english_is_delivered(project)
        elif gate == "showcase_publish":
            # A repository showcase is a separate derivative decision and must
            # never block an otherwise valid production release.
            triggered = False
        results[gate] = {
            "condition": condition,
            "triggered": triggered,
            "approved": gate in approvals,
        }
    return results


def evaluate_workflow_state(
    project: Path,
    profile: ReleaseProfile,
    release_id: str | None = None,
) -> dict[str, Any]:
    root = project.resolve()
    project_contract = root / "project.json"
    workflow = project_workflow(root)
    mode = str(workflow["mode"])
    style = workflow["style_profile"]
    profile_aligned = workflow["release_profile_id"] == profile.profile_id
    mode_valid = mode in {"single-book", "content-system-backed"}
    asset_checks = _asset_checks(root, profile)
    content_status = content_system_status(root) if mode_valid else {
        "required": False,
        "content_package_valid": False,
        "production_eligible": False,
        "traceability_valid": False,
        "errors": ["invalid project workflow mode"],
    }
    approval_events = load_approval_events(root)
    available_release_ids = sorted(
        {
            str(event["release_id"])
            for event in approval_events
            if isinstance(event.get("release_id"), str) and event["release_id"].strip()
        }
    )
    traced_release_id = (
        str(content_status["release_id"])
        if content_status.get("traceability_valid")
        and isinstance(content_status.get("release_id"), str)
        else None
    )
    if release_id is not None and not release_id.strip():
        raise ValueError("release_id cannot be empty")
    active_release_id = release_id or traced_release_id
    ambiguous_release_scope = active_release_id is None and len(available_release_ids) > 1
    if active_release_id is None and len(available_release_ids) == 1:
        active_release_id = available_release_ids[0]
    release_scope_valid = not ambiguous_release_scope and not (
        release_id is not None
        and traced_release_id is not None
        and release_id != traced_release_id
    )
    approvals = (
        current_approvals(root, active_release_id)
        if active_release_id is not None and release_scope_valid
        else {}
    )
    qc_passed = _qc_passed(root, profile, active_release_id)
    conditional = _conditional_approval_status(root, style, approvals)
    required_publish_approvals = list(style.required_publish_approvals)
    required_publish_approvals.extend(
        gate
        for gate, status in conditional.items()
        if status["triggered"] and gate != "showcase_publish"
    )
    required_publish_approvals = list(dict.fromkeys(required_publish_approvals))
    missing_publish_approvals = [
        gate for gate in required_publish_approvals if gate not in approvals
    ]

    state = "draft"
    if (
        not project_contract.is_file()
        or not mode_valid
        or not release_scope_valid
        or not profile_aligned
    ):
        state = "invalid"
    elif "topic" in approvals:
        state = "topic_approved"
        source_gate = (
            "source_audit"
            if "source_audit" in style.required_publish_approvals
            else "source"
        )
        source_ready = source_gate in approvals
        if mode == "content-system-backed":
            package_snapshot = content_status.get("package_snapshot")
            source_ready = bool(
                source_ready
                and content_status["content_package_valid"]
                and content_status["production_eligible"]
                and isinstance(package_snapshot, str)
                and approval_covers_path(
                    root, approvals[source_gate], root / package_snapshot
                )
            )
        if source_ready:
            state = "source_audited"
            script_path = _script_path(root)
            script_ready = "script" in approvals and approval_covers_path(
                root, approvals["script"], script_path
            )
            if script_ready:
                state = "script_reviewed"
                content_assets_ready = mode != "content-system-backed"
                if mode == "content-system-backed":
                    trace_path = content_status.get("traceability_map")
                    content_assets_ready = bool(
                        content_status["traceability_valid"]
                        and traced_release_id == active_release_id
                        and "traceability" in approvals
                        and isinstance(trace_path, str)
                        and approval_covers_path(
                            root,
                            approvals["traceability"],
                            root / trace_path,
                        )
                    )
                style_asset_approvals_ready = all(
                    gate in approvals for gate in style.asset_ready_approvals
                )
                if (
                    all(asset_checks.values())
                    and content_assets_ready
                    and style_asset_approvals_ready
                ):
                    state = "assets_ready"
                    if "timing" in approvals:
                        state = "timeline_verified"
                        if qc_passed:
                            state = "qc_passed"
                            if not missing_publish_approvals:
                                state = "ready_to_publish"
    return {
        "schema_version": "1.0",
        "project_id": root.name,
        "workflow_mode": mode,
        "style_profile_id": style.style_id,
        "style_display_name": style.display_name_zh,
        "execution_mode": style.execution_mode,
        "generation_lane": workflow["generation_lane"],
        "release_id": active_release_id,
        "available_release_ids": available_release_ids,
        "release_scope_valid": release_scope_valid,
        "release_profile_id": profile.profile_id,
        "release_profile_aligned": profile_aligned,
        "derived_state": state,
        "ready_to_publish": state == "ready_to_publish",
        "asset_checks": asset_checks,
        "content_system": content_status,
        "current_approval_gates": sorted(approvals),
        "required_publish_approvals": required_publish_approvals,
        "conditional_publish_approvals": conditional,
        "missing_publish_approvals": missing_publish_approvals,
        "qc_passed": qc_passed,
    }
