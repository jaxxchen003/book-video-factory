#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from book_video_factory.project import initialize_project
from book_video_factory.style_profiles import (
    DEFAULT_STYLE_PROFILE_ID,
    available_style_profile_ids,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize one book-video project")
    parser.add_argument("--warehouse", type=Path, required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--book-title", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--reference-video", type=Path)
    parser.add_argument(
        "--mode",
        choices=("single-book", "content-system-backed"),
        default="single-book",
    )
    parser.add_argument(
        "--release-profile",
        default=None,
        help=(
            "Compatibility assertion only. If supplied, it must equal the release "
            "profile mapped by --style-profile."
        ),
    )
    parser.add_argument(
        "--style-profile",
        choices=available_style_profile_ids(),
        default=DEFAULT_STYLE_PROFILE_ID,
    )
    parser.add_argument(
        "--generation-lane",
        help="Required for VOX style projects: gemini-api or google-flow.",
    )
    args = parser.parse_args()
    project = initialize_project(
        args.warehouse,
        args.slug,
        args.book_title,
        args.author,
        args.reference_video,
        args.mode,
        args.release_profile,
        args.style_profile,
        args.generation_lane,
    )
    print(project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
