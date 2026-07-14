from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
    release_profile_id: str = "book-v4-bilingual-3x4",
) -> Path:
    if mode not in {"single-book", "content-system-backed"}:
        raise ValueError(f"unsupported workflow mode: {mode}")
    project = warehouse.resolve() / "projects" / slug
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
            "release_profile_id": release_profile_id,
            "state_source": "derived_gate_evaluator",
            "status_field_role": "compatibility_cache_only",
        },
    }
    write_json(project / "project.json", manifest, overwrite=False)

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
