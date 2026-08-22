from __future__ import annotations

import json
import re
from datetime import date
from uuid import uuid4

from functools import wraps

from flask import abort, flash, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..constants import CITIES, GENDERS, INTERESTS, MATCH_GENDERS, MBTIS, PURPOSES, SCHEDULES, ZODIACS
from ..db import get_db, utcnow


class ValidationError(ValueError):
    pass


def _decode_user(row):
    if row is None:
        return None
    user = dict(row)
    user["purposes"] = json.loads(user.pop("purposes_json"))
    user["interests"] = json.loads(user.pop("interests_json"))
    return user


def get_user(user_id: str):
    return _decode_user(get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())


def current_user():
    user_id = session.get("user_id")
    return get_user(user_id) if user_id else None


def require_user():
    user = current_user()
    if user is None:
        abort(401)
    return user


def set_current_user(user_id: str) -> None:
    session.clear()
    session["user_id"] = user_id


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("请先登录后继续。", "error")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def authenticate(email: str, password: str):
    row = get_db().execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    if row is None or not check_password_hash(row["password_hash"], password):
        raise ValidationError("邮箱或密码错误。")
    return _decode_user(row)


def _selected(form, key: str, allowed: tuple[str, ...], *, required: bool = False) -> list[str]:
    values = form.getlist(key)
    if required and not values:
        raise ValidationError(f"请至少选择一项{key}。")
    if any(value not in allowed for value in values):
        raise ValidationError(f"{key} 包含无效选项。")
    return values


def create_user(form) -> str:
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")
    alias = form.get("anonymous_alias", "").strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValidationError("请输入有效邮箱。")
    if len(password) < 8:
        raise ValidationError("密码至少需要 8 位。")
    if not 2 <= len(alias) <= 20:
        raise ValidationError("匿名代号需为 2–20 个字符。")
    try:
        birth_year = int(form.get("birth_year", ""))
    except ValueError as error:
        raise ValidationError("请输入出生年份。") from error
    age = date.today().year - birth_year
    if not 18 <= age <= 100:
        raise ValidationError("目前仅支持 18 岁及以上用户注册。")

    gender = form.get("gender")
    match_gender = form.get("match_gender")
    city = form.get("city")
    mbti = form.get("mbti", "不知道")
    zodiac = form.get("zodiac", "不知道")
    schedule = form.get("schedule", "正常")
    if gender not in GENDERS or match_gender not in MATCH_GENDERS or city not in CITIES:
        raise ValidationError("请完整填写性别、匹配偏好和城市。")
    if mbti not in MBTIS or zodiac not in ZODIACS or schedule not in SCHEDULES:
        raise ValidationError("个性标签包含无效选项。")
    purposes = _selected(form, "purposes", PURPOSES, required=True)
    interests = _selected(form, "interests", INTERESTS)
    user_id = f"user_{uuid4().hex[:12]}"
    try:
        get_db().execute(
            """INSERT INTO users (
                id, email, password_hash, anonymous_alias, birth_year, gender, match_gender, city,
                purposes_json, interests_json, mbti, zodiac, schedule, phone_verified, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (user_id, email, generate_password_hash(password), alias, birth_year, gender, match_gender, city,
             json.dumps(purposes, ensure_ascii=False), json.dumps(interests, ensure_ascii=False), mbti, zodiac,
             schedule, utcnow()),
        )
        get_db().commit()
    except Exception as error:
        if "UNIQUE constraint failed: users.email" in str(error):
            raise ValidationError("该邮箱已注册。") from error
        raise
    return user_id


def profile_tags(user_id: str) -> list[dict]:
    rows = get_db().execute(
        "SELECT tag_id, category, name, value_json, source, verified, visibility, updated_at FROM tags WHERE user_id = ? ORDER BY category, id",
        (user_id,),
    ).fetchall()
    tags = []
    for row in rows:
        tag = dict(row)
        tag["value"] = json.loads(tag.pop("value_json"))
        tag["verified"] = bool(tag["verified"])
        tags.append(tag)
    return tags


def source_connections(user_id: str) -> dict[str, dict]:
    rows = get_db().execute(
        "SELECT source, status, refreshed_at FROM external_connections WHERE user_id = ?", (user_id,)
    ).fetchall()
    return {row["source"]: dict(row) for row in rows}
