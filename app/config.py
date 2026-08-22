from __future__ import annotations

import os


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024
    DEMO_MODE = os.environ.get("DEMO_MODE", "1") == "1"
    CSRF_ENABLED = True
