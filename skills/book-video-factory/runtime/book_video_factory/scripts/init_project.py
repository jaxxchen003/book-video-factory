#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from book_video_factory.project import initialize_project


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
        default="book-v4-bilingual-3x4",
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
    )
    print(project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
