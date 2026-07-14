#!/usr/bin/env python3
"""Search Freesound for license-filtered BGM candidates without downloading media."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from book_video_factory.freesound import (
    FreesoundClient,
    FreesoundError,
    normalize_candidates,
    write_candidate_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write auditable, noncommercial-preview Freesound BGM candidates"
    )
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--intent", required=True)
    parser.add_argument(
        "--query",
        help="Concise English Freesound keywords. Defaults to --intent; do not pass a full prose brief here.",
    )
    parser.add_argument("--min-duration", type=float, default=55.0)
    parser.add_argument("--max-duration", type=float, default=360.0)
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()
    if not (args.project / "project.json").is_file():
        raise FileNotFoundError(f"Project manifest not found: {args.project / 'project.json'}")
    if args.limit <= 0:
        raise FreesoundError("--limit must be positive")
    search_query = args.query or args.intent
    client = FreesoundClient()
    raw_payload = client.search_bgm(
        search_query,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        page_size=max(args.limit * 4, 24),
    )
    candidates, rejected_count = normalize_candidates(
        raw_payload["results"],
        intent=args.intent,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        limit=args.limit,
    )
    output = write_candidate_manifest(
        args.project,
        intent=args.intent,
        search_query=search_query,
        raw_payload=raw_payload,
        candidates=candidates,
        rejected_count=rejected_count,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
    )
    print(
        json.dumps(
            {
                "manifest": str(output),
                "candidates": len(candidates),
                "status": "noncommercial_preview_only",
                "downloaded_media": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FreesoundError as exc:
        raise SystemExit(f"Freesound BGM search failed: {exc}")
