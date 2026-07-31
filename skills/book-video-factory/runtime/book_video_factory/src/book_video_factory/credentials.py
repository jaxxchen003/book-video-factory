from __future__ import annotations

import os
import platform
import shutil
import subprocess
from collections.abc import Mapping


def is_macos() -> bool:
    """Return whether the current Python runtime is running on macOS."""

    return platform.system() == "Darwin"


def macos_security_executable() -> str | None:
    """Return the macOS Keychain CLI only when it is actually usable."""

    if not is_macos():
        return None
    return shutil.which("security")


def credential_available(
    env_name: str,
    keychain_service: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Check an environment variable, then the macOS Keychain without reading it."""

    environment = os.environ if environ is None else environ
    if environment.get(env_name, "").strip():
        return True
    security = macos_security_executable()
    if security is None:
        return False
    result = subprocess.run(
        [security, "find-generic-password", "-s", keychain_service],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def load_secret(
    env_name: str,
    keychain_service: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """Load a secret from the environment or macOS Keychain without logging it."""

    environment = os.environ if environ is None else environ
    value = environment.get(env_name, "").strip()
    if value:
        return value
    security = macos_security_executable()
    if security is None:
        return None
    completed = subprocess.run(
        [security, "find-generic-password", "-s", keychain_service, "-w"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0 and completed.stdout.strip():
        return completed.stdout.strip()
    return None
