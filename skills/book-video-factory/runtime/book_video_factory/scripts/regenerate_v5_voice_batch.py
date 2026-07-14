#!/usr/bin/env python3
"""Regenerate clean V5 narration for every approved book-video project.

V4 delivery files contain a mixed narration/music track.  This command rebuilds
the approved Mandarin narration with the selected, locked brand voice so a new
music bed can be mixed without carrying old background audio forward.
"""

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


def project_paths(warehouse: Path, slugs: list[str]) -> list[Path]:
    root = warehouse / "projects"
    if slugs:
        projects = [root / slug for slug in slugs]
    else:
        projects = sorted(path for path in root.iterdir() if path.is_dir())
    return [path for path in projects if (path / "02_story_script_故事脚本/script.v2.bilingual.json").is_file()]


def write_manifest(output: Path, profile: dict, script: dict, sample_rate: int, samples: int) -> None:
    text = script["full_text"].strip()
    manifest = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "locked_for_v5_remix",
        "voice_profile": profile["profile_id"],
        "voice_mode": profile["mode"],
        "script_version": script["version"],
        "script_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "character_count": len(text),
        "duration_seconds": round(samples / sample_rate, 3),
        "sample_rate": sample_rate,
        "output": str(output),
        "generation": profile["generation"],
    }
    output.with_suffix(".generation.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate clean V5 brand-voice narration in one VoxCPM session")
    parser.add_argument("--warehouse", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--slug", action="append", default=[])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    ensure_voxcpm_runtime()
    import numpy as np
    import soundfile as sf
    import torch
    from voxcpm import VoxCPM

    profile_path = args.profile.resolve()
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    generation = profile["generation"]
    model = VoxCPM.from_pretrained(
        str(Path(generation["model_path"]).expanduser().resolve()),
        load_denoiser=bool(generation["load_denoiser"]),
        optimize=bool(generation["optimize"]),
        device=generation["device"],
        local_files_only=True,
    )

    created: list[dict[str, object]] = []
    for project in project_paths(args.warehouse.resolve(), args.slug):
        script_path = project / "02_story_script_故事脚本/script.v2.bilingual.json"
        script = json.loads(script_path.read_text(encoding="utf-8"))
        output = project / "05_voice_人声/v5-b-clean-master.wav"
        if output.exists() and not args.force:
            created.append({"project": project.name, "status": "skipped", "output": str(output)})
            continue

        np.random.seed(int(generation["seed"]))
        torch.manual_seed(int(generation["seed"]))
        wav = model.generate(**build_generation_request(profile, profile_path, script["full_text"]))
        output.parent.mkdir(parents=True, exist_ok=True)
        sf.write(output, wav, model.tts_model.sample_rate)
        write_manifest(output, profile, script, model.tts_model.sample_rate, len(wav))
        created.append(
            {
                "project": project.name,
                "status": "generated",
                "duration_seconds": round(len(wav) / model.tts_model.sample_rate, 3),
                "output": str(output),
            }
        )
        print(json.dumps(created[-1], ensure_ascii=False), flush=True)

    print(json.dumps({"total": len(created), "results": created}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
