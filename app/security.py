from __future__ import annotations

import secrets

from flask import abort, current_app, request, session


CSRF_SESSION_KEY = "_csrf_token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def csrf_token() -> str:
    token = session.get(CSRF_SESSION_KEY)
    if not isinstance(token, str) or not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def init_app(app) -> None:
    @app.before_request
    def validate_csrf() -> None:
        if not current_app.config.get("CSRF_ENABLED", True) or request.method in SAFE_METHODS:
            return
        expected = session.get(CSRF_SESSION_KEY)
        supplied = request.form.get(CSRF_SESSION_KEY) or request.headers.get("X-CSRF-Token")
        if (
            not isinstance(expected, str)
            or not isinstance(supplied, str)
            or not secrets.compare_digest(expected, supplied)
        ):
            abort(400, description="CSRF token missing or invalid.")
