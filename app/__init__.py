from __future__ import annotations

import secrets
from pathlib import Path

import click
from flask import Flask

from .config import Config
from .db import close_db, init_app as init_db
from .security import csrf_token, init_app as init_security


def create_app(config: type[Config] = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config)
    app.config.setdefault("DATABASE", str(Path(app.instance_path) / "realtags.sqlite3"))
    if not app.config.get("SECRET_KEY"):
        if not app.config.get("TESTING") and not app.config.get("DEMO_MODE"):
            raise RuntimeError("FLASK_SECRET_KEY is required when DEMO_MODE is disabled.")
        app.config["SECRET_KEY"] = secrets.token_hex(32)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)
    init_security(app)
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

        return {
            "current_user": current_user(),
            "demo_mode": app.config["DEMO_MODE"],
            "csrf_token": csrf_token,
        }

    @app.cli.command("process-events")
    def process_events_command() -> None:
        """Advance due events; schedule this command in production."""
        from .services.events import refresh_event_statuses

        changed = refresh_event_statuses()
        print(f"Processed events; {changed} status changes.")

    @app.cli.command("create-admin")
    @click.option("--email", prompt="管理员邮箱")
    @click.option("--display-name", prompt="管理员显示名")
    @click.option("--password", prompt="管理员密码", hide_input=True, confirmation_prompt=True)
    def create_admin_command(email: str, display_name: str, password: str) -> None:
        """Create a real administrator without enabling demo credentials."""
        from .services.moderation import create_admin
        from .services.users import ValidationError

        try:
            create_admin(email, password, display_name)
        except ValidationError as error:
            raise click.ClickException(str(error)) from error
        click.echo(f"Created administrator: {email.strip().lower()}")

    return app
