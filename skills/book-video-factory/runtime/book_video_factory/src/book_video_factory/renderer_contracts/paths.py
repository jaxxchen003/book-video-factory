"""Portable relative paths and runtime-only root resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Mapping

from .models import PortableRef


class PortablePathError(ValueError):
    pass


def normalize_portable_path(value: str) -> str:
    """Return a `/`-separated relative path or fail closed.

    Backslashes in relative input are normalized for Windows callers. Drive paths,
    UNC paths and traversal are rejected before normalization.
    """
    if not isinstance(value, str) or not value:
        raise PortablePathError("portable path must be a non-empty string")
    if "\x00" in value:
        raise PortablePathError("portable path must not contain NUL")
    if value.startswith(("\\\\", "//")):
        raise PortablePathError("UNC paths are not portable")
    windows = PureWindowsPath(value)
    if windows.drive or windows.is_absolute():
        raise PortablePathError("drive-qualified paths are not portable")
    if PurePosixPath(value).is_absolute():
        raise PortablePathError("absolute paths are not portable")
    normalized = value.replace("\\", "/")
    parts = normalized.split("/")
    if any(part == "" for part in parts):
        raise PortablePathError("portable path must not contain empty segments")
    if any(part in {".", ".."} for part in parts):
        raise PortablePathError("portable path must not contain '.' or '..' segments")
    return "/".join(parts)


@dataclass(frozen=True)
class RootResolver:
    """Resolve logical refs against injected physical roots.

    Root bindings are runtime-only and must never be serialized or hashed.
    """

    bindings: Mapping[str, Path]

    def __post_init__(self) -> None:
        resolved: dict[str, Path] = {}
        for name, path in self.bindings.items():
            if not isinstance(name, str) or not name:
                raise PortablePathError("root binding name must be non-empty")
            resolved[name] = Path(path).expanduser().resolve(strict=False)
        object.__setattr__(self, "bindings", MappingProxyType(resolved))

    def resolve(self, ref: PortableRef, *, require_exists: bool = False) -> Path:
        root = self.bindings.get(ref.root)
        if root is None:
            raise PortablePathError(f"undeclared root binding: {ref.root}")
        portable = normalize_portable_path(ref.path)
        candidate = root.joinpath(*portable.split("/"))
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError as error:
            raise PortablePathError(
                f"portable path resolves outside root {ref.root}: {ref.path}"
            ) from error
        if require_exists and not resolved.exists():
            raise FileNotFoundError(resolved)
        return resolved

    def resolve_output(
        self,
        ref: PortableRef,
        *,
        writable_roots: frozenset[str] = frozenset({"project", "output"}),
    ) -> Path:
        if ref.root not in writable_roots:
            raise PortablePathError(f"root is not authorized for output: {ref.root}")
        target = self.resolve(ref)
        root = self.bindings[ref.root]
        relative = target.relative_to(root)
        current = root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise PortablePathError(f"output path uses a symlink: {ref.path}")
        # On Windows os.path.abspath also normalizes path case/segments before the
        # final resolve check; on POSIX this remains a no-op safety belt.
        absolute = Path(os.path.abspath(target)).resolve(strict=False)
        try:
            absolute.relative_to(root)
        except ValueError as error:
            raise PortablePathError(f"output path escapes root: {ref.path}") from error
        return target
