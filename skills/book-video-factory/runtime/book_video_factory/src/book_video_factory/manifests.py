from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_file(project: Path, path: Path) -> tuple[Path, str]:
    root = project.resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"manifest artifact is outside project: {path}") from error
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    return resolved, relative.as_posix()


def artifact(project: Path, role: str, path: Path) -> dict[str, Any]:
    resolved, relative = _project_file(project, path)
    return {
        "role": role,
        "path": relative,
        "bytes": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }


def write_immutable_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write("\n")
    return path


def _filename_time(value: str) -> str:
    return value.replace(":", "-").replace("+", "_")


def write_stage_manifest(
    project: Path,
    *,
    stage: str,
    release_id: str,
    release_profile_id: str,
    inputs: Iterable[tuple[str, Path]],
    outputs: Iterable[tuple[str, Path]],
    checks: list[dict[str, Any]],
    producer: str = "book-video-factory",
    approval_event_ids: list[str] | None = None,
    cost_event_ids: list[str] | None = None,
    manifest_id: str | None = None,
    recorded_at: str | None = None,
) -> Path:
    root = project.resolve()
    event_time = recorded_at or utc_now()
    identifier = manifest_id or str(uuid.uuid4())
    payload = {
        "schema_version": "1.0",
        "manifest_id": identifier,
        "project_id": root.name,
        "stage": stage,
        "release_id": release_id,
        "release_profile_id": release_profile_id,
        "producer": {"tool": producer},
        "recorded_at": event_time,
        "status": "success" if all(item.get("result") == "pass" for item in checks if item.get("severity") == "error") else "failed",
        "inputs": [artifact(root, role, path) for role, path in inputs],
        "outputs": [artifact(root, role, path) for role, path in outputs],
        "checks": checks,
        "approval_event_ids": approval_event_ids or [],
        "cost_event_ids": cost_event_ids or [],
    }
    path = root / "manifests" / "stages" / stage / f"{_filename_time(event_time)}-{identifier}.json"
    return write_immutable_json(path, payload)


def record_approval(
    project: Path,
    *,
    release_id: str,
    gate: str,
    decision: str,
    reviewer: str,
    subjects: Iterable[Path],
    evidence_refs: list[str] | None = None,
    note: str = "",
    event_id: str | None = None,
    reviewed_at: str | None = None,
) -> Path:
    if decision not in {"approved", "rejected", "revoked"}:
        raise ValueError("invalid approval decision")
    if not reviewer.strip():
        raise ValueError("reviewer is required")
    root = project.resolve()
    event_time = reviewed_at or utc_now()
    identifier = event_id or str(uuid.uuid4())
    payload = {
        "schema_version": "1.0",
        "event_id": identifier,
        "project_id": root.name,
        "release_id": release_id,
        "gate": gate,
        "decision": decision,
        "reviewer": reviewer,
        "reviewed_at": event_time,
        "subjects": [artifact(root, "approval_subject", path) for path in subjects],
        "evidence_refs": evidence_refs or [],
        "note": note,
    }
    path = root / "logs" / "approval_events" / f"{_filename_time(event_time)}-{identifier}.json"
    return write_immutable_json(path, payload)
