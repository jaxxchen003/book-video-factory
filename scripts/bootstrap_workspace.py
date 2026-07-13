#!/usr/bin/env python3
"""Create an idempotent, media-free workspace for the book-video Skill."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_DIRS = (
    "00_topic",
    "01_research/raw",
    "01_research/normalized",
    "01_research/sources/cover",
    "02_story_script",
    "03_images/prompts",
    "03_images/generated",
    "03_images/approved/v4",
    "04_copy",
    "05_voice",
    "06_music",
    "07_timeline",
    "08_render/preview",
    "08_render/final",
    "09_qc",
    "10_delivery",
    "logs",
)


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


def bootstrap_workspace(workspace: Path) -> list[Path]:
    factory = workspace / "book_video_factory"
    warehouse = workspace / "book_video_warehouse"
    created: list[Path] = []
    for directory in (factory / "config", factory / "docs", warehouse / "projects", warehouse / "operations", warehouse / "reports"):
        directory.mkdir(parents=True, exist_ok=True)
    files = {
        factory / "config/style.json": {
            "schema_version": "1.0",
            "canvas": {"width": 720, "height": 960, "fps": 30},
            "brand": {"label": "YOUR BRAND", "title_font": "set a locally licensed font path before render"},
            "caption": {"mode": "bilingual", "safe_margin_px": 56},
            "release": {"default_version": "v4"},
        },
        factory / "config/voice_profile.example.json": {
            "schema_version": "1.0",
            "status": "configure_before_use",
            "mode": "voice_design_or_authorized_clone",
            "authorization_required": True,
            "note": "Do not add a voice recording to source control. Store user-authorized media outside this repository.",
        },
        factory / "docs/WORKSPACE_CONTRACT.md": {
            "schema_version": "1.0",
            "source_of_truth": "local release files",
            "chatcut": "optional derivative-editing layer; never overwrite the local master",
            "publish_requires": ["rights_review", "native_language_review", "human_publish_approval"],
        },
    }
    for path, payload in files.items():
        if write_json_if_missing(path, payload):
            created.append(path)
    readme = warehouse / "README.md"
    if write_text_if_missing(
        readme,
        "# Book video warehouse\n\n"
        "This directory is intentionally local-only. It may contain media, source evidence, provider usage, and account metadata. Do not publish it without a separate rights and privacy review.\n",
    ):
        created.append(readme)
    return created


def create_project(workspace: Path, slug: str, title: str, author: str) -> tuple[Path, list[Path]]:
    project = workspace / "book_video_warehouse" / "projects" / slug
    created: list[Path] = []
    for relative in PROJECT_DIRS:
        target = project / relative
        target.mkdir(parents=True, exist_ok=True)
        keep = target / ".gitkeep"
        if write_text_if_missing(keep, ""):
            created.append(keep)
    if write_json_if_missing(
        project / "project.json",
        {
            "schema_version": "1.0",
            "project_id": slug,
            "book": {"title": title, "author": author},
            "status": "initialized",
            "current_stage": "00_topic",
            "created_at": utc_now(),
            "release": {"version": "v4", "source_of_truth": "local_master"},
            "review": {
                "script": "pending",
                "cover_rights": "pending",
                "bgm_rights": "pending",
                "english_native_review": "pending",
                "publish": "pending",
            },
        },
    ):
        created.append(project / "project.json")
    if write_json_if_missing(
        project / "02_story_script" / "script.v2.bilingual.template.json",
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
        created.append(project / "02_story_script" / "script.v2.bilingual.template.json")
    if write_json_if_missing(
        project / "01_research" / "sources" / "cover" / "cover_manifest.template.json",
        {
            "status": "pending",
            "source_url": None,
            "source_file": None,
            "acquired_at": None,
            "rights_review": "pending",
            "reviewer": None,
        },
    ):
        created.append(project / "01_research" / "sources" / "cover" / "cover_manifest.template.json")
    if write_json_if_missing(
        project / "06_music" / "attribution.template.json",
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
        created.append(project / "06_music" / "attribution.template.json")
    return project, created


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a portable book-video workspace")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--slug", type=valid_slug)
    parser.add_argument("--book-title")
    parser.add_argument("--author")
    args = parser.parse_args()
    project_args = (args.slug, args.book_title, args.author)
    if any(project_args) and not all(project_args):
        parser.error("--slug, --book-title, and --author must be provided together")

    workspace = args.workspace.expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    created = bootstrap_workspace(workspace)
    payload: dict[str, Any] = {"workspace": str(workspace), "created": [str(path.relative_to(workspace)) for path in created]}
    if args.slug:
        project, project_created = create_project(workspace, args.slug, args.book_title, args.author)
        payload["project"] = str(project.relative_to(workspace))
        payload["project_created"] = [str(path.relative_to(workspace)) for path in project_created]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
