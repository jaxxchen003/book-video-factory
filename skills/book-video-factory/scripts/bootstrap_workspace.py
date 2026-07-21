#!/usr/bin/env python3
"""Create an idempotent, media-free workspace for the book-video Skill."""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_DIRS = (
    "00_topic_选题",
    "01_research_资料搜集/raw",
    "01_research_资料搜集/normalized",
    "01_research_资料搜集/sources/cover",
    "01_research_资料搜集/content_system/imports",
    "02_story_script_故事脚本",
    "02_story_script_故事脚本/traceability",
    "03_images_生成图片/prompts",
    "03_images_生成图片/generated",
    "03_images_生成图片/approved/v4",
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

SKILL_ROOT = Path(__file__).resolve().parents[1]
BUNDLED_FACTORY = SKILL_ROOT / "runtime" / "book_video_factory"
DEFAULT_STYLE_PROFILE_ID = "book-editorial-bilingual-v2"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_text_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def write_json_if_missing(path: Path, payload: dict[str, Any]) -> bool:
    return write_text_if_missing(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def valid_slug(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
        raise argparse.ArgumentTypeError("slug must use lowercase letters, digits, and single hyphens")
    return value


def available_style_profile_ids() -> tuple[str, ...]:
    directory = BUNDLED_FACTORY / "config" / "style_profiles"
    return tuple(sorted(path.stem for path in directory.glob("*.json") if path.is_file()))


def load_style_profile(style_profile_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", style_profile_id):
        raise ValueError("style_profile_id must be a safe identifier")
    directory = (BUNDLED_FACTORY / "config" / "style_profiles").resolve()
    path = (directory / f"{style_profile_id}.json").resolve()
    try:
        path.relative_to(directory)
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError, json.JSONDecodeError) as error:
        allowed = ", ".join(available_style_profile_ids())
        raise ValueError(
            f"cannot load style profile {style_profile_id!r}; available: {allowed}"
        ) from error
    if payload.get("style_id") != style_profile_id:
        raise ValueError("style profile filename and style_id do not match")
    return payload


def resolve_generation_lane(
    style_profile: dict[str, Any], requested: str | None
) -> str:
    lanes = style_profile.get("generation_lanes")
    if not isinstance(lanes, dict) or not lanes:
        raise ValueError("style profile does not define generation_lanes")
    lane = requested or style_profile.get("default_generation_lane")
    if lane is None:
        allowed = ", ".join(sorted(lanes))
        raise ValueError(
            f"style {style_profile['style_id']} requires --generation-lane; use {allowed}"
        )
    if lane not in lanes:
        allowed = ", ".join(sorted(lanes))
        raise ValueError(
            f"unsupported generation lane {lane!r} for {style_profile['style_id']}; "
            f"use {allowed}"
        )
    return str(lane)


def bootstrap_workspace(workspace: Path) -> list[Path]:
    factory = workspace / "book_video_factory"
    warehouse = workspace / "book_video_warehouse"
    created: list[Path] = []
    if not BUNDLED_FACTORY.is_dir():
        raise FileNotFoundError(f"bundled factory runtime is missing: {BUNDLED_FACTORY}")
    for source in sorted(BUNDLED_FACTORY.rglob("*")):
        relative = source.relative_to(BUNDLED_FACTORY)
        if "__pycache__" in relative.parts or source.suffix == ".pyc":
            continue
        destination = factory / relative
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            created.append(destination)
    for directory in (warehouse / "projects", warehouse / "operations", warehouse / "reports"):
        directory.mkdir(parents=True, exist_ok=True)
    readme = warehouse / "README.md"
    if write_text_if_missing(
        readme,
        "# Book video warehouse\n\n"
        "This directory is intentionally local-only. It may contain media, source evidence, provider usage, and account metadata. Do not publish it without a separate rights and privacy review.\n",
    ):
        created.append(readme)
    return created


def create_project(
    workspace: Path,
    slug: str,
    title: str,
    author: str,
    mode: str = "single-book",
    style_profile_id: str = DEFAULT_STYLE_PROFILE_ID,
    generation_lane: str | None = None,
) -> tuple[Path, list[Path]]:
    if mode not in {"single-book", "content-system-backed"}:
        raise ValueError(f"unsupported workflow mode: {mode}")
    style_profile = load_style_profile(style_profile_id)
    if mode not in style_profile.get("supported_workflow_modes", []):
        raise ValueError(
            f"style {style_profile_id} does not support workflow mode {mode}"
        )
    resolved_generation_lane = resolve_generation_lane(
        style_profile, generation_lane
    )
    release_profile_id = str(style_profile["release_profile_id"])
    project = workspace / "book_video_warehouse" / "projects" / slug
    contract_path = project / "project.json"
    if contract_path.is_file():
        try:
            existing = json.loads(contract_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"existing project contract is unreadable: {contract_path}") from error
        workflow = existing.get("workflow") if isinstance(existing, dict) else None
        existing_mode = (
            str(workflow.get("mode") or "single-book")
            if isinstance(workflow, dict)
            else "single-book"
        )
        if existing_mode != mode:
            raise ValueError(
                f"project {slug} already uses workflow mode {existing_mode}; "
                f"refusing requested mode {mode}"
            )
        existing_style = (
            str(workflow.get("style_profile_id") or DEFAULT_STYLE_PROFILE_ID)
            if isinstance(workflow, dict)
            else DEFAULT_STYLE_PROFILE_ID
        )
        existing_release_profile = (
            str(workflow.get("release_profile_id") or "")
            if isinstance(workflow, dict)
            else ""
        )
        if not existing_release_profile:
            existing_release_profile = str(
                load_style_profile(existing_style)["release_profile_id"]
            )
        existing_lane = workflow.get("generation_lane") if isinstance(workflow, dict) else None
        if existing_lane is None and existing_style == DEFAULT_STYLE_PROFILE_ID:
            existing_lane = resolve_generation_lane(
                load_style_profile(existing_style), None
            )
        if (
            existing_style != style_profile_id
            or existing_release_profile != release_profile_id
            or existing_lane != resolved_generation_lane
        ):
            raise ValueError(
                f"project {slug} already uses style {existing_style}, release profile "
                f"{existing_release_profile}, and lane {existing_lane}; refusing requested "
                f"style {style_profile_id}, release profile {release_profile_id}, and lane "
                f"{resolved_generation_lane}"
            )
    created: list[Path] = []
    for relative in PROJECT_DIRS:
        target = project / relative
        target.mkdir(parents=True, exist_ok=True)
        keep = target / ".gitkeep"
        if write_text_if_missing(keep, ""):
            created.append(keep)
    if write_json_if_missing(
        contract_path,
        {
            "schema_version": "1.0",
            "project_id": slug,
            "book": {"title": title, "author": author},
            "status": "initialized",
            "current_stage": "00_topic_选题",
            "created_at": utc_now(),
            "workflow": {
                "mode": mode,
                "style_profile_id": style_profile_id,
                "style_display_name": style_profile["display_name"]["zh-CN"],
                "release_profile_id": release_profile_id,
                "generation_lane": resolved_generation_lane,
                "execution_mode": style_profile["execution_mode"],
                "state_source": "derived_gate_evaluator",
                "status_field_role": "compatibility_cache_only"
            },
            "review": {
                "script": "pending",
                "cover_rights": "pending",
                "bgm_rights": "pending",
                "english_native_review": "pending",
                "publish": "pending",
            },
        },
    ):
        created.append(contract_path)
    if write_json_if_missing(
        project / "02_story_script_故事脚本" / "script.v2.bilingual.template.json",
        {
            "schema_version": "1.0",
            "status": "draft",
            "translation_status": "needs_native_review",
            "book": {"title": title, "author": author},
            "lines": [
                {"id": f"V{index:02d}", "role": "fill_in", "zh": "", "en": "", "start": None, "end": None}
                for index in range(1, 16)
            ],
        },
    ):
        created.append(project / "02_story_script_故事脚本" / "script.v2.bilingual.template.json")
    if write_json_if_missing(
        project / "01_research_资料搜集" / "sources" / "cover" / "cover_manifest.template.json",
        {
            "status": "pending",
            "source_url": None,
            "source_file": None,
            "acquired_at": None,
            "rights_review": "pending",
            "reviewer": None,
        },
    ):
        created.append(project / "01_research_资料搜集" / "sources" / "cover" / "cover_manifest.template.json")
    if write_json_if_missing(
        project / "06_music_音乐" / "attribution.template.json",
        {
            "status": "pending",
            "title": None,
            "creator": None,
            "source_url": None,
            "license": None,
            "license_url": None,
            "file_sha256": None,
            "attribution_text": None,
            "rights_review": "pending",
        },
    ):
        created.append(project / "06_music_音乐" / "attribution.template.json")
    return project, created


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a portable book-video workspace")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--slug", type=valid_slug)
    parser.add_argument("--book-title")
    parser.add_argument("--author")
    parser.add_argument(
        "--mode",
        choices=("single-book", "content-system-backed"),
        default="single-book",
    )
    parser.add_argument(
        "--style-profile",
        choices=available_style_profile_ids(),
        default=DEFAULT_STYLE_PROFILE_ID,
    )
    parser.add_argument(
        "--generation-lane",
        help="Required for styles with multiple provider lanes, such as gemini-api or google-flow.",
    )
    args = parser.parse_args()
    project_args = (args.slug, args.book_title, args.author)
    if any(project_args) and not all(project_args):
        parser.error("--slug, --book-title, and --author must be provided together")

    workspace = args.workspace.expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    created = bootstrap_workspace(workspace)
    payload: dict[str, Any] = {"workspace": str(workspace), "created": [str(path.relative_to(workspace)) for path in created]}
    if args.slug:
        project, project_created = create_project(
            workspace,
            args.slug,
            args.book_title,
            args.author,
            args.mode,
            args.style_profile,
            args.generation_lane,
        )
        payload["project"] = str(project.relative_to(workspace))
        payload["project_created"] = [str(path.relative_to(workspace)) for path in project_created]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
