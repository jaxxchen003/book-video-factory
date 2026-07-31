from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))

import build_final_video_v2 as renderer  # noqa: E402
from book_video_factory.fonts import FontConfigurationError  # noqa: E402
from book_video_factory.scene_contract import V4_SCENE_LINE_CONTRACT  # noqa: E402


class RendererPortabilityTests(unittest.TestCase):
    def test_missing_all_fonts_fails_closed(self) -> None:
        style = json.loads((ROOT / "config/video_style_v2.json").read_text(encoding="utf-8"))
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(FontConfigurationError, "No usable title font"):
                renderer.resolved_font_path(style, "title")

    def test_v4_scene_line_contract_matches_renderer_behavior(self) -> None:
        self.assertEqual(V4_SCENE_LINE_CONTRACT["S01"], ("V01", "V02"))
        self.assertEqual(V4_SCENE_LINE_CONTRACT["S02"], ("V04",))
        self.assertEqual(V4_SCENE_LINE_CONTRACT["S03"], ("V03",))
        self.assertEqual(V4_SCENE_LINE_CONTRACT["S12"], ("V15",))
        lines = [
            renderer.TimedLine(
                line_id=f"V{index:02d}",
                role="line",
                zh="中",
                en="English",
                start=float(index),
                end=float(index) + 0.5,
            )
            for index in range(1, 16)
        ]
        timeline = renderer.create_scene_timeline(lines, 2.5, 3.5, 18.0)
        scenes = {item["id"]: item for item in timeline}
        self.assertEqual(scenes["HOOK"]["lines"], ["V01", "V02"])
        self.assertEqual(scenes["BOOK"]["lines"], ["V03"])
        self.assertEqual(scenes["THESIS"]["lines"], ["V04"])


if __name__ == "__main__":
    unittest.main()
