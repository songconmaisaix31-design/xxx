from __future__ import annotations

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from ..services.chat import (
    advance_demo_progress,
    block_counterpart,
    conversation_list,
    get_conversation,
    report_subject,
    send_message,
    use_tool,
)
from ..services.users import ValidationError, current_user, login_required

bp = Blueprint("chat", __name__)


@bp.get("/conversations")
@login_required
def index():
    user = current_user()
    return render_template("conversations.html", conversations=conversation_list(user["id"]))


@bp.get("/conversations/<conversation_id>")
@login_required
def detail(conversation_id: str):
    user = current_user()
    try:
        conversation = get_conversation(conversation_id, user["id"])
    except ValidationError as error:
        abort(404, str(error))
    return render_template("conversation.html", conversation=conversation, demo_mode=current_app.config["DEMO_MODE"])


@bp.post("/conversations/<conversation_id>/messages")
@login_required
def message(conversation_id: str):
    try:
        send_message(conversation_id, current_user()["id"], request.form.get("content", ""))
    except ValidationError as error:
        flash(str(error), "error")
    return redirect(url_for("chat.detail", conversation_id=conversation_id))


@bp.post("/conversations/<conversation_id>/tools/<tool>")
@login_required
def tool(conversation_id: str, tool: str):
    try:
        use_tool(conversation_id, current_user()["id"], tool)
    except ValidationError as error:
        flash(str(error), "error")
    return redirect(url_for("chat.detail", conversation_id=conversation_id))


@bp.post("/conversations/<conversation_id>/demo/advance")
@login_required
def demo_advance(conversation_id: str):
    if not current_app.config["DEMO_MODE"]:
        abort(404)
    try:
        level = advance_demo_progress(conversation_id, current_user()["id"])
    except ValidationError as error:
        flash(str(error), "error")
    else:
        flash(f"演示模式已推进至 L{level}。", "success")
    return redirect(url_for("chat.detail", conversation_id=conversation_id))


@bp.post("/conversations/<conversation_id>/report")
@login_required
def report(conversation_id: str):
    try:
        report_subject(current_user()["id"], "conversation", conversation_id, request.form.get("reason", ""))
    except ValidationError as error:
        flash(str(error), "error")
    else:
        flash("举报已记录，审核人员会跟进处理。", "success")
    return redirect(url_for("chat.detail", conversation_id=conversation_id))


@bp.post("/conversations/<conversation_id>/block")
@login_required
def block(conversation_id: str):
    try:
        block_counterpart(current_user()["id"], conversation_id)
    except ValidationError as error:
        flash(str(error), "error")
    else:
        flash("已拉黑对方；后续无法再建立新的一对一会话。", "success")
    return redirect(url_for("chat.index"))
