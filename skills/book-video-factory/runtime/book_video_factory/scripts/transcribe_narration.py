#!/usr/bin/env python3
"""Create the exact Whisper word-timestamp JSON required by the V4 renderer."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe one narration WAV with word timestamps")
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default="turbo")
    parser.add_argument("--language", default="zh")
    args = parser.parse_args()
    audio = args.audio.resolve()
    output = args.out.resolve()
    if not audio.is_file():
        raise FileNotFoundError(audio)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="book-video-asr-") as temp_dir:
        temp = Path(temp_dir)
        subprocess.run([
            "whisper", str(audio), "--model", args.model, "--language", args.language,
            "--task", "transcribe", "--word_timestamps", "True", "--output_format", "json",
            "--output_dir", str(temp),
        ], check=True)
        generated = temp / f"{audio.stem}.json"
        if not generated.is_file():
            raise RuntimeError(f"Whisper did not create {generated.name}")
        payload = json.loads(generated.read_text(encoding="utf-8"))
    if not payload.get("segments"):
        raise RuntimeError("Whisper output contains no segments")
    if not any(segment.get("words") for segment in payload["segments"]):
        raise RuntimeError("Whisper output contains no word timestamps")
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"audio": str(audio), "asr": str(output), "segments": len(payload["segments"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
