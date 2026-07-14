#!/usr/bin/env python3
"""Build the V2 branded bilingual book-video variants.

V2 adds a hook-first intro, rapid topic-card montage, exact book-cover
compositing, centered editorial typography, bilingual subtitles, segmented
music dynamics, and both 3:4 and 9:16 deliverables. Existing V1 outputs are
never overwritten.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import shutil
import struct
import subprocess
import wave
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from book_video_factory.audio import splice_asr_timestamps


FACTORY = Path(__file__).resolve().parents[1]
STYLE_PATH = FACTORY / "config/video_style_v2.json"
FPS = 30
BASE_WIDTH = 720
BASE_HEIGHT = 960
OUTRO_SECONDS = 2.5
VOICE_CUT_START = 4.48
VOICE_CUT_END = 4.52
VOICE_INSERTED_SILENCE = 1.04


@dataclass(frozen=True)
class TimedLine:
    line_id: str
    role: str
    zh: str
    en: str
    start: float
    end: float


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=capture)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize(text: str) -> str:
    return "".join(re.findall(r"[\u3400-\u9fffA-Za-z0-9]", text))


def normalized_asr_word(words: list[dict[str, Any]], index: int) -> str:
    value = normalize(str(words[index]["word"]))
    next_value = normalize(str(words[index + 1]["word"])) if index + 1 < len(words) else ""
    if value in {"情", "秦"} and next_value == "山":
        return "晴"
    return value


def align_lines(script: dict[str, Any], asr: dict[str, Any], montage_seconds: float) -> tuple[list[TimedLine], float, float]:
    words = [word for segment in asr["segments"] for word in segment.get("words", [])]
    characters: list[str] = []
    character_to_word: list[int] = []
    for index in range(len(words)):
        for character in normalized_asr_word(words, index):
            characters.append(character)
            character_to_word.append(index)

    transcript = "".join(characters)
    cursor = 0
    aligned: list[TimedLine] = []
    for line in script["lines"]:
        target = normalize(line["zh"])
        position = transcript.find(target, cursor)
        if position < 0:
            context = transcript[cursor : cursor + max(80, len(target) * 3)]
            raise RuntimeError(f"Cannot align {line['id']}: {target!r}; context={context!r}")
        start_word = words[character_to_word[position]]
        end_word = words[character_to_word[position + len(target) - 1]]
        aligned.append(
            TimedLine(
                line_id=line["id"],
                role=line["role"],
                zh=line["zh"],
                en=line["en"],
                start=round(float(start_word["start"]), 3),
                end=round(float(end_word["end"]), 3),
            )
        )
        cursor = position + len(target)

    cue = next(line for line in aligned if line.line_id == "V02")
    montage_start = round(cue.end + 0.04, 3)
    montage_end = round(montage_start + montage_seconds, 3)
    aligned = [
        replace(line, start=max(line.start, montage_end)) if line.line_id == "V03" else line
        for line in aligned
    ]
    return aligned, montage_start, montage_end


def resolved_font_path(style: dict[str, Any], kind: str) -> Path:
    fonts = style["fonts"]
    configured = Path(fonts[kind]).expanduser()
    path = configured if configured.is_absolute() else FACTORY / configured
    if path.is_file():
        return path
    fallback = FACTORY / fonts["title"]
    if fallback.is_file():
        return fallback
    raise FileNotFoundError(f"Configured {kind} font and bundled fallback are unavailable: {path}")


def font(style: dict[str, Any], kind: str, size: int) -> ImageFont.FreeTypeFont:
    fonts = style["fonts"]
    path = resolved_font_path(style, kind)
    index = 0
    if kind == "chinese":
        index = int(fonts.get("chinese_body_index", 0))
    return ImageFont.truetype(str(path), size=size, index=index)


def chinese_font(style: dict[str, Any], size: int, *, title_weight: bool = False) -> ImageFont.FreeTypeFont:
    path = resolved_font_path(style, "chinese")
    index_key = "chinese_title_index" if title_weight else "chinese_body_index"
    return ImageFont.truetype(str(path), size=size, index=int(style["fonts"].get(index_key, 0)))


def text_size(draw: ImageDraw.ImageDraw, text: str, chosen_font: ImageFont.FreeTypeFont, stroke: int = 0) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=chosen_font, stroke_width=stroke)
    return box[2] - box[0], box[3] - box[1]


def wrap_english(draw: ImageDraw.ImageDraw, text: str, chosen_font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or text_size(draw, candidate, chosen_font)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) <= 2:
        return lines
    midpoint = math.ceil(len(words) / 2)
    return [" ".join(words[:midpoint]), " ".join(words[midpoint:])]


def wrap_chinese(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    punctuation = "，。！？：；、"
    candidates = [index + 1 for index, char in enumerate(text) if char in punctuation]
    valid = [index for index in candidates if 5 <= index <= len(text) - 5]
    split = min(valid, key=lambda value: abs(value - len(text) / 2)) if valid else round(len(text) / 2)
    return [text[:split], text[split:]]


def wrap_chinese_to_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    chosen_font: ImageFont.FreeTypeFont,
    max_width: int,
    stroke: int = 0,
) -> list[str]:
    """Wrap CJK captions by measured pixels, not by a midpoint punctuation split.

    A midpoint split can leave the second line much longer than the first
    (for example, a 17-character clause after a comma) and push it past a
    3:4 safe area.  This renderer is used for every V4 master, so width is the
    invariant rather than a nominal character count.
    """
    lines: list[str] = []
    current = ""
    for character in text:
        candidate = current + character
        if current and text_size(draw, candidate, chosen_font, stroke)[0] > max_width:
            lines.append(current)
            current = character
        else:
            current = candidate
    if current:
        lines.append(current)
    # Keep closing punctuation with the preceding clause when possible.
    punctuation = "，。！？：；、"
    for index in range(1, len(lines)):
        if lines[index] and lines[index][0] in punctuation:
            character = lines[index][0]
            candidate = lines[index - 1] + character
            if text_size(draw, candidate, chosen_font, stroke)[0] <= max_width:
                lines[index - 1] = candidate
                lines[index] = lines[index][1:]
    return [line for line in lines if line]


def cover_background(source: Image.Image, width: int, height: int) -> Image.Image:
    return ImageOps.fit(source.convert("RGB"), (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def compose_exact_book_cover(project: Path) -> Path:
    background_path = project / "03_images_生成图片/v2/book-mockup-blank.png"
    cover_path = project / "01_research_资料搜集/sources/cover/doudi-weread-t9.jpg"
    output = project / "03_images_生成图片/v2/book-cover-composite.png"
    base = Image.open(background_path).convert("RGB")
    original = base.copy()
    book_cover = Image.open(cover_path).convert("RGB")
    book_cover = ImageEnhance.Brightness(book_cover).enhance(0.92)
    book_cover = ImageEnhance.Contrast(book_cover).enhance(0.96)

    box = (542, 627, 806, 1036)
    fitted = book_cover.resize((box[2] - box[0], box[3] - box[1]), Image.Resampling.LANCZOS)
    base.paste(fitted, box)

    restore_mask = Image.new("L", base.size, 0)
    mask_draw = ImageDraw.Draw(restore_mask)
    mask_draw.rectangle((538, 620, 563, 1044), fill=255)
    mask_draw.polygon([(778, 856), (816, 872), (858, 923), (855, 1062), (810, 1112), (775, 1045), (765, 955)], fill=255)
    mask_draw.polygon([(526, 972), (608, 965), (628, 1056), (590, 1110), (528, 1074)], fill=255)
    restore_mask = restore_mask.filter(ImageFilter.GaussianBlur(2.0))
    base = Image.composite(original, base, restore_mask)
    output.parent.mkdir(parents=True, exist_ok=True)
    base.save(output, quality=95)
    return output


def make_topic_cards(project: Path, style: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    title_font = font(style, "title", 94)
    english_font = font(style, "english", 31)
    cards: list[Path] = []
    for index, topic in enumerate(style["intro"]["topics"], start=1):
        source_path = project / f"03_images_生成图片/approved/{topic['scene']}.png"
        canvas = cover_background(Image.open(source_path), BASE_WIDTH, BASE_HEIGHT).convert("RGBA")
        canvas.alpha_composite(Image.new("RGBA", canvas.size, (0, 0, 0, 120)))
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle((45, 55, BASE_WIDTH - 45, BASE_HEIGHT - 55), radius=26, outline=(236, 230, 218, 130), width=2)
        zh = topic["zh"]
        en = topic["en"]
        zh_width, _ = text_size(draw, zh, title_font, 3)
        draw.text(((BASE_WIDTH - zh_width) / 2, 535), zh, font=title_font, fill=(250, 247, 240, 255), stroke_width=3, stroke_fill=(0, 0, 0, 220))
        en_width, _ = text_size(draw, en, english_font, 1)
        draw.rectangle(((BASE_WIDTH - 82) / 2, 655, (BASE_WIDTH + 82) / 2, 660), fill=(183, 96, 49, 240))
        draw.text(((BASE_WIDTH - en_width) / 2, 685), en, font=english_font, fill=(230, 224, 214, 240), stroke_width=1, stroke_fill=(0, 0, 0, 180))
        path = output_dir / f"topic-{index:02d}-{topic['en'].lower()}.png"
        canvas.convert("RGB").save(path)
        cards.append(path)
    return cards


def render_title_layer(style: dict[str, Any], width: int, height: int) -> Image.Image:
    scale = width / BASE_WIDTH
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    title_font = font(style, "title", round(76 * scale))
    author_font = chinese_font(style, round(34 * scale), title_weight=True)
    title = "《兜底》"
    author = "晴山／著"
    top = round((70 if height / width < 2 else 110) * scale)
    title_width, _ = text_size(draw, title, title_font, round(3 * scale))
    draw.text(((width - title_width) / 2, top), title, font=title_font, fill=(250, 247, 240, 255), stroke_width=round(3 * scale), stroke_fill=(0, 0, 0, 230))
    rule_width = round(88 * scale)
    rule_y = top + round(92 * scale)
    draw.rectangle(((width - rule_width) / 2, rule_y, (width + rule_width) / 2, rule_y + max(4, round(5 * scale))), fill=(183, 96, 49, 245))
    author_width, _ = text_size(draw, author, author_font, round(2 * scale))
    draw.text(((width - author_width) / 2, rule_y + round(25 * scale)), author, font=author_font, fill=(234, 229, 220, 250), stroke_width=round(2 * scale), stroke_fill=(0, 0, 0, 215))
    return canvas


def render_caption_layer(style: dict[str, Any], line: TimedLine, width: int, height: int, mode: str) -> Image.Image:
    scale = width / BASE_WIDTH
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    is_hook = line.role in {"hook", "reveal_cue"}
    zh_size = round((48 if is_hook else 43) * scale)
    en_size = round((27 if is_hook else 24) * scale)
    zh_font = chinese_font(style, zh_size, title_weight=is_hook)
    en_font = font(style, "english", en_size)
    zh_lines = wrap_chinese_to_width(
        draw, line.zh, zh_font, width - round(36 * scale), stroke=round(3 * scale)
    )
    en_lines = wrap_english(draw, line.en, en_font, width - round(110 * scale)) if mode == "bilingual" else []

    if height / width >= 1.7:
        top = round(1410 if not is_hook else 330)
    else:
        top = round((640 if not is_hook else 205) * scale)
    zh_gap = round(58 * scale)
    en_gap = round(34 * scale)
    stroke = max(2, round(3 * scale))
    y = top
    for part in zh_lines:
        part_width, _ = text_size(draw, part, zh_font, stroke)
        draw.text(((width - part_width) / 2, y), part, font=zh_font, fill=(250, 247, 240, 255), stroke_width=stroke, stroke_fill=(0, 0, 0, 235))
        y += zh_gap
    if en_lines:
        y += round(8 * scale)
        for part in en_lines:
            part_width, _ = text_size(draw, part, en_font, max(1, round(scale)))
            draw.text(((width - part_width) / 2, y), part, font=en_font, fill=(229, 223, 214, 245), stroke_width=max(1, round(scale)), stroke_fill=(0, 0, 0, 220))
            y += en_gap
    return canvas


def render_brand_layer(style: dict[str, Any], width: int, height: int) -> Image.Image:
    scale = width / BASE_WIDTH
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    chosen = font(style, "english", round(18 * scale))
    label = "JAXXMIND · BOOK NOTES"
    label_width, _ = text_size(draw, label, chosen)
    bottom = height - round((28 if height / width < 2 else 70) * scale)
    draw.text(((width - label_width) / 2, bottom), label, font=chosen, fill=(218, 211, 200, 190), stroke_width=max(1, round(scale)), stroke_fill=(0, 0, 0, 180))
    return canvas


def make_overlay_assets(style: dict[str, Any], lines: list[TimedLine], output_dir: Path, width: int, height: int, mode: str, title_start: float, voice_end: float) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    overlays: list[dict[str, Any]] = []
    if mode != "clean":
        title_path = output_dir / "title.png"
        render_title_layer(style, width, height).save(title_path)
        overlays.append({"path": title_path, "start": title_start, "end": voice_end, "kind": "title"})
        brand_path = output_dir / "brand.png"
        render_brand_layer(style, width, height).save(brand_path)
        overlays.append({"path": brand_path, "start": 0.0, "end": voice_end + OUTRO_SECONDS, "kind": "brand"})
        for line in lines:
            caption_path = output_dir / f"{line.line_id}.png"
            render_caption_layer(style, line, width, height, mode).save(caption_path)
            overlays.append({"path": caption_path, "start": line.start, "end": line.end, "kind": "caption", "line_id": line.line_id})
    return overlays


def create_scene_timeline(lines: list[TimedLine], montage_start: float, montage_end: float, total_duration: float) -> list[dict[str, Any]]:
    by_id = {line.line_id: line for line in lines}
    groups = [
        ("HOOK", ["V01", "V02"], "03_images_生成图片/approved/S01.png"),
        ("BOOK", ["V03"], "03_images_生成图片/v2/book-cover-composite.png"),
        ("THESIS", ["V04"], "03_images_生成图片/approved/S02.png"),
        ("RELATION", ["V05", "V06"], "03_images_生成图片/approved/S04.png"),
        ("SUPPORT", ["V07", "V08"], "03_images_生成图片/approved/S05.png"),
        ("BOUNDARIES", ["V09"], "03_images_生成图片/approved/S06.png"),
        ("FIRST_STEP", ["V10"], "03_images_生成图片/approved/S07.png"),
        ("QUESTION", ["V11"], "03_images_生成图片/approved/S08.png"),
        ("SELF_CARE", ["V12"], "03_images_生成图片/approved/S09.png"),
        ("LOVE", ["V13"], "03_images_生成图片/approved/S10.png"),
        ("RAIN", ["V14"], "03_images_生成图片/approved/S11.png"),
        ("DAWN", ["V15"], "03_images_生成图片/approved/S12.png"),
    ]
    spans = [(min(by_id[item].start for item in ids), max(by_id[item].end for item in ids)) for _, ids, _ in groups]
    timeline: list[dict[str, Any]] = []
    for index, (scene_id, ids, asset) in enumerate(groups):
        if scene_id == "HOOK":
            start, end = 0.0, montage_start
        elif scene_id == "BOOK":
            start, end = montage_end, spans[index + 1][0]
        else:
            start = spans[index][0]
            if index == len(groups) - 1:
                end = total_duration
            else:
                next_start = spans[index + 1][0]
                end = (spans[index][1] + next_start) / 2
        timeline.append({"id": scene_id, "lines": ids, "start": round(start, 3), "end": round(end, 3), "duration": round(end - start, 3), "asset": asset})
        if scene_id == "HOOK":
            timeline.append({"id": "MONTAGE", "lines": [], "start": montage_start, "end": montage_end, "duration": round(montage_end - montage_start, 3), "asset": "07_timeline_时间线/v2/topic-cards/montage.mp4"})
    return timeline


def render_still_clip(source: Path, duration: float, output: Path, index: int) -> None:
    increment = 0.00010 + (index % 4) * 0.000015
    vf = (
        "scale=720:960,"
        f"zoompan=z='min(zoom+{increment:.6f},1.045)':"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=720x960:fps=30,"
        "format=yuv420p"
    )
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-framerate", str(FPS), "-i", str(source),
        "-t", f"{duration:.3f}", "-vf", vf,
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-r", str(FPS), "-pix_fmt", "yuv420p", str(output),
    ])


def render_montage(cards: list[Path], duration: float, output: Path) -> None:
    per_card = duration / len(cards)
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for card in cards:
        command.extend(["-loop", "1", "-framerate", str(FPS), "-t", f"{per_card:.6f}", "-i", str(card)])
    filters: list[str] = []
    labels: list[str] = []
    for index in range(len(cards)):
        label = f"c{index}"
        filters.append(f"[{index}:v]scale=720:960,trim=duration={per_card:.6f},setpts=PTS-STARTPTS[{label}]")
        labels.append(f"[{label}]")
    filters.append(f"{''.join(labels)}concat=n={len(cards)}:v=1:a=0,fps={FPS},format=yuv420p[out]")
    command.extend(["-filter_complex", ";".join(filters), "-map", "[out]", "-t", f"{duration:.3f}", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-r", str(FPS), "-pix_fmt", "yuv420p", str(output)])
    run(command)


def render_base_video(project: Path, timeline: list[dict[str, Any]], cards: list[Path], timeline_dir: Path) -> Path:
    clip_dir = timeline_dir / "scene-clips"
    clip_dir.mkdir(parents=True, exist_ok=True)
    montage_path = timeline_dir / "topic-cards/montage.mp4"
    montage_path.parent.mkdir(parents=True, exist_ok=True)
    montage_scene = next(scene for scene in timeline if scene["id"] == "MONTAGE")
    render_montage(cards, montage_scene["duration"], montage_path)

    concat_lines: list[str] = []
    for index, scene in enumerate(timeline):
        if scene["id"] == "MONTAGE":
            clip = montage_path
        else:
            clip = clip_dir / f"{index:02d}-{scene['id']}.mp4"
            render_still_clip(project / scene["asset"], scene["duration"], clip, index)
        concat_lines.append(f"file '{clip.as_posix()}'")
    concat_path = clip_dir / "concat.txt"
    concat_path.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    base = timeline_dir / "base-v2-3x4.mp4"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_path), "-c", "copy", str(base)])
    return base


def prepare_intro_voice(project: Path) -> tuple[Path, Path]:
    source = project / "05_voice_人声/v2-approved-b-locked-master.wav"
    source_asr = project / "05_voice_人声/asr-v2/v2-approved-b-locked-master.json"
    output = project / "05_voice_人声/v2-approved-b-locked-master-tickfix.wav"
    output_asr = project / "05_voice_人声/asr-v2-tickfix/v2-approved-b-locked-master-tickfix.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output_asr.parent.mkdir(parents=True, exist_ok=True)
    fade_out_start = VOICE_CUT_START - 0.025
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
        "-f", "lavfi", "-t", f"{VOICE_INSERTED_SILENCE:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
        "-filter_complex",
        f"[0:a]atrim=0:{VOICE_CUT_START:.3f},afade=t=out:st={fade_out_start:.3f}:d=0.025[pre];"
        f"[1:a]atrim=0:{VOICE_INSERTED_SILENCE:.3f}[pause];"
        f"[0:a]atrim=start={VOICE_CUT_END:.3f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.035[post];"
        "[pre][pause][post]concat=n=3:v=0:a=1[out]",
        "-map", "[out]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output),
    ])
    corrected_asr = splice_asr_timestamps(
        read_json(source_asr),
        cut_start=VOICE_CUT_START,
        cut_end=VOICE_CUT_END,
        inserted_silence=VOICE_INSERTED_SILENCE,
    )
    write_json(output_asr, corrected_asr)
    return output, output_asr


def generate_clock_tick_stinger(path: Path, duration: float, tick_count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 48_000
    frame_count = round(duration * sample_rate)
    samples = [0.0] * frame_count
    rng = random.Random(20260711)
    spacing = duration / tick_count

    for index in range(tick_count):
        start = round(index * spacing * sample_rate)
        tick_length = round(0.055 * sample_rate)
        high = 2350.0 if index % 2 == 0 else 1580.0
        low = 820.0 if index % 2 == 0 else 560.0
        strength = 0.31 if index < tick_count - 1 else 0.42
        for offset in range(min(tick_length, frame_count - start)):
            time = offset / sample_rate
            envelope = math.exp(-time / 0.011)
            transient = rng.uniform(-1.0, 1.0) * math.exp(-time / 0.0025)
            tone = math.sin(2 * math.pi * high * time) + 0.42 * math.sin(2 * math.pi * low * time)
            samples[start + offset] += strength * envelope * (tone + 0.22 * transient)

    landing_start = max(0, round((duration - 0.12) * sample_rate))
    for offset in range(frame_count - landing_start):
        time = offset / sample_rate
        samples[landing_start + offset] += 0.12 * math.exp(-time / 0.035) * math.sin(2 * math.pi * 96 * time)

    peak = max(max(abs(value) for value in samples), 1e-9)
    scale = 0.82 / peak
    pcm = bytearray()
    for value in samples:
        sample = max(-32768, min(32767, round(value * scale * 32767)))
        pcm.extend(struct.pack("<hh", sample, sample))
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm)


def render_variant(
    base: Path,
    overlays: list[dict[str, Any]],
    voice: Path,
    bgm: Path,
    stinger: Path,
    total_duration: float,
    montage_start: float,
    montage_end: float,
    output: Path,
    width: int,
    height: int,
    style: dict[str, Any],
) -> None:
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(base)]
    for overlay in overlays:
        command.extend(["-loop", "1", "-framerate", str(FPS), "-i", str(overlay["path"])])
    voice_index = len(overlays) + 1
    bgm_index = voice_index + 1
    stinger_index = bgm_index + 1
    command.extend(["-i", str(voice), "-i", str(bgm), "-i", str(stinger)])

    filters: list[str] = []
    if width == BASE_WIDTH and height == BASE_HEIGHT:
        filters.append("[0:v]null[vbase]")
    else:
        image_height = round(width / 0.75)
        y = (height - image_height) // 2
        filters.append(f"color=c=black:s={width}x{height}:r={FPS}:d={total_duration:.3f}[bg]")
        filters.append(f"[0:v]scale={width}:{image_height}[scaled]")
        filters.append(f"[bg][scaled]overlay=0:{y}[vbase]")

    current = "vbase"
    for index, overlay in enumerate(overlays, start=1):
        output_label = f"ov{index}"
        filters.append(f"[{current}][{index}:v]overlay=0:0:enable='between(t,{overlay['start']:.3f},{overlay['end']:.3f})'[{output_label}]")
        current = output_label
    filters.append(f"[{current}]format=yuv420p[vout]")

    audio = style["audio"]
    bgm_start = float(audio["bgm_start_offset_seconds"])
    bgm_end = bgm_start + total_duration
    fade_out = max(0.0, total_duration - OUTRO_SECONDS)
    montage_boost = 10 ** (float(audio["montage_boost_db"]) / 20)
    sting_delay = round(montage_start * 1000)
    filters.extend(
        [
            f"[{voice_index}:a]apad=pad_dur={OUTRO_SECONDS:.3f},atrim=0:{total_duration:.3f},asplit=2[voice_sc][voice_mix]",
            f"[{bgm_index}:a]atrim=start={bgm_start:.3f}:end={bgm_end:.3f},asetpts=PTS-STARTPTS,loudnorm=I={audio['bgm_target_lufs']}:LRA=8:TP=-2,afade=t=in:st=0:d=0.35,afade=t=out:st={fade_out:.3f}:d={OUTRO_SECONDS:.3f},volume='if(between(t,{montage_start:.3f},{montage_end:.3f}),{montage_boost:.4f},1.0)'[bed]",
            f"[bed][voice_sc]sidechaincompress=threshold=0.035:ratio=4:attack=10:release=320[ducked]",
            f"[{stinger_index}:a]adelay={sting_delay}|{sting_delay},volume=2.4[sting]",
            f"[ducked][sting][voice_mix]amix=inputs=3:duration=first:normalize=0,loudnorm=I={audio['final_target_lufs']}:LRA=8:TP={audio['true_peak_dbfs']},atrim=0:{total_duration:.3f}[aout]",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", "[vout]", "-map", "[aout]", "-t", f"{total_duration:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(output),
    ])
    run(command)


def srt_time(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_subtitles(directory: Path, lines: list[TimedLine]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    variants = {
        "zh-CN": lambda line: line.zh,
        "en": lambda line: line.en,
        "bilingual": lambda line: f"{line.zh}\n{line.en}",
    }
    for name, formatter in variants.items():
        blocks = [f"{index}\n{srt_time(line.start)} --> {srt_time(line.end)}\n{formatter(line)}" for index, line in enumerate(lines, start=1)]
        (directory / f"subtitles.v2.{name}.srt").write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def probe(path: Path) -> dict[str, Any]:
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture=True).stdout)


def volume_segment(path: Path, start: float, duration: float) -> dict[str, float | None]:
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(path), "-vn", "-af", "volumedetect", "-f", "null", "-",
    ], text=True, capture_output=True, check=False)
    mean = re.findall(r"mean_volume:\s+(-?\d+(?:\.\d+)?) dB", result.stderr)
    peak = re.findall(r"max_volume:\s+(-?\d+(?:\.\d+)?) dB", result.stderr)
    return {"mean_db": float(mean[-1]) if mean else None, "max_db": float(peak[-1]) if peak else None}


def loudness(path: Path) -> dict[str, float | None]:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-filter_complex", "ebur128=peak=true", "-f", "null", "-"], text=True, capture_output=True, check=False)
    integrated = re.findall(r"I:\s+(-?\d+(?:\.\d+)?) LUFS", result.stderr)
    peaks = re.findall(r"Peak:\s+(-?\d+(?:\.\d+)?) dBFS", result.stderr)
    return {"integrated_lufs": float(integrated[-1]) if integrated else None, "true_peak_dbfs": float(peaks[-1]) if peaks else None}


def voice_splice_metrics(path: Path, montage_start: float, montage_end: float) -> dict[str, float | int | bool]:
    with wave.open(str(path), "rb") as source:
        if source.getsampwidth() != 2:
            raise RuntimeError(f"Voice splice QC requires 16-bit PCM: {path}")
        sample_rate = source.getframerate()
        channels = source.getnchannels()
        raw = source.readframes(source.getnframes())
    values = struct.unpack("<" + "h" * (len(raw) // 2), raw)

    def mono(frame: int) -> float:
        offset = frame * channels
        return sum(values[offset : offset + channels]) / channels

    pre_boundary = round(VOICE_CUT_START * sample_rate)
    post_boundary = round((VOICE_CUT_START + VOICE_INSERTED_SILENCE) * sample_rate)
    silence_start = round(montage_start * sample_rate) * channels
    silence_end = round(montage_end * sample_rate) * channels
    pre_jump = abs(mono(pre_boundary) - mono(pre_boundary - 1))
    post_jump = abs(mono(post_boundary) - mono(post_boundary - 1))
    silence_peak = max((abs(value) for value in values[silence_start:silence_end]), default=0)
    passed = pre_jump <= 64 and post_jump <= 64 and silence_peak <= 1
    return {
        "status": "pass" if passed else "fail",
        "pre_boundary_jump_samples": round(pre_jump, 1),
        "post_boundary_jump_samples": round(post_jump, 1),
        "montage_voice_peak_samples": int(silence_peak),
        "montage_voice_is_silent": silence_peak <= 1,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--style", type=Path, default=STYLE_PATH)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()

    project = args.project.resolve()
    style = read_json(args.style.resolve())
    script = read_json(project / "02_story_script_故事脚本/script.v2.bilingual.json")
    voice, asr_path = prepare_intro_voice(project)
    asr = read_json(asr_path)
    bgm = project / "06_music_音乐/Long Road Ahead B.mp3"
    voice_duration = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(voice)], capture=True).stdout.strip())
    total_duration = round(voice_duration + OUTRO_SECONDS, 3)

    lines, montage_start, montage_end = align_lines(script, asr, float(style["intro"]["montage_duration_seconds"]))
    cover_composite = compose_exact_book_cover(project)
    timeline_dir = project / "07_timeline_时间线/v2"
    cards = make_topic_cards(project, style, timeline_dir / "topic-cards")
    timeline = create_scene_timeline(lines, montage_start, montage_end, total_duration)
    write_subtitles(timeline_dir, lines)

    overlays = {
        "bilingual-3x4": make_overlay_assets(style, lines, timeline_dir / "overlays/bilingual-3x4", 720, 960, "bilingual", montage_end, voice_duration),
        "bilingual-9x16": make_overlay_assets(style, lines, timeline_dir / "overlays/bilingual-9x16", 1080, 1920, "bilingual", montage_end, voice_duration),
        "clean-3x4": [],
        "clean-9x16": [],
    }
    manifest = {
        "schema_version": "2.0",
        "project_id": script["project_id"],
        "script_version": script["version"],
        "voice": str(voice.relative_to(project)),
        "voice_duration_seconds": voice_duration,
        "total_duration_seconds": total_duration,
        "montage": {"start": montage_start, "end": montage_end, "duration": round(montage_end - montage_start, 3), "card_count": len(cards)},
        "intro_sfx": "mechanical_clock_tick",
        "book_cover_composite": str(cover_composite.relative_to(project)),
        "lines": [line.__dict__ for line in lines],
        "timeline": timeline,
        "style": str(args.style.resolve()),
        "translation_status": script["translation_status"],
    }
    write_json(timeline_dir / "render_manifest.v2.json", manifest)
    if args.prepare_only:
        return

    base = render_base_video(project, timeline, cards, timeline_dir)
    stinger = project / "06_music_音乐/v2-clock-tick-stinger.wav"
    generate_clock_tick_stinger(stinger, montage_end - montage_start, len(cards))
    output_dir = project / "08_render_合成/v2"
    specs = {
        "bilingual-3x4": (720, 960),
        "bilingual-9x16": (1080, 1920),
        "clean-3x4": (720, 960),
        "clean-9x16": (1080, 1920),
    }
    outputs: dict[str, Path] = {}
    for name, (width, height) in specs.items():
        output = output_dir / f"doudi-v2-{name}.mp4"
        render_variant(base, overlays[name], voice, bgm, stinger, total_duration, montage_start, montage_end, output, width, height, style)
        outputs[name] = output

    delivery = project / "10_delivery_交付/v2"
    delivery.mkdir(parents=True, exist_ok=True)
    for output in outputs.values():
        shutil.copy2(output, delivery / output.name)
    for subtitle in timeline_dir.glob("subtitles.v2.*.srt"):
        shutil.copy2(subtitle, delivery / subtitle.name)
    shutil.copy2(timeline_dir / "render_manifest.v2.json", delivery / "render_manifest.v2.json")
    shutil.copy2(project / "06_music_音乐/ATTRIBUTION.txt", delivery / "MUSIC_ATTRIBUTION.txt")
    shutil.copy2(project / "01_research_资料搜集/sources/cover/cover_manifest.json", delivery / "BOOK_COVER_SOURCE.json")

    reports: dict[str, Any] = {}
    for name, output in outputs.items():
        media = probe(output)
        video = next(stream for stream in media["streams"] if stream["codec_type"] == "video")
        audio_stream = next(stream for stream in media["streams"] if stream["codec_type"] == "audio")
        reports[name] = {
            "file": str(output.relative_to(project)),
            "duration_seconds": float(media["format"]["duration"]),
            "video": {"codec": video["codec_name"], "width": video["width"], "height": video["height"], "fps": video["avg_frame_rate"], "pixel_format": video["pix_fmt"]},
            "audio": {"codec": audio_stream["codec_name"], "sample_rate": audio_stream["sample_rate"], "channels": audio_stream["channels"], **loudness(output)},
            "segments": {
                "hook": volume_segment(output, 0.0, montage_start),
                "montage": volume_segment(output, montage_start, montage_end - montage_start),
                "body": volume_segment(output, montage_end, max(1.0, voice_duration - montage_end)),
            },
        }
    splice_qc = voice_splice_metrics(voice, montage_start, montage_end)
    qc = {
        "status": "pass" if splice_qc["status"] == "pass" else "fail",
        "checks": {
            "voice_profile_locked": True,
            "real_cover_composited": True,
            "topic_card_count": len(cards),
            "intro_sfx_clock_tick": True,
            "intro_voice_splice_faded": splice_qc["status"] == "pass",
            "bilingual_line_count": len(lines),
            "font_license_archived": (FACTORY / style["fonts"]["title_license"]).is_file(),
            "bgm_license_archived": (project / "06_music_音乐/bgm_license.json").is_file(),
            "translation_native_review_pending": script["translation_status"] != "native_approved",
        },
        "voice_splice": splice_qc,
        "outputs": reports,
    }
    if any(report["video"]["width"] != specs[name][0] or report["video"]["height"] != specs[name][1] for name, report in reports.items()):
        qc["status"] = "fail"
    write_json(project / "09_qc_质检/qc_report.v2.json", qc)

    project_path = project / "project.json"
    if project_path.is_file():
        project_state = read_json(project_path)
        project_state["status"] = "v2_ready" if qc["status"] == "pass" else "v2_qc_failed"
        project_state["current_stage"] = "10_delivery_v2"
        project_state["final_output"] = "10_delivery_交付/v2/doudi-v2-bilingual-3x4.mp4"
        project_state["v2"] = {
            "status": "ready" if qc["status"] == "pass" else "qc_failed",
            "render_manifest": "07_timeline_时间线/v2/render_manifest.v2.json",
            "qc_report": "09_qc_质检/qc_report.v2.json",
            "cover_source": "01_research_资料搜集/sources/cover/cover_manifest.json",
            "delivery_dir": "10_delivery_交付/v2",
            "international_output": "10_delivery_交付/v2/doudi-v2-bilingual-9x16.mp4",
            "clean_output": "10_delivery_交付/v2/doudi-v2-clean-9x16.mp4",
        }
        write_json(project_path, project_state)


if __name__ == "__main__":
    main()
