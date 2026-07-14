#!/usr/bin/env python3
"""Render a batch-produced book video from a 15-line research-backed script.

This renderer is deliberately separate from V2 so the proven 《兜底》 delivery
remains immutable. It uses an original high-frequency transition effect tuned
against the user's H2 reference audition, never samples the reference audio.
"""

from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import math
import random
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

import build_final_video_v2 as v2
from book_video_factory.contracts import ReleaseProfile
from book_video_factory.typography import (
    centered_text_x,
    fit_book_title,
    fit_single_line_font_size,
    text_box,
)


FACTORY = Path(__file__).resolve().parents[1]
STYLE_PATH = FACTORY / "config/video_style_v2.json"
RELEASE_PROFILE_PATH = FACTORY / "config/release_profiles/book-v4-bilingual-3x4.json"
FPS = 30
WIDTH = 720
HEIGHT = 960
OUTRO_SECONDS = 2.5
MONTAGE_SECONDS = 0.96


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=capture)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_style_profile(style: dict[str, Any]) -> ReleaseProfile:
    profile = ReleaseProfile.load(RELEASE_PROFILE_PATH)
    layout = style.get("title_layout", {})
    expected = profile.payload["typography"]
    pairs = {
        "safe_margin_x_px": "title_safe_margin_x_px",
        "max_font_size_px": "title_max_font_size_px",
        "min_font_size_px": "title_min_font_size_px",
        "max_lines": "title_max_lines",
    }
    mismatches = [
        style_key
        for style_key, profile_key in pairs.items()
        if layout.get(style_key) != expected.get(profile_key)
    ]
    if mismatches:
        raise ValueError(
            "video style diverges from release profile typography: "
            + ", ".join(mismatches)
        )
    return profile


def proportional_lines(script: dict[str, Any], asr: dict[str, Any]) -> tuple[list[v2.TimedLine], float, float]:
    """Last-resort timing map when ASR wording is too lossy to align safely."""
    duration = max(
        (float(segment.get("end", 0.0)) for segment in asr.get("segments", [])),
        default=0.0,
    )
    if duration <= 0:
        raise RuntimeError("ASR does not contain a usable duration")
    weights = [max(1, len(v2.normalize(line["zh"]))) for line in script["lines"]]
    total_weight = sum(weights)
    cursor = 0.0
    aligned: list[v2.TimedLine] = []
    for line, weight in zip(script["lines"], weights, strict=True):
        end = cursor + duration * weight / total_weight
        aligned.append(v2.TimedLine(
            line_id=line["id"], role=line["role"], zh=line["zh"], en=line["en"],
            start=round(cursor, 3), end=round(end, 3),
        ))
        cursor = end
    cue = next(line for line in aligned if line.line_id == "V02")
    montage_start = round(cue.end + 0.04, 3)
    montage_end = round(montage_start + MONTAGE_SECONDS, 3)
    aligned = [
        v2.replace(line, start=max(line.start, montage_end)) if line.line_id == "V03" else line
        for line in aligned
    ]
    return aligned, montage_start, montage_end


def align_lines(script: dict[str, Any], asr: dict[str, Any]) -> tuple[list[v2.TimedLine], float, float]:
    """Align captions to Whisper, tolerating simplified/traditional output.

    Whisper's Chinese model can emit traditional characters even when the
    narration script is simplified Chinese.  V2 intentionally uses exact
    matching for a single locked script; batch V3 falls back to an ordered
    fuzzy match so transcription orthography cannot move the subtitle timing.
    """
    try:
        return v2.align_lines(script, asr, MONTAGE_SECONDS)
    except RuntimeError:
        pass

    words = [word for segment in asr["segments"] for word in segment.get("words", [])]
    characters: list[str] = []
    character_to_word: list[int] = []
    for index in range(len(words)):
        for character in v2.normalized_asr_word(words, index):
            characters.append(character)
            character_to_word.append(index)
    transcript = "".join(characters)
    cursor = 0
    aligned: list[v2.TimedLine] = []
    for line in script["lines"]:
        target = v2.normalize(line["zh"])
        best: tuple[float, int, int] | None = None
        min_length = max(1, len(target) - 7)
        max_length = len(target) + 9
        # Preserve ordering and search only the local section that can belong
        # to this caption. This avoids matching a repeated phrase later on.
        for start in range(cursor, min(len(transcript), cursor + 40) + 1):
            for length in range(min_length, max_length + 1):
                end = start + length
                if end > len(transcript):
                    break
                ratio = difflib.SequenceMatcher(a=target, b=transcript[start:end], autojunk=False).ratio()
                score = ratio - abs(length - len(target)) * 0.006
                if best is None or score > best[0]:
                    best = (score, start, end)
        # Keep a deliberately conservative floor, while accepting dropped
        # words in otherwise ordered Whisper output (for example, it may omit
        # "刺激" while preserving the surrounding sentence). If this floor is
        # not met, Whisper is no longer a reliable textual timing source.
        if best is None or best[0] < 0.45:
            return proportional_lines(script, asr)
        _, start, end = best
        start_word = words[character_to_word[start]]
        end_word = words[character_to_word[end - 1]]
        aligned.append(v2.TimedLine(
            line_id=line["id"], role=line["role"], zh=line["zh"], en=line["en"],
            start=round(float(start_word["start"]), 3), end=round(float(end_word["end"]), 3),
        ))
        cursor = end
    cue = next(line for line in aligned if line.line_id == "V02")
    montage_start = round(cue.end + 0.04, 3)
    montage_end = round(montage_start + MONTAGE_SECONDS, 3)
    aligned = [
        v2.replace(line, start=max(line.start, montage_end)) if line.line_id == "V03" else line
        for line in aligned
    ]
    return aligned, montage_start, montage_end


def asr_with_intro_pause(
    source_voice: Path, source_asr: Path, script: dict[str, Any], output_voice: Path, output_asr: Path
) -> tuple[Path, dict[str, Any]]:
    """Insert the V2-style reveal pause without leaving a hard audio splice."""
    original_asr = read_json(source_asr)
    original_lines, _, _ = align_lines(script, original_asr)
    cue_end = next(line.end for line in original_lines if line.line_id == "V02")
    cut_start = cue_end
    cut_end = cue_end + 0.020
    inserted_silence = 1.040
    output_voice.parent.mkdir(parents=True, exist_ok=True)
    output_asr.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source_voice),
        "-f", "lavfi", "-t", f"{inserted_silence:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
        "-filter_complex",
        f"[0:a]atrim=0:{cut_start:.3f},afade=t=out:st={max(0, cut_start - 0.025):.3f}:d=0.025[pre];"
        f"[1:a]atrim=0:{inserted_silence:.3f}[pause];"
        f"[0:a]atrim=start={cut_end:.3f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.035[post];"
        "[pre][pause][post]concat=n=3:v=0:a=1[out]",
        "-map", "[out]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output_voice),
    ])

    # ASR is a timing map, not transcript truth. Shift every following word,
    # including a new line that begins exactly at the prior cue boundary.
    shifted = copy.deepcopy(original_asr)
    delta = inserted_silence - (cut_end - cut_start)
    for segment in shifted.get("segments", []):
        if float(segment["start"]) >= cut_start:
            segment["start"] = round(float(segment["start"]) + delta, 3)
        if float(segment["end"]) >= cut_start:
            segment["end"] = round(float(segment["end"]) + delta, 3)
        for word in segment.get("words", []):
            start = float(word["start"])
            end = float(word["end"])
            if start >= cut_start:
                word["start"] = round(start + delta, 3)
                word["end"] = round(end + delta, 3)
            elif end > cut_start:
                word["end"] = round(cut_start, 3)
    write_json(output_asr, shifted)
    return output_voice, shifted


def generate_h2_inspired_original_sfx(path: Path, duration: float) -> None:
    """Create an original airy high-frequency transition; no reference audio is used."""
    sample_rate = 48_000
    frames = round(duration * sample_rate)
    samples = [0.0] * frames
    rng = random.Random(20260712)
    previous = 0.0
    for index in range(frames):
        t = index / sample_rate
        progress = min(1.0, t / max(duration, 1e-6))
        envelope = (math.sin(math.pi * progress) ** 1.15) * (0.48 + 0.52 * progress)
        noise = rng.uniform(-1.0, 1.0)
        high_noise = noise - previous * 0.92
        previous = noise
        shimmer = math.sin(2 * math.pi * (2700 + 6500 * progress * progress) * t)
        flutter = math.sin(2 * math.pi * (4200 + 1300 * math.sin(2 * math.pi * 3.2 * t)) * t)
        samples[index] = envelope * (0.38 * high_noise + 0.095 * shimmer + 0.055 * flutter)
    # A short soft high-frequency landing replaces per-card ticks.
    landing = round((duration - 0.11) * sample_rate)
    for index in range(max(0, landing), frames):
        t = (index - landing) / sample_rate
        samples[index] += 0.12 * math.exp(-t / 0.026) * math.sin(2 * math.pi * 2300 * t)
    peak = max(max(abs(sample) for sample in samples), 1e-9)
    scale = 0.24 / peak
    pcm = bytearray()
    for sample in samples:
        value = max(-32768, min(32767, round(sample * scale * 32767)))
        pcm.extend(struct.pack("<hh", value, value))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm)


def provision_user_approved_h2(project: Path) -> tuple[Path, str]:
    """Use only the explicitly provisioned project-local H2 asset."""
    target = project / "06_music_音乐/H2-用户确认原片高频音效层.wav"
    if not target.is_file():
        raise FileNotFoundError(
            "Project-local H2 asset is missing. Provision an authorized file at "
            f"{target} and record its approval before rendering."
        )
    return target, hashlib.sha256(target.read_bytes()).hexdigest()


def select_bgm(project: Path, version: str) -> Path:
    if version == "v4":
        candidates = sorted((project / "06_music_音乐").glob("v4-*-original-bgm.mp3"))
        if len(candidates) != 1:
            raise RuntimeError(f"V4 requires exactly one project-specific BGM, found {len(candidates)}")
        return candidates[0]
    return project / "06_music_音乐/Long Road Ahead B.mp3"


def ensure_unique_scene_assets(scene_dir: Path) -> None:
    expected = [scene_dir / f"S{index:02d}.png" for index in range(1, 13)]
    missing = [str(path) for path in expected if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing V4 scene assets: {missing}")
    hashes = {hashlib.sha256(path.read_bytes()).hexdigest() for path in expected}
    if len(hashes) != len(expected):
        raise RuntimeError("V4 requires 12 unique scene-image files; duplicate image bytes found")


def fit_background(path: Path) -> Image.Image:
    return ImageOps.fit(Image.open(path).convert("RGB"), (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)


def compose_real_cover(project: Path, scene_dir: Path, version: str) -> Path:
    sources = sorted(scene_dir.glob("S*.png"))
    if not sources:
        raise FileNotFoundError("No approved scene images are available")
    cover = project / "01_research_资料搜集/sources/cover/cover.jpg"
    if not cover.is_file():
        matches = list((project / "01_research_资料搜集/sources/cover").glob("*"))
        cover = next((item for item in matches if item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}), cover)
    if not cover.is_file():
        raise FileNotFoundError("No real WeRead cover is available")
    # S03 is reserved for the book reveal, so the title card does not repeat
    # the same visual as the following thesis scene (S02).
    reveal_background = scene_dir / "S03.png"
    canvas = fit_background(reveal_background if reveal_background.is_file() else sources[min(2, len(sources) - 1)]).convert("RGBA")
    canvas.alpha_composite(Image.new("RGBA", canvas.size, (0, 0, 0, 126)))
    book = Image.open(cover).convert("RGBA")
    max_height = 560
    ratio = min(330 / book.width, max_height / book.height)
    book = book.resize((round(book.width * ratio), round(book.height * ratio)), Image.Resampling.LANCZOS)
    x = (WIDTH - book.width) // 2
    y = 275
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((x + 18, y + 22, x + book.width + 18, y + book.height + 22), radius=12, fill=(0, 0, 0, 190))
    shadow = shadow.filter(ImageFilter.GaussianBlur(13))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(book, (x, y))
    output = project / f"03_images_生成图片/{version}/book-cover-composite.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, quality=95)
    return output


def make_topic_cards(
    project: Path,
    style: dict[str, Any],
    topics: list[dict[str, str]],
    output_dir: Path,
    scene_dir: Path | None = None,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    # V4 deliberately stores its independently generated assets under
    # ``approved/v4``.  The former root-only lookup made V4 intro cards reuse
    # assets from a prior version (or fail for a clean V4 project).
    source_dir = scene_dir or project / "03_images_生成图片/approved"
    scenes = sorted(source_dir.glob("S*.png"))
    if not scenes:
        raise FileNotFoundError("No scene images available for topic cards")
    title_font = v2.font(style, "title", 88)
    english_font = v2.font(style, "english", 29)
    cards: list[Path] = []
    for index, topic in enumerate(topics[:8], start=1):
        canvas = fit_background(scenes[(index - 1) % len(scenes)]).convert("RGBA")
        canvas.alpha_composite(Image.new("RGBA", canvas.size, (0, 0, 0, 136)))
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle((45, 55, WIDTH - 45, HEIGHT - 55), radius=26, outline=(236, 230, 218, 130), width=2)
        zh = topic["zh"]
        en = topic["en"]
        zh_width, _ = v2.text_size(draw, zh, title_font, 3)
        draw.text(((WIDTH - zh_width) / 2, 525), zh, font=title_font, fill=(250, 247, 240, 255), stroke_width=3, stroke_fill=(0, 0, 0, 220))
        en_width, _ = v2.text_size(draw, en, english_font, 1)
        draw.rectangle(((WIDTH - 82) / 2, 650, (WIDTH + 82) / 2, 655), fill=(183, 96, 49, 240))
        draw.text(((WIDTH - en_width) / 2, 680), en, font=english_font, fill=(230, 224, 214, 240), stroke_width=1, stroke_fill=(0, 0, 0, 180))
        output = output_dir / f"topic-{index:02d}.png"
        canvas.convert("RGB").save(output)
        cards.append(output)
    return cards


def build_title_layer(
    style: dict[str, Any], title: str, author: str, width: int, height: int
) -> tuple[Image.Image, dict[str, Any]]:
    scale = width / WIDTH
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    config = style.get("title_layout", {})
    safe_margin = round(int(config.get("safe_margin_x_px", 56)) * scale)
    max_width = width - safe_margin * 2
    stroke = max(1, round(3 * scale))
    title_loader = lambda size: v2.font(style, "title", size)
    layout = fit_book_title(
        draw,
        title,
        title_loader,
        max_width=max_width,
        max_font_size=round(int(config.get("max_font_size_px", 70)) * scale),
        min_font_size=round(int(config.get("min_font_size_px", 34)) * scale),
        stroke_width=stroke,
    )
    title_font = title_loader(layout.font_size)
    top_key = "top_px_tall" if height / width >= 2 else "top_px"
    y = round(int(config.get(top_key, 104 if height / width >= 2 else 62)) * scale)
    line_gap = round(int(config.get("line_gap_px", 8)) * scale)
    for label in layout.lines:
        box = text_box(draw, label, title_font, stroke)
        draw.text(
            (centered_text_x(draw, label, title_font, width, stroke), y - box[1]),
            label,
            font=title_font,
            fill=(250, 247, 240, 255),
            stroke_width=stroke,
            stroke_fill=(0, 0, 0, 230),
        )
        y += box[3] - box[1] + line_gap

    rule_y = y - line_gap + round(int(config.get("rule_gap_px", 14)) * scale)
    draw.rectangle(((width - 88 * scale) / 2, rule_y, (width + 88 * scale) / 2, rule_y + max(4, round(5 * scale))), fill=(183, 96, 49, 245))
    byline = f"{author}／著"
    author_stroke = max(1, round(2 * scale))
    author_loader = lambda size: v2.chinese_font(style, size, title_weight=True)
    author_size = fit_single_line_font_size(
        draw,
        byline,
        author_loader,
        max_width=max_width,
        max_font_size=round(int(config.get("author_max_font_size_px", 31)) * scale),
        min_font_size=round(int(config.get("author_min_font_size_px", 20)) * scale),
        stroke_width=author_stroke,
    )
    author_font = author_loader(author_size)
    author_y = rule_y + round(int(config.get("author_gap_px", 20)) * scale)
    author_box = text_box(draw, byline, author_font, author_stroke)
    draw.text(
        (centered_text_x(draw, byline, author_font, width, author_stroke), author_y - author_box[1]),
        byline,
        font=author_font,
        fill=(234, 229, 220, 250),
        stroke_width=author_stroke,
        stroke_fill=(0, 0, 0, 215),
    )
    report = {
        "schema_version": "1.0",
        "title": title,
        "author": author,
        "canvas": {"width": width, "height": height},
        "safe_area": {
            "left": safe_margin,
            "right": width - safe_margin,
            "max_width": max_width,
        },
        "title_layout": {
            "lines": list(layout.lines),
            "line_widths": list(layout.line_widths),
            "font_size": layout.font_size,
            "overflow": any(line_width > max_width for line_width in layout.line_widths),
        },
        "author_layout": {"font_size": author_size},
    }
    return canvas, report


def render_title(style: dict[str, Any], title: str, author: str, width: int, height: int) -> Image.Image:
    return build_title_layer(style, title, author, width, height)[0]


def make_overlays(style: dict[str, Any], lines: list[v2.TimedLine], output_dir: Path, title: str, author: str, title_start: float, voice_end: float) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    overlays: list[dict[str, Any]] = []
    title_path = output_dir / "title.png"
    title_layer, title_layout = build_title_layer(style, title, author, WIDTH, HEIGHT)
    title_layer.save(title_path)
    write_json(output_dir / "title.layout.json", title_layout)
    overlays.append({"path": title_path, "start": title_start, "end": voice_end, "kind": "title"})
    brand_path = output_dir / "brand.png"
    v2.render_brand_layer(style, WIDTH, HEIGHT).save(brand_path)
    overlays.append({"path": brand_path, "start": 0.0, "end": voice_end + OUTRO_SECONDS, "kind": "brand"})
    for line in lines:
        caption_path = output_dir / f"{line.line_id}.png"
        v2.render_caption_layer(style, line, WIDTH, HEIGHT, "bilingual").save(caption_path)
        overlays.append({"path": caption_path, "start": line.start, "end": line.end, "kind": "caption", "line_id": line.line_id})
    return overlays


def default_topics() -> list[dict[str, str]]:
    return [
        {"zh": "关系", "en": "RELATION"}, {"zh": "边界", "en": "BOUNDARY"},
        {"zh": "情绪", "en": "EMOTION"}, {"zh": "自我", "en": "SELF"},
        {"zh": "选择", "en": "CHOICE"}, {"zh": "成长", "en": "GROWTH"},
        {"zh": "勇气", "en": "COURAGE"}, {"zh": "自由", "en": "FREEDOM"},
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a batch book-video pilot")
    parser.add_argument("project", type=Path)
    parser.add_argument("--style", type=Path, default=STYLE_PATH)
    parser.add_argument("--release-version", choices=["v3", "v4"], default="v3")
    args = parser.parse_args()
    project = args.project.resolve()
    version = args.release_version
    style = read_json(args.style.resolve())
    if version == "v4":
        validate_style_profile(style)
    script = read_json(project / "02_story_script_故事脚本/script.v2.bilingual.json")
    source_voice = project / "05_voice_人声/v3-b-locked-master.wav"
    source_asr = project / "05_voice_人声/asr-v3/v3-b-locked-master.json"
    if not source_voice.is_file() or not source_asr.is_file():
        raise FileNotFoundError("Generate v3-b-locked-master.wav and its ASR JSON before rendering")
    voice, asr = asr_with_intro_pause(
        source_voice, source_asr, script,
        project / "05_voice_人声/v3-b-locked-master-paused.wav",
        project / "05_voice_人声/asr-v3-paused/v3-b-locked-master-paused.json",
    )
    voice_duration = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(voice)], capture=True).stdout.strip())
    total_duration = round(voice_duration + OUTRO_SECONDS, 3)
    lines, montage_start, montage_end = align_lines(script, asr)
    scene_dir = project / "03_images_生成图片/approved"
    if version == "v4":
        scene_dir = scene_dir / "v4"
        ensure_unique_scene_assets(scene_dir)
    cover = compose_real_cover(project, scene_dir, version)
    # The established V2 timeline builder names its BOOK scene with this
    # legacy location. Mirror the V3 composite for compatibility while keeping
    # the generated asset in the V3 directory as the canonical source.
    legacy_cover = project / "03_images_生成图片/v2/book-cover-composite.png"
    legacy_cover.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cover, legacy_cover)
    timeline_dir = project / f"07_timeline_时间线/{version}"
    topics = script.get("intro_topics") or default_topics()
    cards = make_topic_cards(project, style, topics, timeline_dir / "topic-cards", scene_dir)
    if len(cards) < 8:
        raise RuntimeError("Need eight topic cards")
    timeline = v2.create_scene_timeline(lines, montage_start, montage_end, total_duration)
    if version == "v4":
        for scene in timeline:
            if scene["asset"].startswith("03_images_生成图片/approved/S"):
                filename = Path(scene["asset"]).name
                scene["asset"] = str(Path("03_images_生成图片/approved/v4") / filename)
            elif scene["id"] == "BOOK":
                scene["asset"] = str(cover.relative_to(project))
    v2.write_subtitles(timeline_dir, lines)
    overlays = make_overlays(style, lines, timeline_dir / "overlays/bilingual-3x4", script["book"]["title"], script["book"]["author"], montage_end, voice_duration)
    base = v2.render_base_video(project, timeline, cards, timeline_dir)
    stinger, h2_sha256 = provision_user_approved_h2(project)
    bgm = select_bgm(project, version)
    if not bgm.is_file():
        raise FileNotFoundError("Licensed BGM must be present in 06_music_音乐")
    slug = str(read_json(project / "project.json")["project_id"])
    render_path = project / f"08_render_合成/{version}" / f"{slug}-{version}-bilingual-3x4.mp4"
    v2.render_variant(base, overlays, voice, bgm, stinger, total_duration, montage_start, montage_end, render_path, WIDTH, HEIGHT, style)
    delivery = project / f"10_delivery_交付/{version}"
    delivery.mkdir(parents=True, exist_ok=True)
    shutil.copy2(render_path, delivery / render_path.name)
    for subtitle in timeline_dir.glob("subtitles.v2.*.srt"):
        shutil.copy2(subtitle, delivery / subtitle.name.replace("v2", version))
    cover_manifest = project / "01_research_资料搜集/sources/cover/cover_manifest.json"
    if cover_manifest.is_file():
        shutil.copy2(cover_manifest, delivery / "BOOK_COVER_SOURCE.json")
    attribution = project / "06_music_音乐/ATTRIBUTION.txt"
    if attribution.is_file():
        shutil.copy2(attribution, delivery / "MUSIC_ATTRIBUTION.txt")
    media = v2.probe(render_path)
    video = next(stream for stream in media["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in media["streams"] if stream["codec_type"] == "audio")
    manifest = {
        "schema_version": "3.0",
        "project_id": slug,
        "script_version": script["version"],
        "voice": str(voice.relative_to(project)),
        "voice_duration_seconds": voice_duration,
        "montage": {"start": montage_start, "end": montage_end, "duration": round(montage_end - montage_start, 3), "card_count": len(cards)},
        "intro_sfx": {
            "id": "user_approved_h2_original_high_frequency_layer",
            "user_approved_reuse": True,
            "file": str(stinger.relative_to(project)),
            "sha256": h2_sha256,
        },
        "book_cover_composite": str(cover.relative_to(project)),
        "lines": [line.__dict__ for line in lines],
        "timeline": timeline,
        "translation_status": script["translation_status"],
        "output": str(render_path.relative_to(project)),
    }
    write_json(timeline_dir / f"render_manifest.{version}.json", manifest)
    shutil.copy2(timeline_dir / f"render_manifest.{version}.json", delivery / f"render_manifest.{version}.json")
    qc = {
        "status": "pass" if video["width"] == WIDTH and video["height"] == HEIGHT and audio["codec_name"] == "aac" else "fail",
        "checks": {
            "output_dimensions": [video["width"], video["height"]],
            "topic_card_count": len(cards),
            "real_cover_composited": cover.is_file(),
            "user_approved_h2_directly_used": True,
            "translation_native_review_pending": script["translation_status"] != "native_approved",
            "cover_rights_review_pending": True,
        },
        "audio": v2.loudness(render_path),
        "output": str(render_path.relative_to(project)),
    }
    write_json(project / "09_qc_质检" / f"qc_report.{version}.json", qc)
    state_path = project / "project.json"
    state = read_json(state_path)
    state.update({"status": f"{version}_ready" if qc["status"] == "pass" else f"{version}_qc_failed", "current_stage": f"10_delivery_{version}", "final_output": str((delivery / render_path.name).relative_to(project))})
    write_json(state_path, state)
    print(json.dumps({"project": slug, "output": str(delivery / render_path.name), "qc": qc["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
