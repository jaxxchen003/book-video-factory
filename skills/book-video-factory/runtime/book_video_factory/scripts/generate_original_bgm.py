#!/usr/bin/env python3
"""Create a deterministic, project-owned ambient BGM without external samples."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
import wave
from datetime import UTC, datetime
from pathlib import Path

import _bootstrap  # noqa: F401


SAMPLE_RATE = 48_000


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def hash_seed(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:16], 16)


def build_wave(path: Path, duration: float, seed: int, mood: str) -> None:
    """Layer soft pads, a sparse bell motif, and shaped room tone.

    This is generated audio synthesis, not a remix: no recorded sample or
    third-party composition enters the file.
    """
    rng = random.Random(seed)
    frames = round(duration * SAMPLE_RATE)
    root_options = [146.83, 164.81, 174.61, 196.00, 220.00]
    root = root_options[seed % len(root_options)]
    brightness = {"calm": 0.72, "warm": 0.85, "reflective": 0.62, "tender": 0.78, "focused": 0.92}.get(mood, 0.75)
    motif = [0, 3, 7, 10, 7, 3, 5, 0]
    pcm = bytearray()
    previous_noise = 0.0
    for index in range(frames):
        t = index / SAMPLE_RATE
        fade = min(1.0, t / 1.8, (duration - t) / 2.2)
        pad = 0.0
        for ratio, gain, drift in ((1.0, 0.19, 0.0011), (1.4983, 0.11, 0.0017), (2.0, 0.052, 0.0007)):
            pad += gain * math.sin(2 * math.pi * root * ratio * (1 + drift * math.sin(t * 0.37)) * t)
        note_step = int(t / 2.55) % len(motif)
        semi = motif[note_step] + (12 if (int(t / 20) % 2) else 0)
        bell_freq = root * (2 ** (semi / 12)) * 2
        note_pos = (t % 2.55) / 2.55
        bell_env = math.exp(-note_pos * 5.8) * (0.25 if note_pos < 0.72 else 0.0)
        bell = bell_env * (0.13 * math.sin(2 * math.pi * bell_freq * t) + 0.038 * math.sin(2 * math.pi * bell_freq * 2.01 * t))
        raw_noise = rng.uniform(-1.0, 1.0)
        previous_noise = previous_noise * 0.985 + raw_noise * 0.015
        air = previous_noise * 0.018 * brightness
        duck = 0.80 + 0.18 * math.sin(2 * math.pi * 0.045 * t + (seed % 13))
        value = (pad * 0.52 + bell + air) * fade * duck
        # A slightly different second channel gives a subtle stereo field.
        left = max(-1.0, min(1.0, value))
        right = max(-1.0, min(1.0, value * 0.96 + 0.012 * math.sin(2 * math.pi * (root * 0.5) * t)))
        pcm.extend(int(left * 32767).to_bytes(2, "little", signed=True))
        pcm.extend(int(right * 32767).to_bytes(2, "little", signed=True))
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate project-specific original ambient BGM")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--mood", default="reflective", choices=["calm", "warm", "reflective", "tender", "focused"])
    parser.add_argument("--duration", type=float, default=75.0)
    args = parser.parse_args()
    project = args.project.resolve()
    project_meta = json.loads((project / "project.json").read_text(encoding="utf-8"))
    slug = project_meta["project_id"]
    music_dir = project / "06_music_音乐"
    music_dir.mkdir(parents=True, exist_ok=True)
    for old in music_dir.glob("v4-*-original-bgm.mp3"):
        old.unlink()
    output = music_dir / f"v4-{slug}-original-bgm.mp3"
    temporary_wave = music_dir / f".{slug}-original-bgm.tmp.wav"
    seed = hash_seed(f"{slug}:{args.mood}:v1")
    build_wave(temporary_wave, args.duration, seed, args.mood)
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(temporary_wave),
        "-c:a", "libmp3lame", "-b:a", "192k", str(output),
    ], check=True)
    temporary_wave.unlink(missing_ok=True)
    sha256 = hashlib.sha256(output.read_bytes()).hexdigest()
    metadata = {
        "schema_version": "1.0",
        "title": f"{slug} — original procedural ambient",
        "artist": "Book Video Factory local procedural generator",
        "duration_seconds": args.duration,
        "mood": args.mood,
        "generator": "book_video_factory/scripts/generate_original_bgm.py",
        "seed": seed,
        "generated_at": datetime.now(UTC).isoformat(),
        "license": "Channel-owned original composition; no third-party recordings or samples.",
        "rights_status": "channel_owned_original",
        "source_page": "local://book_video_factory/scripts/generate_original_bgm.py",
        "file": str(output.relative_to(project)),
        "sha256": sha256,
        "required_attribution": "No external attribution required.",
    }
    write_json(music_dir / "bgm_license.json", metadata)
    (music_dir / "ATTRIBUTION.txt").write_text(
        "Original procedural ambient BGM generated locally for this project. No third-party samples or attribution required.\n",
        encoding="utf-8",
    )
    print(json.dumps({"bgm": str(output), "sha256": sha256, "seed": seed}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
