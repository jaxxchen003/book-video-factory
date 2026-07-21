#!/usr/bin/env python3
"""Append-only run-cost ledger for the local book-video factory."""
from __future__ import annotations

import argparse
import json
import subprocess
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COST_FIELDS = (
    "codex_input_tokens", "codex_cached_input_tokens", "codex_output_tokens",
    "images_generated", "music_jobs", "voice_seconds", "render_seconds", "retries",
)

def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ledger_path(warehouse: Path) -> Path:
    return warehouse / "operations/run_cost.jsonl"


def read_events(warehouse: Path) -> list[dict[str, Any]]:
    path = ledger_path(warehouse)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_event(warehouse: Path, event: dict[str, Any]) -> None:
    path = ledger_path(warehouse)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(event, ensure_ascii=False) + "\n")


def duration(path: Path) -> float | None:
    if not path.is_file():
        return None
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)],
        text=True, capture_output=True, check=False,
    )
    try:
        return round(float(result.stdout.strip()), 3)
    except ValueError:
        return None


def project_cost_view(warehouse: Path, slug: str) -> dict[str, Any]:
    events = effective_events([event for event in read_events(warehouse) if event.get("project_slug") == slug])
    return {"schema_version": "1.0", "project_slug": slug, "updated_at": now(), "events": events, "totals": dict(sum_costs(events)), "token_evidence": "recorded_only; null means unavailable"}


def effective_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Do not count a later asset inventory as a second production run.

    `asset_inventory` is retained in the append-only ledger as audit evidence,
    but a project with a concrete `v4_local_master` event must use the latter
    as its production record.  A separate `v4_measurements` event can then
    supply only duration measurements that the master event did not capture.
    """
    has_master = any(event.get("stage") == "v4_local_master" for event in events)
    return [event for event in events if not (has_master and event.get("stage") == "asset_inventory")]


def sum_costs(events: list[dict[str, Any]]) -> defaultdict[str, float]:
    """Use explicit master values, falling back to later measurements only when absent."""
    totals: defaultdict[str, float] = defaultdict(float)
    masters = [event for event in events if event.get("stage") == "v4_local_master"]
    measurements = [event for event in events if event.get("stage") == "v4_measurements"]
    ordinary = [event for event in events if event.get("stage") not in {"v4_local_master", "v4_measurements"}]
    for key in COST_FIELDS:
        master_values = [float(event[key]) for event in masters if event.get(key) is not None]
        if master_values:
            totals[key] = sum(master_values) + sum(float(event.get(key) or 0) for event in ordinary)
            continue
        totals[key] = sum(float(event.get(key) or 0) for event in ordinary + measurements)
    return totals


def current_batch_slugs(warehouse: Path) -> set[str]:
    """Discover the newest approved V4 batch instead of mixing historical V4s."""
    candidates: list[tuple[str, set[str]]] = []
    approved = warehouse / "topic_library" / "approved"
    for path in approved.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        projects = payload.get("projects")
        if not isinstance(projects, list):
            continue
        slugs = {str(item.get("project_id")) for item in projects if isinstance(item, dict) and item.get("project_id")}
        if slugs:
            candidates.append((str(payload.get("approved_at") or path.stat().st_mtime), slugs))
    return max(candidates, default=("", set()))[1]


def record(args: argparse.Namespace) -> None:
    warehouse = args.warehouse.resolve()
    event = {
        "event_id": str(uuid.uuid4()), "recorded_at": now(), "run_id": args.run_id or str(uuid.uuid4()),
        "project_slug": args.project, "stage": args.stage, "status": args.status, "source": args.source,
        "codex_model": args.codex_model, "codex_input_tokens": args.input_tokens,
        "codex_cached_input_tokens": args.cached_input_tokens, "codex_output_tokens": args.output_tokens,
        "images_generated": args.images, "music_jobs": args.music_jobs, "voice_seconds": args.voice_seconds,
        "render_seconds": args.render_seconds, "retries": args.retries, "note": args.note,
    }
    append_event(warehouse, event)
    project = warehouse / "projects" / args.project
    write_json(project / "09_qc_质检/run_cost.json", project_cost_view(warehouse, args.project))
    print(json.dumps(event, ensure_ascii=False, indent=2))


def backfill(args: argparse.Namespace) -> None:
    warehouse = args.warehouse.resolve()
    for project in sorted((warehouse / "projects").glob("*")):
        if not project.is_dir() or not (project / "project.json").is_file():
            continue
        slug = project.name
        project_events = [event for event in read_events(warehouse) if event.get("project_slug") == slug]
        has_master = any(event.get("stage") == "v4_local_master" for event in project_events)
        stage = "v4_measurements" if has_master else "asset_inventory"
        if any(event.get("stage") == stage for event in project_events):
            write_json(project / "09_qc_质检/run_cost.json", project_cost_view(warehouse, slug))
            continue
        images = None if has_master else len(list((project / "03_images_生成图片/approved/v4").glob("S[0-9][0-9].png")))
        music = None if has_master else len(list((project / "06_music_音乐").glob("v4-*-original-bgm.mp3")))
        voice = duration(project / "05_voice_人声/v3-b-locked-master.wav")
        renders = list((project / "10_delivery_交付/v4").glob("*-v4-bilingual-3x4.mp4"))
        render = duration(renders[0]) if renders else None
        event = {"event_id": str(uuid.uuid4()), "recorded_at": now(), "run_id": f"backfill-{slug}", "project_slug": slug,
                 "stage": stage, "status": "observed", "source": "backfill", "codex_model": None,
                 "codex_input_tokens": None, "codex_cached_input_tokens": None, "codex_output_tokens": None,
                 "images_generated": images, "music_jobs": music, "voice_seconds": voice, "render_seconds": render,
                 "retries": None, "note": "Duration measurement only; token fields intentionally unavailable." if has_master else "Inventory only; token fields intentionally unavailable."}
        append_event(warehouse, event)
        write_json(project / "09_qc_质检/run_cost.json", project_cost_view(warehouse, slug))
    print(ledger_path(warehouse))


def report(args: argparse.Namespace) -> None:
    warehouse = args.warehouse.resolve()
    by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in read_events(warehouse):
        by_project[event.get("project_slug", "unknown")].append(event)
    cost_fields = ("images_generated", "music_jobs", "voice_seconds", "render_seconds", "codex_input_tokens", "codex_cached_input_tokens", "codex_output_tokens")

    def totals(events: list[dict[str, Any]]) -> dict[str, float]:
        return sum_costs(events)

    def has_recorded(events: list[dict[str, Any]], key: str) -> bool:
        return any(event.get(key) is not None for event in events)

    def token_text(events: list[dict[str, Any]], key: str) -> str:
        return f"{totals(events)[key]:.0f}" if has_recorded(events, key) else "—"

    def v4_delivered(slug: str) -> bool:
        return any((warehouse / "projects" / slug / "10_delivery_交付/v4").glob("*-v4-bilingual-3x4.mp4"))

    batch_slugs = current_batch_slugs(warehouse)
    v4_projects = [
        (slug, effective_events(events)) for slug, events in sorted(by_project.items())
        if v4_delivered(slug) and (not batch_slugs or slug in batch_slugs)
    ]
    historical_projects = [
        (slug, effective_events(events)) for slug, events in sorted(by_project.items())
        if slug not in {project_slug for project_slug, _ in v4_projects}
    ]
    rows = [
        "# 图书视频工厂运行成本台账",
        "",
        "仅汇总已记录数字；`—` 表示平台未提供或尚未人工导入 token，绝不把缺失值伪装成 0。",
        "",
        "## 当前 V4 生产批次",
        "",
        "| 项目 | 图片 | 音乐任务 | 人声秒数 | 成片秒数 | 输入 token | 缓存 token | 输出 token |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for slug, events in v4_projects:
        sums = totals(events)
        rows.append(f"| {slug} | {sums['images_generated']:.0f} | {sums['music_jobs']:.0f} | {sums['voice_seconds']:.1f} | {sums['render_seconds']:.1f} | {token_text(events, 'codex_input_tokens')} | {token_text(events, 'codex_cached_input_tokens')} | {token_text(events, 'codex_output_tokens')} |")
    if v4_projects:
        cohort: defaultdict[str, float] = defaultdict(float)
        for _, events in v4_projects:
            for key, value in totals(events).items():
                cohort[key] += value
        count = len(v4_projects)
        rows.extend([
            "",
            f"**批次均值（{count} 条）**：图片 {cohort['images_generated'] / count:.1f} 张；音乐 {cohort['music_jobs'] / count:.1f} 个任务；人声 {cohort['voice_seconds'] / count:.1f} 秒；成片 {cohort['render_seconds'] / count:.1f} 秒。",
            "**Codex token 均值**：仅在每一步有可归因的 usage 数据写入后计算；当前为 `—`，不能从本地成片反推出实际 token。",
        ])
    if historical_projects:
        rows.extend(["", "## 历史项目（不计入当前 V4 批次均值）", "", "| 项目 | 图片 | 音乐任务 | 人声秒数 | 成片秒数 | 输入 token | 缓存 token | 输出 token |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"])
        for slug, events in historical_projects:
            sums = totals(events)
            rows.append(f"| {slug} | {sums['images_generated']:.0f} | {sums['music_jobs']:.0f} | {sums['voice_seconds']:.1f} | {sums['render_seconds']:.1f} | {token_text(events, 'codex_input_tokens')} | {token_text(events, 'codex_cached_input_tokens')} | {token_text(events, 'codex_output_tokens')} |")
    output = warehouse / "reports/run-cost-report.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Record or report book-video factory run costs")
    parser.add_argument("--warehouse", type=Path, default=Path("book_video_warehouse"))
    sub = parser.add_subparsers(required=True)
    record_parser = sub.add_parser("record")
    record_parser.add_argument("--project", required=True); record_parser.add_argument("--stage", required=True)
    record_parser.add_argument("--status", default="success"); record_parser.add_argument("--source", default="manual")
    record_parser.add_argument("--run-id"); record_parser.add_argument("--codex-model")
    for flag in ("input-tokens", "cached-input-tokens", "output-tokens", "images", "music-jobs", "voice-seconds", "render-seconds", "retries"):
        record_parser.add_argument(f"--{flag}", type=float)
    record_parser.add_argument("--note"); record_parser.set_defaults(func=record)
    sub.add_parser("backfill").set_defaults(func=backfill)
    sub.add_parser("report").set_defaults(func=report)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
