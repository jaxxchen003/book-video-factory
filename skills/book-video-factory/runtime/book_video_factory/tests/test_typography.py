from __future__ import annotations

import sys
import unittest
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from book_video_factory.typography import fit_book_title  # noqa: E402


class BookTitleLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.font_path = ROOT / "resources/fonts/SmileySans-Oblique.otf"
        cls.draw = ImageDraw.Draw(Image.new("RGBA", (720, 960)))

    def font_loader(self, size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(self.font_path), size=size)

    def assert_safe(self, title: str) -> None:
        layout = fit_book_title(
            self.draw,
            title,
            self.font_loader,
            max_width=608,
            max_font_size=70,
            min_font_size=34,
            stroke_width=3,
        )
        self.assertLessEqual(len(layout.lines), 2)
        self.assertTrue(all(width <= 608 for width in layout.line_widths))

    def test_long_titles_fit_inside_v4_safe_area(self) -> None:
        for title in (
            "允许一切发生：过不紧绷松弛的人生",
            "自卑与超越（完整全译本）",
            "当你开始爱自己，全世界都会来爱你",
            "原生家庭：如何修补自己的性格缺陷",
        ):
            with self.subTest(title=title):
                self.assert_safe(title)

    def test_prefers_semantic_break_before_parenthetical_subtitle(self) -> None:
        layout = fit_book_title(
            self.draw,
            "自卑与超越（完整全译本）",
            self.font_loader,
            max_width=608,
            max_font_size=70,
            min_font_size=34,
            stroke_width=3,
        )
        self.assertEqual(layout.lines, ("《自卑与超越", "（完整全译本）》"))

    def test_semantic_break_can_trade_a_little_font_size(self) -> None:
        layout = fit_book_title(
            self.draw,
            "原生家庭：如何修补自己的性格缺陷",
            self.font_loader,
            max_width=608,
            max_font_size=70,
            min_font_size=34,
            stroke_width=3,
        )
        self.assertEqual(layout.lines, ("《原生家庭：", "如何修补自己的性格缺陷》"))


if __name__ == "__main__":
    unittest.main()
