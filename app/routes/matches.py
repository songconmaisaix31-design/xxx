from __future__ import annotations

import secrets

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from ..services.chat import start_direct_conversation
from ..services.matching import ranked_matches
from ..services.users import ValidationError, current_user, get_user, login_required

bp = Blueprint("matches", __name__)
MATCH_FLOW_SESSION_KEY = "match_flow"
MATCH_FLOW_PHASES = {"searching", "result"}


def _flow_for(user_id: str) -> dict:
    raw = session.get(MATCH_FLOW_SESSION_KEY)
    if not isinstance(raw, dict) or raw.get("user_id") != user_id:
        return {"user_id": user_id, "phase": None, "attempt_id": None, "candidate_id": None, "seen_ids": []}
    seen_ids = raw.get("seen_ids")
    if not isinstance(seen_ids, list):
        seen_ids = []
    return {
        "user_id": user_id,
        "phase": raw.get("phase") if raw.get("phase") in MATCH_FLOW_PHASES else None,
        "attempt_id": raw.get("attempt_id") if isinstance(raw.get("attempt_id"), str) else None,
        "candidate_id": raw.get("candidate_id") if isinstance(raw.get("candidate_id"), str) else None,
        "seen_ids": list(dict.fromkeys(item for item in seen_ids[:20] if isinstance(item, str))),
    }


def _matches_attempt(flow: dict, phase: str) -> bool:
    supplied = request.form.get("attempt_id", "")
    expected = flow.get("attempt_id") or ""
    return flow.get("phase") == phase and bool(supplied) and secrets.compare_digest(supplied, expected)


def _find_match(viewer_id: str, candidate_id: str | None) -> dict | None:
    if not candidate_id:
        return None
    return next((item for item in ranked_matches(viewer_id) if item["candidate"]["id"] == candidate_id), None)


def _start_attempt(user_id: str, match: dict, seen_ids: list[str]) -> dict:
    candidate_id = match["candidate"]["id"]
    flow = {
        "user_id": user_id,
        "phase": "searching",
        "attempt_id": secrets.token_urlsafe(12),
        "candidate_id": candidate_id,
        "seen_ids": list(dict.fromkeys([*seen_ids, candidate_id])),
    }
    session[MATCH_FLOW_SESSION_KEY] = flow
    return flow


@bp.get("/matches")
@login_required
def index():
    user = current_user()
    matches = ranked_matches(user["id"])
    return render_template("matches.html", candidate_count=len(matches))


@bp.post("/matches/search/start")
@login_required
def search_start():
    user = current_user()
    matches = ranked_matches(user["id"])
    if not matches:
        flash("暂时没有符合硬性筛选条件的候选人。我们不会为了填满结果而放宽你的偏好。", "info")
        return redirect(url_for("matches.index"))

    flow = _flow_for(user["id"])
    if flow["phase"] == "searching" and _find_match(user["id"], flow["candidate_id"]):
        return redirect(url_for("matches.searching"))

    _start_attempt(user["id"], matches[0], [])
    return redirect(url_for("matches.searching"))


@bp.get("/matches/searching")
@login_required
def searching():
    user = current_user()
    flow = _flow_for(user["id"])
    if flow["phase"] != "searching" or _find_match(user["id"], flow["candidate_id"]) is None:
        session.pop(MATCH_FLOW_SESSION_KEY, None)
        flash("当前没有进行中的匹配，请重新开始。", "info")
        return redirect(url_for("matches.index"))
    return render_template("match_searching.html", attempt_id=flow["attempt_id"])


@bp.post("/matches/search/complete")
@login_required
def search_complete():
    user = current_user()
    flow = _flow_for(user["id"])
    match = _find_match(user["id"], flow["candidate_id"])
    if not _matches_attempt(flow, "searching") or match is None:
        flash("这次匹配已失效，请重新开始。", "info")
        return redirect(url_for("matches.index"))
    flow["phase"] = "result"
    session[MATCH_FLOW_SESSION_KEY] = flow
    return redirect(url_for("matches.detail", candidate_id=flow["candidate_id"]))


@bp.post("/matches/search/cancel")
@login_required
def search_cancel():
    user = current_user()
    flow = _flow_for(user["id"])
    if not _matches_attempt(flow, "searching"):
        flash("匹配状态已经更新，没有取消任何新任务。", "info")
        return redirect(url_for("matches.index"))
    session.pop(MATCH_FLOW_SESSION_KEY, None)
    flash("已取消本次匹配，没有建立任何会话。", "success")
    return redirect(url_for("matches.index"))


@bp.post("/matches/search/retry")
@login_required
def search_retry():
    user = current_user()
    flow = _flow_for(user["id"])
    if not _matches_attempt(flow, "result"):
        flash("当前结果已经更新，请重新开始匹配。", "info")
        return redirect(url_for("matches.index"))

    matches = ranked_matches(user["id"])
    current_id = flow["candidate_id"]
    seen_ids = flow["seen_ids"]
    selected = next((item for item in matches if item["candidate"]["id"] not in set(seen_ids)), None)
    if selected is None:
        selected = next((item for item in matches if item["candidate"]["id"] != current_id), None)
        seen_ids = [current_id] if selected else []
    if selected is None:
        flash("候选池里暂时没有其他人，稍后再来试试。", "info")
        return redirect(url_for("matches.detail", candidate_id=current_id))

    _start_attempt(user["id"], selected, seen_ids)
    return redirect(url_for("matches.searching"))


@bp.get("/matches/<candidate_id>")
@login_required
def detail(candidate_id: str):
    user = current_user()
    match = _find_match(user["id"], candidate_id)
    if match is None:
        abort(404)
    # Candidate profile is intentionally not supplied to this template.
    flow = _flow_for(user["id"])
    attempt_id = flow["attempt_id"] if flow["phase"] == "result" and flow["candidate_id"] == candidate_id else None
    return render_template("match_detail.html", match=match, attempt_id=attempt_id)


@bp.post("/matches/<candidate_id>/start")
@login_required
def start(candidate_id: str):
    user = current_user()
    try:
        conversation_id = start_direct_conversation(user["id"], candidate_id)
    except ValidationError as error:
        flash(str(error), "error")
        return redirect(url_for("matches.index"))
    session.pop(MATCH_FLOW_SESSION_KEY, None)
    return redirect(url_for("chat.detail", conversation_id=conversation_id))
