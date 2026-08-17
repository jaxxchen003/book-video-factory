"""canonical-json-v1 and semantic hash helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import PurePath
from typing import Any, Mapping


class CanonicalizationError(ValueError):
    pass


def normalize_for_canonical_json(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: normalize_for_canonical_json(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError("canonical JSON object keys must be strings")
            normalized[key] = normalize_for_canonical_json(item)
        return normalized
    if isinstance(value, (list, tuple)):
        return [normalize_for_canonical_json(item) for item in value]
    if isinstance(value, PurePath):
        return value.as_posix()
    if isinstance(value, float):
        raise CanonicalizationError("canonical-json-v1 rejects all floating-point values")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise CanonicalizationError(
        f"canonical-json-v1 cannot encode {type(value).__name__}"
    )


def canonical_json_text(payload: Any) -> str:
    normalized = normalize_for_canonical_json(payload)
    try:
        return json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise CanonicalizationError(str(error)) from error


def canonical_json_bytes(payload: Any) -> bytes:
    return canonical_json_text(payload).encode("utf-8")


def canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def semantic_request_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    semantic = normalize_for_canonical_json(payload)
    if not isinstance(semantic, dict):
        raise CanonicalizationError("RenderRequest payload must be an object")
    for key in (
        "request_id",
        "request_hash",
        "metadata",
        "attempt_id",
        "started_at",
        "finished_at",
        "temp_dir",
        "work_dir",
        "cache_dir",
        "log_dir",
        "logs",
        "pid",
        "host_name",
        "retry_count",
        "ui_state",
        "root_bindings",
    ):
        semantic.pop(key, None)
    return semantic


def semantic_request_hash(payload: Mapping[str, Any]) -> str:
    return canonical_sha256(semantic_request_payload(payload))


def request_id_from_hash(request_hash: str) -> str:
    if len(request_hash) != 64 or any(char not in "0123456789abcdef" for char in request_hash):
        raise ValueError("request_hash must be 64 lowercase hexadecimal characters")
    return "rrq_" + request_hash[:24]


def semantic_snapshot_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    semantic = normalize_for_canonical_json(payload)
    if not isinstance(semantic, dict):
        raise CanonicalizationError("ReleaseSnapshot payload must be an object")
    for key in ("snapshot_id", "snapshot_hash", "created_at", "metadata"):
        semantic.pop(key, None)
    return semantic


def semantic_snapshot_hash(payload: Mapping[str, Any]) -> str:
    return canonical_sha256(semantic_snapshot_payload(payload))


def snapshot_id_from_hash(snapshot_hash: str) -> str:
    if len(snapshot_hash) != 64 or any(char not in "0123456789abcdef" for char in snapshot_hash):
        raise ValueError("snapshot_hash must be 64 lowercase hexadecimal characters")
    return "rsn_" + snapshot_hash[:24]
