#!/usr/bin/env python3
"""Regenerate traceable title overlays without rebuilding the V4 base timeline."""

from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
import build_batch_video_v3 as renderer


def refresh(project: Path, style: dict, source_release: str, target_release: str) -> str:
    script_path = project / "02_story_script_故事脚本/script.v2.bilingual.json"
    source_dir = project / f"07_timeline_时间线/{source_release}/overlays/bilingual-3x4"
    overlay_dir = project / f"07_timeline_时间线/{target_release}/overlays/bilingual-3x4"
    if not script_path.is_file() or not source_dir.is_dir():
        return "skipped_missing_script_or_overlay_dir"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    script = renderer.read_json(script_path)
    layer, manifest = renderer.build_title_layer(
        style,
        script["book"]["title"],
        script["book"]["author"],
        renderer.WIDTH,
        renderer.HEIGHT,
    )
    layer.save(overlay_dir / "title.png")
    renderer.write_json(overlay_dir / "title.layout.json", manifest)
    return "refreshed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warehouse", type=Path, required=True)
    parser.add_argument("--style", type=Path, default=renderer.STYLE_PATH)
    parser.add_argument("--source-release", default="v4")
    parser.add_argument("--target-release", default="v5.2")
    parser.add_argument("--projects", nargs="*")
    args = parser.parse_args()

    style = renderer.read_json(args.style.resolve())
    renderer.validate_style_profile(style)
    projects_dir = args.warehouse.resolve() / "projects"
    selected = set(args.projects or [])
    projects = [
        path
        for path in sorted(projects_dir.iterdir())
        if path.is_dir() and (not selected or path.name in selected)
    ]
    refreshed = 0
    for project in projects:
        result = refresh(project, style, args.source_release, args.target_release)
        print(f"{project.name}: {result}")
        refreshed += result == "refreshed"
    print(f"refreshed={refreshed}/{len(projects)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
