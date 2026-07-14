from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

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
    directory = project.resolve() / "logs" / "approval_events"
    events: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else []:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def current_approvals(project: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for event in load_approval_events(project):
        gate = str(event.get("gate", ""))
        if gate:
            latest[gate] = event
    return {
        gate: event
        for gate, event in latest.items()
        if approval_is_current(project, event)
    }


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


def evaluate_workflow_state(project: Path, profile: ReleaseProfile) -> dict[str, Any]:
    root = project.resolve()
    project_contract = root / "project.json"
    approvals = current_approvals(root)
    asset_checks = _asset_checks(root, profile)
    qc_path = root / "09_qc_质检/v4_release_gate.json"
    qc_passed = False
    if qc_path.is_file():
        try:
            qc_passed = json.loads(qc_path.read_text(encoding="utf-8")).get("local_master_status") == "pass"
        except (OSError, json.JSONDecodeError):
            pass

    state = "draft"
    if not project_contract.is_file():
        state = "invalid"
    elif "topic" in approvals:
        state = "topic_approved"
        if "source" in approvals:
            state = "source_audited"
            if "script" in approvals:
                state = "script_reviewed"
                if all(asset_checks.values()):
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
        "release_profile_id": profile.profile_id,
        "derived_state": state,
        "ready_to_publish": state == "ready_to_publish",
        "asset_checks": asset_checks,
        "current_approval_gates": sorted(approvals),
        "missing_publish_approvals": [
            gate for gate in REQUIRED_PUBLISH_APPROVALS if gate not in approvals
        ],
        "qc_passed": qc_passed,
    }
