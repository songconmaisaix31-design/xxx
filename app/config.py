from __future__ import annotations

import os


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024
    DEMO_MODE = os.environ.get("DEMO_MODE", "1") == "1"
    DATA_SOURCE_TIMEOUT_SECONDS = 4.0
