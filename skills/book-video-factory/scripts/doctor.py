#!/usr/bin/env python3
"""Run dependency and public-release diagnostics from the bundled runtime."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DOCTOR = SKILL_ROOT / "runtime/book_video_factory/scripts/doctor.py"


def main() -> int:
    if not RUNTIME_DOCTOR.is_file():
        print(f"Bundled runtime doctor is missing: {RUNTIME_DOCTOR}", file=sys.stderr)
        return 3
    return subprocess.run([sys.executable, str(RUNTIME_DOCTOR), *sys.argv[1:]], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
