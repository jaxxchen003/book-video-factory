from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_STYLE_PROFILE_ID = "book-editorial-bilingual-v2"
STYLE_ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


class StyleProfileError(ValueError):
    pass


def default_style_profile_directory() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "style_profiles"


@dataclass(frozen=True)
class StyleProfile:
    path: Path
    payload: dict[str, Any]

    @classmethod
    def load(cls, path: Path) -> "StyleProfile":
        resolved = path.expanduser().resolve()
        try:
            payload = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise StyleProfileError(
                f"cannot load style profile {resolved}: {error}"
            ) from error
        if not isinstance(payload, dict):
            raise StyleProfileError("style profile root must be an object")
        cls._validate(payload)
        if resolved.stem != payload["style_id"]:
            raise StyleProfileError(
                "style profile filename must match its style_id"
            )
        return cls(resolved, payload)

    @staticmethod
    def _validate(payload: dict[str, Any]) -> None:
        if payload.get("schema_version") != "1.0":
            raise StyleProfileError("unsupported style profile schema_version")
        style_id = payload.get("style_id")
        if not isinstance(style_id, str) or STYLE_ID_PATTERN.fullmatch(style_id) is None:
            raise StyleProfileError("style profile requires a safe style_id")
        display_name = payload.get("display_name")
        if not isinstance(display_name, dict) or not all(
            isinstance(display_name.get(locale), str) and display_name[locale].strip()
            for locale in ("zh-CN", "en")
        ):
            raise StyleProfileError(
                "style profile requires display_name.zh-CN and display_name.en"
            )
        release_profile_id = payload.get("release_profile_id")
        if (
            not isinstance(release_profile_id, str)
            or STYLE_ID_PATTERN.fullmatch(release_profile_id) is None
        ):
            raise StyleProfileError("style profile requires a safe release_profile_id")
        if payload.get("execution_mode") not in {
            "deterministic_local_renderer",
            "orchestration_and_import",
        }:
            raise StyleProfileError("style profile uses an unknown execution_mode")
        supported_modes = payload.get("supported_workflow_modes")
        if (
            not isinstance(supported_modes, list)
            or not supported_modes
            or not all(
                mode in {"single-book", "content-system-backed"}
                for mode in supported_modes
            )
        ):
            raise StyleProfileError(
                "style profile requires supported_workflow_modes"
            )
        local_master = payload.get("output", {}).get("local_master")
        if not isinstance(local_master, dict):
            raise StyleProfileError("style profile requires output.local_master")
        for key in ("width", "height", "fps"):
            value = local_master.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise StyleProfileError(
                    f"style profile requires positive output.local_master.{key}"
                )
        lanes = payload.get("generation_lanes")
        if not isinstance(lanes, dict) or not lanes:
            raise StyleProfileError("style profile requires generation_lanes")
        if not all(
            isinstance(lane_id, str)
            and STYLE_ID_PATTERN.fullmatch(lane_id) is not None
            and isinstance(lane, dict)
            for lane_id, lane in lanes.items()
        ):
            raise StyleProfileError("style profile contains an invalid generation lane")
        default_lane = payload.get("default_generation_lane")
        if default_lane is not None and default_lane not in lanes:
            raise StyleProfileError("default_generation_lane is not defined")
        if payload.get("generation_lane_required") is True and default_lane is not None:
            raise StyleProfileError(
                "a style requiring explicit lane selection cannot define a default lane"
            )
        required_approvals = payload.get("required_publish_approvals")
        if not isinstance(required_approvals, list) or not all(
            isinstance(gate, str) and gate.strip() for gate in required_approvals
        ):
            raise StyleProfileError(
                "style profile requires required_publish_approvals"
            )

    @property
    def style_id(self) -> str:
        return str(self.payload["style_id"])

    @property
    def display_name_zh(self) -> str:
        return str(self.payload["display_name"]["zh-CN"])

    @property
    def release_profile_id(self) -> str:
        return str(self.payload["release_profile_id"])

    @property
    def execution_mode(self) -> str:
        return str(self.payload["execution_mode"])

    @property
    def supported_workflow_modes(self) -> tuple[str, ...]:
        return tuple(str(mode) for mode in self.payload["supported_workflow_modes"])

    @property
    def required_publish_approvals(self) -> tuple[str, ...]:
        return tuple(str(gate) for gate in self.payload["required_publish_approvals"])

    @property
    def asset_ready_approvals(self) -> tuple[str, ...]:
        return tuple(str(gate) for gate in self.payload.get("asset_ready_approvals", []))

    @property
    def conditional_publish_approvals(self) -> dict[str, str]:
        value = self.payload.get("conditional_publish_approvals", {})
        return {str(gate): str(condition) for gate, condition in value.items()}

    @property
    def generation_lane_ids(self) -> tuple[str, ...]:
        return tuple(str(lane) for lane in self.payload["generation_lanes"])

    def resolve_generation_lane(self, requested: str | None) -> str:
        lane = requested or self.payload.get("default_generation_lane")
        if lane is None:
            if self.payload.get("generation_lane_required") is True:
                allowed = ", ".join(self.generation_lane_ids)
                raise StyleProfileError(
                    f"style {self.style_id} requires an explicit generation lane: {allowed}"
                )
            raise StyleProfileError(
                f"style {self.style_id} does not define a generation lane"
            )
        if lane not in self.payload["generation_lanes"]:
            allowed = ", ".join(self.generation_lane_ids)
            raise StyleProfileError(
                f"unsupported generation lane {lane!r} for {self.style_id}; use {allowed}"
            )
        return str(lane)


def available_style_profile_ids(directory: Path | None = None) -> tuple[str, ...]:
    root = (directory or default_style_profile_directory()).resolve()
    return tuple(sorted(path.stem for path in root.glob("*.json") if path.is_file()))


def load_style_profile(
    style_profile_id: str,
    directory: Path | None = None,
) -> StyleProfile:
    if STYLE_ID_PATTERN.fullmatch(style_profile_id) is None:
        raise StyleProfileError("style_profile_id must be a safe identifier")
    root = (directory or default_style_profile_directory()).resolve()
    path = (root / f"{style_profile_id}.json").resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise StyleProfileError("style profile escapes its config directory") from error
    if not path.is_file():
        allowed = ", ".join(available_style_profile_ids(root))
        raise StyleProfileError(
            f"unknown style profile {style_profile_id!r}; available: {allowed}"
        )
    return StyleProfile.load(path)


def project_workflow(project: Path) -> dict[str, Any]:
    path = project.resolve() / "project.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StyleProfileError(f"cannot load project contract {path}: {error}") from error
    workflow = payload.get("workflow")
    if not isinstance(workflow, dict):
        workflow = {}
    style_profile_id = workflow.get("style_profile_id", DEFAULT_STYLE_PROFILE_ID)
    if not isinstance(style_profile_id, str):
        raise StyleProfileError("project workflow style_profile_id must be a string")
    style = load_style_profile(style_profile_id)
    mode = workflow.get("mode", "single-book")
    if mode not in style.supported_workflow_modes:
        raise StyleProfileError(
            f"style {style.style_id} does not support workflow mode {mode!r}"
        )
    release_profile_id = workflow.get("release_profile_id", style.release_profile_id)
    if not isinstance(release_profile_id, str) or not release_profile_id.strip():
        raise StyleProfileError("project workflow release_profile_id must be a string")
    if release_profile_id != style.release_profile_id:
        raise StyleProfileError(
            f"style {style.style_id} requires release profile "
            f"{style.release_profile_id}; project records incompatible profile "
            f"{release_profile_id}"
        )
    generation_lane = workflow.get("generation_lane")
    if generation_lane is None and style.style_id == DEFAULT_STYLE_PROFILE_ID:
        generation_lane = style.resolve_generation_lane(None)
    elif not isinstance(generation_lane, str):
        raise StyleProfileError("project workflow generation_lane must be a string")
    elif generation_lane not in style.generation_lane_ids:
        raise StyleProfileError(
            f"project generation lane {generation_lane!r} is not valid for {style.style_id}"
        )
    return {
        "mode": mode,
        "style_profile": style,
        "style_profile_id": style.style_id,
        "release_profile_id": release_profile_id,
        "generation_lane": generation_lane,
    }
