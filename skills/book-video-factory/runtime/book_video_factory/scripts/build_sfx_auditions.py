#!/usr/bin/env python3
"""Build short intro-SFX auditions with the approved voice and current BGM."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path


WINDOW_START = 2.5
WINDOW_DURATION = 5.5
MONTAGE_START = 4.52
MONTAGE_END = 5.48
BGM_OFFSET = 18.0


@dataclass(frozen=True)
class Audition:
    name: str
    source: str | None
    effect_filter: str | None
    anchor: float = MONTAGE_START


AUDITIONS = [
    Audition(
        "A-电影感快速whoosh-情境试听.mp3",
        "A-电影感快速whoosh.mp3",
        "atrim=0:1.334,asetpts=PTS-STARTPTS,atempo=1.3896,afade=t=out:st=0.88:d=0.08,volume=0.78",
    ),
    Audition(
        "B-短促riser-情境试听.mp3",
        "B-短促riser.mp3",
        "atrim=1.615:2.575,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.04,volume=0.78",
    ),
    Audition(
        "C-磁带倒带-情境试听.mp3",
        "C-磁带倒带.mp3",
        "atrim=0:4.389,asetpts=PTS-STARTPTS,atempo=4.572,afade=t=out:st=0.88:d=0.08,volume=0.72",
    ),
    Audition(
        "D-心跳转场-情境试听.mp3",
        "D-心跳转场.mp3",
        "atrim=0:3.84,asetpts=PTS-STARTPTS,atempo=4.0,afade=t=out:st=0.88:d=0.08,volume=0.70",
    ),
    Audition(
        "E-水晶提示音落书封-情境试听.mp3",
        "E-水晶提示音.mp3",
        "atrim=0:1.8,asetpts=PTS-STARTPTS,afade=t=out:st=1.45:d=0.30,volume=0.48",
        MONTAGE_END,
    ),
    Audition(
        "F-低频电影落点-情境试听.mp3",
        "F-低频电影落点.mp3",
        "atrim=0:2.2,asetpts=PTS-STARTPTS,afade=t=out:st=1.55:d=0.60,volume=0.38",
        MONTAGE_END,
    ),
    Audition("G-不加额外音效仅BGM-情境试听.mp3", None, None),
    Audition(
        "H1-原片快切音效去中心人声-情境试听.mp3",
        "../reference-original/H1-原片快切段去中心人声.wav",
        "atrim=0:0.96,asetpts=PTS-STARTPTS,afade=t=out:st=0.88:d=0.08,volume=0.76",
    ),
    Audition(
        "H2-原片快切高频音效层-情境试听.mp3",
        "../reference-original/H2-原片快切段高频音效层.wav",
        "atrim=0:0.96,asetpts=PTS-STARTPTS,afade=t=out:st=0.88:d=0.08,volume=0.70",
    ),
]


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def build(project: Path, audition_root: Path) -> None:
    voice = project / "05_voice_人声/v2-approved-b-locked-master-tickfix.wav"
    bgm = project / "06_music_音乐/Long Road Ahead B.mp3"
    raw = audition_root / "raw"
    output = audition_root / "context"
    output.mkdir(parents=True, exist_ok=True)

    local_montage_start = MONTAGE_START - WINDOW_START
    local_montage_end = MONTAGE_END - WINDOW_START
    bgm_start = BGM_OFFSET + WINDOW_START
    bgm_end = bgm_start + WINDOW_DURATION
    montage_boost = 10 ** (8.0 / 20)

    for audition in AUDITIONS:
        command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(voice), "-i", str(bgm)]
        filters = [
            f"[0:a]atrim={WINDOW_START:.3f}:{WINDOW_START + WINDOW_DURATION:.3f},asetpts=PTS-STARTPTS,asplit=2[voice_sc][voice_mix]",
            f"[1:a]atrim={bgm_start:.3f}:{bgm_end:.3f},asetpts=PTS-STARTPTS,loudnorm=I=-22:LRA=8:TP=-2,volume='if(between(t,{local_montage_start:.3f},{local_montage_end:.3f}),{montage_boost:.4f},1.0)'[bed]",
            "[bed][voice_sc]sidechaincompress=threshold=0.035:ratio=4:attack=10:release=320[ducked]",
        ]
        if audition.source and audition.effect_filter:
            command.extend(["-i", str(raw / audition.source)])
            delay = round((audition.anchor - WINDOW_START) * 1000)
            filters.extend(
                [
                    f"[2:a]{audition.effect_filter},adelay={delay}|{delay}[effect]",
                    "[ducked][voice_mix][effect]amix=inputs=3:duration=first:normalize=0,loudnorm=I=-15:LRA=8:TP=-1.2[out]",
                ]
            )
        else:
            filters.append("[ducked][voice_mix]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-15:LRA=8:TP=-1.2[out]")
        command.extend(
            [
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[out]",
                "-t",
                f"{WINDOW_DURATION:.3f}",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                str(output / audition.name),
            ]
        )
        run(command)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("audition_root", type=Path)
    args = parser.parse_args()
    build(args.project.resolve(), args.audition_root.resolve())


if __name__ == "__main__":
    main()
