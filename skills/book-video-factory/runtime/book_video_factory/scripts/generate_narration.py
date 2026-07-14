#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import _bootstrap  # noqa: F401
from book_video_factory.voice import build_generation_request


DEFAULT_RUNTIME = Path.home() / ".local/share/voxcpm-py314/bin/python"


def ensure_voxcpm_runtime() -> None:
    try:
        import voxcpm  # noqa: F401
    except ImportError:
        if DEFAULT_RUNTIME.is_file() and Path(sys.executable) != DEFAULT_RUNTIME:
            os.execv(str(DEFAULT_RUNTIME), [str(DEFAULT_RUNTIME), __file__, *sys.argv[1:]])
        raise SystemExit("VoxCPM runtime is unavailable")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a versioned narration from an approved or draft script"
    )
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ensure_voxcpm_runtime()

    import numpy as np
    import soundfile as sf
    import torch
    from voxcpm import VoxCPM

    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    script = json.loads(args.script.read_text(encoding="utf-8"))
    generation = profile["generation"]
    text = script["full_text"].strip()
    model_path = Path(generation["model_path"]).expanduser().resolve()
    model = VoxCPM.from_pretrained(
        str(model_path),
        load_denoiser=bool(generation["load_denoiser"]),
        optimize=bool(generation["optimize"]),
        device=generation["device"],
        local_files_only=True,
    )
    seed = int(generation["seed"])
    np.random.seed(seed)
    torch.manual_seed(seed)
    request = build_generation_request(profile, args.profile.resolve(), text)
    wav = model.generate(**request)

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output, wav, model.tts_model.sample_rate)
    manifest = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "draft" if script.get("status") != "approved" else "approved_source",
        "voice_profile": profile["profile_id"],
        "voice_mode": profile["mode"],
        "script_version": script["version"],
        "script_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "character_count": len(text),
        "duration_seconds": round(len(wav) / model.tts_model.sample_rate, 3),
        "sample_rate": model.tts_model.sample_rate,
        "output": str(output),
        "generation": generation,
    }
    if profile["mode"] == "ultimate_clone":
        reference = Path(request["reference_wav_path"])
        manifest["clone"] = {
            "reference_audio": str(reference),
            "reference_sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
            "prompt_audio": request["prompt_wav_path"],
            "prompt_text": request["prompt_text"],
        }
    manifest_path = output.with_suffix(".generation.json")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
