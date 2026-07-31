"""Frozen persistence models for Renderer Contract v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from .enums import RenderMode, RenderStatus


def freeze_value(value: Any) -> Any:
    """Recursively freeze JSON-shaped values without changing their semantics."""
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): freeze_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze_value(item) for item in value)
    return value


@dataclass(frozen=True)
class PortableRef:
    root: str
    path: str


@dataclass(frozen=True)
class ArtifactBinding:
    asset_id: str
    role: str
    ref: PortableRef
    bytes: int
    sha256: str
    media_type: str
    source_manifest_artifact_id: str | None = None
    rights_ref: str | None = None


@dataclass(frozen=True)
class ProjectBinding:
    id: str
    manifest_ref: PortableRef
    manifest_sha256: str


@dataclass(frozen=True)
class ReleaseBinding:
    id: str
    manifest_id: str
    manifest_version: str
    manifest_ref: PortableRef
    manifest_sha256: str


@dataclass(frozen=True)
class ProfileBinding:
    id: str
    revision: int
    ref: PortableRef
    sha256: str


@dataclass(frozen=True)
class RendererIdentity:
    id: str
    version: str
    capability_document_sha256: str
    capability_document_ref: PortableRef | None = None
    required_capabilities: tuple[str, ...] = ()
    degradation_plan: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_capabilities", tuple(self.required_capabilities))
        if self.degradation_plan is not None:
            object.__setattr__(self, "degradation_plan", freeze_value(self.degradation_plan))


@dataclass(frozen=True)
class RenderRequest:
    schema_version: str
    request_id: str
    request_hash: str
    project: ProjectBinding
    release: ReleaseBinding
    render_mode: RenderMode
    renderer: RendererIdentity
    profile: ProfileBinding
    roots: Mapping[str, Any]
    output_spec: Mapping[str, Any]
    output: Mapping[str, Any]
    timeline: Mapping[str, Any]
    audio: Mapping[str, Any]
    captions: Mapping[str, Any]
    assets: tuple[ArtifactBinding, ...]
    overlays: tuple[Mapping[str, Any], ...]
    rights: Mapping[str, Any]
    approvals: Mapping[str, Any]
    determinism: Mapping[str, Any]
    extensions: Mapping[str, Any]
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        for name in (
            "roots",
            "output_spec",
            "output",
            "timeline",
            "audio",
            "captions",
            "rights",
            "approvals",
            "determinism",
            "extensions",
        ):
            object.__setattr__(self, name, freeze_value(getattr(self, name)))
        object.__setattr__(self, "assets", tuple(self.assets))
        object.__setattr__(
            self, "overlays", tuple(freeze_value(item) for item in self.overlays)
        )
        if self.metadata is not None:
            object.__setattr__(self, "metadata", freeze_value(self.metadata))

    @property
    def project_id(self) -> str:
        return self.project.id

    @property
    def release_id(self) -> str:
        return self.release.id

    @property
    def release_snapshot_hash(self) -> str:
        return self.release.manifest_sha256


@dataclass(frozen=True)
class RenderResult:
    schema_version: str
    request_id: str
    request_hash: str
    attempt_id: str
    status: RenderStatus
    renderer: RendererIdentity
    started_at: str | None
    finished_at: str | None
    output: tuple[ArtifactBinding, ...]
    sidecars: tuple[ArtifactBinding, ...]
    media_probe: Mapping[str, Any] | None
    warnings: tuple[Mapping[str, Any], ...]
    errors: tuple[Mapping[str, Any], ...]
    primary_error_code: str | None
    metrics: Mapping[str, Any]
    input_hashes: Mapping[str, str]
    output_hashes: Mapping[str, str]
    qc_handoff: Mapping[str, Any] | None
    logs: tuple[Mapping[str, Any], ...]
    extensions: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "output", tuple(self.output))
        object.__setattr__(self, "sidecars", tuple(self.sidecars))
        for name in ("metrics", "input_hashes", "output_hashes", "extensions"):
            object.__setattr__(self, name, freeze_value(getattr(self, name)))
        for name in ("warnings", "errors", "logs"):
            object.__setattr__(
                self, name, tuple(freeze_value(item) for item in getattr(self, name))
            )
        if self.media_probe is not None:
            object.__setattr__(self, "media_probe", freeze_value(self.media_probe))
        if self.qc_handoff is not None:
            object.__setattr__(self, "qc_handoff", freeze_value(self.qc_handoff))


@dataclass(frozen=True)
class CapabilityDefinition:
    supported: bool
    version: str
    constraints: Mapping[str, Any]
    determinism: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "constraints", freeze_value(self.constraints))


@dataclass(frozen=True)
class RendererCapabilities:
    schema_version: str
    renderer: RendererIdentity
    supported_contract_versions: tuple[str, ...]
    determinism: Mapping[str, Any]
    constraints: Mapping[str, Any]
    capabilities: Mapping[str, CapabilityDefinition]
    supported_extensions: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "supported_contract_versions", tuple(self.supported_contract_versions)
        )
        for name in ("determinism", "constraints", "capabilities", "supported_extensions"):
            object.__setattr__(self, name, freeze_value(getattr(self, name)))


@dataclass(frozen=True)
class ReleaseSnapshot:
    schema_version: str
    snapshot_id: str
    snapshot_hash: str
    project_id: str
    release_id: str
    created_at: str
    profile: Mapping[str, Any]
    artifacts: tuple[ArtifactBinding, ...]
    artifact_hashes: Mapping[str, str]
    timeline_source: Mapping[str, Any]
    audio_source: Mapping[str, Any]
    caption_source: Mapping[str, Any]
    rights: Mapping[str, Any]
    approvals: Mapping[str, Any]
    release_gates: Mapping[str, Any]
    source_manifests: tuple[Mapping[str, Any], ...]
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(
            self,
            "source_manifests",
            tuple(freeze_value(item) for item in self.source_manifests),
        )
        for name in (
            "profile",
            "artifact_hashes",
            "timeline_source",
            "audio_source",
            "caption_source",
            "rights",
            "approvals",
            "release_gates",
            "metadata",
        ):
            object.__setattr__(self, name, freeze_value(getattr(self, name)))
