#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from book_video_factory.weread import WeReadError, collect_book_source_pack


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect public WeChat Reading material for one book"
    )
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--author")
    args = parser.parse_args()
    try:
        pack = collect_book_source_pack(args.project, args.title, args.author)
    except WeReadError as exc:
        parser.exit(2, f"collection failed: {exc}\n")
    summary = {
        "book_id": pack["book"]["book_id"],
        "title": pack["book"]["title"],
        "author": pack["book"]["author"],
        "chapters": len(pack["chapter_outline"]),
        "popular_highlights": len(pack["popular_highlights"]),
        "public_reviews": len(pack["public_reviews"]),
        "output": str(
            args.project.resolve()
            / "01_research_资料搜集"
            / "normalized"
            / "book_source_pack.json"
        ),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
