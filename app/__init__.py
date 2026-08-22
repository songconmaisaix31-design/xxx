from __future__ import annotations

from pathlib import Path

from flask import Flask

from .config import Config
from .db import close_db, init_app as init_db


def create_app(config: type[Config] = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config)
    app.config.setdefault("DATABASE", str(Path(app.instance_path) / "realtags.sqlite3"))

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)
    init_db(app)

    from .routes.auth import bp as auth_bp
    from .routes.admin import bp as admin_bp
    from .routes.chat import bp as chat_bp
    from .routes.events import bp as events_bp
    from .routes.main import bp as main_bp
    from .routes.matches import bp as matches_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(matches_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(events_bp)
    @app.context_processor
    def inject_template_globals() -> dict:
        from .services.users import current_user

        return {"current_user": current_user()}

    @app.cli.command("process-events")
    def process_events_command() -> None:
        """Advance due events; schedule this command in production."""
        from .services.events import refresh_event_statuses

        changed = refresh_event_statuses()
        print(f"Processed events; {changed} status changes.")

    return app
