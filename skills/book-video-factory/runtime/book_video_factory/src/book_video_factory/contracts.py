from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ContractError(ValueError):
    pass


def _mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ContractError(f"release profile requires object field: {key}")
    return value


def _positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ContractError(f"release profile requires positive integer: {key}")
    return value


@dataclass(frozen=True)
class ReleaseProfile:
    path: Path
    payload: dict[str, Any]

    @classmethod
    def load(cls, path: Path) -> "ReleaseProfile":
        resolved = path.expanduser().resolve()
        try:
            payload = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ContractError(f"cannot load release profile {resolved}: {error}") from error
        if not isinstance(payload, dict):
            raise ContractError("release profile root must be an object")
        cls._validate(payload)
        return cls(resolved, payload)

    @staticmethod
    def _validate(payload: dict[str, Any]) -> None:
        if payload.get("schema_version") != "1.0":
            raise ContractError("unsupported release profile schema_version")
        profile_id = payload.get("profile_id")
        if not isinstance(profile_id, str) or not profile_id.strip():
            raise ContractError("release profile requires profile_id")
        if payload.get("renderer") not in {"build_batch_video_v3"}:
            raise ContractError("release profile uses an unknown renderer")

        canvas = _mapping(payload, "canvas")
        width = _positive_int(canvas, "width")
        _positive_int(canvas, "height")
        _positive_int(canvas, "fps")

        script = _mapping(payload, "script")
        if script.get("language_mode") not in {"zh", "bilingual"}:
            raise ContractError("unsupported script language_mode")
        _positive_int(script, "line_count")

        visual = _mapping(payload, "visual")
        _positive_int(visual, "scene_count")
        if visual.get("scene_format") not in {"png", "jpg", "jpeg"}:
            raise ContractError("unsupported scene_format")

        typography = _mapping(payload, "typography")
        margin = _positive_int(typography, "title_safe_margin_x_px")
        max_width = _positive_int(typography, "title_max_width_px")
        max_lines = _positive_int(typography, "title_max_lines")
        max_size = _positive_int(typography, "title_max_font_size_px")
        min_size = _positive_int(typography, "title_min_font_size_px")
        if max_lines > 2:
            raise ContractError("current renderer supports at most two title lines")
        if max_size < min_size:
            raise ContractError("title font-size range is inverted")
        if max_width > width - 2 * margin:
            raise ContractError("title_max_width_px exceeds the configured safe area")
        if typography.get("overflow_policy") != "fail":
            raise ContractError("title overflow_policy must fail closed")

        if _mapping(payload, "video").get("codec") != "h264":
            raise ContractError("current renderer requires h264")
        if _mapping(payload, "audio").get("codec") != "aac":
            raise ContractError("current renderer requires aac")

    @property
    def profile_id(self) -> str:
        return str(self.payload["profile_id"])

    @property
    def title_max_width(self) -> int:
        return int(self.payload["typography"]["title_max_width_px"])

    @property
    def scene_count(self) -> int:
        return int(self.payload["visual"]["scene_count"])

    @property
    def line_count(self) -> int:
        return int(self.payload["script"]["line_count"])
