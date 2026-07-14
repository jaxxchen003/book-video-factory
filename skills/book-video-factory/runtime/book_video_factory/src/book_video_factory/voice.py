from __future__ import annotations

from pathlib import Path
from typing import Any


class VoiceProfileError(ValueError):
    pass


def resolve_profile_path(profile_path: Path, configured_path: str) -> Path:
    path = Path(configured_path).expanduser()
    if not path.is_absolute():
        path = profile_path.resolve().parent / path
    return path.resolve()


def build_generation_request(
    profile: dict[str, Any], profile_path: Path, text: str
) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise VoiceProfileError("Narration text is empty")

    generation = profile["generation"]
    request: dict[str, Any] = {
        "text": text,
        "cfg_value": float(generation["cfg_value"]),
        "inference_timesteps": int(generation["inference_timesteps"]),
    }
    mode = profile.get("mode")

    if mode == "voice_design":
        control = str(profile.get("control", "")).strip()
        request["text"] = f"({control}){text}" if control else text
        return request

    if mode == "ultimate_clone":
        clone = profile.get("clone")
        if not isinstance(clone, dict):
            raise VoiceProfileError("Ultimate clone profile is missing clone settings")
        reference = resolve_profile_path(profile_path, str(clone["reference_audio"]))
        prompt_audio = resolve_profile_path(
            profile_path, str(clone.get("prompt_audio") or clone["reference_audio"])
        )
        prompt_text = str(clone.get("prompt_text", "")).strip()
        if not reference.is_file():
            raise VoiceProfileError(f"Reference audio not found: {reference}")
        if not prompt_audio.is_file():
            raise VoiceProfileError(f"Prompt audio not found: {prompt_audio}")
        if not prompt_text:
            raise VoiceProfileError("Ultimate clone profile is missing prompt_text")
        request.update(
            {
                "reference_wav_path": str(reference),
                "prompt_wav_path": str(prompt_audio),
                "prompt_text": prompt_text,
            }
        )
        return request

    raise VoiceProfileError(f"Unsupported voice profile mode: {mode!r}")
