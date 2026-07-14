from __future__ import annotations

import json
import os
import ssl
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .project import write_json


GATEWAY_URL = "https://i.weread.qq.com/api/agent/gateway"
SKILL_VERSION = "1.0.4"


class WeReadError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_api_key() -> str:
    env_value = os.environ.get("WEREAD_API_KEY", "").strip()
    if env_value:
        return env_value
    if os.uname().sysname == "Darwin":
        completed = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                "codex-weread-api-key",
                "-w",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            return completed.stdout.strip()
    raise WeReadError(
        "WeChat Reading credential not found in WEREAD_API_KEY or macOS Keychain"
    )


def trusted_ssl_context() -> ssl.SSLContext:
    """Build a verified TLS context for Python installs without a default CA path."""
    configured = os.environ.get("SSL_CERT_FILE", "").strip()
    candidates = [Path(configured)] if configured else []
    try:
        import certifi  # type: ignore[import-not-found]

        candidates.append(Path(certifi.where()))
    except ImportError:
        pass
    candidates.extend(
        [
            Path("/etc/ssl/cert.pem"),
            Path("/opt/homebrew/etc/openssl@3/cert.pem"),
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return ssl.create_default_context(cafile=str(candidate))
    return ssl.create_default_context()


class WeReadClient:
    def __init__(self, api_key: str | None = None, timeout: int = 30) -> None:
        self._api_key = api_key or load_api_key()
        self._timeout = timeout
        self._ssl_context = trusted_ssl_context()

    def call(self, api_name: str, **params: Any) -> dict[str, Any]:
        body = {"api_name": api_name, **params, "skill_version": SKILL_VERSION}
        request = urllib.request.Request(
            GATEWAY_URL,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "User-Agent": "book-video-factory/0.1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self._timeout, context=self._ssl_context
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise WeReadError(f"WeChat Reading HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise WeReadError(f"WeChat Reading request failed: {exc}") from exc

        if not isinstance(payload, dict):
            raise WeReadError("WeChat Reading returned a non-object response")
        if payload.get("upgrade_info"):
            raise WeReadError(f"WeChat Reading skill upgrade required: {payload['upgrade_info']}")
        return payload


def iter_search_books(search: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for group in search.get("results", []):
        if not isinstance(group, dict):
            continue
        for entry in group.get("books", []):
            if isinstance(entry, dict):
                yield entry


def select_book(
    search: dict[str, Any], title: str, author: str | None = None
) -> dict[str, Any]:
    title_key = title.strip().casefold()
    author_key = author.strip().casefold() if author else None
    exact_title: list[dict[str, Any]] = []
    exact_both: list[dict[str, Any]] = []
    all_books = list(iter_search_books(search))
    for entry in all_books:
        info = entry.get("bookInfo", {})
        if str(info.get("title", "")).strip().casefold() != title_key:
            continue
        exact_title.append(entry)
        if author_key and author_key in str(info.get("author", "")).strip().casefold():
            exact_both.append(entry)
    candidates = exact_both or exact_title
    if not candidates:
        available = [
            {
                "title": item.get("bookInfo", {}).get("title"),
                "author": item.get("bookInfo", {}).get("author"),
                "bookId": item.get("bookInfo", {}).get("bookId"),
            }
            for item in all_books[:10]
        ]
        raise WeReadError(
            f"No exact book match for {title!r}/{author!r}; candidates={available}"
        )
    return candidates[0]


def _review_content(entry: dict[str, Any]) -> dict[str, Any]:
    wrapper = entry.get("review", {})
    review = wrapper.get("review", {}) if isinstance(wrapper, dict) else {}
    if not isinstance(review, dict):
        review = {}
    author = review.get("author", {}) if isinstance(review.get("author"), dict) else {}
    return {
        "review_id": review.get("reviewId"),
        "content": review.get("content"),
        "star": review.get("star"),
        "is_finish": review.get("isFinish"),
        "created_at_unix": review.get("createTime"),
        "author_name": author.get("name"),
    }


def normalize_source_pack(
    selected: dict[str, Any],
    book_info: dict[str, Any],
    chapters: dict[str, Any],
    highlights: dict[str, Any],
    reviews: dict[str, Any],
) -> dict[str, Any]:
    search_info = selected.get("bookInfo", {})
    chapter_by_uid = {
        str(item.get("chapterUid")): item.get("title")
        for item in chapters.get("chapters", [])
        if isinstance(item, dict)
    }
    normalized_highlights = []
    for item in highlights.get("items", []):
        if not isinstance(item, dict):
            continue
        uid = item.get("chapterUid")
        normalized_highlights.append(
            {
                "source_type": "popular_highlight",
                "source_locator": {
                    "chapter_uid": uid,
                    "chapter_title": chapter_by_uid.get(str(uid)),
                    "range": item.get("range"),
                    "bookmark_id": item.get("bookmarkId"),
                },
                "quote": item.get("markText"),
                "reader_highlight_count": item.get("totalCount"),
                "usage_status": "requires_editorial_review",
            }
        )

    normalized_reviews = [
        {"source_type": "public_review", **_review_content(item)}
        for item in reviews.get("reviews", [])
        if isinstance(item, dict)
    ]
    return {
        "schema_version": "1.0",
        "collected_at": utc_now(),
        "provider": "WeChat Reading Agent Gateway",
        "provider_skill_version": SKILL_VERSION,
        "book": {
            "book_id": book_info.get("bookId") or search_info.get("bookId"),
            "title": book_info.get("title") or search_info.get("title"),
            "author": book_info.get("author") or search_info.get("author"),
            "translator": book_info.get("translator"),
            "intro": book_info.get("intro") or search_info.get("intro"),
            "publisher": book_info.get("publisher") or search_info.get("publisher"),
            "publish_time": book_info.get("publishTime"),
            "isbn": book_info.get("isbn"),
            "category": book_info.get("category") or search_info.get("category"),
            "word_count": book_info.get("wordCount"),
            "rating_raw": book_info.get("newRating") or selected.get("newRating"),
            "rating_count": book_info.get("newRatingCount")
            or selected.get("newRatingCount"),
            "cover_url": book_info.get("cover") or search_info.get("cover"),
            "deep_link": book_info.get("deepLink") or search_info.get("deepLink"),
        },
        "chapter_outline": [
            {
                "chapter_uid": item.get("chapterUid"),
                "chapter_index": item.get("chapterIdx"),
                "title": item.get("title"),
                "level": item.get("level"),
                "word_count": item.get("wordCount"),
            }
            for item in chapters.get("chapters", [])
            if isinstance(item, dict)
        ],
        "popular_highlights": normalized_highlights,
        "public_reviews": normalized_reviews,
        "editorial_rules": {
            "do_not_treat_reviews_as_book_facts": True,
            "quotes_require_manual_review": True,
            "do_not_generate_full_book_summary_from_this_pack": True,
        },
    }


def collect_book_source_pack(
    project: Path,
    title: str,
    author: str | None = None,
    client: WeReadClient | None = None,
) -> dict[str, Any]:
    client = client or WeReadClient()
    raw_dir = project.resolve() / "01_research_资料搜集" / "raw"
    normalized_dir = project.resolve() / "01_research_资料搜集" / "normalized"

    search = client.call("/store/search", keyword=title, scope=10)
    selected = select_book(search, title, author)
    info = selected.get("bookInfo", {})
    book_id = str(info.get("bookId", "")).strip()
    if not book_id:
        raise WeReadError("Selected WeChat Reading result has no bookId")

    book_info = client.call("/book/info", bookId=book_id)
    chapters = client.call("/book/chapterinfo", bookId=book_id)
    highlights = client.call(
        "/book/bestbookmarks", bookId=book_id, chapterUid=0, synckey=0
    )
    reviews = client.call(
        "/review/list",
        bookId=book_id,
        reviewListType=0,
        count=20,
        maxIdx=0,
        synckey=0,
    )

    raw_payloads = {
        "search.json": search,
        "book_info.json": book_info,
        "chapters.json": chapters,
        "popular_highlights.json": highlights,
        "public_reviews.json": reviews,
    }
    for filename, payload in raw_payloads.items():
        write_json(raw_dir / filename, payload)

    source_pack = normalize_source_pack(
        selected, book_info, chapters, highlights, reviews
    )
    write_json(normalized_dir / "book_source_pack.json", source_pack)
    collection_manifest = {
        "schema_version": "1.0",
        "collected_at": source_pack["collected_at"],
        "provider": source_pack["provider"],
        "book_id": source_pack["book"]["book_id"],
        "endpoints": [
            "/store/search",
            "/book/info",
            "/book/chapterinfo",
            "/book/bestbookmarks",
            "/review/list",
        ],
        "raw_files": sorted(raw_payloads),
        "counts": {
            "chapters": len(source_pack["chapter_outline"]),
            "popular_highlights": len(source_pack["popular_highlights"]),
            "public_reviews": len(source_pack["public_reviews"]),
        },
        "credential_persisted": False,
    }
    write_json(normalized_dir / "collection_manifest.json", collection_manifest)

    project_manifest_path = project.resolve() / "project.json"
    if project_manifest_path.is_file():
        project_manifest = json.loads(project_manifest_path.read_text(encoding="utf-8"))
        project_manifest.update(
            {
                "status": "research_collected",
                "current_stage": "01_research",
                "updated_at": source_pack["collected_at"],
                "research": {
                    "provider": source_pack["provider"],
                    "book_id": source_pack["book"]["book_id"],
                    "source_pack": "01_research_资料搜集/normalized/book_source_pack.json",
                    "collection_manifest": "01_research_资料搜集/normalized/collection_manifest.json",
                },
            }
        )
        write_json(project_manifest_path, project_manifest)
    return source_pack
