from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..constants import CITIES, GENDERS, INTERESTS, MATCH_GENDERS, MBTIS, PURPOSES, SCHEDULES, ZODIACS
from ..services.adapters import AdapterError, connect_source
from ..services.users import (
    ValidationError,
    authenticate,
    create_user,
    current_user,
    login_required,
    profile_tags,
    set_current_user,
    source_connections,
)

bp = Blueprint("auth", __name__)


@bp.route("/register", methods=("GET", "POST"))
def register():
    if current_user():
        return redirect(url_for("auth.profile"))
    if request.method == "POST":
        try:
            user_id = create_user(request.form)
        except ValidationError as error:
            flash(str(error), "error")
        else:
            set_current_user(user_id)
            flash("注册成功。下一步可连接真实行为数据（当前为 mock 授权）。", "success")
            return redirect(url_for("auth.connections"))
    return render_template(
        "register.html", cities=CITIES, genders=GENDERS, match_genders=MATCH_GENDERS,
        purposes=PURPOSES, interests=INTERESTS, mbtis=MBTIS, zodiacs=ZODIACS, schedules=SCHEDULES,
    )


@bp.route("/login", methods=("GET", "POST"))
def login():
    if current_user():
        return redirect(url_for("auth.profile"))
    if request.method == "POST":
        try:
            user = authenticate(request.form.get("email", ""), request.form.get("password", ""))
        except ValidationError as error:
            flash(str(error), "error")
        else:
            set_current_user(user["id"])
            return redirect(url_for("auth.profile"))
    return render_template("login.html")


@bp.post("/demo/login")
def demo_login():
    set_current_user("demo_001")
    flash("已进入预置演示账号。", "success")
    return redirect(url_for("auth.profile"))


@bp.post("/logout")
def logout():
    from flask import session

    session.clear()
    flash("已退出登录。", "success")
    return redirect(url_for("main.home"))


@bp.get("/profile")
@login_required
def profile():
    user = current_user()
    return render_template("profile.html", user=user, tags=profile_tags(user["id"]), connections=source_connections(user["id"]))


@bp.get("/profile/connections")
@login_required
def connections():
    user = current_user()
    return render_template("connections.html", user=user, connections=source_connections(user["id"]))


@bp.post("/profile/connections/<source>/authorize")
@login_required
def authorize_source(source: str):
    user = current_user()
    try:
        count = connect_source(user["id"], source, request.form.get("authorization_code", ""))
    except AdapterError as error:
        flash(f"{error.code}：{error}", "error")
    else:
        flash(f"{source} 已连接，刷新了 {count} 个带来源标识的真实标签。", "success")
    return redirect(url_for("auth.connections"))
