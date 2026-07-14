from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_final_video_v2 as renderer  # noqa: E402


class RendererPortabilityTests(unittest.TestCase):
    def test_missing_system_fonts_fall_back_to_bundled_ofl_font(self) -> None:
        style = json.loads((ROOT / "config/video_style_v2.json").read_text(encoding="utf-8"))
        style = copy.deepcopy(style)
        style["fonts"]["chinese"] = "/missing/chinese-font.ttf"
        style["fonts"]["english"] = "/missing/english-font.ttf"
        expected = ROOT / "resources/fonts/SmileySans-Oblique.otf"
        self.assertEqual(renderer.resolved_font_path(style, "chinese"), expected)
        self.assertEqual(renderer.resolved_font_path(style, "english"), expected)


if __name__ == "__main__":
    unittest.main()
