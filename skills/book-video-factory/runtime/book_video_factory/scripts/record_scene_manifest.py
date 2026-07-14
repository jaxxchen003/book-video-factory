#!/usr/bin/env python3
"""Record the generated V4 scene inventory without mutating scene files."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import _bootstrap  # noqa: F401
from PIL import Image
from book_video_factory.scene_contract import V4_SCENE_LINE_CONTRACT


def main() -> int:
    parser = argparse.ArgumentParser(description="Write an auditable V4 scene manifest")
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    plan = json.loads((project / "03_images_生成图片/prompts/v4_scene_plan.json").read_text(encoding="utf-8"))
    scene_dir = project / "03_images_生成图片/approved/v4"
    assets = []
    for scene in plan["scenes"]:
        scene_id = scene["id"]
        expected_lines = list(V4_SCENE_LINE_CONTRACT.get(scene_id, ()))
        if scene.get("line_ids") != expected_lines:
            raise RuntimeError(
                f"{scene_id} line_ids diverge from the renderer scene contract: "
                f"expected {expected_lines}, got {scene.get('line_ids')}"
            )
        path = scene_dir / f"{scene_id}.png"
        if not path.is_file():
            raise FileNotFoundError(path)
        with Image.open(path) as image:
            dimensions = list(image.size)
        assets.append({
            "id": scene_id,
            "line_ids": expected_lines,
            "file": str(path.relative_to(project)), "dimensions": dimensions,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "prompt": scene["prompt"],
            "generator": "GPT Image 2 via Codex local image generation",
        })
    if len({asset["sha256"] for asset in assets}) != 12:
        raise RuntimeError("Scene manifest refuses duplicate V4 image bytes")
    payload = {
        "schema_version": "2.0",
        "scene_contract": "book-v4-scene-line-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "project_id": project.name,
        "assets": assets,
    }
    (scene_dir / "scene_manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"project": project.name, "assets": len(assets)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
