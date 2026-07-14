#!/usr/bin/env python3
"""Download and audit the actual cover referenced by a WeRead source pack.

The source pack is the single source of truth for the book record; this helper
never guesses a cover URL and does not embed credentials in artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import _bootstrap  # noqa: F401
from PIL import Image

from book_video_factory.weread import trusted_ssl_context


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extension_for(url: str, content_type: str | None) -> str:
    if content_type:
        mime = content_type.partition(";")[0].strip().lower()
        if mime in {"image/jpeg", "image/jpg"}:
            return ".jpg"
        if mime == "image/png":
            return ".png"
        if mime == "image/webp":
            return ".webp"
    guessed = Path(urllib.parse.urlparse(url).path).suffix.lower()
    return guessed if guessed in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a real cover from a WeRead source pack")
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    source_pack_path = project / "01_research_资料搜集/normalized/book_source_pack.json"
    source_pack = read_json(source_pack_path)
    book = source_pack["book"]
    cover_url = str(book.get("cover_url") or "").strip()
    if not cover_url:
        raise RuntimeError("WeRead source pack does not contain book.cover_url")

    request = urllib.request.Request(cover_url, headers={"User-Agent": "BookVideoFactory/1.0"})
    with urllib.request.urlopen(request, timeout=30, context=trusted_ssl_context()) as response:
        data = response.read()
        content_type = response.headers.get("Content-Type")
        resolved_url = response.geturl()
    if not data:
        raise RuntimeError("Downloaded cover is empty")
    extension = extension_for(resolved_url, content_type)
    cover_dir = project / "01_research_资料搜集/sources/cover"
    cover_dir.mkdir(parents=True, exist_ok=True)
    cover_path = cover_dir / f"weread-cover{extension}"
    cover_path.write_bytes(data)
    with Image.open(cover_path) as image:
        width, height = image.size
        image.verify()
    sha256 = hashlib.sha256(data).hexdigest()
    manifest = {
        "schema_version": "1.1",
        "source_type": "book_cover_metadata_asset",
        "provider": "WeChat Reading Agent Gateway",
        "source_url": resolved_url,
        "source_record": "01_research_资料搜集/normalized/book_source_pack.json",
        "book_id": book.get("book_id"),
        "title": book.get("title"),
        "author": book.get("author"),
        "local_file": str(cover_path.relative_to(project)),
        "downloaded_at": datetime.now(UTC).isoformat(),
        "content_type": content_type,
        "dimensions": [width, height],
        "sha256": sha256,
        "rights_status": "editorial_reference_pending_platform_rights_review",
        "rights_note": "The cover is retained with its source record for editorial preview and must be cleared before public commercial release.",
    }
    write_json(cover_dir / "cover_manifest.json", manifest)
    print(json.dumps({"cover": str(cover_path), "sha256": sha256, "dimensions": [width, height]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
