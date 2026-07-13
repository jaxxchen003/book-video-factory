#!/usr/bin/env python3
"""Report portable planning and local-render prerequisites without installing anything."""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import sys
from typing import Any


def check_command(name: str, required: bool) -> dict[str, Any]:
    path = shutil.which(name)
    return {"name": name, "required": required, "status": "ready" if path else ("blocked" if required else "optional"), "path": path}


def check_module(name: str, required: bool) -> dict[str, Any]:
    available = importlib.util.find_spec(name) is not None
    return {"name": f"python:{name}", "required": required, "status": "ready" if available else ("blocked" if required else "optional"), "path": "installed" if available else None}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check portable book-video prerequisites")
    parser.add_argument("--profile", choices=("planning", "local-render"), default="planning")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    local = args.profile == "local-render"
    checks = [
        {"name": "python>=3.11", "required": True, "status": "ready" if sys.version_info >= (3, 11) else "blocked", "path": sys.executable},
        check_command("ffmpeg", local),
        check_command("ffprobe", local),
        check_module("PIL", local),
        check_command("whisper", False),
        check_command("whisper-cli", False),
        check_command("voxcpm", False),
        check_command("node", False),
    ]
    report = {
        "profile": args.profile,
        "platform": platform.platform(),
        "overall": "blocked" if any(check["status"] == "blocked" for check in checks) else "ready",
        "checks": checks,
        "notes": [
            "Planning can start without TTS, ASR, WeRead, ChatCut, or an image-provider credential.",
            "Local rendering additionally needs FFmpeg/FFprobe and Pillow. Narration and ASR remain user-selected providers with their own licences.",
        ],
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"book-video factory ({args.profile}): {report['overall']}")
        for check in checks:
            print(f"[{check['status'].upper():8}] {check['name']}: {check['path'] or 'not found'}")
    return 1 if report["overall"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
