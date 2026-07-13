#!/usr/bin/env python3
"""Append-only, provider-neutral cost ledger for book-video projects."""
from __future__ import annotations

import argparse
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FIELDS = (
    "codex_input_tokens",
    "codex_cached_input_tokens",
    "codex_output_tokens",
    "images_generated",
    "music_jobs",
    "voice_seconds",
    "render_seconds",
    "retries",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ledger_path(warehouse: Path) -> Path:
    return warehouse / "operations" / "run_cost.jsonl"


def read_events(warehouse: Path) -> list[dict[str, Any]]:
    path = ledger_path(warehouse)
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSONL at {path}:{number}: {exc}") from exc
        if not isinstance(event, dict):
            raise RuntimeError(f"Invalid non-object event at {path}:{number}")
        events.append(event)
    return events


def append_event(warehouse: Path, event: dict[str, Any]) -> None:
    path = ledger_path(warehouse)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def aggregate(events: list[dict[str, Any]]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for event in events:
        for field in FIELDS:
            value = event.get(field)
            if value is not None:
                totals[field] += float(value)
    return totals


def seen(events: list[dict[str, Any]], field: str) -> bool:
    return any(event.get(field) is not None for event in events)


def token_value(events: list[dict[str, Any]], field: str) -> str:
    return f"{aggregate(events)[field]:.0f}" if seen(events, field) else "—"


def record(args: argparse.Namespace) -> int:
    warehouse = args.warehouse.expanduser().resolve()
    event = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "recorded_at": utc_now(),
        "run_id": args.run_id or str(uuid.uuid4()),
        "project_slug": args.project,
        "stage": args.stage,
        "status": args.status,
        "source": args.source,
        "codex_model": args.codex_model,
        "codex_input_tokens": args.input_tokens,
        "codex_cached_input_tokens": args.cached_input_tokens,
        "codex_output_tokens": args.output_tokens,
        "images_generated": args.images,
        "music_jobs": args.music_jobs,
        "voice_seconds": args.voice_seconds,
        "render_seconds": args.render_seconds,
        "retries": args.retries,
        "note": args.note,
    }
    append_event(warehouse, event)
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


def report(args: argparse.Namespace) -> int:
    warehouse = args.warehouse.expanduser().resolve()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in read_events(warehouse):
        grouped[str(event.get("project_slug", "unknown"))].append(event)
    rows = [
        "# Book-video run cost ledger",
        "",
        "`—` means the provider did not expose the value or it was not recorded. It never means zero cost.",
        "",
        "| Project | Images | Music jobs | Voice seconds | Render seconds | Input tokens | Cached tokens | Output tokens | Retries |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for slug, events in sorted(grouped.items()):
        totals = aggregate(events)
        rows.append(
            "| {slug} | {images:.0f} | {music:.0f} | {voice:.1f} | {render:.1f} | {input} | {cached} | {output} | {retries:.0f} |".format(
                slug=slug,
                images=totals["images_generated"],
                music=totals["music_jobs"],
                voice=totals["voice_seconds"],
                render=totals["render_seconds"],
                input=token_value(events, "codex_input_tokens"),
                cached=token_value(events, "codex_cached_input_tokens"),
                output=token_value(events, "codex_output_tokens"),
                retries=totals["retries"],
            )
        )
    if grouped:
        all_events = [event for events in grouped.values() for event in events]
        totals = aggregate(all_events)
        count = len(grouped)
        rows.extend(
            [
                "",
                "## Per-project average",
                "",
                f"Images: {totals['images_generated'] / count:.1f}; music jobs: {totals['music_jobs'] / count:.1f}; voice: {totals['voice_seconds'] / count:.1f}s; render: {totals['render_seconds'] / count:.1f}s.",
                "Token averages are shown only when every compared project has recorded provider usage for that field.",
            ]
        )
    output = warehouse / "reports" / "run-cost-report.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(output)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Record known book-video usage without inventing provider telemetry")
    subcommands = parser.add_subparsers(required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--warehouse", type=Path, default=Path("book_video_warehouse"))

    record_parser = subcommands.add_parser("record", parents=[common])
    record_parser.add_argument("--project", required=True)
    record_parser.add_argument("--stage", required=True)
    record_parser.add_argument("--status", default="completed")
    record_parser.add_argument("--source", default="manual")
    record_parser.add_argument("--run-id")
    record_parser.add_argument("--codex-model")
    for flag in ("input-tokens", "cached-input-tokens", "output-tokens", "images", "music-jobs", "voice-seconds", "render-seconds", "retries"):
        record_parser.add_argument(f"--{flag}", type=float)
    record_parser.add_argument("--note")
    record_parser.set_defaults(handler=record)

    report_parser = subcommands.add_parser("report", parents=[common])
    report_parser.set_defaults(handler=report)
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
