#!/usr/bin/env python3
"""Operate immutable manifests, hash-bound approvals, and derived workflow gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from book_video_factory.contracts import ContractError, ReleaseProfile
from book_video_factory.gates import evaluate_workflow_state
from book_video_factory.manifests import record_approval, write_stage_manifest


FACTORY = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = FACTORY / "config/release_profiles/book-v4-bilingual-3x4.json"
STATE_ORDER = (
    "invalid",
    "draft",
    "topic_approved",
    "source_audited",
    "script_reviewed",
    "assets_ready",
    "timeline_verified",
    "qc_passed",
    "ready_to_publish",
)


def artifact_spec(project: Path, value: str) -> tuple[str, Path]:
    role, separator, relative = value.partition("=")
    if not separator or not role or not relative:
        raise argparse.ArgumentTypeError("artifact must use role=project/relative/path")
    return role, project / relative


def check_spec(value: str) -> dict[str, str]:
    parts = value.split(":")
    if len(parts) not in {2, 3} or parts[1] not in {"pass", "fail"}:
        raise argparse.ArgumentTypeError("check must use id:pass|fail[:error|warning]")
    return {
        "id": parts[0],
        "result": parts[1],
        "severity": parts[2] if len(parts) == 3 else "error",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    evaluate = subcommands.add_parser("evaluate")
    evaluate.add_argument("--project", type=Path, required=True)
    evaluate.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    evaluate.add_argument("--release-id")
    evaluate.add_argument("--target", choices=STATE_ORDER[1:])

    approve = subcommands.add_parser("approve")
    approve.add_argument("--project", type=Path, required=True)
    approve.add_argument("--release-id", required=True)
    approve.add_argument("--gate", required=True)
    approve.add_argument("--decision", choices=("approved", "rejected", "revoked"), required=True)
    approve.add_argument("--reviewer", required=True)
    approve.add_argument("--subject", action="append", required=True)
    approve.add_argument("--evidence-ref", action="append", default=[])
    approve.add_argument("--note", default="")

    manifest = subcommands.add_parser("manifest-stage")
    manifest.add_argument("--project", type=Path, required=True)
    manifest.add_argument("--stage", required=True)
    manifest.add_argument("--release-id", required=True)
    manifest.add_argument("--release-profile", default="book-v4-bilingual-3x4")
    manifest.add_argument("--input", action="append", default=[])
    manifest.add_argument("--output", action="append", required=True)
    manifest.add_argument("--check", action="append", default=[])
    manifest.add_argument("--producer", default="book-video-factory")

    args = parser.parse_args()
    project = args.project.expanduser().resolve()

    if args.command == "evaluate":
        try:
            profile = ReleaseProfile.load(args.profile)
        except ContractError as error:
            print(json.dumps({"error": str(error)}, ensure_ascii=False))
            return 3
        result = evaluate_workflow_state(project, profile, release_id=args.release_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not args.target:
            return 0
        return 0 if STATE_ORDER.index(result["derived_state"]) >= STATE_ORDER.index(args.target) else 2

    if args.command == "approve":
        output = record_approval(
            project,
            release_id=args.release_id,
            gate=args.gate,
            decision=args.decision,
            reviewer=args.reviewer,
            subjects=[project / subject for subject in args.subject],
            evidence_refs=args.evidence_ref,
            note=args.note,
        )
        print(output)
        return 0

    inputs = [artifact_spec(project, value) for value in args.input]
    outputs = [artifact_spec(project, value) for value in args.output]
    checks = [check_spec(value) for value in args.check]
    output = write_stage_manifest(
        project,
        stage=args.stage,
        release_id=args.release_id,
        release_profile_id=args.release_profile,
        inputs=inputs,
        outputs=outputs,
        checks=checks,
        producer=args.producer,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
