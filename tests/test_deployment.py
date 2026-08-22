from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DeploymentEntrypointTests(unittest.TestCase):
    def test_vercel_entrypoint_uses_writable_instance_and_secure_cookie(self) -> None:
        with tempfile.TemporaryDirectory() as instance_path:
            environment = os.environ.copy()
            environment.update(
                {
                    "APP_INSTANCE_PATH": instance_path,
                    "DEMO_MODE": "1",
                    "FLASK_SECRET_KEY": "deployment-test-secret-not-for-production",
                    "VERCEL": "1",
                }
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import index; "
                        "assert index.app.instance_path == " + repr(instance_path) + ", 'instance'; "
                        "assert index.app.config['SESSION_COOKIE_SECURE'] is True, 'cookie'; "
                        "assert index.app.config['EPHEMERAL_DEMO'] is True, 'ephemeral'; "
                        "assert '线上演示' in index.app.test_client().get('/').get_data(as_text=True), 'banner'"
                    ),
                ],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
