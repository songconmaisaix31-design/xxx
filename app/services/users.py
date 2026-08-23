from __future__ import annotations

import base64
import json
import re
from datetime import date
from uuid import uuid4

from functools import wraps

from flask import abort, current_app, flash, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..constants import (
    CITIES,
    GENDERS,
    INTERESTS,
    MATCH_GENDERS,
    MBTIS,
    PHOTO_MATCH_PREFERENCES,
    PURPOSES,
    SCHEDULES,
    ZODIACS,
)
from ..db import get_db, is_integrity_error, utcnow


class ValidationError(ValueError):
    pass


MAX_AVATAR_BYTES = 400 * 1024
AVATAR_MIME_SIGNATURES = (
    ("image/jpeg", lambda value: value.startswith(b"\xff\xd8\xff")),
    ("image/png", lambda value: value.startswith(b"\x89PNG\r\n\x1a\n")),
    ("image/webp", lambda value: value.startswith(b"RIFF") and value[8:12] == b"WEBP"),
)


def _decode_user(row):
    if row is None:
        return None
    user = dict(row)
    user["purposes"] = json.loads(user.pop("purposes_json"))
    user["interests"] = json.loads(user.pop("interests_json"))
    user["has_avatar"] = bool(user.get("avatar_data_url"))
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


def _avatar_data_url(upload) -> tuple[str | None, str]:
    if upload is None or not getattr(upload, "filename", ""):
        return None, "not_submitted"
    payload = upload.stream.read(MAX_AVATAR_BYTES + 1)
    if not payload:
        raise ValidationError("头像文件不能为空。")
    if len(payload) > MAX_AVATAR_BYTES:
        raise ValidationError("头像需小于 400 KiB。")
    mime = next((name for name, matches in AVATAR_MIME_SIGNATURES if matches(payload)), None)
    if mime is None:
        raise ValidationError("头像仅支持 JPG、PNG 或 WebP。")
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime};base64,{encoded}", "mock_placeholder"


def create_user(form, avatar_upload=None) -> str:
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
    mbti = form.get("mbti") or "不知道"
    zodiac = form.get("zodiac") or "不知道"
    schedule = form.get("schedule") or "正常"
    photo_match_preference = form.get("photo_match_preference") or "photo_or_standby"
    if gender not in GENDERS or match_gender not in MATCH_GENDERS or city not in CITIES:
        raise ValidationError("请完整填写性别、匹配偏好和城市。")
    if mbti not in MBTIS or zodiac not in ZODIACS or schedule not in SCHEDULES:
        raise ValidationError("个性标签包含无效选项。")
    if photo_match_preference not in PHOTO_MATCH_PREFERENCES:
        raise ValidationError("照片匹配偏好无效。")
    avatar_data_url, avatar_face_check = _avatar_data_url(avatar_upload)
    if photo_match_preference == "photo_only" and avatar_data_url is None:
        raise ValidationError("上传头像后才能选择只匹配有头像用户。")
    purposes = _selected(form, "purposes", PURPOSES, required=True)
    interests = _selected(form, "interests", INTERESTS)
    user_id = f"user_{uuid4().hex[:12]}"
    try:
        get_db().execute(
            """INSERT INTO users (
                id, email, password_hash, anonymous_alias, birth_year, gender, match_gender, city,
                purposes_json, interests_json, mbti, zodiac, schedule, avatar_data_url,
                avatar_face_check, photo_match_preference, phone_verified, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (user_id, email, generate_password_hash(password), alias, birth_year, gender, match_gender, city,
             json.dumps(purposes, ensure_ascii=False), json.dumps(interests, ensure_ascii=False), mbti, zodiac,
             schedule, avatar_data_url, avatar_face_check, photo_match_preference, utcnow()),
        )
        get_db().commit()
    except Exception as error:
        if is_integrity_error(error) and "users.email" in str(error):
            raise ValidationError("该邮箱已注册。") from error
        raise
    return user_id


def profile_tags(user_id: str) -> list[dict]:
    columns = {row["name"] for row in get_db().execute("PRAGMA table_info(tags)").fetchall()}
    optional_columns = (
        "data_mode",
        "evidence_kind",
        "identity_assurance",
        "mapping_version",
    )
    selected_columns = [
        "tag_id",
        "category",
        "name",
        "value_json",
        "source",
        "verified",
        "visibility",
        "updated_at",
        *(column for column in optional_columns if column in columns),
    ]
    rows = get_db().execute(
        f"SELECT {', '.join(selected_columns)} FROM tags WHERE user_id = ? ORDER BY category, id",
        (user_id,),
    ).fetchall()
    tags = []
    for row in rows:
        tag = dict(row)
        tag["value"] = json.loads(tag.pop("value_json"))
        tag["verified"] = bool(tag["verified"])
        tag.setdefault("data_mode", "fixture")
        tag.setdefault("evidence_kind", "direct")
        tag.setdefault("identity_assurance", "synthetic_fixture")
        tag.setdefault("mapping_version", "legacy-fixture-v1")
        tag["observed_at"] = tag["updated_at"] if tag["data_mode"] == "public_live" else None
        tags.append(tag)
    return tags


def matching_tags(user_id: str) -> list[dict]:
    """Project eligible tags to the identity-free matching contract."""
    db = get_db()
    columns = {row["name"] for row in db.execute("PRAGMA table_info(tags)").fetchall()}
    has_data_mode = "data_mode" in columns
    selected = "tag_id, value_json, verified, visibility"
    if has_data_mode:
        selected += ", data_mode"
    rows = db.execute(
        f"SELECT {selected} FROM tags WHERE user_id = ? ORDER BY id",
        (user_id,),
    ).fetchall()
    projected: dict[str, dict] = {}
    for row in rows:
        mode = row["data_mode"] if has_data_mode else "fixture"
        if row["visibility"] != "self_only":
            continue
        if mode == "public_live":
            if not row["verified"]:
                continue
        elif mode == "fixture":
            if not current_app.config.get("DEMO_MODE", False):
                continue
            # Legacy Fixture rows predate data_mode and were incorrectly marked verified.
            if has_data_mode and row["verified"]:
                continue
        else:
            continue
        if not re.fullmatch(r"[a-z][a-z0-9_]*", row["tag_id"]):
            continue
        try:
            value = json.loads(row["value_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict):
            continue
        projected[row["tag_id"]] = {"tag_id": row["tag_id"], "value": value}
    return list(projected.values())


def source_connections(user_id: str) -> dict[str, dict]:
    rows = get_db().execute(
        "SELECT source, status, refreshed_at FROM external_connections WHERE user_id = ?", (user_id,)
    ).fetchall()
    return {row["source"]: dict(row) for row in rows}
