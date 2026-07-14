#!/usr/bin/env python3
"""Validate and import content-system snapshots, then attach traceability maps."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from book_video_factory.content_bridge import (
    ContentBridgeError,
    attach_traceability,
    content_system_status,
    export_dbs_content_package,
    import_content_package,
    validate_content_package,
)


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate-package")
    validate.add_argument("--package", type=Path, required=True)

    export = commands.add_parser("export-dbs")
    export.add_argument("--content-root", type=Path, required=True)
    export.add_argument("--assembly", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)

    import_package = commands.add_parser("import-package")
    import_package.add_argument("--project", type=Path, required=True)
    import_package.add_argument("--package", type=Path, required=True)

    attach = commands.add_parser("attach-traceability")
    attach.add_argument("--project", type=Path, required=True)
    attach.add_argument("--map", type=Path, required=True)

    status = commands.add_parser("status")
    status.add_argument("--project", type=Path, required=True)
    status.add_argument(
        "--require",
        choices=("package", "production-eligible", "traceability"),
    )

    args = parser.parse_args()
    try:
        if args.command == "validate-package":
            result = validate_content_package(load_json(args.package))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "export-dbs":
            output = export_dbs_content_package(
                args.content_root,
                args.assembly,
                args.output,
            )
            print(output)
            return 0
        if args.command == "import-package":
            output = import_content_package(args.project, args.package)
            print(output)
            return 0
        if args.command == "attach-traceability":
            output = attach_traceability(args.project, args.map)
            print(output)
            return 0

        result = content_system_status(args.project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        required = args.require
        if required == "package":
            return 0 if result["content_package_valid"] else 2
        if required == "production-eligible":
            return 0 if result["content_package_valid"] and result["production_eligible"] else 2
        if required == "traceability":
            return 0 if result["traceability_valid"] else 2
        return 0
    except (ContentBridgeError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False, indent=2))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
