from __future__ import annotations

import os
import tempfile
from pathlib import Path

from app import create_app


def deployment_instance_path() -> str:
    """Use Vercel's writable scratch directory without changing local runs."""
    configured = os.environ.get("APP_INSTANCE_PATH")
    if configured:
        return configured
    if os.environ.get("VERCEL") == "1":
        return "/tmp/realtags"
    return str(Path(tempfile.gettempdir()) / "realtags-vercel")


app = create_app(instance_path=deployment_instance_path())
