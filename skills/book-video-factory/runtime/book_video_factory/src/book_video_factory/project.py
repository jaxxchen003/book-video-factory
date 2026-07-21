from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .style_profiles import (
    DEFAULT_STYLE_PROFILE_ID,
    load_style_profile,
)


PROJECT_DIRECTORIES = (
    "00_topic_选题",
    "01_research_资料搜集/raw",
    "01_research_资料搜集/normalized",
    "01_research_资料搜集/sources",
    "01_research_资料搜集/content_system/imports",
    "02_story_script_故事脚本",
    "02_story_script_故事脚本/traceability",
    "03_images_生成图片/prompts",
    "03_images_生成图片/generated",
    "03_images_生成图片/approved",
    "03_images_生成图片/collage-broll",
    "04_copy_文案",
    "05_voice_人声",
    "06_music_音乐",
    "07_timeline_时间线",
    "08_render_合成/preview",
    "08_render_合成/final",
    "09_qc_质检",
    "10_delivery_交付",
    "manifests/stages",
    "logs/approval_events",
    "logs",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, payload: Any, *, overwrite: bool = True) -> bool:
    if path.exists() and not overwrite:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)
    return True


def probe_media(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,size:stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
        "-of",
        "json",
        str(path),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def initialize_project(
    warehouse: Path,
    slug: str,
    book_title: str,
    author: str,
    reference_video: Path | None = None,
    mode: str = "single-book",
    release_profile_id: str | None = None,
    style_profile_id: str = DEFAULT_STYLE_PROFILE_ID,
    generation_lane: str | None = None,
) -> Path:
    if mode not in {"single-book", "content-system-backed"}:
        raise ValueError(f"unsupported workflow mode: {mode}")
    style_profile = load_style_profile(style_profile_id)
    if mode not in style_profile.supported_workflow_modes:
        raise ValueError(
            f"style {style_profile_id} does not support workflow mode {mode}"
        )
    resolved_generation_lane = style_profile.resolve_generation_lane(generation_lane)
    resolved_release_profile_id = release_profile_id or style_profile.release_profile_id
    if resolved_release_profile_id != style_profile.release_profile_id:
        raise ValueError(
            f"style {style_profile_id} requires release profile "
            f"{style_profile.release_profile_id}; refusing incompatible override "
            f"{resolved_release_profile_id}"
        )
    project = warehouse.resolve() / "projects" / slug
    contract_path = project / "project.json"
    if contract_path.is_file():
        try:
            existing = json.loads(contract_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(
                f"existing project contract is unreadable: {contract_path}"
            ) from error
        workflow = existing.get("workflow") if isinstance(existing, dict) else None
        existing_workflow = workflow if isinstance(workflow, dict) else {}
        existing_style = existing_workflow.get(
            "style_profile_id", DEFAULT_STYLE_PROFILE_ID
        )
        existing_mode = existing_workflow.get("mode", "single-book")
        existing_lane = existing_workflow.get("generation_lane")
        existing_release_profile = existing_workflow.get(
            "release_profile_id",
            load_style_profile(existing_style).release_profile_id,
        )
        if existing_lane is None and existing_style == DEFAULT_STYLE_PROFILE_ID:
            existing_lane = load_style_profile(existing_style).resolve_generation_lane(None)
        requested = (
            mode,
            style_profile_id,
            resolved_release_profile_id,
            resolved_generation_lane,
        )
        recorded = (
            existing_mode,
            existing_style,
            existing_release_profile,
            existing_lane,
        )
        if requested != recorded:
            raise ValueError(
                "project already exists with workflow "
                f"mode={existing_mode}, style_profile_id={existing_style}, "
                f"release_profile_id={existing_release_profile}, "
                f"generation_lane={existing_lane}; refusing requested "
                f"mode={mode}, style_profile_id={style_profile_id}, "
                f"release_profile_id={resolved_release_profile_id}, "
                f"generation_lane={resolved_generation_lane}"
            )
    for relative in PROJECT_DIRECTORIES:
        directory = project / relative
        directory.mkdir(parents=True, exist_ok=True)
        (directory / ".gitkeep").touch(exist_ok=True)

    manifest = {
        "schema_version": "1.0",
        "project_id": slug,
        "book": {"title": book_title, "author": author},
        "status": "initialized",
        "current_stage": "00_topic",
        "created_at": utc_now(),
        "reference_video": str(reference_video.resolve()) if reference_video else None,
        "workflow": {
            "mode": mode,
            "style_profile_id": style_profile.style_id,
            "style_display_name": style_profile.display_name_zh,
            "release_profile_id": resolved_release_profile_id,
            "generation_lane": resolved_generation_lane,
            "execution_mode": style_profile.execution_mode,
            "state_source": "derived_gate_evaluator",
            "status_field_role": "compatibility_cache_only",
        },
    }
    write_json(contract_path, manifest, overwrite=False)

    if reference_video:
        reference_video = reference_video.expanduser().resolve()
        if not reference_video.is_file():
            raise FileNotFoundError(f"Reference video not found: {reference_video}")
        reference = {
            "source_path": str(reference_video),
            "role": "style_and_timing_reference_only",
            "publishable_asset": False,
            "probed_at": utc_now(),
            "ffprobe": probe_media(reference_video),
        }
        write_json(project / "00_topic_选题" / "reference.json", reference)

    return project
