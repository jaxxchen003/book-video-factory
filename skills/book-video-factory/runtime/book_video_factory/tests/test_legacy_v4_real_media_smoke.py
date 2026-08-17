from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from book_video_factory.smoke.legacy_v4_real_media import (  # noqa: E402
    EXPECTED_OUTPUT_TICKS,
    SmokeFixtureError,
    compare_probes,
    initialize_fixture_root,
    validate_fixture_root,
)


class SmokeMarkerTests(unittest.TestCase):
    def test_marker_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(SmokeFixtureError):
                validate_fixture_root(Path(temp))

    def test_initializer_writes_strict_nonproduction_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "fixture"
            marker_path = initialize_fixture_root(root)
            marker = validate_fixture_root(root)
            self.assertTrue(marker_path.is_file())
            self.assertFalse(marker["production_use"])
            self.assertEqual(marker["expected_output_duration_ticks"], EXPECTED_OUTPUT_TICKS)
            self.assertEqual(marker["visual_motif_families"], 3)
            self.assertEqual(marker["v4_scene_assets"], 12)

    def test_initializer_refuses_nonempty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "production.txt").write_text("do not touch", encoding="utf-8")
            with self.assertRaises(SmokeFixtureError):
                initialize_fixture_root(root)


class SmokeComparisonTests(unittest.TestCase):
    def test_duration_within_one_frame_passes(self) -> None:
        base = {
            "sha256": "a",
            "format_name": "mov,mp4",
            "format_duration": "11.520000",
            "video_stream_count": 1,
            "audio_stream_count": 1,
            "video": {
                "codec_name": "h264", "width": 720, "height": 960,
                "r_frame_rate": "30/1", "avg_frame_rate": "30/1",
                "pix_fmt": "yuv420p", "rotation": None,
                "sample_aspect_ratio": "1:1", "display_aspect_ratio": "3:4",
            },
            "audio": {
                "codec_name": "aac", "sample_rate": "48000", "channels": 2,
                "channel_layout": "stereo",
            },
        }
        facade = json.loads(json.dumps(base))
        facade["sha256"] = "b"
        facade["format_duration"] = "11.535000"
        comparison = compare_probes(base, facade)
        self.assertTrue(comparison["passed"])
        self.assertFalse(comparison["bitwise_equal"])


if __name__ == "__main__":
    unittest.main()
