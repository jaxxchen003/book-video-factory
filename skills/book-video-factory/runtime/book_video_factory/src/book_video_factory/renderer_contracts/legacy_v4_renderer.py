"""Renderer Contract facade for the unmodified legacy V4 render chain."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from .enums import RendererErrorCode, RenderStatus
from .errors import ContractValidationError, RenderIssue
from .models import ArtifactBinding, PortableRef, RenderRequest, RendererIdentity, RenderResult
from .paths import PortablePathError, RootResolver
from .persistence import write_attempt_event, write_canonical_once, write_render_result
from .serialization import capabilities_from_dict
from .validation import (
    stable_issues,
    validate_capabilities,
    validate_render_request,
    validate_request_capabilities,
    validate_request_filesystem,
    validate_request_hash,
)
from .v4_compat import LEGACY_EXTENSION, LEGACY_RENDERER_ID, LEGACY_RENDERER_VERSION


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    elapsed_ms: int = 0


class CommandRunner(Protocol):
    def run(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
    ) -> CommandResult: ...


class MediaProbe(Protocol):
    def probe(self, path: Path) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class RenderExecutionContext:
    resolver: RootResolver
    attempts_directory: Path
    attempt_id: str
    environment: Mapping[str, str] | None = None


class SubprocessCommandRunner:
    def run(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
    ) -> CommandResult:
        started = datetime.now(UTC)
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            env=dict(env),
            check=False,
            capture_output=True,
            text=True,
        )
        elapsed = datetime.now(UTC) - started
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            elapsed_ms=max(0, int(elapsed.total_seconds() * 1000)),
        )


class FFprobeMediaProbe:
    def probe(self, path: Path) -> Mapping[str, Any]:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,codec_name,width,height,avg_frame_rate,pix_fmt,nb_frames,sample_rate,channels",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        streams = payload.get("streams")
        if not isinstance(streams, list):
            raise ValueError("ffprobe streams are missing")
        video = next(item for item in streams if item.get("codec_type") == "video")
        audio = next(item for item in streams if item.get("codec_type") == "audio")
        duration = Decimal(str(payload["format"]["duration"]))
        duration_ticks = int(
            (duration * 1000).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
        rate = Fraction(str(video["avg_frame_rate"]))
        raw_frames = video.get("nb_frames")
        frame_count = (
            int(raw_frames)
            if isinstance(raw_frames, str) and raw_frames.isdigit()
            else max(1, (duration_ticks * rate.numerator * 2 + 1000 * rate.denominator) // (2 * 1000 * rate.denominator))
        )
        return {
            "duration_ticks": duration_ticks,
            "video": {
                "codec": str(video["codec_name"]),
                "width": int(video["width"]),
                "height": int(video["height"]),
                "fps": {"numerator": rate.numerator, "denominator": rate.denominator},
                "pixel_format": str(video["pix_fmt"]),
                "frame_count": frame_count,
            },
            "audio": {
                "codec": str(audio["codec_name"]),
                "sample_rate": int(audio["sample_rate"]),
                "channels": int(audio["channels"]),
            },
        }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _portable(project: Path, path: Path) -> PortableRef:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(project.resolve())
    except ValueError as error:
        raise PortablePathError("attempt artifact is outside the project root") from error
    return PortableRef("project", relative.as_posix())


def _result_artifact(
    project: Path,
    path: Path,
    *,
    asset_id: str,
    role: str,
    media_type: str,
) -> ArtifactBinding:
    return ArtifactBinding(
        asset_id=asset_id,
        role=role,
        ref=_portable(project, path),
        bytes=path.stat().st_size,
        sha256=_sha256_file(path),
        media_type=media_type,
    )


def _issue(
    code: RendererErrorCode,
    message: str,
    field: str,
    *,
    stage: str,
    details: Mapping[str, Any] | None = None,
) -> RenderIssue:
    return RenderIssue(code, message, field, details or {}, stage)


class LegacyV4Renderer:
    def __init__(
        self,
        *,
        runner: CommandRunner | None = None,
        probe: MediaProbe | None = None,
        clock: Any = _utc_now,
    ) -> None:
        self._runner = runner or SubprocessCommandRunner()
        self._probe = probe or FFprobeMediaProbe()
        self._clock = clock

    def _validate_context(self, context: RenderExecutionContext) -> None:
        project = context.resolver.bindings.get("project")
        runtime = context.resolver.bindings.get("runtime")
        if project is None or runtime is None:
            raise ContractValidationError(
                (_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Execution context requires project and runtime root bindings.", "$.execution_context.root_bindings", stage="validate"),)
            )
        attempts = Path(context.attempts_directory).expanduser().resolve(strict=False)
        try:
            relative = attempts.relative_to(project)
        except ValueError as error:
            raise ContractValidationError(
                (_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Attempt persistence must stay inside the project root.", "$.execution_context.attempts_directory", stage="validate"),)
            ) from error
        current = project
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise ContractValidationError(
                    (_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Attempt persistence path must not use symlinks.", "$.execution_context.attempts_directory", stage="validate"),)
                )

    def _capabilities(self, request: RenderRequest, resolver: RootResolver) -> Any:
        ref = request.renderer.capability_document_ref
        if ref is None:
            raise ContractValidationError(
                (_issue(RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED, "Capability ref is missing.", "$.renderer.capability_document_ref", stage="negotiate"),)
            )
        try:
            path = resolver.resolve(ref, require_exists=True)
            payload = json.loads(path.read_text(encoding="utf-8"))
            document = capabilities_from_dict(payload)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise ContractValidationError(
                (_issue(RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED, "Capability document is unreadable.", "$.renderer.capability_document_ref", stage="negotiate"),)
            ) from error
        issues = list(validate_capabilities(document))
        if _sha256_file(path) != request.renderer.capability_document_sha256:
            issues.append(
                _issue(RendererErrorCode.RENDER_HASH_MISMATCH, "Capability document hash changed.", "$.renderer.capability_document_sha256", stage="validate")
            )
        issues.extend(validate_request_capabilities(request, document))
        if issues:
            raise ContractValidationError(stable_issues(issues))
        return document

    def _legacy_sources(
        self, request: RenderRequest, resolver: RootResolver
    ) -> tuple[Path, tuple[RenderIssue, ...]]:
        extension = request.extensions.get(LEGACY_EXTENSION)
        if not isinstance(extension, Mapping):
            return Path(), (
                _issue(RendererErrorCode.RENDER_INPUT_INVALID, "Legacy V4 extension is missing.", f"$.extensions.{LEGACY_EXTENSION}", stage="validate"),
            )
        sources = extension.get("legacy_code")
        entrypoint = extension.get("entrypoint")
        issues: list[RenderIssue] = []
        entrypoint_path: Path | None = None
        if not isinstance(sources, tuple) or not isinstance(entrypoint, Mapping):
            issues.append(
                _issue(RendererErrorCode.RENDER_INPUT_INVALID, "Legacy code bindings are missing.", f"$.extensions.{LEGACY_EXTENSION}.legacy_code", stage="validate")
            )
        else:
            for index, binding in enumerate(sources):
                field = f"$.extensions.{LEGACY_EXTENSION}.legacy_code[{index}]"
                if not isinstance(binding, Mapping) or not isinstance(binding.get("ref"), Mapping):
                    issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Legacy code binding is invalid.", field, stage="validate"))
                    continue
                ref = PortableRef(str(binding["ref"].get("root", "")), str(binding["ref"].get("path", "")))
                try:
                    path = resolver.resolve(ref, require_exists=True)
                except (PortablePathError, FileNotFoundError):
                    issues.append(_issue(RendererErrorCode.RENDER_ASSET_MISSING, "Bound legacy renderer source is unavailable.", field, stage="validate"))
                    continue
                if _sha256_file(path) != binding.get("sha256"):
                    issues.append(_issue(RendererErrorCode.RENDER_HASH_MISMATCH, "Bound legacy renderer source changed.", field, stage="validate"))
                if binding.get("id") == entrypoint.get("id"):
                    entrypoint_path = path
        if entrypoint_path is None:
            issues.append(
                _issue(RendererErrorCode.RENDER_INPUT_INVALID, "Legacy entrypoint is not bound to the frozen code list.", f"$.extensions.{LEGACY_EXTENSION}.entrypoint", stage="validate")
            )
        return entrypoint_path or Path(), stable_issues(issues)

    def _expected_paths(
        self, request: RenderRequest, resolver: RootResolver
    ) -> tuple[Path, list[tuple[dict[str, Any], Path]], tuple[RenderIssue, ...]]:
        issues: list[RenderIssue] = []
        extension = request.extensions.get(LEGACY_EXTENSION)
        expected_output = extension.get("expected_output") if isinstance(extension, Mapping) else None
        target = request.output.get("target")
        output_path = Path()
        if not isinstance(target, Mapping) or not isinstance(expected_output, Mapping) or dict(target) != dict(expected_output):
            issues.append(
                _issue(RendererErrorCode.RENDER_INPUT_INVALID, "Request output differs from the frozen legacy output.", "$.output.target", stage="validate")
            )
        else:
            try:
                output_path = resolver.resolve_output(PortableRef(str(target["root"]), str(target["path"])))
            except (KeyError, PortablePathError):
                issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Legacy output target is invalid.", "$.output.target", stage="validate"))
        sidecars: list[tuple[dict[str, Any], Path]] = []
        declarations = extension.get("expected_sidecars") if isinstance(extension, Mapping) else None
        if not isinstance(declarations, tuple):
            issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Legacy sidecar declarations are missing.", f"$.extensions.{LEGACY_EXTENSION}.expected_sidecars", stage="validate"))
        else:
            for index, declaration in enumerate(declarations):
                field = f"$.extensions.{LEGACY_EXTENSION}.expected_sidecars[{index}]"
                ref = declaration.get("ref") if isinstance(declaration, Mapping) else None
                if not isinstance(ref, Mapping):
                    issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Legacy sidecar ref is invalid.", field, stage="validate"))
                    continue
                try:
                    path = resolver.resolve(PortableRef(str(ref.get("root", "")), str(ref.get("path", ""))))
                except PortablePathError:
                    issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Legacy sidecar ref is invalid.", field, stage="validate"))
                    continue
                sidecars.append((dict(declaration), path))
        return output_path, sidecars, stable_issues(issues)

    def validate(
        self, request: RenderRequest, context: RenderExecutionContext
    ) -> tuple[RenderIssue, ...]:
        issues: list[RenderIssue] = [
            *validate_render_request(request),
            *validate_request_hash(request),
            *validate_request_filesystem(request, context.resolver),
        ]
        if request.renderer.id != LEGACY_RENDERER_ID or request.renderer.version != LEGACY_RENDERER_VERSION:
            issues.append(_issue(RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED, "Request does not select the Legacy V4 facade.", "$.renderer", stage="negotiate"))
        try:
            self._capabilities(request, context.resolver)
        except ContractValidationError as error:
            issues.extend(error.issues)
        _, source_issues = self._legacy_sources(request, context.resolver)
        issues.extend(source_issues)
        output, sidecars, path_issues = self._expected_paths(request, context.resolver)
        issues.extend(path_issues)
        if output and output.exists():
            issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Write-once output target already exists.", "$.output.target", stage="validate"))
        for index, (_, path) in enumerate(sidecars):
            if path.exists():
                issues.append(_issue(RendererErrorCode.RENDER_INPUT_INVALID, "Write-once legacy sidecar target already exists.", f"$.extensions.{LEGACY_EXTENSION}.expected_sidecars[{index}]", stage="validate"))
        return stable_issues(issues)

    def _input_hashes(self, request: RenderRequest) -> dict[str, str]:
        values = {
            "request": request.request_hash,
            "release_snapshot": request.release.manifest_sha256,
            "release_profile": request.profile.sha256,
            "renderer_capabilities": request.renderer.capability_document_sha256,
        }
        values.update({item.asset_id: item.sha256 for item in request.assets})
        return values

    def _event(
        self,
        request: RenderRequest,
        context: RenderExecutionContext,
        index: int,
        status: RenderStatus,
        recorded_at: str,
    ) -> None:
        write_attempt_event(
            {
                "schema_version": "1.0",
                "request_id": request.request_id,
                "request_hash": request.request_hash,
                "attempt_id": context.attempt_id,
                "event_index": index,
                "status": status.value,
                "recorded_at": recorded_at,
            },
            context.attempts_directory,
        )

    def _terminal_result(
        self,
        request: RenderRequest,
        context: RenderExecutionContext,
        *,
        status: RenderStatus,
        started_at: str,
        finished_at: str,
        errors: tuple[RenderIssue, ...] = (),
        output: tuple[ArtifactBinding, ...] = (),
        sidecars: tuple[ArtifactBinding, ...] = (),
        media_probe: Mapping[str, Any] | None = None,
        metrics: Mapping[str, int] | None = None,
        qc_handoff: Mapping[str, Any] | None = None,
        logs: tuple[Mapping[str, Any], ...] = (),
        extensions: Mapping[str, Any] | None = None,
    ) -> RenderResult:
        output_hashes = {item.asset_id: item.sha256 for item in (*output, *sidecars)}
        result = RenderResult(
            schema_version="1.0",
            request_id=request.request_id,
            request_hash=request.request_hash,
            attempt_id=context.attempt_id,
            status=status,
            renderer=RendererIdentity(
                id=request.renderer.id,
                version=request.renderer.version,
                capability_document_sha256=request.renderer.capability_document_sha256,
            ),
            started_at=started_at,
            finished_at=finished_at,
            output=output,
            sidecars=sidecars,
            media_probe=media_probe,
            warnings=(),
            errors=tuple(item.to_dict() for item in errors),
            primary_error_code=errors[0].code.value if errors else None,
            metrics=metrics or {},
            input_hashes=self._input_hashes(request),
            output_hashes=output_hashes,
            qc_handoff=qc_handoff,
            logs=logs,
            extensions=extensions or {LEGACY_EXTENSION: {"schema_version": "1.0", "post_qc_invoked": False}},
        )
        write_render_result(result, context.attempts_directory)
        self._event(request, context, 2, status, finished_at)
        return result

    def _blocked_or_failed(
        self,
        request: RenderRequest,
        context: RenderExecutionContext,
        issues: tuple[RenderIssue, ...],
        started_at: str,
        *,
        metrics: Mapping[str, int] | None = None,
        logs: tuple[Mapping[str, Any], ...] = (),
    ) -> RenderResult:
        blocking = {
            RendererErrorCode.RENDER_GATE_BLOCKED,
            RendererErrorCode.RENDER_RIGHTS_BLOCKED,
            RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED,
        }
        status = RenderStatus.BLOCKED if issues and issues[0].code in blocking else RenderStatus.FAILED
        return self._terminal_result(
            request,
            context,
            status=status,
            started_at=started_at,
            finished_at=self._clock(),
            errors=issues,
            metrics=metrics,
            logs=logs,
        )

    def _font_environment(
        self, request: RenderRequest, resolver: RootResolver
    ) -> dict[str, str]:
        assets = {item.asset_id: item for item in request.assets}
        extension = request.extensions[LEGACY_EXTENSION]
        font_ids = extension["font_asset_ids"]
        environment: dict[str, str] = {}
        for role, variable in (
            ("title", "BOOK_VIDEO_TITLE_FONT"),
            ("chinese", "BOOK_VIDEO_CHINESE_FONT"),
            ("english", "BOOK_VIDEO_ENGLISH_FONT"),
        ):
            asset = assets[str(font_ids[role])]
            environment[variable] = str(resolver.resolve(asset.ref, require_exists=True))
        return environment

    def _probe_issues(
        self, request: RenderRequest, probe: Mapping[str, Any]
    ) -> tuple[RenderIssue, ...]:
        issues: list[RenderIssue] = []
        expected = request.output_spec
        video = probe.get("video")
        audio = probe.get("audio")
        if not isinstance(video, Mapping) or not isinstance(audio, Mapping):
            return (_issue(RendererErrorCode.RENDER_PROBE_FAILED, "Probe lacks video/audio streams.", "$.media_probe", stage="probe"),)
        comparisons = (
            (video.get("codec"), expected["video"]["codec"], "video.codec"),
            (video.get("width"), expected["width"], "video.width"),
            (video.get("height"), expected["height"], "video.height"),
            (dict(video.get("fps", {})) if isinstance(video.get("fps"), Mapping) else None, dict(expected["fps"]), "video.fps"),
            (video.get("pixel_format"), expected["pixel_format"], "video.pixel_format"),
            (audio.get("codec"), expected["audio"]["codec"], "audio.codec"),
            (audio.get("sample_rate"), expected["audio"]["sample_rate"], "audio.sample_rate"),
            (audio.get("channels"), expected["audio"]["channels"], "audio.channels"),
        )
        for actual, wanted, field in comparisons:
            if actual != wanted:
                issues.append(_issue(RendererErrorCode.RENDER_PROBE_FAILED, "Probe value differs from OutputSpec.", f"$.media_probe.{field}", stage="probe"))
        duration = probe.get("duration_ticks")
        fps = expected["fps"]
        tolerance = (1000 * int(fps["denominator"]) + int(fps["numerator"]) - 1) // int(fps["numerator"]) + 1
        if not isinstance(duration, int) or isinstance(duration, bool) or abs(duration - int(expected["duration_ticks"])) > tolerance:
            issues.append(_issue(RendererErrorCode.RENDER_PROBE_FAILED, "Probe duration exceeds one-frame tolerance.", "$.media_probe.duration_ticks", stage="probe"))
        frame_count = video.get("frame_count")
        if not isinstance(frame_count, int) or isinstance(frame_count, bool) or frame_count <= 0:
            issues.append(_issue(RendererErrorCode.RENDER_PROBE_FAILED, "Probe frame_count is invalid.", "$.media_probe.video.frame_count", stage="probe"))
        return stable_issues(issues)

    def render(
        self, request: RenderRequest, context: RenderExecutionContext
    ) -> RenderResult:
        self._validate_context(context)
        started_at = self._clock()
        self._event(request, context, 0, RenderStatus.PENDING, started_at)
        preflight = self.validate(request, context)
        if preflight:
            return self._blocked_or_failed(request, context, preflight, started_at)

        entrypoint, _ = self._legacy_sources(request, context.resolver)
        output_path, sidecar_paths, _ = self._expected_paths(request, context.resolver)
        project = context.resolver.bindings["project"]
        runtime = context.resolver.bindings["runtime"]
        running_at = self._clock()
        self._event(request, context, 1, RenderStatus.RUNNING, running_at)
        attempt_dir = Path(context.attempts_directory).resolve() / context.attempt_id
        logs_dir = attempt_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = logs_dir / "renderer.stdout.log"
        stderr_path = logs_dir / "renderer.stderr.log"
        environment = dict(os.environ if context.environment is None else context.environment)
        environment.update(self._font_environment(request, context.resolver))
        command = [sys.executable, str(entrypoint), str(project), "--release-version", "v4"]
        try:
            completed = self._runner.run(command, cwd=runtime, env=environment)
        except Exception:
            completed = CommandResult(returncode=-1, stderr="Legacy renderer runner raised an exception.")
        stdout_path.write_text(completed.stdout, encoding="utf-8", errors="replace")
        stderr_path.write_text(completed.stderr, encoding="utf-8", errors="replace")
        logs = (
            {"role": "renderer_stdout", "ref": {"root": "project", "path": _portable(project, stdout_path).path}},
            {"role": "renderer_stderr", "ref": {"root": "project", "path": _portable(project, stderr_path).path}},
        )
        metrics = {"elapsed_ms": max(0, int(completed.elapsed_ms)), "runner_return_code": int(completed.returncode)}
        if completed.returncode != 0:
            issues = (
                _issue(RendererErrorCode.RENDER_PROCESS_FAILED, "Legacy V4 renderer process failed.", "$.attempt", stage="render", details={"returncode": int(completed.returncode)}),
            )
            return self._blocked_or_failed(request, context, issues, started_at, metrics=metrics, logs=logs)

        post_input_issues = validate_request_filesystem(request, context.resolver)
        if post_input_issues:
            return self._blocked_or_failed(request, context, post_input_issues, started_at, metrics=metrics, logs=logs)
        if not output_path.is_file() or output_path.stat().st_size <= 0:
            issues = (_issue(RendererErrorCode.RENDER_OUTPUT_MISSING, "Legacy V4 output is missing or empty.", "$.output", stage="collect"),)
            return self._blocked_or_failed(request, context, issues, started_at, metrics=metrics, logs=logs)
        missing_sidecars = [declaration["asset_id"] for declaration, path in sidecar_paths if not path.is_file() or path.stat().st_size <= 0]
        if missing_sidecars:
            issues = (_issue(RendererErrorCode.RENDER_OUTPUT_MISSING, "Required legacy sidecars are missing or empty.", "$.sidecars", stage="collect", details={"missing_count": len(missing_sidecars)}),)
            return self._blocked_or_failed(request, context, issues, started_at, metrics=metrics, logs=logs)

        try:
            probe_payload = dict(self._probe.probe(output_path))
            probe_issues = self._probe_issues(request, probe_payload)
            if probe_issues:
                return self._blocked_or_failed(request, context, probe_issues, started_at, metrics=metrics, logs=logs)
            probe_path = write_canonical_once(attempt_dir / "probe" / "media-probe.json", probe_payload)
        except Exception:
            issues = (_issue(RendererErrorCode.RENDER_PROBE_FAILED, "Legacy V4 output probe failed.", "$.media_probe", stage="probe"),)
            return self._blocked_or_failed(request, context, issues, started_at, metrics=metrics, logs=logs)

        output_artifact = _result_artifact(project, output_path, asset_id=str(request.output["artifact_id"]), role=str(request.output["role"]), media_type="video/mp4")
        sidecar_artifacts = [
            _result_artifact(
                project,
                path,
                asset_id=str(declaration["asset_id"]),
                role=str(declaration["role"]),
                media_type=str(declaration["media_type"]),
            )
            for declaration, path in sidecar_paths
        ]
        probe_artifact = _result_artifact(project, probe_path, asset_id="media-probe", role="media_probe", media_type="application/json")
        all_sidecars = tuple([*sidecar_artifacts, probe_artifact])
        media_probe = {"sidecar_artifact_id": probe_artifact.asset_id, **probe_payload}
        checks = [
            {"id": "output_exists", "result": "pass", "severity": "error"},
            {"id": "output_nonzero", "result": "pass", "severity": "error"},
            {"id": "input_hashes_stable", "result": "pass", "severity": "error"},
            {"id": "media_probe_readable", "result": "pass", "severity": "error"},
            {"id": "output_spec_match", "result": "pass", "severity": "error"},
        ]
        qc_handoff = {
            "release_id": request.release.id,
            "request_hash": request.request_hash,
            "attempt_id": context.attempt_id,
            "output_asset_ids": [output_artifact.asset_id],
            "output_spec_snapshot": dict(request.output_spec),
            "media_probe_artifact_id": probe_artifact.asset_id,
            "renderer_checks": checks,
            "expected_post_qc_profile_id": "v4-post-qc-v1",
            "rights_snapshot_sha256": str(request.rights["snapshot_sha256"]),
            "approval_snapshot_sha256": str(request.approvals["snapshot_sha256"]),
        }
        metrics.update(
            {
                "output_bytes": output_artifact.bytes,
                "duration_ticks": int(probe_payload["duration_ticks"]),
                "frame_count": int(probe_payload["video"]["frame_count"]),
            }
        )
        return self._terminal_result(
            request,
            context,
            status=RenderStatus.SUCCEEDED,
            started_at=started_at,
            finished_at=self._clock(),
            output=(output_artifact,),
            sidecars=all_sidecars,
            media_probe=media_probe,
            metrics=metrics,
            qc_handoff=qc_handoff,
            logs=logs,
            extensions={
                LEGACY_EXTENSION: {
                    "schema_version": "1.0",
                    "legacy_manifest_asset_id": "legacy-render-manifest",
                    "legacy_renderer_qc_asset_id": "legacy-renderer-qc",
                    "post_qc_invoked": False,
                }
            },
        )


__all__ = [
    "CommandResult",
    "FFprobeMediaProbe",
    "LegacyV4Renderer",
    "RenderExecutionContext",
    "SubprocessCommandRunner",
]
