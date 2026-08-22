from __future__ import annotations

from flask import Blueprint, render_template

from ..services.users import current_user, profile_tags, source_connections

bp = Blueprint("main", __name__)


@bp.get("/")
def home():
    user = current_user()
    stats = None
    if user:
        connections = source_connections(user["id"])
        stats = {
            "tag_count": len(profile_tags(user["id"])),
            "connection_count": sum(item["status"] == "connected" for item in connections.values()),
        }
    return render_template("home.html", user=user, stats=stats)
