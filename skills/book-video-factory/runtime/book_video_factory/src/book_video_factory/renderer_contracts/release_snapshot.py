"""Construction and write-once persistence for Release Snapshot v1."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping

from .canonical import (
    canonical_json_bytes,
    semantic_snapshot_hash,
    snapshot_id_from_hash,
)
from .errors import ContractValidationError, SnapshotWriteError
from .models import ArtifactBinding, ReleaseSnapshot
from .serialization import release_snapshot_from_dict, release_snapshot_to_dict
from .validation import validate_release_snapshot, validate_snapshot_hash


def create_release_snapshot(
    *,
    project_id: str,
    release_id: str,
    created_at: str,
    profile: Mapping[str, Any],
    artifacts: Iterable[ArtifactBinding],
    timeline_source: Mapping[str, Any],
    audio_source: Mapping[str, Any],
    caption_source: Mapping[str, Any],
    rights: Mapping[str, Any],
    approvals: Mapping[str, Any],
    release_gates: Mapping[str, Any],
    source_manifests: Iterable[Mapping[str, Any]],
    metadata: Mapping[str, Any] | None = None,
) -> ReleaseSnapshot:
    bound_artifacts = tuple(artifacts)
    artifact_hashes = {item.asset_id: item.sha256 for item in bound_artifacts}
    provisional = ReleaseSnapshot(
        schema_version="1.0",
        snapshot_id="pending",
        snapshot_hash="0" * 64,
        project_id=project_id,
        release_id=release_id,
        created_at=created_at,
        profile=profile,
        artifacts=bound_artifacts,
        artifact_hashes=artifact_hashes,
        timeline_source=timeline_source,
        audio_source=audio_source,
        caption_source=caption_source,
        rights=rights,
        approvals=approvals,
        release_gates=release_gates,
        source_manifests=tuple(source_manifests),
        metadata=metadata or {},
    )
    digest = semantic_snapshot_hash(release_snapshot_to_dict(provisional))
    snapshot = ReleaseSnapshot(
        schema_version=provisional.schema_version,
        snapshot_id=snapshot_id_from_hash(digest),
        snapshot_hash=digest,
        project_id=provisional.project_id,
        release_id=provisional.release_id,
        created_at=provisional.created_at,
        profile=provisional.profile,
        artifacts=provisional.artifacts,
        artifact_hashes=provisional.artifact_hashes,
        timeline_source=provisional.timeline_source,
        audio_source=provisional.audio_source,
        caption_source=provisional.caption_source,
        rights=provisional.rights,
        approvals=provisional.approvals,
        release_gates=provisional.release_gates,
        source_manifests=provisional.source_manifests,
        metadata=provisional.metadata,
    )
    issues = (*validate_release_snapshot(snapshot), *validate_snapshot_hash(snapshot))
    if issues:
        raise ContractValidationError(issues)
    return snapshot


def snapshot_filename(snapshot: ReleaseSnapshot) -> str:
    return f"release-snapshot-v1-{snapshot.snapshot_hash}.json"


def _existing_matches(path: Path, expected: bytes) -> bool:
    try:
        return path.read_bytes() == expected
    except OSError as error:
        raise SnapshotWriteError(f"cannot read existing release snapshot: {path.name}") from error


def write_release_snapshot(snapshot: ReleaseSnapshot, directory: Path) -> Path:
    """Atomically persist an immutable snapshot without overwriting old bytes."""
    issues = (*validate_release_snapshot(snapshot), *validate_snapshot_hash(snapshot))
    if issues:
        raise ContractValidationError(issues)
    requested_dir = Path(directory).expanduser()
    if requested_dir.is_symlink():
        raise SnapshotWriteError("release snapshot directory must not be a symlink")
    target_dir = requested_dir.resolve(strict=False)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / snapshot_filename(snapshot)
    payload = release_snapshot_to_dict(snapshot)
    encoded = canonical_json_bytes(payload)
    if target.exists():
        if _existing_matches(target, encoded):
            return target
        raise SnapshotWriteError("release snapshot path already contains different bytes")

    temporary = target_dir / f".{target.name}.{uuid.uuid4().hex}.tmp"
    created_target = False
    try:
        with temporary.open("xb") as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
        try:
            # A hard-link publication is same-volume, atomic and exclusive: it
            # never replaces an existing immutable snapshot.
            os.link(temporary, target)
            created_target = True
        except FileExistsError:
            if _existing_matches(target, encoded):
                return target
            raise SnapshotWriteError(
                "release snapshot path was concurrently created with different bytes"
            )
        persisted = target.read_bytes()
        if persisted != encoded:
            raise SnapshotWriteError("persisted release snapshot bytes changed after write")
        try:
            decoded = json.loads(persisted.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SnapshotWriteError("persisted release snapshot is not canonical UTF-8 JSON") from error
        restored = release_snapshot_from_dict(decoded)
        restored_issues = (*validate_release_snapshot(restored), *validate_snapshot_hash(restored))
        if restored_issues:
            raise SnapshotWriteError("persisted release snapshot failed read-back validation")
        return target
    except Exception:
        if created_target:
            try:
                target.unlink()
            except OSError:
                pass
        raise
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass
