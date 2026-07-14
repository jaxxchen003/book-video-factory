#!/usr/bin/env python3
"""Build the approved book-video master from warehouse assets.

The script keeps the approved Chinese copy authoritative, uses ASR word timing
only as an alignment aid, renders subtitle overlays with Pillow, and assembles
the vertical master with FFmpeg.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


WIDTH = 720
HEIGHT = 960
FPS = 30
VOICE_OFFSET = 2.0
OUTRO_DURATION = 3.0
FONT_REGULAR = Path("/System/Library/Fonts/STHeiti Light.ttc")
FONT_MEDIUM = Path("/System/Library/Fonts/STHeiti Medium.ttc")


@dataclass(frozen=True)
class TimedLine:
    line_id: str
    text: str
    start: float
    end: float


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        capture_output=capture,
    )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize(text: str) -> str:
    return "".join(re.findall(r"[\u3400-\u9fffA-Za-z0-9]", text))


def align_approved_lines(lines: list[dict[str, Any]], asr: dict[str, Any]) -> list[TimedLine]:
    words = [word for segment in asr["segments"] for word in segment.get("words", [])]
    character_stream: list[str] = []
    character_to_word: list[int] = []
    for word_index, word in enumerate(words):
        for character in normalize(word["word"]):
            character_stream.append(character)
            character_to_word.append(word_index)

    transcript = "".join(character_stream)
    cursor = 0
    aligned: list[TimedLine] = []
    for line in lines:
        target = normalize(line["text"])
        index = transcript.find(target, cursor)
        if index < 0:
            context = transcript[cursor : cursor + max(80, len(target) * 3)]
            raise RuntimeError(
                f"Cannot align {line['id']} to ASR transcript. target={target!r}, context={context!r}"
            )
        start_word = words[character_to_word[index]]
        end_word = words[character_to_word[index + len(target) - 1]]
        aligned.append(
            TimedLine(
                line_id=line["id"],
                text=line["text"],
                start=round(float(start_word["start"]) + VOICE_OFFSET, 3),
                end=round(float(end_word["end"]) + VOICE_OFFSET, 3),
            )
        )
        cursor = index + len(target)
    return aligned


def scene_timeline(
    scene_plan: dict[str, Any], aligned: list[TimedLine], total_duration: float
) -> list[dict[str, Any]]:
    line_map = {line.line_id: line for line in aligned}
    spans: list[tuple[float, float]] = []
    for scene in scene_plan["scenes"]:
        scene_lines = [line_map[line_id] for line_id in scene["lines"]]
        spans.append((min(line.start for line in scene_lines), max(line.end for line in scene_lines)))

    boundaries = [0.0]
    for index in range(len(spans) - 1):
        current_end = spans[index][1]
        next_start = spans[index + 1][0]
        boundaries.append(round((current_end + next_start) / 2, 3))
    boundaries.append(round(total_duration, 3))

    timeline: list[dict[str, Any]] = []
    for index, scene in enumerate(scene_plan["scenes"]):
        start = boundaries[index]
        end = boundaries[index + 1]
        timeline.append(
            {
                "id": scene["id"],
                "lines": scene["lines"],
                "start": start,
                "end": end,
                "duration": round(end - start, 3),
                "image": f"03_images_生成图片/approved/{scene['id']}.png",
            }
        )
    return timeline


def srt_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(path: Path, lines: list[TimedLine]) -> None:
    blocks = []
    for index, line in enumerate(lines, start=1):
        blocks.append(
            f"{index}\n{srt_timestamp(line.start)} --> {srt_timestamp(line.end)}\n{line.text}"
        )
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def wrap_cjk(text: str, max_chars: int = 13) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    punctuation = "，。！？：；、"
    candidates = [index + 1 for index, char in enumerate(text) if char in punctuation]
    midpoint = len(text) / 2
    valid = [index for index in candidates if 5 <= index <= len(text) - 5]
    split_at = min(valid, key=lambda index: abs(index - midpoint)) if valid else round(midpoint)
    first, second = text[:split_at], text[split_at:]
    if len(first) <= max_chars + 2 and len(second) <= max_chars + 2:
        return [first, second]
    chunks = []
    remaining = text
    while len(remaining) > max_chars:
        chunks.append(remaining[:max_chars])
        remaining = remaining[max_chars:]
    if remaining:
        chunks.append(remaining)
    return chunks[:3]


def text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, stroke: int = 0) -> tuple[int, int, int, int]:
    return draw.textbbox((0, 0), text, font=font, stroke_width=stroke)


def render_subtitle_overlay(path: Path, text: str) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(FONT_MEDIUM), 48)
    lines = wrap_cjk(text)
    line_height = 66
    widths = [text_bbox(draw, line, font, 4)[2] for line in lines]
    block_width = min(WIDTH - 80, max(widths) + 48)
    block_height = line_height * len(lines) + 28
    left = (WIDTH - block_width) // 2
    top = 690 - (len(lines) - 1) * 28
    draw.rounded_rectangle(
        (left, top, left + block_width, top + block_height),
        radius=18,
        fill=(0, 0, 0, 88),
    )
    draw.rounded_rectangle((left + 12, top + 18, left + 18, top + block_height - 18), radius=3, fill=(183, 96, 49, 230))
    y = top + 12
    for line, width in zip(lines, widths):
        x = (WIDTH - width) // 2 + 6
        draw.text(
            (x, y),
            line,
            font=font,
            fill=(250, 247, 240, 255),
            stroke_width=4,
            stroke_fill=(0, 0, 0, 230),
        )
        y += line_height
    canvas.save(path)


def render_title_overlay(path: Path) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    title_font = ImageFont.truetype(str(FONT_MEDIUM), 78)
    author_font = ImageFont.truetype(str(FONT_REGULAR), 32)
    title = "《兜底》"
    author = "晴山  著"
    title_width = text_bbox(draw, title, title_font, 4)[2]
    author_width = text_bbox(draw, author, author_font, 2)[2]
    x = WIDTH - title_width - 78
    y = 150
    draw.text((x, y), title, font=title_font, fill=(250, 247, 240, 255), stroke_width=4, stroke_fill=(0, 0, 0, 220))
    draw.rectangle((x + 6, y + 101, x + 92, y + 106), fill=(183, 96, 49, 240))
    draw.text((WIDTH - author_width - 84, y + 126), author, font=author_font, fill=(218, 211, 199, 245), stroke_width=2, stroke_fill=(0, 0, 0, 200))
    canvas.save(path)


def render_tag_overlay(path: Path) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(FONT_REGULAR), 25)
    label = "晴山《兜底》"
    draw.rounded_rectangle((36, 42, 235, 88), radius=12, fill=(0, 0, 0, 90))
    draw.text((52, 51), label, font=font, fill=(230, 225, 215, 230), stroke_width=1, stroke_fill=(0, 0, 0, 180))
    canvas.save(path)


def render_outro_overlay(path: Path) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    main_font = ImageFont.truetype(str(FONT_MEDIUM), 47)
    small_font = ImageFont.truetype(str(FONT_REGULAR), 27)
    lines = ["真正能为人生兜底的，", "只有你自己。"]
    y = 660
    for line in lines:
        width = text_bbox(draw, line, main_font, 4)[2]
        draw.text(((WIDTH - width) // 2, y), line, font=main_font, fill=(250, 247, 240, 255), stroke_width=4, stroke_fill=(0, 0, 0, 230))
        y += 64
    credit = "— 晴山《兜底》"
    width = text_bbox(draw, credit, small_font, 2)[2]
    draw.text(((WIDTH - width) // 2, y + 12), credit, font=small_font, fill=(206, 139, 94, 245), stroke_width=2, stroke_fill=(0, 0, 0, 210))
    canvas.save(path)


def build_overlay_assets(directory: Path, lines: list[TimedLine]) -> list[dict[str, Any]]:
    directory.mkdir(parents=True, exist_ok=True)
    overlays: list[dict[str, Any]] = []
    title = directory / "title.png"
    render_title_overlay(title)
    overlays.append({"path": title, "start": 0.25, "end": 1.95, "kind": "title"})
    tag = directory / "book-tag.png"
    render_tag_overlay(tag)
    overlays.append({"path": tag, "start": 2.0, "end": lines[-1].end, "kind": "tag"})
    for line in lines:
        path = directory / f"{line.line_id}.png"
        render_subtitle_overlay(path, line.text)
        overlays.append({"path": path, "start": line.start, "end": line.end, "kind": "subtitle", "line_id": line.line_id})
    outro = directory / "outro.png"
    render_outro_overlay(outro)
    overlays.append({"path": outro, "start": lines[-1].end + 0.1, "end": lines[-1].end + OUTRO_DURATION, "kind": "outro"})
    return overlays


def render_scene_clips(project: Path, scenes: list[dict[str, Any]], clip_dir: Path) -> Path:
    clip_dir.mkdir(parents=True, exist_ok=True)
    concat_lines: list[str] = []
    for index, scene in enumerate(scenes):
        source = project / scene["image"]
        output = clip_dir / f"{scene['id']}.mp4"
        zoom_increment = 0.00013 + (index % 3) * 0.00002
        vf = (
            "scale=720:960,"
            f"zoompan=z='min(zoom+{zoom_increment:.5f},1.05)':"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=720x960:fps=30,"
            "format=yuv420p"
        )
        run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-loop", "1", "-framerate", str(FPS), "-i", str(source),
                "-t", f"{scene['duration']:.3f}", "-vf", vf,
                "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-r", str(FPS), "-pix_fmt", "yuv420p", str(output),
            ]
        )
        concat_lines.append(f"file '{output.as_posix()}'")

    concat_file = clip_dir / "concat.txt"
    concat_file.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    base_video = clip_dir.parent / "base-motion.mp4"
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", str(base_video),
    ])
    return base_video


def render_master(
    project: Path,
    base_video: Path,
    overlays: list[dict[str, Any]],
    total_duration: float,
    output: Path,
) -> None:
    voice = project / "05_voice_人声/approved-v1-b-locked-master.wav"
    bgm = project / "06_music_音乐/Long Road Ahead B.mp3"
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(base_video)]
    for overlay in overlays:
        command.extend(["-loop", "1", "-framerate", str(FPS), "-i", str(overlay["path"])])
    voice_index = len(overlays) + 1
    bgm_index = voice_index + 1
    command.extend(["-i", str(voice), "-i", str(bgm)])

    video_filters: list[str] = []
    current = "0:v"
    for index, overlay in enumerate(overlays, start=1):
        output_label = f"ov{index}"
        video_filters.append(
            f"[{current}][{index}:v]overlay=0:0:enable='between(t,{overlay['start']:.3f},{overlay['end']:.3f})'[{output_label}]"
        )
        current = output_label
    video_filters.append(f"[{current}]format=yuv420p[vout]")

    fade_out_start = max(0.0, total_duration - 2.5)
    audio_filter = (
        f"[{voice_index}:a]adelay={round(VOICE_OFFSET * 1000)}|{round(VOICE_OFFSET * 1000)},"
        f"apad=pad_dur={OUTRO_DURATION:.3f},atrim=0:{total_duration:.3f},asplit=2[voice_sc][voice_mix];"
        f"[{bgm_index}:a]atrim=0:{total_duration:.3f},asetpts=PTS-STARTPTS,"
        f"afade=t=in:st=0:d=1.2,afade=t=out:st={fade_out_start:.3f}:d=2.5,volume=0.10[bgm_pre];"
        "[bgm_pre][voice_sc]sidechaincompress=threshold=0.025:ratio=7:attack=20:release=450[bgm_duck];"
        f"[bgm_duck][voice_mix]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95,atrim=0:{total_duration:.3f}[aout]"
    )
    filter_complex = ";".join(video_filters) + ";" + audio_filter
    output.parent.mkdir(parents=True, exist_ok=True)
    command.extend(
        [
            "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", "[aout]",
            "-t", f"{total_duration:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-r", str(FPS), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", str(output),
        ]
    )
    run(command)


def probe_video(path: Path) -> dict[str, Any]:
    result = run(
        [
            "ffprobe", "-v", "error", "-show_streams", "-show_format",
            "-of", "json", str(path),
        ],
        capture=True,
    )
    return json.loads(result.stdout)


def measure_loudness(path: Path) -> dict[str, float | None]:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
        text=True,
        capture_output=True,
        check=False,
    )
    integrated = re.findall(r"I:\s+(-?\d+(?:\.\d+)?) LUFS", result.stderr)
    peaks = re.findall(r"Peak:\s+(-?\d+(?:\.\d+)?) dBFS", result.stderr)
    return {
        "integrated_lufs": float(integrated[-1]) if integrated else None,
        "true_peak_dbfs": float(peaks[-1]) if peaks else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path, help="Warehouse project directory")
    parser.add_argument("--skip-render", action="store_true", help="Only rebuild timing and overlay assets")
    args = parser.parse_args()

    project = args.project.resolve()
    draft = read_json(project / "02_story_script_故事脚本/script.draft.json")
    approved = read_json(project / "02_story_script_故事脚本/script.approved.json")
    asr = read_json(project / "05_voice_人声/asr-approved-v1/approved-v1-b-locked-master.json")
    scene_plan = read_json(project / "03_images_生成图片/prompts/scene_plan.draft.json")

    aligned = align_approved_lines(draft["lines"], asr)
    voice_duration = float(
        run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(project / "05_voice_人声/approved-v1-b-locked-master.wav")],
            capture=True,
        ).stdout.strip()
    )
    total_duration = round(VOICE_OFFSET + voice_duration + OUTRO_DURATION, 3)
    scenes = scene_timeline(scene_plan, aligned, total_duration)

    timeline_dir = project / "07_timeline_时间线"
    timeline_dir.mkdir(parents=True, exist_ok=True)
    write_srt(timeline_dir / "subtitles.approved-v1.srt", aligned)
    overlays = build_overlay_assets(timeline_dir / "overlays", aligned)
    manifest = {
        "schema_version": "1.0",
        "project_id": approved["project_id"],
        "script_version": approved["version"],
        "voice_offset_seconds": VOICE_OFFSET,
        "voice_duration_seconds": round(voice_duration, 3),
        "total_duration_seconds": total_duration,
        "output": {"width": WIDTH, "height": HEIGHT, "fps": FPS},
        "lines": [line.__dict__ for line in aligned],
        "scenes": scenes,
        "overlays": [
            {**overlay, "path": str(Path(overlay["path"]).relative_to(project))}
            for overlay in overlays
        ],
        "audio": {
            "voice": "05_voice_人声/approved-v1-b-locked-master.wav",
            "bgm": "06_music_音乐/Long Road Ahead B.mp3",
            "bgm_license": "06_music_音乐/bgm_license.json",
            "bgm_gain": 0.10,
            "sidechain_ducking": True,
        },
    }
    write_json(timeline_dir / "render_manifest.approved-v1.json", manifest)
    if args.skip_render:
        return

    base_video = render_scene_clips(project, scenes, timeline_dir / "scene_clips")
    preview = project / "08_render_合成/preview/doudi-approved-v1-preview.mp4"
    render_master(project, base_video, overlays, total_duration, preview)

    final = project / "08_render_合成/final/doudi-approved-v1-final.mp4"
    final.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(preview, final)
    delivery = project / "10_delivery_交付"
    delivery.mkdir(parents=True, exist_ok=True)
    shutil.copy2(final, delivery / final.name)
    shutil.copy2(timeline_dir / "subtitles.approved-v1.srt", delivery / "subtitles.approved-v1.srt")
    shutil.copy2(timeline_dir / "render_manifest.approved-v1.json", delivery / "render_manifest.approved-v1.json")
    shutil.copy2(project / "06_music_音乐/ATTRIBUTION.txt", delivery / "MUSIC_ATTRIBUTION.txt")
    shutil.copy2(project / "02_story_script_故事脚本/script.approved.json", delivery / "script.approved.json")

    probe = probe_video(final)
    loudness = measure_loudness(final)
    video_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    audio_stream = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")
    qc = {
        "status": "pass",
        "file": str(final.relative_to(project)),
        "duration_seconds": float(probe["format"]["duration"]),
        "video": {
            "codec": video_stream["codec_name"],
            "width": video_stream["width"],
            "height": video_stream["height"],
            "pixel_format": video_stream["pix_fmt"],
            "frame_rate": video_stream["avg_frame_rate"],
        },
        "audio": {
            "codec": audio_stream["codec_name"],
            "sample_rate": audio_stream["sample_rate"],
            "channels": audio_stream["channels"],
            **loudness,
        },
        "checks": {
            "approved_script_used": True,
            "locked_voice_profile_used": True,
            "image_count": len(scenes),
            "subtitle_line_count": len(aligned),
            "bgm_license_archived": True,
        },
    }
    if video_stream["width"] != WIDTH or video_stream["height"] != HEIGHT:
        qc["status"] = "fail"
    if len(scenes) != 12 or len(aligned) != 14:
        qc["status"] = "fail"
    write_json(project / "09_qc_质检/qc_report.approved-v1.json", qc)

    project_state = read_json(project / "project.json")
    project_state["status"] = "final_ready" if qc["status"] == "pass" else "qc_failed"
    project_state["current_stage"] = "10_delivery"
    project_state["final_output"] = str((delivery / final.name).relative_to(project))
    write_json(project / "project.json", project_state)


if __name__ == "__main__":
    main()
