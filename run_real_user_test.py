from __future__ import annotations

import argparse
import secrets
from pathlib import Path

from flask import Flask

from app import create_app
from app.config import Config
from app.db import get_db


ROOT = Path(__file__).resolve().parent
DEFAULT_DATABASE = (ROOT / "instance" / "real-user-test.sqlite3").resolve()

CONTAMINATION_CHECKS = (
    ("demo users", "SELECT COUNT(*) AS count FROM users WHERE is_demo = 1 OR id LIKE 'demo_%'"),
    ("demo administrator", "SELECT COUNT(*) AS count FROM admins WHERE id = 'admin_demo'"),
    ("Fixture tags", "SELECT COUNT(*) AS count FROM tags WHERE data_mode = 'fixture'"),
    (
        "Fixture connections",
        "SELECT COUNT(*) AS count FROM external_connections WHERE data_mode = 'fixture'",
    ),
    ("Fixture merchant events", "SELECT COUNT(*) AS count FROM events WHERE host_type = 'merchant'"),
)


def _assert_real_user_only(app: Flask) -> None:
    """Refuse to run against a database contaminated by demo or Fixture rows."""
    with app.app_context():
        db = get_db()
        contamination = [
            label
            for label, query in CONTAMINATION_CHECKS
            if db.execute(query).fetchone()["count"]
        ]
    if contamination:
        joined = ", ".join(contamination)
        raise RuntimeError(
            f"Real-user test database contains prohibited data: {joined}. "
            "Select a fresh dedicated database instead of reusing a demo database."
        )


def create_real_user_test_app(database_path: str | Path = DEFAULT_DATABASE) -> Flask:
    """Create the loopback-only app profile backed by a dedicated real-user database."""
    database = Path(database_path).expanduser().resolve()
    config = type(
        "RealUserTestConfig",
        (Config,),
        {
            "DATABASE": str(database),
            "DEBUG": False,
            "DEMO_MODE": False,
            "SECRET_KEY": secrets.token_urlsafe(48),
            "SESSION_COOKIE_SECURE": False,
            "TESTING": False,
        },
    )
    app = create_app(config)
    _assert_real_user_only(app)
    return app


def _port(value: str) -> int:
    port = int(value)
    if not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1024 and 65535")
    return port


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the isolated RealTags real-user test environment.")
    parser.add_argument("--port", type=_port, default=5001, help="loopback port (default: 5001)")
    args = parser.parse_args()

    app = create_real_user_test_app()
    print("Real-user test mode: DEMO_MODE=0")
    print("Database: instance/real-user-test.sqlite3")
    print(f"Open: http://127.0.0.1:{args.port}")
    app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
