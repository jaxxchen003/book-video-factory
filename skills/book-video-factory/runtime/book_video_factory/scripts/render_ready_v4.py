#!/usr/bin/env python3
"""Render only V4 projects whose independently produced assets are complete."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def ready(project: Path) -> bool:
    scenes = project / "03_images_生成图片/approved/v4"
    images = [scenes / f"S{index:02d}.png" for index in range(1, 13)]
    return (
        all(path.is_file() for path in images)
        and (project / "05_voice_人声/v3-b-locked-master.wav").is_file()
        and (project / "05_voice_人声/asr-v3/v3-b-locked-master.json").is_file()
        and len(list((project / "06_music_音乐").glob("v4-*-original-bgm.mp3"))) == 1
        and (project / "01_research_资料搜集/sources/cover/cover_manifest.json").is_file()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Render ready V4 projects without touching incomplete ones")
    parser.add_argument("--warehouse", type=Path, required=True)
    parser.add_argument("--slug", action="append", default=[])
    parser.add_argument(
        "--release-id",
        help="Bind generated QC reports to this release ID. Required before publish approval.",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    warehouse = args.warehouse.resolve()
    candidates = [warehouse / "projects" / slug for slug in args.slug] if args.slug else sorted((warehouse / "projects").glob("*"))
    rendered = []
    skipped = []
    for project in candidates:
        if not (project / "project.json").is_file():
            continue
        target = project / f"10_delivery_交付/v4/{project.name}-v4-bilingual-3x4.mp4"
        if target.is_file() and not args.force:
            skipped.append(f"{project.name}:already_rendered")
            continue
        if not ready(project):
            skipped.append(f"{project.name}:assets_incomplete")
            continue
        subprocess.run(["python3", "book_video_factory/scripts/build_batch_video_v3.py", str(project), "--release-version", "v4"], check=True)
        qc_command = [
            "python3",
            "book_video_factory/scripts/v4_post_qc.py",
            "--project",
            str(project),
        ]
        if args.release_id:
            qc_command.extend(["--release-id", args.release_id])
        subprocess.run(qc_command, check=True)
        rendered.append(project.name)
    print("rendered=" + ",".join(rendered))
    print("skipped=" + ",".join(skipped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
