#!/usr/bin/env python3
"""Run a release-aware gate after the V4 renderer's technical smoke check."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def probe(path: Path) -> dict:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path),
    ], check=True, text=True, capture_output=True)
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a V4 local master and release constraints")
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    meta = read_json(project / "project.json")
    slug = meta["project_id"]
    script = read_json(project / "02_story_script_故事脚本/script.v2.bilingual.json")
    scene_dir = project / "03_images_生成图片/approved/v4"
    scenes = [scene_dir / f"S{index:02d}.png" for index in range(1, 13)]
    scene_ok = all(path.is_file() for path in scenes)
    scene_hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in scenes if path.is_file()]
    cover_manifest = read_json(project / "01_research_资料搜集/sources/cover/cover_manifest.json")
    cover_file = project / cover_manifest["local_file"]
    bgms = list((project / "06_music_音乐").glob("v4-*-original-bgm.mp3"))
    bgm_manifest = read_json(project / "06_music_音乐/bgm_license.json")
    voice = project / "05_voice_人声/v3-b-locked-master.wav"
    asr = read_json(project / "05_voice_人声/asr-v3/v3-b-locked-master.json")
    local_master = project / f"10_delivery_交付/v4/{slug}-v4-bilingual-3x4.mp4"
    media = probe(local_master) if local_master.is_file() else {"streams": []}
    video = next((stream for stream in media["streams"] if stream.get("codec_type") == "video"), {})
    audio = next((stream for stream in media["streams"] if stream.get("codec_type") == "audio"), {})
    technical_checks = {
        "fifteen_bilingual_lines": len(script.get("lines", [])) == 15 and all(line.get("zh") and line.get("en") for line in script.get("lines", [])),
        "twelve_unique_topic_scenes": scene_ok and len(set(scene_hashes)) == 12,
        "real_cover_source_recorded": cover_file.is_file() and bool(cover_manifest.get("source_url")),
        "one_original_project_bgm": len(bgms) == 1 and bgm_manifest.get("rights_status") == "channel_owned_original",
        "voice_and_word_asr_present": voice.is_file() and bool(asr.get("segments")) and any(segment.get("words") for segment in asr.get("segments", [])),
        "delivery_video_h264_aac_720x960": video.get("width") == 720 and video.get("height") == 960 and audio.get("codec_name") == "aac",
    }
    technical_pass = all(technical_checks.values())
    release_holds = []
    if script.get("translation_status") != "native_approved":
        release_holds.append("English captions need native-language review before public distribution.")
    if cover_manifest.get("rights_status") != "cleared_for_public_release":
        release_holds.append("Book-cover reuse needs platform/publisher rights review before public commercial release.")
    release_holds.append("User-supplied H2 intro audio needs an external rights clearance record before public distribution.")
    report = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "project_id": slug,
        "local_master_status": "pass" if technical_pass else "fail",
        "public_release_allowed": technical_pass and not release_holds,
        "technical_checks": technical_checks,
        "release_holds": release_holds,
        "output": str(local_master.relative_to(project)),
    }
    out = project / "09_qc_质检/v4_release_gate.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"project": slug, "local_master": report["local_master_status"], "public_release_allowed": report["public_release_allowed"]}, ensure_ascii=False))
    return 0 if technical_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
