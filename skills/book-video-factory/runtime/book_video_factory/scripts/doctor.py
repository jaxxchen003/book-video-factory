#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
from pathlib import Path

import _bootstrap  # noqa: F401
from book_video_factory.freesound import (
    API_KEYCHAIN_SERVICE as FREESOUND_API_KEYCHAIN_SERVICE,
    COMMERCIAL_AUTHORIZATION_ENV,
    commercial_api_authorized,
    credential_available as freesound_credential_available,
)
from book_video_factory.contracts import ContractError, ReleaseProfile
from book_video_factory.credentials import credential_available
from book_video_factory.gates import evaluate_workflow_state
from book_video_factory.style_profiles import StyleProfileError, project_workflow


def executable_check(name: str, *, required: bool) -> dict[str, object]:
    path = shutil.which(name)
    return {
        "name": name,
        "status": "ready" if path else ("blocked" if required else "warn"),
        "path": path,
    }


def python_module_check(name: str, *, required: bool) -> dict[str, object]:
    try:
        available = importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError):
        available = False
    return {
        "name": f"python_module:{name}",
        "status": "ready" if available else ("blocked" if required else "warn"),
        "path": "installed" if available else "missing",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check book-video factory dependencies")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--profile",
        choices=("planning", "local-render", "production", "public-release"),
        default="planning",
    )
    parser.add_argument("--project", type=Path)
    parser.add_argument("--release-id")
    args = parser.parse_args()

    local_render = args.profile in {"local-render", "production", "public-release"}
    project = args.project.expanduser().resolve() if args.project else None
    workflow: dict[str, object] | None = None

    checks = [
        executable_check("python3", required=True),
        executable_check("ffmpeg", required=local_render),
        executable_check("ffprobe", required=local_render),
        executable_check("voxcpm", required=False),
        executable_check("whisper", required=False),
        executable_check("whisper-cli", required=False),
        executable_check("hyperframes", required=False),
        executable_check("node", required=False),
        executable_check("npm", required=False),
        python_module_check("PIL", required=local_render),
    ]
    model = Path.home() / ".local/share/voxcpm-models/VoxCPM2-modelscope"
    checks.append(
        {
            "name": "voxcpm2_model",
            "status": "ready" if model.is_dir() else "warn",
            "path": str(model),
        }
    )
    if project is not None:
        try:
            workflow = project_workflow(project)
        except StyleProfileError as error:
            checks.append(
                {
                    "name": "project_style_profile",
                    "status": "blocked",
                    "path": str(project),
                    "note": str(error),
                }
            )
        else:
            style_profile = workflow["style_profile"]
            checks.append(
                {
                    "name": "project_style_profile",
                    "status": "ready",
                    "path": str(style_profile.path),
                    "style_profile_id": style_profile.style_id,
                    "display_name": style_profile.display_name_zh,
                    "generation_lane": workflow["generation_lane"],
                }
            )
            if (
                args.profile == "production"
                and workflow["generation_lane"] == "gemini-api"
            ):
                checks.append(
                    {
                        "name": "gemini_api_credential",
                        "status": (
                            "ready"
                            if os.environ.get("GEMINI_API_KEY", "").strip()
                            else "blocked"
                        ),
                        "path": "GEMINI_API_KEY environment variable",
                        "note": "Required only for the selected Gemini API generation lane; never write it to project files or manifests.",
                    }
                )
                checks.append(python_module_check("google.genai", required=True))
            elif (
                args.profile == "production"
                and workflow["generation_lane"] == "google-flow"
            ):
                checks.append(
                    {
                        "name": "google_flow_manual_prerequisites",
                        "status": "warn",
                        "path": "eligible Google AI plan, credits, region, and desktop browser",
                        "note": "Manual account eligibility cannot be verified by doctor.py. Flow is not treated as a programmable API.",
                    }
                )
    checks.append(
        {
            "name": "weread_credential",
            "status": "ready" if credential_available("WEREAD_API_KEY", "codex-weread-api-key") else "warn",
            "path": "environment_or_macos_keychain",
            "note": "Optional. Use attributable public metadata or user-provided evidence when unavailable.",
        }
    )
    freesound_ready = freesound_credential_available(
        "FREESOUND_API_KEY", FREESOUND_API_KEYCHAIN_SERVICE
    )
    checks.append(
        {
            "name": "freesound_candidate_search",
            "status": "ready" if freesound_ready else "warn",
            "path": "environment_or_macos_keychain",
            "note": "Candidate search and non-commercial audition only; API credentials are never written to project manifests.",
        }
    )
    if args.profile == "public-release":
        if project is None:
            checks.append(
                {
                    "name": "project_public_release_gate",
                    "status": "blocked",
                    "path": "--project is required for public-release",
                }
            )
        else:
            try:
                resolved_workflow = workflow or project_workflow(project)
                profile_directory = (
                    Path(__file__).resolve().parents[1]
                    / "config"
                    / "release_profiles"
                ).resolve()
                profile_id = str(resolved_workflow["release_profile_id"])
                profile_path = (profile_directory / f"{profile_id}.json").resolve()
                profile_path.relative_to(profile_directory)
                gate = evaluate_workflow_state(
                    project,
                    ReleaseProfile.load(profile_path),
                    release_id=args.release_id,
                )
            except (ContractError, StyleProfileError, OSError, ValueError) as error:
                checks.append(
                    {
                        "name": "project_public_release_gate",
                        "status": "blocked",
                        "path": str(project),
                        "note": str(error),
                    }
                )
            else:
                checks.append(
                    {
                        "name": "project_public_release_gate",
                        "status": "ready" if gate["ready_to_publish"] else "blocked",
                        "path": str(project),
                        "style_profile_id": gate["style_profile_id"],
                        "derived_state": gate["derived_state"],
                        "missing_publish_approvals": gate["missing_publish_approvals"],
                    }
                )
    checks.append(
        {
            "name": "freesound_commercial_api_authorization",
            "status": "ready" if commercial_api_authorized() else "warn",
            "path": COMMERCIAL_AUTHORIZATION_ENV,
            "note": "Freesound free API use is non-commercial only. Do not make this provider publishable until a commercial API agreement is recorded by the operator.",
        }
    )
    checks.append(
        {
            "name": "image_provider_mode",
            "status": "ready",
            "path": "codex_builtin_image_generation",
            "note": "Images are generated inside Codex and copied into the project warehouse; no local OpenAI API key is required.",
        }
    )
    free_gib = shutil.disk_usage(Path.cwd()).free / (1024**3)
    checks.append(
        {
            "name": "disk_free",
            "status": "ready" if free_gib >= 10 else "warn",
            "free_gib": round(free_gib, 2),
        }
    )
    overall = "blocked" if any(c["status"] == "blocked" for c in checks) else "ready"
    report = {"profile": args.profile, "overall": overall, "checks": checks}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"book-video factory ({args.profile}): {overall}")
        for check in checks:
            detail = check.get("path") or check.get("free_gib") or ""
            print(f"[{str(check['status']).upper():7}] {check['name']}: {detail}")
    return 1 if overall == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
