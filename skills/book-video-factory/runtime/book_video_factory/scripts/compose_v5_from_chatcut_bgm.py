#!/usr/bin/env python3
"""Create a corrected book-video release from the approved V4 visual contract
and a ChatCut-generated BGM file.

The V4 base is intentionally a silent, text-free timeline.  The V4 manifest
therefore remains the visual contract: its title, bilingual-caption overlays,
rapid topic montage timings, locked paused narration and user-approved H2
stinger are restored exactly.  Only the old BGM is replaced.
"""

from __future__ import annotations

import argparse
import copy
import os
import json
import shutil
from pathlib import Path

import _bootstrap  # noqa: F401
import build_batch_video_v3 as batch
import build_final_video_v2 as v2


AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")
FACTORY = Path(__file__).resolve().parents[1]
STYLE_PATH = FACTORY / "config/video_style_v2.json"


def find_bgm(music_dir: Path) -> Path | None:
    candidates = sorted(
        path
        for path in music_dir.iterdir()
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    ) if music_dir.exists() else []
    if len(candidates) > 1:
        raise RuntimeError(f"{music_dir} contains more than one V5 music file")
    return candidates[0] if candidates else None


def v4_visual_contract(
    project: Path, title_override: Path | None = None
) -> tuple[Path, Path, Path, list[dict[str, object]], float, float, float]:
    """Read the already-approved V4 timing/overlay contract without rerendering it."""
    timeline_dir = project / "07_timeline_时间线" / "v4"
    manifest = json.loads((timeline_dir / "render_manifest.v4.json").read_text(encoding="utf-8"))
    base = timeline_dir / "base-v2-3x4.mp4"
    voice = project / str(manifest["voice"])
    stinger = project / str(manifest["intro_sfx"]["file"])
    voice_duration = float(manifest["voice_duration_seconds"])
    montage_start = float(manifest["montage"]["start"])
    montage_end = float(manifest["montage"]["end"])
    total_duration = float(manifest["timeline"][-1]["end"])
    overlay_dir = timeline_dir / "overlays" / "bilingual-3x4"
    overlays: list[dict[str, object]] = [
        {"path": title_override or overlay_dir / "title.png", "start": montage_end, "end": voice_duration, "kind": "title"},
        {"path": overlay_dir / "brand.png", "start": 0.0, "end": total_duration, "kind": "brand"},
    ]
    for line in manifest["lines"]:
        overlays.append(
            {
                "path": overlay_dir / f"{line['line_id']}.png",
                "start": float(line["start"]),
                "end": float(line["end"]),
                "kind": "caption",
                "line_id": line["line_id"],
            }
        )
    required = [base, voice, stinger, *(Path(item["path"]) for item in overlays)]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"V4 visual contract is incomplete: {missing}")
    return base, voice, stinger, overlays, total_duration, montage_start, montage_end


def v5_style() -> dict:
    """Keep V4's editorial mix while starting the new BGM at the opening frame."""
    style = copy.deepcopy(json.loads(STYLE_PATH.read_text(encoding="utf-8")))
    style["audio"].update(
        {
            "bgm_start_offset_seconds": 0.0,
            "bgm_target_lufs": -22.0,
            "montage_boost_db": 14.0,
            "final_target_lufs": -16.0,
            "true_peak_dbfs": -1.5,
        }
    )
    return style


def release_title_overlay(project: Path, release_label: str) -> tuple[Path, Path]:
    style = v5_style()
    batch.validate_style_profile(style)
    script = json.loads(
        (project / "02_story_script_故事脚本/script.v2.bilingual.json").read_text(
            encoding="utf-8"
        )
    )
    output_dir = project / "07_timeline_时间线" / release_label / "overlays/bilingual-3x4"
    output_dir.mkdir(parents=True, exist_ok=True)
    title_path = output_dir / "title.png"
    layout_path = output_dir / "title.layout.json"
    layer, layout = batch.build_title_layer(
        style,
        script["book"]["title"],
        script["book"]["author"],
        batch.WIDTH,
        batch.HEIGHT,
    )
    layer.save(title_path)
    batch.write_json(layout_path, layout)
    return title_path, layout_path


def compose(project: Path, force: bool, release_label: str) -> tuple[str, str]:
    slug = project.name
    music = find_bgm(project / "06_music_音乐" / "v5")
    target_dir = project / "08_render_合成" / release_label
    target = target_dir / f"{slug}-{release_label}-bilingual-3x4.mp4"
    delivery_dir = project / "10_delivery_交付" / release_label
    delivery = delivery_dir / target.name
    manifest = target_dir / f"{slug}-{release_label}-manifest.json"

    if music is None:
        return slug, "waiting for ChatCut BGM in 06_music_音乐/v5"
    if target.exists() and not force:
        return slug, f"kept existing {target.name}"

    title_overlay, title_layout = release_title_overlay(project, release_label)
    base, voice, stinger, overlays, duration, montage_start, montage_end = v4_visual_contract(
        project, title_override=title_overlay
    )

    target_dir.mkdir(parents=True, exist_ok=True)
    # The V4 renderer is reused because it correctly holds the final visual
    # frame through the outro and applies all timing-accurate PNG overlays.
    v2.render_variant(
        base,
        overlays,
        voice,
        music,
        stinger,
        duration,
        montage_start,
        montage_end,
        target,
        720,
        960,
        v5_style(),
    )
    delivery_dir.mkdir(parents=True, exist_ok=True)
    if delivery.exists():
        delivery.unlink()
    os.link(target, delivery)
    subtitle_source = project / "07_timeline_时间线" / "v4" / "subtitles.v2.bilingual.srt"
    if subtitle_source.is_file():
        shutil.copy2(subtitle_source, delivery_dir / f"subtitles.{release_label}.bilingual.srt")
    payload = {
        "version": f"{release_label}-chatcut-bgm-editorial-repair",
        "visual_base": str(base),
        "visual_contract": "release-specific safe title plus V4 brand, bilingual captions, and montage timing",
        "title_overlay": str(title_overlay),
        "title_layout": str(title_layout),
        "voice": str(voice),
        "chatcut_bgm": str(music),
        "intro_sfx": str(stinger),
        "output": str(target),
        "delivery": str(delivery),
        "duration_seconds": duration,
        "mix": {
            "bgm_starts_at_seconds": 0,
            "ducking": "sidechaincompress ratio 4:1",
            "montage_h2_sfx": True,
            "target_loudness": "-16 LUFS",
        },
    }
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return slug, f"rendered {target.name}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", type=Path, required=True)
    parser.add_argument("--projects", nargs="*", help="optional project slugs")
    parser.add_argument("--release-label", default="v5.1")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    projects_dir = args.warehouse / "projects"
    selected = set(args.projects or [])
    projects = [
        path for path in sorted(projects_dir.iterdir())
        if path.is_dir()
        and (not selected or path.name in selected)
        and (path / "07_timeline_时间线" / "v4" / "render_manifest.v4.json").is_file()
    ]
    known = {path.name for path in projects_dir.iterdir() if path.is_dir()}
    unknown = selected - known
    if unknown:
        raise SystemExit(f"unknown project(s): {', '.join(sorted(unknown))}")

    completed = 0
    for project in projects:
        slug, state = compose(project, args.force, args.release_label)
        print(f"{slug}: {state}")
        completed += state.startswith("rendered")
    print(f"completed={completed}/{len(projects)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
