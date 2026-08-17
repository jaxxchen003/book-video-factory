"""Strict serialization and deserialization for Renderer Contract v1."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .canonical import normalize_for_canonical_json
from .enums import RenderMode, RendererCapability, RendererErrorCode, RenderStatus
from .errors import ContractValidationError, RenderIssue
from .models import (
    ArtifactBinding,
    CapabilityDefinition,
    PortableRef,
    ProfileBinding,
    ProjectBinding,
    ReleaseBinding,
    ReleaseSnapshot,
    RenderRequest,
    RendererCapabilities,
    RendererIdentity,
    RenderResult,
)


def _plain(value: Any) -> Any:
    return normalize_for_canonical_json(value)


def _ref_to_dict(ref: PortableRef) -> dict[str, str]:
    return {"root": ref.root, "path": ref.path}


def _artifact_to_dict(
    artifact: ArtifactBinding, *, id_key: str = "asset_id"
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        id_key: artifact.asset_id,
        "role": artifact.role,
        "ref": _ref_to_dict(artifact.ref),
        "bytes": artifact.bytes,
        "sha256": artifact.sha256,
        "media_type": artifact.media_type,
    }
    if artifact.source_manifest_artifact_id is not None:
        payload["source_manifest_artifact_id"] = artifact.source_manifest_artifact_id
    if artifact.rights_ref is not None:
        payload["rights_ref"] = artifact.rights_ref
    return payload


def render_request_to_dict(request: RenderRequest) -> dict[str, Any]:
    renderer: dict[str, Any] = {
        "id": request.renderer.id,
        "version": request.renderer.version,
        "capability_document_ref": _ref_to_dict(
            request.renderer.capability_document_ref  # type: ignore[arg-type]
        ),
        "capability_document_sha256": request.renderer.capability_document_sha256,
        "required_capabilities": list(request.renderer.required_capabilities),
    }
    if request.renderer.degradation_plan is not None:
        renderer["degradation_plan"] = _plain(request.renderer.degradation_plan)
    payload: dict[str, Any] = {
        "schema_version": request.schema_version,
        "request_id": request.request_id,
        "request_hash": request.request_hash,
        "project": {
            "id": request.project.id,
            "manifest_ref": _ref_to_dict(request.project.manifest_ref),
            "manifest_sha256": request.project.manifest_sha256,
        },
        "release": {
            "id": request.release.id,
            "manifest_id": request.release.manifest_id,
            "manifest_version": request.release.manifest_version,
            "manifest_ref": _ref_to_dict(request.release.manifest_ref),
            "manifest_sha256": request.release.manifest_sha256,
        },
        "render_mode": request.render_mode.value,
        "renderer": renderer,
        "profile": {
            "id": request.profile.id,
            "revision": request.profile.revision,
            "ref": _ref_to_dict(request.profile.ref),
            "sha256": request.profile.sha256,
        },
        "roots": _plain(request.roots),
        "output_spec": _plain(request.output_spec),
        "output": _plain(request.output),
        "timeline": _plain(request.timeline),
        "audio": _plain(request.audio),
        "captions": _plain(request.captions),
        "assets": [_artifact_to_dict(item) for item in request.assets],
        "overlays": [_plain(item) for item in request.overlays],
        "rights": _plain(request.rights),
        "approvals": _plain(request.approvals),
        "determinism": _plain(request.determinism),
        "extensions": _plain(request.extensions),
    }
    if request.metadata is not None:
        payload["metadata"] = _plain(request.metadata)
    return payload


def render_result_to_dict(result: RenderResult) -> dict[str, Any]:
    return {
        "schema_version": result.schema_version,
        "request_id": result.request_id,
        "request_hash": result.request_hash,
        "attempt_id": result.attempt_id,
        "status": result.status.value,
        "renderer": {
            "id": result.renderer.id,
            "version": result.renderer.version,
            "capability_document_sha256": result.renderer.capability_document_sha256,
        },
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "output": [_artifact_to_dict(item, id_key="artifact_id") for item in result.output],
        "sidecars": [_artifact_to_dict(item, id_key="artifact_id") for item in result.sidecars],
        "media_probe": _plain(result.media_probe),
        "warnings": [_plain(item) for item in result.warnings],
        "errors": [_plain(item) for item in result.errors],
        "primary_error_code": result.primary_error_code,
        "metrics": _plain(result.metrics),
        "input_hashes": _plain(result.input_hashes),
        "output_hashes": _plain(result.output_hashes),
        "qc_handoff": _plain(result.qc_handoff),
        "logs": [_plain(item) for item in result.logs],
        "extensions": _plain(result.extensions),
    }


def capabilities_to_dict(document: RendererCapabilities) -> dict[str, Any]:
    return {
        "schema_version": document.schema_version,
        "renderer": {"id": document.renderer.id, "version": document.renderer.version},
        "supported_contract_versions": list(document.supported_contract_versions),
        "determinism": _plain(document.determinism),
        "constraints": _plain(document.constraints),
        "capabilities": {
            name: {
                "supported": definition.supported,
                "version": definition.version,
                "constraints": _plain(definition.constraints),
                "determinism": definition.determinism,
            }
            for name, definition in document.capabilities.items()
        },
        "supported_extensions": _plain(document.supported_extensions),
    }


def release_snapshot_to_dict(snapshot: ReleaseSnapshot) -> dict[str, Any]:
    return {
        "schema_version": snapshot.schema_version,
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_hash": snapshot.snapshot_hash,
        "project_id": snapshot.project_id,
        "release_id": snapshot.release_id,
        "created_at": snapshot.created_at,
        "profile": _plain(snapshot.profile),
        "artifacts": [_artifact_to_dict(item) for item in snapshot.artifacts],
        "artifact_hashes": _plain(snapshot.artifact_hashes),
        "timeline_source": _plain(snapshot.timeline_source),
        "audio_source": _plain(snapshot.audio_source),
        "caption_source": _plain(snapshot.caption_source),
        "rights": _plain(snapshot.rights),
        "approvals": _plain(snapshot.approvals),
        "release_gates": _plain(snapshot.release_gates),
        "source_manifests": [_plain(item) for item in snapshot.source_manifests],
        "metadata": _plain(snapshot.metadata),
    }


class _Parser:
    def __init__(self) -> None:
        self.issues: list[RenderIssue] = []

    def issue(self, message: str, field: str) -> None:
        self.issues.append(
            RenderIssue(RendererErrorCode.RENDER_INPUT_INVALID, message, field)
        )

    def obj(self, value: Any, field: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            self.issue("expected object", field)
            return {}
        return value

    def array(self, value: Any, field: str) -> list[Any]:
        if not isinstance(value, list):
            self.issue("expected array", field)
            return []
        return value

    def exact(
        self,
        payload: Mapping[str, Any],
        *,
        required: Iterable[str],
        optional: Iterable[str] = (),
        field: str = "$",
    ) -> None:
        required_set = set(required)
        allowed = required_set | set(optional)
        for key in sorted(required_set - payload.keys()):
            self.issue("required field is missing", f"{field}.{key}")
        for key in sorted(payload.keys() - allowed):
            self.issue("unknown field is not allowed", f"{field}.{key}")

    def finish(self) -> None:
        if self.issues:
            raise ContractValidationError(self.issues)


def _string(parser: _Parser, value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        parser.issue("expected non-empty string", field)
        return ""
    return value


def _integer(parser: _Parser, value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        parser.issue("expected integer", field)
        return 0
    return value


def _ref(parser: _Parser, value: Any, field: str) -> PortableRef:
    payload = parser.obj(value, field)
    parser.exact(payload, required=("root", "path"), field=field)
    return PortableRef(
        _string(parser, payload.get("root"), f"{field}.root"),
        _string(parser, payload.get("path"), f"{field}.path"),
    )


def _artifact(
    parser: _Parser, value: Any, field: str, *, id_key: str = "asset_id"
) -> ArtifactBinding:
    payload = parser.obj(value, field)
    parser.exact(
        payload,
        required=(id_key, "role", "ref", "bytes", "sha256", "media_type"),
        optional=("source_manifest_artifact_id", "rights_ref"),
        field=field,
    )
    return ArtifactBinding(
        asset_id=_string(parser, payload.get(id_key), f"{field}.{id_key}"),
        role=_string(parser, payload.get("role"), f"{field}.role"),
        ref=_ref(parser, payload.get("ref"), f"{field}.ref"),
        bytes=_integer(parser, payload.get("bytes"), f"{field}.bytes"),
        sha256=_string(parser, payload.get("sha256"), f"{field}.sha256"),
        media_type=_string(parser, payload.get("media_type"), f"{field}.media_type"),
        source_manifest_artifact_id=payload.get("source_manifest_artifact_id"),
        rights_ref=payload.get("rights_ref"),
    )


def _enum(parser: _Parser, enum_type: Any, value: Any, field: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError):
        parser.issue("unknown enum value", field)
        return next(iter(enum_type))


def render_request_from_dict(value: Mapping[str, Any]) -> RenderRequest:
    parser = _Parser()
    payload = parser.obj(value, "$")
    required = (
        "schema_version", "request_id", "request_hash", "project", "release",
        "render_mode", "renderer", "profile", "roots", "output_spec", "output",
        "timeline", "audio", "captions", "assets", "overlays", "rights",
        "approvals", "determinism", "extensions",
    )
    parser.exact(payload, required=required, optional=("metadata",))
    project = parser.obj(payload.get("project"), "$.project")
    parser.exact(project, required=("id", "manifest_ref", "manifest_sha256"), field="$.project")
    release = parser.obj(payload.get("release"), "$.release")
    parser.exact(
        release,
        required=("id", "manifest_id", "manifest_version", "manifest_ref", "manifest_sha256"),
        field="$.release",
    )
    renderer = parser.obj(payload.get("renderer"), "$.renderer")
    parser.exact(
        renderer,
        required=("id", "version", "capability_document_ref", "capability_document_sha256", "required_capabilities"),
        optional=("degradation_plan",),
        field="$.renderer",
    )
    profile = parser.obj(payload.get("profile"), "$.profile")
    parser.exact(profile, required=("id", "revision", "ref", "sha256"), field="$.profile")
    required_caps = parser.array(renderer.get("required_capabilities"), "$.renderer.required_capabilities")
    assets = parser.array(payload.get("assets"), "$.assets")
    overlays = parser.array(payload.get("overlays"), "$.overlays")
    model = RenderRequest(
        schema_version=_string(parser, payload.get("schema_version"), "$.schema_version"),
        request_id=_string(parser, payload.get("request_id"), "$.request_id"),
        request_hash=_string(parser, payload.get("request_hash"), "$.request_hash"),
        project=ProjectBinding(
            _string(parser, project.get("id"), "$.project.id"),
            _ref(parser, project.get("manifest_ref"), "$.project.manifest_ref"),
            _string(parser, project.get("manifest_sha256"), "$.project.manifest_sha256"),
        ),
        release=ReleaseBinding(
            _string(parser, release.get("id"), "$.release.id"),
            _string(parser, release.get("manifest_id"), "$.release.manifest_id"),
            _string(parser, release.get("manifest_version"), "$.release.manifest_version"),
            _ref(parser, release.get("manifest_ref"), "$.release.manifest_ref"),
            _string(parser, release.get("manifest_sha256"), "$.release.manifest_sha256"),
        ),
        render_mode=_enum(parser, RenderMode, payload.get("render_mode"), "$.render_mode"),
        renderer=RendererIdentity(
            id=_string(parser, renderer.get("id"), "$.renderer.id"),
            version=_string(parser, renderer.get("version"), "$.renderer.version"),
            capability_document_sha256=_string(parser, renderer.get("capability_document_sha256"), "$.renderer.capability_document_sha256"),
            capability_document_ref=_ref(parser, renderer.get("capability_document_ref"), "$.renderer.capability_document_ref"),
            required_capabilities=tuple(
                _string(parser, item, f"$.renderer.required_capabilities[{index}]")
                for index, item in enumerate(required_caps)
            ),
            degradation_plan=renderer.get("degradation_plan"),
        ),
        profile=ProfileBinding(
            _string(parser, profile.get("id"), "$.profile.id"),
            _integer(parser, profile.get("revision"), "$.profile.revision"),
            _ref(parser, profile.get("ref"), "$.profile.ref"),
            _string(parser, profile.get("sha256"), "$.profile.sha256"),
        ),
        roots=parser.obj(payload.get("roots"), "$.roots"),
        output_spec=parser.obj(payload.get("output_spec"), "$.output_spec"),
        output=parser.obj(payload.get("output"), "$.output"),
        timeline=parser.obj(payload.get("timeline"), "$.timeline"),
        audio=parser.obj(payload.get("audio"), "$.audio"),
        captions=parser.obj(payload.get("captions"), "$.captions"),
        assets=tuple(_artifact(parser, item, f"$.assets[{index}]") for index, item in enumerate(assets)),
        overlays=tuple(parser.obj(item, f"$.overlays[{index}]") for index, item in enumerate(overlays)),
        rights=parser.obj(payload.get("rights"), "$.rights"),
        approvals=parser.obj(payload.get("approvals"), "$.approvals"),
        determinism=parser.obj(payload.get("determinism"), "$.determinism"),
        extensions=parser.obj(payload.get("extensions"), "$.extensions"),
        metadata=parser.obj(payload.get("metadata"), "$.metadata") if "metadata" in payload else None,
    )
    parser.finish()
    return model


def render_result_from_dict(value: Mapping[str, Any]) -> RenderResult:
    parser = _Parser()
    payload = parser.obj(value, "$")
    required = (
        "schema_version", "request_id", "request_hash", "attempt_id", "status",
        "renderer", "started_at", "finished_at", "output", "sidecars", "media_probe",
        "warnings", "errors", "primary_error_code", "metrics", "input_hashes",
        "output_hashes", "qc_handoff", "logs", "extensions",
    )
    parser.exact(payload, required=required)
    renderer = parser.obj(payload.get("renderer"), "$.renderer")
    parser.exact(renderer, required=("id", "version", "capability_document_sha256"), field="$.renderer")
    output = parser.array(payload.get("output"), "$.output")
    sidecars = parser.array(payload.get("sidecars"), "$.sidecars")
    warnings = parser.array(payload.get("warnings"), "$.warnings")
    errors = parser.array(payload.get("errors"), "$.errors")
    logs = parser.array(payload.get("logs"), "$.logs")
    model = RenderResult(
        schema_version=_string(parser, payload.get("schema_version"), "$.schema_version"),
        request_id=_string(parser, payload.get("request_id"), "$.request_id"),
        request_hash=_string(parser, payload.get("request_hash"), "$.request_hash"),
        attempt_id=_string(parser, payload.get("attempt_id"), "$.attempt_id"),
        status=_enum(parser, RenderStatus, payload.get("status"), "$.status"),
        renderer=RendererIdentity(
            id=_string(parser, renderer.get("id"), "$.renderer.id"),
            version=_string(parser, renderer.get("version"), "$.renderer.version"),
            capability_document_sha256=_string(parser, renderer.get("capability_document_sha256"), "$.renderer.capability_document_sha256"),
        ),
        started_at=payload.get("started_at"), finished_at=payload.get("finished_at"),
        output=tuple(_artifact(parser, item, f"$.output[{index}]", id_key="artifact_id") for index, item in enumerate(output)),
        sidecars=tuple(_artifact(parser, item, f"$.sidecars[{index}]", id_key="artifact_id") for index, item in enumerate(sidecars)),
        media_probe=parser.obj(payload.get("media_probe"), "$.media_probe") if payload.get("media_probe") is not None else None,
        warnings=tuple(parser.obj(item, f"$.warnings[{index}]") for index, item in enumerate(warnings)),
        errors=tuple(parser.obj(item, f"$.errors[{index}]") for index, item in enumerate(errors)),
        primary_error_code=payload.get("primary_error_code"),
        metrics=parser.obj(payload.get("metrics"), "$.metrics"),
        input_hashes=parser.obj(payload.get("input_hashes"), "$.input_hashes"),
        output_hashes=parser.obj(payload.get("output_hashes"), "$.output_hashes"),
        qc_handoff=parser.obj(payload.get("qc_handoff"), "$.qc_handoff") if payload.get("qc_handoff") is not None else None,
        logs=tuple(parser.obj(item, f"$.logs[{index}]") for index, item in enumerate(logs)),
        extensions=parser.obj(payload.get("extensions"), "$.extensions"),
    )
    parser.finish()
    return model


def capabilities_from_dict(value: Mapping[str, Any]) -> RendererCapabilities:
    parser = _Parser()
    payload = parser.obj(value, "$")
    parser.exact(
        payload,
        required=("schema_version", "renderer", "supported_contract_versions", "determinism", "constraints", "capabilities", "supported_extensions"),
    )
    renderer = parser.obj(payload.get("renderer"), "$.renderer")
    parser.exact(renderer, required=("id", "version"), field="$.renderer")
    raw_capabilities = parser.obj(payload.get("capabilities"), "$.capabilities")
    definitions: dict[str, CapabilityDefinition] = {}
    known = {item.value for item in RendererCapability}
    for name, raw in raw_capabilities.items():
        field = f"$.capabilities.{name}"
        if name not in known:
            parser.issue("unknown capability is not allowed", field)
        item = parser.obj(raw, field)
        parser.exact(item, required=("supported", "version", "constraints", "determinism"), field=field)
        if not isinstance(item.get("supported"), bool):
            parser.issue("expected boolean", f"{field}.supported")
        definitions[name] = CapabilityDefinition(
            supported=bool(item.get("supported")),
            version=_string(parser, item.get("version"), f"{field}.version"),
            constraints=parser.obj(item.get("constraints"), f"{field}.constraints"),
            determinism=_string(parser, item.get("determinism"), f"{field}.determinism"),
        )
    versions = parser.array(payload.get("supported_contract_versions"), "$.supported_contract_versions")
    model = RendererCapabilities(
        schema_version=_string(parser, payload.get("schema_version"), "$.schema_version"),
        renderer=RendererIdentity(
            id=_string(parser, renderer.get("id"), "$.renderer.id"),
            version=_string(parser, renderer.get("version"), "$.renderer.version"),
            capability_document_sha256="",
        ),
        supported_contract_versions=tuple(
            _string(parser, item, f"$.supported_contract_versions[{index}]")
            for index, item in enumerate(versions)
        ),
        determinism=parser.obj(payload.get("determinism"), "$.determinism"),
        constraints=parser.obj(payload.get("constraints"), "$.constraints"),
        capabilities=definitions,
        supported_extensions=parser.obj(payload.get("supported_extensions"), "$.supported_extensions"),
    )
    parser.finish()
    return model


def release_snapshot_from_dict(value: Mapping[str, Any]) -> ReleaseSnapshot:
    parser = _Parser()
    payload = parser.obj(value, "$")
    required = (
        "schema_version", "snapshot_id", "snapshot_hash", "project_id", "release_id",
        "created_at", "profile", "artifacts", "artifact_hashes", "timeline_source",
        "audio_source", "caption_source", "rights", "approvals", "release_gates",
        "source_manifests", "metadata",
    )
    parser.exact(payload, required=required)
    artifacts = parser.array(payload.get("artifacts"), "$.artifacts")
    source_manifests = parser.array(payload.get("source_manifests"), "$.source_manifests")
    model = ReleaseSnapshot(
        schema_version=_string(parser, payload.get("schema_version"), "$.schema_version"),
        snapshot_id=_string(parser, payload.get("snapshot_id"), "$.snapshot_id"),
        snapshot_hash=_string(parser, payload.get("snapshot_hash"), "$.snapshot_hash"),
        project_id=_string(parser, payload.get("project_id"), "$.project_id"),
        release_id=_string(parser, payload.get("release_id"), "$.release_id"),
        created_at=_string(parser, payload.get("created_at"), "$.created_at"),
        profile=parser.obj(payload.get("profile"), "$.profile"),
        artifacts=tuple(_artifact(parser, item, f"$.artifacts[{index}]") for index, item in enumerate(artifacts)),
        artifact_hashes=parser.obj(payload.get("artifact_hashes"), "$.artifact_hashes"),
        timeline_source=parser.obj(payload.get("timeline_source"), "$.timeline_source"),
        audio_source=parser.obj(payload.get("audio_source"), "$.audio_source"),
        caption_source=parser.obj(payload.get("caption_source"), "$.caption_source"),
        rights=parser.obj(payload.get("rights"), "$.rights"),
        approvals=parser.obj(payload.get("approvals"), "$.approvals"),
        release_gates=parser.obj(payload.get("release_gates"), "$.release_gates"),
        source_manifests=tuple(parser.obj(item, f"$.source_manifests[{index}]") for index, item in enumerate(source_manifests)),
        metadata=parser.obj(payload.get("metadata"), "$.metadata"),
    )
    parser.finish()
    return model
