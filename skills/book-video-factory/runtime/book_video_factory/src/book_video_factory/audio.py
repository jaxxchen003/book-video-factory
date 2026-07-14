from __future__ import annotations

import copy
from typing import Any


def splice_asr_timestamps(
    asr: dict[str, Any],
    *,
    cut_start: float,
    cut_end: float,
    inserted_silence: float,
) -> dict[str, Any]:
    """Move ASR timestamps to match a cut-and-insert edit.

    Audio in ``[cut_start, cut_end)`` is removed and replaced by a new silence
    block. Words crossing the left cut are trimmed there; words beginning at
    the right cut move after the inserted silence.
    """
    if cut_start < 0 or cut_end <= cut_start or inserted_silence < 0:
        raise ValueError("Invalid splice boundaries")

    shifted = copy.deepcopy(asr)
    delta = inserted_silence - (cut_end - cut_start)

    def move(value: float) -> float:
        if value <= cut_start:
            return value
        if value >= cut_end:
            return value + delta
        return cut_start

    for segment in shifted.get("segments", []):
        segment["start"] = round(move(float(segment["start"])), 3)
        segment["end"] = round(move(float(segment["end"])), 3)
        for word in segment.get("words", []):
            start = float(word["start"])
            end = float(word["end"])
            word["start"] = round(move(start), 3)
            if start < cut_start < end:
                word["end"] = round(cut_start, 3)
            else:
                word["end"] = round(move(end), 3)

    return shifted
