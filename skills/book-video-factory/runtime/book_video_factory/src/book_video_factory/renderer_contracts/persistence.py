"""Atomic, exclusive persistence for requests, attempt events and results."""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Mapping

from .canonical import canonical_json_bytes
from .errors import ContractValidationError
from .models import RenderRequest, RenderResult
from .serialization import (
    render_request_from_dict,
    render_request_to_dict,
    render_result_from_dict,
    render_result_to_dict,
)
from .validation import (
    validate_render_request,
    validate_render_result,
    validate_request_hash,
)


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_ATTEMPT_STATUSES = {
    "pending",
    "running",
    "succeeded",
    "failed",
    "blocked",
    "cancelled",
}


class ContractPersistenceError(RuntimeError):
    """Raised when write-once contract bytes cannot be safely published."""


def _safe_id(value: str, *, field: str) -> str:
    if not isinstance(value, str) or _SAFE_ID.fullmatch(value) is None:
        raise ContractPersistenceError(f"{field} is not safe for a persistent filename")
    return value


def _exclusive_canonical_write(path: Path, payload: Mapping[str, Any]) -> Path:
    requested_parent = path.parent
    if requested_parent.is_symlink():
        raise ContractPersistenceError("contract output directory must not be a symlink")
    parent = requested_parent.resolve(strict=False)
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / path.name
    encoded = canonical_json_bytes(payload)
    if target.exists():
        try:
            existing = target.read_bytes()
        except OSError as error:
            raise ContractPersistenceError(
                f"cannot read existing contract file: {target.name}"
            ) from error
        if existing == encoded:
            return target
        raise ContractPersistenceError(
            f"write-once contract path already contains different bytes: {target.name}"
        )

    temporary = parent / f".{target.name}.{uuid.uuid4().hex}.tmp"
    created_target = False
    try:
        with temporary.open("xb") as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary, target)
            created_target = True
        except FileExistsError:
            if target.read_bytes() == encoded:
                return target
            raise ContractPersistenceError(
                f"contract path was concurrently created with different bytes: {target.name}"
            )
        if target.read_bytes() != encoded:
            raise ContractPersistenceError(
                f"persisted contract bytes changed after publication: {target.name}"
            )
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
        except (FileNotFoundError, OSError):
            pass


def write_canonical_once(path: Path, payload: Mapping[str, Any]) -> Path:
    """Publish a canonical JSON document without replacing existing bytes."""
    return _exclusive_canonical_write(Path(path), payload)


def write_render_request(request: RenderRequest, directory: Path) -> Path:
    issues = (*validate_render_request(request), *validate_request_hash(request))
    if issues:
        raise ContractValidationError(issues)
    target = Path(directory) / f"render-request-v1-{request.request_hash}.json"
    path = _exclusive_canonical_write(target, render_request_to_dict(request))
    try:
        restored = render_request_from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractPersistenceError("persisted RenderRequest is unreadable") from error
    restored_issues = (*validate_render_request(restored), *validate_request_hash(restored))
    if restored_issues:
        raise ContractPersistenceError("persisted RenderRequest failed read-back validation")
    return path


def write_attempt_event(
    event: Mapping[str, Any],
    directory: Path,
) -> Path:
    required = {
        "schema_version",
        "request_id",
        "request_hash",
        "attempt_id",
        "event_index",
        "status",
        "recorded_at",
    }
    if set(event) != required:
        raise ContractPersistenceError("attempt event fields do not match v1 event contract")
    if event.get("schema_version") != "1.0":
        raise ContractPersistenceError("unsupported attempt event schema_version")
    attempt_id = _safe_id(str(event.get("attempt_id", "")), field="attempt_id")
    event_index = event.get("event_index")
    if not isinstance(event_index, int) or isinstance(event_index, bool) or event_index < 0:
        raise ContractPersistenceError("attempt event_index must be a non-negative integer")
    status = event.get("status")
    if status not in _ATTEMPT_STATUSES:
        raise ContractPersistenceError("attempt event status is invalid")
    target = Path(directory) / attempt_id / "events" / f"{event_index:03d}-{status}.json"
    return _exclusive_canonical_write(target, event)


def write_render_result(result: RenderResult, directory: Path) -> Path:
    issues = validate_render_result(result)
    if issues:
        raise ContractValidationError(issues)
    attempt_id = _safe_id(result.attempt_id, field="attempt_id")
    target = Path(directory) / attempt_id / "render-result-v1.json"
    path = _exclusive_canonical_write(target, render_result_to_dict(result))
    try:
        restored = render_result_from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractPersistenceError("persisted RenderResult is unreadable") from error
    if validate_render_result(restored):
        raise ContractPersistenceError("persisted RenderResult failed read-back validation")
    return path


__all__ = [
    "ContractPersistenceError",
    "write_canonical_once",
    "write_attempt_event",
    "write_render_request",
    "write_render_result",
]
