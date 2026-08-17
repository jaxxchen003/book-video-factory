from __future__ import annotations

import os
import platform
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from PIL import ImageFont


class FontConfigurationError(FileNotFoundError):
    """Raised when no configured, system, or licensed bundled font is usable."""


def _font_index(fonts: Mapping[str, Any], kind: str) -> int:
    if kind == "chinese":
        return int(fonts.get("chinese_body_index", 0))
    return 0


def _require_openable(path: Path, *, kind: str, index: int) -> Path:
    if not path.is_file():
        raise FontConfigurationError(f"Configured {kind} font does not exist: {path}")
    try:
        ImageFont.truetype(str(path), size=16, index=index)
    except OSError as error:
        raise FontConfigurationError(
            f"Configured {kind} font cannot be opened by Pillow: {path}"
        ) from error
    return path.resolve()


def _configured_path(factory: Path, raw: object) -> Path | None:
    value = str(raw or "").strip()
    if not value:
        return None
    configured = Path(value).expanduser()
    return configured if configured.is_absolute() else factory / configured


def system_font_directories(
    fonts: Mapping[str, Any],
    *,
    environ: Mapping[str, str],
    platform_name: str,
) -> tuple[Path, ...]:
    environment_names = fonts.get("environment")
    environment = environment_names if isinstance(environment_names, Mapping) else {}
    search_env_name = str(environment.get("search_dirs") or "").strip()
    directories: list[Path] = []
    if search_env_name:
        configured = environ.get(search_env_name, "").strip()
        if configured:
            directories.extend(
                Path(item).expanduser()
                for item in configured.split(os.pathsep)
                if item.strip()
            )
    if platform_name == "Windows":
        windows_directory = environ.get("WINDIR", "").strip()
        if windows_directory:
            directories.append(Path(windows_directory) / "Fonts")
    unique: list[Path] = []
    for directory in directories:
        resolved = directory.resolve()
        if resolved not in unique:
            unique.append(resolved)
    return tuple(unique)


def resolve_font_path(
    factory: Path,
    fonts: Mapping[str, Any],
    kind: str,
    *,
    environ: Mapping[str, str] | None = None,
    platform_name: str | None = None,
) -> Path:
    """Resolve one font deterministically and fail closed when none is usable."""

    if kind not in {"title", "chinese", "english"}:
        raise FontConfigurationError(f"Unknown font role: {kind}")
    environment = os.environ if environ is None else environ
    current_platform = platform.system() if platform_name is None else platform_name
    index = _font_index(fonts, kind)

    environment_names = fonts.get("environment")
    environment_config = (
        environment_names if isinstance(environment_names, Mapping) else {}
    )
    explicit_environment = str(environment_config.get(kind) or "").strip()
    if explicit_environment:
        value = environment.get(explicit_environment, "").strip()
        if value:
            return _require_openable(Path(value).expanduser(), kind=kind, index=index)

    configured = _configured_path(factory, fonts.get(kind))
    if configured is not None:
        return _require_openable(configured, kind=kind, index=index)

    system_candidates = fonts.get("system_candidates")
    candidates_by_kind = (
        system_candidates if isinstance(system_candidates, Mapping) else {}
    )
    raw_candidates = candidates_by_kind.get(kind, [])
    candidates = raw_candidates if isinstance(raw_candidates, list) else []
    for raw_candidate in candidates:
        name = str(raw_candidate).strip()
        relative = Path(name)
        if not name or relative.is_absolute() or len(relative.parts) != 1:
            raise FontConfigurationError(
                f"System font candidate for {kind} must be a filename: {name!r}"
            )
        for directory in system_font_directories(
            fonts, environ=environment, platform_name=current_platform
        ):
            candidate = directory / relative
            if not candidate.is_file():
                continue
            try:
                return _require_openable(candidate, kind=kind, index=index)
            except FontConfigurationError:
                continue

    fallback_config = fonts.get("bundled_fallback")
    if isinstance(fallback_config, Mapping):
        fallback_raw = fallback_config.get(kind)
    else:
        fallback_raw = fallback_config
    fallback = _configured_path(factory, fallback_raw)
    if fallback is not None:
        factory_root = factory.resolve()
        resolved_fallback = fallback.resolve()
        try:
            resolved_fallback.relative_to(factory_root)
        except ValueError as error:
            raise FontConfigurationError(
                f"Bundled {kind} fallback must stay inside the runtime: {fallback}"
            ) from error
        return _require_openable(resolved_fallback, kind=kind, index=index)

    remediation = (
        f"Set {explicit_environment} to a licensed font file"
        if explicit_environment
        else f"Configure fonts.{kind} with a licensed font file"
    )
    raise FontConfigurationError(
        f"No usable {kind} font is configured. {remediation}; "
        "the renderer refuses to silently use a bitmap or missing-glyph fallback."
    )
