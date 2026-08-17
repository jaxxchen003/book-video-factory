from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from book_video_factory import credentials  # noqa: E402
from book_video_factory.freesound import (  # noqa: E402
    FreesoundError,
    load_secret as load_freesound_secret,
)
from book_video_factory.weread import (  # noqa: E402
    WeReadError,
    load_api_key as load_weread_api_key,
)


class CredentialPortabilityTests(unittest.TestCase):
    @mock.patch("book_video_factory.credentials.subprocess.run")
    @mock.patch("book_video_factory.credentials.platform.system", return_value="Windows")
    def test_windows_missing_credential_does_not_call_security(
        self, _system: mock.Mock, run: mock.Mock
    ) -> None:
        self.assertFalse(
            credentials.credential_available("MISSING_TOKEN", "test-service", environ={})
        )
        run.assert_not_called()

    @mock.patch("book_video_factory.credentials.subprocess.run")
    @mock.patch("book_video_factory.credentials.platform.system", return_value="Linux")
    def test_linux_missing_credential_does_not_call_security(
        self, _system: mock.Mock, run: mock.Mock
    ) -> None:
        self.assertFalse(
            credentials.credential_available("MISSING_TOKEN", "test-service", environ={})
        )
        run.assert_not_called()

    @mock.patch("book_video_factory.credentials.platform.system", return_value="Darwin")
    @mock.patch("book_video_factory.credentials.shutil.which", return_value=None)
    def test_macos_without_security_returns_missing(
        self, _which: mock.Mock, _system: mock.Mock
    ) -> None:
        self.assertFalse(
            credentials.credential_available("MISSING_TOKEN", "test-service", environ={})
        )

    @mock.patch("book_video_factory.credentials.platform.system", return_value="Darwin")
    @mock.patch(
        "book_video_factory.credentials.shutil.which", return_value="/usr/bin/security"
    )
    @mock.patch("book_video_factory.credentials.subprocess.run")
    def test_macos_security_preserves_keychain_probe_semantics(
        self, run: mock.Mock, _which: mock.Mock, _system: mock.Mock
    ) -> None:
        run.return_value = subprocess.CompletedProcess([], 0)
        self.assertTrue(
            credentials.credential_available("MISSING_TOKEN", "test-service", environ={})
        )
        run.assert_called_once_with(
            ["/usr/bin/security", "find-generic-password", "-s", "test-service"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    @mock.patch("book_video_factory.credentials.platform.system", return_value="Darwin")
    @mock.patch(
        "book_video_factory.credentials.shutil.which", return_value="/usr/bin/security"
    )
    @mock.patch("book_video_factory.credentials.subprocess.run")
    def test_macos_security_nonzero_means_missing(
        self, run: mock.Mock, _which: mock.Mock, _system: mock.Mock
    ) -> None:
        run.return_value = subprocess.CompletedProcess([], 44)
        self.assertFalse(
            credentials.credential_available("MISSING_TOKEN", "test-service", environ={})
        )

    @mock.patch("book_video_factory.credentials.subprocess.run")
    def test_environment_credential_wins_without_keychain_probe(
        self, run: mock.Mock
    ) -> None:
        self.assertTrue(
            credentials.credential_available(
                "TOKEN", "test-service", environ={"TOKEN": "secret-value"}
            )
        )
        run.assert_not_called()

    @mock.patch("book_video_factory.credentials.platform.system", return_value="Windows")
    def test_provider_loaders_fail_cleanly_on_windows(
        self, _system: mock.Mock
    ) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(WeReadError, "credential not found"):
                load_weread_api_key()
            with self.assertRaisesRegex(FreesoundError, "credential not found"):
                load_freesound_secret("FREESOUND_API_KEY", "test-service")


if __name__ == "__main__":
    unittest.main()
