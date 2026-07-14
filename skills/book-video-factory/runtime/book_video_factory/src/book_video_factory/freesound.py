from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .project import write_json
from .weread import trusted_ssl_context


API_URL = "https://freesound.org/apiv2/search/text/"
API_KEYCHAIN_SERVICE = "book-video-factory.freesound.api-key"
CLIENT_ID_KEYCHAIN_SERVICE = "book-video-factory.freesound.client-id"
COMMERCIAL_AUTHORIZATION_ENV = "FREESOUND_COMMERCIAL_API_AUTHORIZED"


class FreesoundError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_secret(env_name: str, keychain_service: str) -> str:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value
    if os.uname().sysname == "Darwin":
        completed = subprocess.run(
            ["security", "find-generic-password", "-s", keychain_service, "-w"],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            return completed.stdout.strip()
    raise FreesoundError(
        f"Freesound credential not found in {env_name} or macOS Keychain"
    )


def load_api_key() -> str:
    return load_secret("FREESOUND_API_KEY", API_KEYCHAIN_SERVICE)


def credential_available(env_name: str, keychain_service: str) -> bool:
    if os.environ.get(env_name, "").strip():
        return True
    if os.uname().sysname != "Darwin":
        return False
    completed = subprocess.run(
        ["security", "find-generic-password", "-s", keychain_service],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def commercial_api_authorized() -> bool:
    return os.environ.get(COMMERCIAL_AUTHORIZATION_ENV, "").strip().casefold() in {
        "1",
        "true",
        "yes",
    }


def license_details(raw_license: object) -> dict[str, str] | None:
    """Return a publication-safe license record, rejecting NC and unknown terms."""
    raw = str(raw_license or "").strip()
    lowered = raw.casefold()
    if not raw or "noncommercial" in lowered or "by-nc" in lowered:
        return None
    if "publicdomain/zero" in lowered or lowered == "creative commons 0":
        return {
            "code": "CC0-1.0",
            "name": "Creative Commons Zero 1.0",
            "url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "attribution_required": "false",
        }
    if lowered == "attribution" or "creativecommons.org/licenses/by/" in lowered:
        return {
            "code": "CC-BY-4.0",
            "name": "Creative Commons Attribution 4.0",
            "url": "https://creativecommons.org/licenses/by/4.0/",
            "attribution_required": "true",
        }
    return None


def _number(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_candidates(
    results: Iterable[dict[str, Any]],
    *,
    intent: str,
    min_duration: float,
    max_duration: float,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    """Keep only auditable CC0/CC-BY candidates with a usable preview."""
    if limit <= 0:
        raise FreesoundError("Candidate limit must be positive")
    candidates: list[dict[str, Any]] = []
    rejected = 0
    for result in results:
        license_info = license_details(result.get("license"))
        duration = _number(result.get("duration"))
        previews = result.get("previews") if isinstance(result.get("previews"), dict) else {}
        preview_url = previews.get("preview-hq-mp3") or previews.get("preview-hq-ogg")
        sound_id = result.get("id")
        if (
            not license_info
            or not sound_id
            or duration < min_duration
            or duration > max_duration
            or not preview_url
        ):
            rejected += 1
            continue
        username = str(result.get("username") or "unknown-uploader").strip()
        title = str(result.get("name") or f"Freesound sound {sound_id}").strip()
        source_page = str(
            result.get("url") or f"https://freesound.org/people/{username}/sounds/{sound_id}/"
        )
        attribution = (
            f'"{title}" by {username} — {license_info["name"]} ({source_page})'
            if license_info["attribution_required"] == "true"
            else "CC0: attribution not required; retain source record for audit."
        )
        candidates.append(
            {
                "provider": "Freesound APIv2",
                "sound_id": int(sound_id),
                "title": title,
                "uploader": username,
                "source_page": source_page,
                "duration_seconds": round(duration, 3),
                "license": license_info,
                "required_attribution": attribution,
                "preview_url": str(preview_url),
                "tags": [str(tag) for tag in result.get("tags", []) if isinstance(tag, str)],
                "description": str(result.get("description") or "").strip(),
                "audio_type": str(result.get("type") or ""),
                "channels": int(_number(result.get("channels"))),
                "search_score": _number(result.get("score")),
                "avg_rating": _number(result.get("avg_rating")),
                "rating_count": int(_number(result.get("num_ratings"))),
                "download_count": int(_number(result.get("num_downloads"))),
                "selection_intent": intent,
            }
        )
    candidates.sort(
        key=lambda item: (
            0 if item["license"]["code"] == "CC0-1.0" else 1,
            -item["search_score"],
            -item["avg_rating"],
            -item["rating_count"],
        )
    )
    return candidates[:limit], rejected


class FreesoundClient:
    def __init__(self, api_key: str | None = None, timeout: int = 30) -> None:
        self._api_key = api_key or load_api_key()
        self._timeout = timeout
        self._ssl_context = trusted_ssl_context()

    def search_bgm(
        self,
        intent: str,
        *,
        min_duration: float = 55.0,
        max_duration: float = 360.0,
        page_size: int = 50,
    ) -> dict[str, Any]:
        if not intent.strip():
            raise FreesoundError("Freesound BGM search intent cannot be empty")
        if min_duration <= 0 or max_duration <= min_duration:
            raise FreesoundError("Duration range must be positive and ascending")
        fields = ",".join(
            [
                "id",
                "name",
                "tags",
                "description",
                "username",
                "license",
                "duration",
                "type",
                "channels",
                "previews",
                "url",
                "score",
                "avg_rating",
                "num_ratings",
                "num_downloads",
            ]
        )
        query = urllib.parse.urlencode(
            {
                "query": intent,
                "filter": f"duration:[{min_duration:g} TO {max_duration:g}]",
                "fields": fields,
                "page_size": min(max(int(page_size), 1), 150),
                "token": self._api_key,
            }
        )
        request = urllib.request.Request(
            f"{API_URL}?{query}",
            headers={"User-Agent": "book-video-factory/0.1"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self._timeout, context=self._ssl_context
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise FreesoundError(f"Freesound HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise FreesoundError(f"Freesound request failed: {exc}") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise FreesoundError("Freesound returned an invalid search payload")
        return payload


def write_candidate_manifest(
    project: Path,
    *,
    intent: str,
    search_query: str | None = None,
    raw_payload: dict[str, Any],
    candidates: list[dict[str, Any]],
    rejected_count: int,
    min_duration: float,
    max_duration: float,
) -> Path:
    """Persist search evidence without downloading or selecting a BGM file."""
    publication_allowed = commercial_api_authorized()
    manifest = {
        "schema_version": "1.0",
        "provider": "Freesound APIv2",
        "generated_at": utc_now(),
        "purpose": "BGM candidate research only",
        "query": intent,
        "search_query": search_query or intent,
        "duration_range_seconds": {"min": min_duration, "max": max_duration},
        "source_result_count": raw_payload.get("count"),
        "eligible_candidate_count": len(candidates),
        "rejected_candidate_count": rejected_count,
        "license_policy": {
            "accepted": ["CC0-1.0", "CC-BY-4.0"],
            "rejected": ["CC-BY-NC", "CC-BY-ND", "CC-BY-SA", "unknown"],
            "attribution_required_for": ["CC-BY-4.0"],
        },
        "provider_api_authorization": {
            "commercial_use_authorized": publication_allowed,
            "status": "commercial_authorized" if publication_allowed else "noncommercial_preview_only",
            "release_gate": (
                "A separate commercial Freesound API agreement is recorded by the operator."
                if publication_allowed
                else "Freesound free API terms permit non-commercial use only; do not download, render, or publish this source in a commercial release without provider authorization."
            ),
        },
        "candidates": candidates,
    }
    output = project.resolve() / "06_music_音乐" / "freesound-candidates.json"
    write_json(output, manifest)
    return output
