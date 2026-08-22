from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..services.moderation import (
    admin_login_required,
    authenticate_admin,
    clear_current_admin,
    current_admin,
    get_event_for_review,
    get_report_for_review,
    list_pending_events,
    list_reports,
    recent_audit_logs,
    review_event,
    review_report,
    set_current_admin,
)
from ..services.users import ValidationError


bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if current_admin():
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        try:
            admin = authenticate_admin(request.form.get("email", ""), request.form.get("password", ""))
            set_current_admin(admin["id"])
        except ValidationError as error:
            flash(str(error), "error")
            return redirect(url_for("admin.login"))
        flash("管理员登录成功。", "success")
        return redirect(url_for("admin.dashboard"))
    return render_template("admin_login.html")


@bp.post("/logout")
@admin_login_required
def logout():
    clear_current_admin()
    flash("已退出管理员后台。", "success")
    return redirect(url_for("admin.login"))


@bp.get("")
@bp.get("/")
@admin_login_required
def dashboard():
    return render_template(
        "admin_dashboard.html",
        admin=current_admin(),
        pending_events=list_pending_events(),
        pending_reports=list_reports(),
        audit_logs=recent_audit_logs(),
    )


@bp.get("/events/<event_id>")
@admin_login_required
def event_review(event_id: str):
    event = get_event_for_review(event_id)
    if event is None:
        abort(404)
    return render_template("admin_event_review.html", admin=current_admin(), event=event)


@bp.post("/events/<event_id>/review")
@admin_login_required
def event_decision(event_id: str):
    decision = request.form.get("decision", "")
    try:
        status = review_event(
            event_id,
            current_admin()["id"],
            decision,
            request.form.get("rejection_reason", ""),
        )
    except ValidationError as error:
        flash(str(error), "error")
    else:
        flash("活动已通过审核。" if status == "recruiting" else "活动已拒绝。", "success")
    return redirect(url_for("admin.event_review", event_id=event_id))


@bp.get("/reports/<report_id>")
@admin_login_required
def report_review(report_id: str):
    report = get_report_for_review(report_id)
    if report is None:
        abort(404)
    return render_template("admin_report_review.html", admin=current_admin(), report=report)


@bp.post("/reports/<report_id>/review")
@admin_login_required
def report_decision(report_id: str):
    decision = request.form.get("decision", "")
    try:
        status = review_report(
            report_id,
            current_admin()["id"],
            decision,
            request.form.get("note", ""),
        )
    except ValidationError as error:
        flash(str(error), "error")
    else:
        flash("举报已标记为已处理。" if status == "resolved" else "举报已驳回。", "success")
    return redirect(url_for("admin.report_review", report_id=report_id))
