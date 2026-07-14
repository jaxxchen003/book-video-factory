#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_RUNTIME = Path.home() / ".local/share/voxcpm-py314/bin/python"


def ensure_voxcpm_runtime() -> None:
    try:
        import voxcpm  # noqa: F401
    except ImportError:
        if DEFAULT_RUNTIME.is_file() and Path(sys.executable) != DEFAULT_RUNTIME:
            os.execv(str(DEFAULT_RUNTIME), [str(DEFAULT_RUNTIME), __file__, *sys.argv[1:]])
        raise SystemExit("VoxCPM runtime is unavailable")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate VoxCPM2 brand-voice auditions")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    ensure_voxcpm_runtime()

    import numpy as np
    import soundfile as sf
    import torch
    from voxcpm import VoxCPM

    config = json.loads(args.config.read_text(encoding="utf-8"))
    generation = config["generation"]
    model_path = Path(config["model_path"]).expanduser().resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    model = VoxCPM.from_pretrained(
        str(model_path),
        load_denoiser=generation["load_denoiser"],
        optimize=generation["optimize"],
        device=generation["device"],
        local_files_only=True,
    )

    outputs = []
    for candidate in config["candidates"]:
        seed = int(candidate["seed"])
        np.random.seed(seed)
        torch.manual_seed(seed)
        final_text = f"({candidate['control']}){config['sample_text']}"
        wav = model.generate(
            text=final_text,
            cfg_value=float(generation["cfg_value"]),
            inference_timesteps=int(generation["inference_timesteps"]),
        )
        output = output_dir / f"{candidate['id']}.wav"
        sf.write(output, wav, model.tts_model.sample_rate)
        outputs.append(
            {
                "id": candidate["id"],
                "label": candidate["label"],
                "recommended": candidate["recommended"],
                "control": candidate["control"],
                "seed": seed,
                "path": str(output),
                "duration_seconds": round(len(wav) / model.tts_model.sample_rate, 3),
                "sample_rate": model.tts_model.sample_rate,
            }
        )
        print(f"generated {candidate['label']}: {output}", flush=True)

    manifest = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": config["model"],
        "model_path": str(model_path),
        "sample_text": config["sample_text"],
        "generation": generation,
        "selected_voice": None,
        "outputs": outputs,
    }
    (output_dir / "audition_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
