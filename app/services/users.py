from __future__ import annotations

import json
import re
from datetime import date
from uuid import uuid4

from functools import wraps

from flask import abort, current_app, flash, redirect, session, url_for
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
    user = get_user(user_id) if user_id else None
    if user and user["is_demo"] and not current_app.config["DEMO_MODE"]:
        session.pop("user_id", None)
        return None
    return user


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
    if (
        row is None
        or (row["is_demo"] and not current_app.config["DEMO_MODE"])
        or not check_password_hash(row["password_hash"], password)
    ):
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
    try:
        match_age_min = int(form.get("match_age_min") or 18)
        match_age_max = int(form.get("match_age_max") or 100)
    except ValueError as error:
        raise ValidationError("匹配年龄范围必须是有效数字。") from error
    if not 18 <= match_age_min <= match_age_max <= 100:
        raise ValidationError("匹配年龄范围须满足 18 ≤ 最小年龄 ≤ 最大年龄 ≤ 100。")

    gender = form.get("gender")
    match_gender = form.get("match_gender")
    city = form.get("city")
    mbti = form.get("mbti") or "不知道"
    zodiac = form.get("zodiac") or "不知道"
    schedule = form.get("schedule") or "正常"
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
                id, email, password_hash, anonymous_alias, birth_year, gender, match_gender,
                match_age_min, match_age_max, city,
                purposes_json, interests_json, mbti, zodiac, schedule, phone_verified, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (user_id, email, generate_password_hash(password), alias, birth_year, gender, match_gender,
             match_age_min, match_age_max, city,
             json.dumps(purposes, ensure_ascii=False), json.dumps(interests, ensure_ascii=False), mbti, zodiac,
             schedule, utcnow()),
        )
        get_db().commit()
    except Exception as error:
        if "UNIQUE constraint failed: users.email" in str(error):
            raise ValidationError("该邮箱已注册。") from error
        raise
    return user_id


def _self_reported_tags(user: dict) -> list[dict]:
    age = date.today().year - user["birth_year"]
    age_range = "18–24" if age < 25 else "25–29" if age < 30 else "30–34" if age < 35 else "35+"
    values = (
        ("self_age", "基础", "年龄与偏好", {"age_range": age_range, "match_age_range": f"{user['match_age_min']}–{user['match_age_max']}"}),
        ("self_gender", "基础", "性别与匹配偏好", {"gender": user["gender"], "match_gender": user["match_gender"]}),
        ("self_city", "基础", "所在城市", {"value": user["city"]}),
        ("self_purposes", "基础", "交友目的", {"items": user["purposes"]}),
        ("self_interests", "基础", "兴趣爱好", {"items": user["interests"]}),
        ("self_mbti", "基础", "MBTI", {"value": user["mbti"]}),
        ("self_zodiac", "基础", "星座", {"value": user["zodiac"]}),
        ("self_schedule", "基础", "作息类型", {"value": user["schedule"]}),
    )
    return [
        {
            "tag_id": tag_id,
            "category": category,
            "name": name,
            "value": value,
            "source": "self_reported",
            "data_mode": "self_reported",
            "verified": False,
            "visibility": "self_only",
            "updated_at": user["created_at"],
        }
        for tag_id, category, name, value in values
    ]


def profile_tags(user_id: str) -> list[dict]:
    user = get_user(user_id)
    if user is None:
        return []
    rows = get_db().execute(
        """SELECT tag_id, category, name, value_json, source, data_mode, verified, visibility, updated_at
           FROM tags WHERE user_id = ? ORDER BY category, id""",
        (user_id,),
    ).fetchall()
    tags = _self_reported_tags(user)
    for row in rows:
        tag = dict(row)
        tag["value"] = json.loads(tag.pop("value_json"))
        tag["verified"] = bool(tag["verified"])
        tags.append(tag)
    return tags


def source_connections(user_id: str) -> dict[str, dict]:
    rows = get_db().execute(
        "SELECT source, status, data_mode, refreshed_at FROM external_connections WHERE user_id = ?", (user_id,)
    ).fetchall()
    return {row["source"]: dict(row) for row in rows}


def verify_phone_for_demo(user_id: str) -> None:
    if not current_app.config["DEMO_MODE"]:
        raise ValidationError("演示手机号验证仅在 DEMO_MODE 中可用。")
    result = get_db().execute("UPDATE users SET phone_verified = 1 WHERE id = ?", (user_id,))
    if not result.rowcount:
        raise ValidationError("用户不存在。")
    get_db().commit()
