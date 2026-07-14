from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .content_bridge import content_system_status
from .contracts import ReleaseProfile


REQUIRED_PUBLISH_APPROVALS = (
    "script",
    "cover_rights",
    "bgm_rights",
    "sfx_rights",
    "voice_rights",
    "english_native",
    "publish",
)


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


def _project_mode(project: Path) -> str:
    try:
        payload = json.loads((project / "project.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "invalid"
    workflow = payload.get("workflow")
    if not isinstance(workflow, dict):
        return "single-book"
    mode = workflow.get("mode", "single-book")
    return mode if mode in {"single-book", "content-system-backed"} else "invalid"


def _asset_checks(project: Path, profile: ReleaseProfile) -> dict[str, bool]:
    scenes = project / "03_images_生成图片" / "approved" / "v4"
    scene_paths = [scenes / f"S{index:02d}.png" for index in range(1, profile.scene_count + 1)]
    hashes = [_sha256(path) for path in scene_paths if path.is_file()]
    script_path = project / "02_story_script_故事脚本" / "script.v2.bilingual.json"
    script_lines_ok = False
    if script_path.is_file():
        try:
            script = json.loads(script_path.read_text(encoding="utf-8"))
            script_lines_ok = len(script.get("lines", [])) == profile.line_count
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "script_contract": script_lines_ok,
        "unique_scenes": len(hashes) == profile.scene_count and len(set(hashes)) == profile.scene_count,
        "cover_manifest": (project / "01_research_资料搜集/sources/cover/cover_manifest.json").is_file(),
        "voice": (project / "05_voice_人声/v3-b-locked-master.wav").is_file(),
        "asr": (project / "05_voice_人声/asr-v3/v3-b-locked-master.json").is_file(),
        "bgm": len(list((project / "06_music_音乐").glob("v4-*-original-bgm.mp3"))) == 1,
        "sfx": (project / "06_music_音乐/H2-用户确认原片高频音效层.wav").is_file(),
    }


def evaluate_workflow_state(
    project: Path,
    profile: ReleaseProfile,
    release_id: str | None = None,
) -> dict[str, Any]:
    root = project.resolve()
    project_contract = root / "project.json"
    asset_checks = _asset_checks(root, profile)
    mode = _project_mode(root)
    content_status = content_system_status(root) if mode != "invalid" else {
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
    ambiguous_release_scope = (
        active_release_id is None and len(available_release_ids) > 1
    )
    if active_release_id is None and len(available_release_ids) == 1:
        active_release_id = available_release_ids[0]
    release_scope_valid = not ambiguous_release_scope and not (
        release_id is not None and traced_release_id is not None and release_id != traced_release_id
    )
    approvals = (
        current_approvals(root, active_release_id)
        if active_release_id is not None and release_scope_valid
        else {}
    )
    qc_path = root / "09_qc_质检/v4_release_gate.json"
    qc_passed = False
    if qc_path.is_file():
        try:
            qc = json.loads(qc_path.read_text(encoding="utf-8"))
            qc_passed = bool(
                active_release_id
                and qc.get("release_id") == active_release_id
                and qc.get("local_master_status") == "pass"
            )
        except (OSError, json.JSONDecodeError):
            pass

    state = "draft"
    if not project_contract.is_file() or mode == "invalid" or not release_scope_valid:
        state = "invalid"
    elif "topic" in approvals:
        state = "topic_approved"
        source_ready = "source" in approvals
        if mode == "content-system-backed":
            package_snapshot = content_status.get("package_snapshot")
            source_ready = bool(
                source_ready
                and content_status["content_package_valid"]
                and content_status["production_eligible"]
                and isinstance(package_snapshot, str)
                and approval_covers_path(root, approvals["source"], root / package_snapshot)
            )
        if source_ready:
            state = "source_audited"
            script_path = root / "02_story_script_故事脚本/script.v2.bilingual.json"
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
                if all(asset_checks.values()) and content_assets_ready:
                    state = "assets_ready"
                    if "timing" in approvals:
                        state = "timeline_verified"
                        if qc_passed:
                            state = "qc_passed"
                            if all(gate in approvals for gate in REQUIRED_PUBLISH_APPROVALS):
                                state = "ready_to_publish"
    return {
        "schema_version": "1.0",
        "project_id": root.name,
        "workflow_mode": mode,
        "release_id": active_release_id,
        "available_release_ids": available_release_ids,
        "release_scope_valid": release_scope_valid,
        "release_profile_id": profile.profile_id,
        "derived_state": state,
        "ready_to_publish": state == "ready_to_publish",
        "asset_checks": asset_checks,
        "content_system": content_status,
        "current_approval_gates": sorted(approvals),
        "missing_publish_approvals": [
            gate for gate in REQUIRED_PUBLISH_APPROVALS if gate not in approvals
        ],
        "qc_passed": qc_passed,
    }
