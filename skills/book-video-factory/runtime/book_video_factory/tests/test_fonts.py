from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import ImageFont


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from book_video_factory.fonts import (  # noqa: E402
    FontConfigurationError,
    resolve_font_path,
)


def test_font_bytes() -> bytes:
    """Return Pillow's embedded test font; never use it as a production fallback."""

    font = ImageFont.load_default(size=16)
    return font.font_bytes


def base_config() -> dict[str, object]:
    return {
        "title": "",
        "chinese": "",
        "english": "",
        "chinese_body_index": 0,
        "environment": {
            "title": "BOOK_VIDEO_TITLE_FONT",
            "chinese": "BOOK_VIDEO_CHINESE_FONT",
            "english": "BOOK_VIDEO_ENGLISH_FONT",
            "search_dirs": "BOOK_VIDEO_FONT_DIRS",
        },
        "system_candidates": {"title": [], "chinese": [], "english": []},
        "bundled_fallback": "",
    }


class FontContractTests(unittest.TestCase):
    def write_font(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(test_font_bytes())
        return path.resolve()

    def test_explicit_environment_font_is_openable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            explicit = self.write_font(root / "licensed test font.ttf")
            resolved = resolve_font_path(
                root,
                base_config(),
                "title",
                environ={"BOOK_VIDEO_TITLE_FONT": str(explicit)},
                platform_name="Windows",
            )
            self.assertEqual(resolved, explicit)

    def test_invalid_explicit_environment_path_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing = root / "missing.ttf"
            with self.assertRaisesRegex(FontConfigurationError, "does not exist"):
                resolve_font_path(
                    root,
                    base_config(),
                    "title",
                    environ={"BOOK_VIDEO_TITLE_FONT": str(missing)},
                    platform_name="Windows",
                )

    def test_invalid_font_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            invalid = root / "invalid.ttf"
            invalid.write_text("not a font", encoding="utf-8")
            config = base_config()
            config["title"] = str(invalid)
            with self.assertRaisesRegex(FontConfigurationError, "cannot be opened"):
                resolve_font_path(
                    root, config, "title", environ={}, platform_name="Windows"
                )

    def test_profile_explicit_relative_font_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected = self.write_font(root / "fonts" / "profile.ttf")
            config = base_config()
            config["title"] = "fonts/profile.ttf"
            self.assertEqual(
                resolve_font_path(
                    root, config, "title", environ={}, platform_name="Linux"
                ),
                expected,
            )

    def test_windows_system_font_candidate_is_discovered(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            windows = root / "Windows"
            expected = self.write_font(windows / "Fonts" / "approved.ttf")
            config = base_config()
            config["system_candidates"] = {
                "title": ["approved.ttf"],
                "chinese": [],
                "english": [],
            }
            resolved = resolve_font_path(
                root,
                config,
                "title",
                environ={"WINDIR": str(windows)},
                platform_name="Windows",
            )
            self.assertEqual(resolved, expected)

    def test_missing_system_font_candidate_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = base_config()
            config["system_candidates"] = {
                "title": ["missing.ttf"],
                "chinese": [],
                "english": [],
            }
            with self.assertRaisesRegex(FontConfigurationError, "No usable title font"):
                resolve_font_path(
                    root,
                    config,
                    "title",
                    environ={"WINDIR": str(root / "Windows")},
                    platform_name="Windows",
                )

    def test_licensed_bundled_fallback_is_supported_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected = self.write_font(root / "resources" / "fonts" / "approved.ttf")
            config = base_config()
            config["bundled_fallback"] = "resources/fonts/approved.ttf"
            self.assertEqual(
                resolve_font_path(
                    root, config, "title", environ={}, platform_name="Linux"
                ),
                expected,
            )

    def test_all_sources_unavailable_fail_closed_with_remediation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                FontConfigurationError, "Set BOOK_VIDEO_TITLE_FONT"
            ):
                resolve_font_path(
                    Path(temporary),
                    base_config(),
                    "title",
                    environ={},
                    platform_name="Linux",
                )

    def test_search_directory_environment_is_portable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "empty"
            second = root / "approved"
            first.mkdir()
            expected = self.write_font(second / "portable.ttf")
            config = base_config()
            config["system_candidates"] = {
                "title": ["portable.ttf"],
                "chinese": [],
                "english": [],
            }
            resolved = resolve_font_path(
                root,
                config,
                "title",
                environ={
                    "BOOK_VIDEO_FONT_DIRS": os.pathsep.join(
                        (str(first), str(second))
                    )
                },
                platform_name="Linux",
            )
            self.assertEqual(resolved, expected)


if __name__ == "__main__":
    unittest.main()
