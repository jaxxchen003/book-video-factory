from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PIL import ImageDraw, ImageFont


FontLoader = Callable[[int], ImageFont.FreeTypeFont]


@dataclass(frozen=True)
class BookTitleLayout:
    font_size: int
    lines: tuple[str, ...]
    line_widths: tuple[int, ...]


def text_box(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    stroke_width: int = 0,
) -> tuple[int, int, int, int]:
    return draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)


def centered_text_x(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    canvas_width: int,
    stroke_width: int = 0,
) -> float:
    left, _, right, _ = text_box(draw, text, font, stroke_width)
    return (canvas_width - (right - left)) / 2 - left


def _split_candidates(title: str) -> list[tuple[tuple[str, str], int]]:
    candidates: list[tuple[tuple[str, str], int]] = []
    for index in range(1, len(title)):
        left = title[:index].rstrip()
        right = title[index:].lstrip()
        if not left or not right:
            continue
        previous = title[index - 1]
        following = title[index]
        if previous in "：:；;，,。！？!?—-" or following in "（([【《":
            semantic_penalty = 0
        elif previous.isspace() or following.isspace():
            semantic_penalty = 1
        else:
            semantic_penalty = 8
        candidates.append(((f"《{left}", f"{right}》"), semantic_penalty))
    return candidates


def fit_book_title(
    draw: ImageDraw.ImageDraw,
    title: str,
    font_loader: FontLoader,
    *,
    max_width: int,
    max_font_size: int,
    min_font_size: int,
    stroke_width: int = 0,
) -> BookTitleLayout:
    """Fit a book title into one or two measured lines without cropping."""
    normalized = " ".join(title.split()).strip()
    if not normalized:
        raise ValueError("book title must not be empty")
    if min_font_size <= 0 or max_font_size < min_font_size:
        raise ValueError("invalid title font-size range")

    one_line = f"《{normalized}》"
    splits = _split_candidates(normalized)
    fitting_across_sizes: list[
        tuple[int, int, int, tuple[str, str], tuple[int, int]]
    ] = []
    for size in range(max_font_size, min_font_size - 1, -1):
        font = font_loader(size)
        one_box = text_box(draw, one_line, font, stroke_width)
        one_width = one_box[2] - one_box[0]
        if size == max_font_size and one_width <= max_width:
            return BookTitleLayout(size, (one_line,), (one_width,))

        for lines, semantic_penalty in splits:
            boxes = [text_box(draw, line, font, stroke_width) for line in lines]
            widths = tuple(box[2] - box[0] for box in boxes)
            if max(widths) <= max_width:
                fitting_across_sizes.append(
                    (
                        semantic_penalty,
                        -size,
                        abs(widths[0] - widths[1]),
                        lines,
                        widths,
                    )
                )

    if fitting_across_sizes:
        _, negative_size, _, lines, widths = min(
            fitting_across_sizes,
            key=lambda item: (item[0], item[1], item[2], max(item[4])),
        )
        return BookTitleLayout(-negative_size, lines, widths)

    raise ValueError(
        f"book title cannot fit within {max_width}px using up to two lines "
        f"at {min_font_size}px: {title!r}"
    )


def fit_single_line_font_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_loader: FontLoader,
    *,
    max_width: int,
    max_font_size: int,
    min_font_size: int,
    stroke_width: int = 0,
) -> int:
    for size in range(max_font_size, min_font_size - 1, -1):
        font = font_loader(size)
        left, _, right, _ = text_box(draw, text, font, stroke_width)
        if right - left <= max_width:
            return size
    raise ValueError(f"text cannot fit within {max_width}px: {text!r}")
