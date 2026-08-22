from __future__ import annotations

import hashlib
import json
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


MAX_RESPONSE_BYTES = 256 * 1024
REQUEST_TIMEOUT_SECONDS = 5
DUOLINGO_PROFILE_URL = "https://www.duolingo.com/2017-06-30/users"
IDENTIFIER_PATTERN = re.compile(r"[A-Za-z0-9._-]{2,64}")
LANGUAGE_NAMES = {
    "en": "英语",
    "english": "英语",
    "ja": "日语",
    "japanese": "日语",
    "ko": "韩语",
    "korean": "韩语",
    "es": "西班牙语",
    "spanish": "西班牙语",
    "fr": "法语",
    "french": "法语",
    "de": "德语",
    "german": "德语",
    "zh": "中文",
    "chinese": "中文",
}


class AdapterError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ExternalTag:
    tag_id: str
    category: str
    name: str
    value: dict
    source: str
    data_mode: str
    verified: bool


class DataSourceAdapter(ABC):
    """Normalize a single external or Fixture source behind one stable boundary."""

    source: str
    data_mode: str

    @abstractmethod
    def authorize(self, authorization_input: str) -> str:
        """Validate consent input and return an in-memory fetch context."""

    @abstractmethod
    def fetch_tags(self, fetch_context: str, user_id: str) -> list[ExternalTag]:
        """Return normalized tags without persisting raw source data."""


def _tag(
    tag_id: str,
    category: str,
    name: str,
    value: dict,
    source: str,
    data_mode: str,
) -> ExternalTag:
    return ExternalTag(
        tag_id=tag_id,
        category=category,
        name=name,
        value=value,
        source=source,
        data_mode=data_mode,
        verified=data_mode == "live",
    )


class FixtureDataSourceAdapter(DataSourceAdapter):
    data_mode = "fixture"

    def __init__(self, source: str):
        if source not in {"duolingo", "keep"}:
            raise ValueError(f"Unsupported Fixture source: {source}")
        self.source = source

    def authorize(self, authorization_input: str) -> str:
        if authorization_input != "demo-authorized":
            raise AdapterError("authorization_denied", "演示样例授权未完成，请重新确认。")
        return "fixture-consent"

    def fetch_tags(self, fetch_context: str, user_id: str) -> list[ExternalTag]:
        if fetch_context != "fixture-consent":
            raise AdapterError("invalid_context", "演示样例授权已失效，请重新连接。")
        seed = int(hashlib.sha256(f"{self.source}:{user_id}".encode()).hexdigest()[:4], 16)
        return self._duolingo_tags(seed) if self.source == "duolingo" else self._keep_tags(seed)

    def _duolingo_tags(self, seed: int) -> list[ExternalTag]:
        languages = [["英语", "日语"], ["英语", "韩语"], ["日语"]][seed % 3]
        streak = 90 + seed % 600
        active_hours = [20 + seed % 3, 22 + seed % 2]
        total_xp = streak * 52
        weekly_days = min(7, max(1, streak % 7 + 1))
        values = (
            ("lang_learning", "在学语种", {"items": languages}),
            ("lang_streak", "连续打卡天数", {"days": streak}),
            ("learning_consistency", "学习坚持度", {"level": "硬核" if streak > 250 else "稳定"}),
            ("learning_active_hours", "学习活跃时段", {"hours": active_hours}),
            ("learning_level", "当前等级", {"level": max(3, streak // 40)}),
            ("learning_total_xp", "累计经验值", {"xp": total_xp}),
            ("learning_course_count", "活跃课程数", {"count": len(languages)}),
            ("learning_weekly_days", "周学习天数", {"days": weekly_days}),
            ("learning_session_style", "学习节奏", {"level": "夜间专注" if max(active_hours) >= 21 else "日间专注"}),
            ("learning_language_count", "学习语种数", {"count": len(languages)}),
            ("learning_momentum", "近期学习势头", {"level": "持续" if streak >= 90 else "起步"}),
        )
        return [_tag(tag_id, "学习", name, value, self.source, self.data_mode) for tag_id, name, value in values]

    def _keep_tags(self, seed: int) -> list[ExternalTag]:
        sports = [["跑步", "瑜伽"], ["骑行", "力量训练"], ["跑步"]][seed % 3]
        weekly = 2 + seed % 5
        active_hours = [6 + seed % 2, 19 + seed % 3]
        values = (
            ("sport_primary", "主要运动类型", {"items": sports}),
            ("sport_weekly", "周运动频次", {"times": weekly}),
            ("sport_total", "累计运动量", {"km": weekly * 72}),
            ("sport_active_hours", "运动活跃时段", {"hours": active_hours}),
            ("sport_intensity", "运动强度等级", {"level": "进阶" if weekly >= 3 else "入门"}),
            ("sport_total_hours", "累计运动时长", {"hours": weekly * 18}),
            ("sport_consistency_weeks", "连续运动周数", {"weeks": 4 + weekly * 2}),
            ("sport_weekly_minutes", "周运动时长", {"minutes": weekly * 45}),
            ("sport_session_duration", "单次运动时长", {"minutes": 35 + weekly * 5}),
            ("sport_variety", "运动多样性", {"count": len(sports)}),
            ("sport_routine", "运动习惯", {"level": "规律" if weekly >= 3 else "轻量"}),
        )
        return [_tag(tag_id, "运动", name, value, self.source, self.data_mode) for tag_id, name, value in values]


def _non_negative_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    integer = int(value)
    return integer if integer == value and integer >= 0 else None


def _language_name(course: dict) -> str | None:
    for key in ("title", "learningLanguage"):
        value = course.get(key)
        if not isinstance(value, str):
            continue
        value = value.strip()
        if not 1 <= len(value) <= 64:
            continue
        return LANGUAGE_NAMES.get(value.casefold(), value)
    return None


class DuolingoPublicDataSourceAdapter(DataSourceAdapter):
    source = "duolingo"
    data_mode = "live"

    def __init__(self, opener: Callable = urlopen):
        self._opener = opener

    def authorize(self, authorization_input: str) -> str:
        identifier = authorization_input.strip()
        if not IDENTIFIER_PATTERN.fullmatch(identifier):
            raise AdapterError("invalid_identifier", "Duolingo 用户名格式无效。")
        return identifier

    def fetch_tags(self, fetch_context: str, user_id: str) -> list[ExternalTag]:
        del user_id
        identifier = self.authorize(fetch_context)
        url = f"{DUOLINGO_PROFILE_URL}?{urlencode({'username': identifier})}"
        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "RealTags-Hackathon/1.0"},
            method="GET",
        )
        try:
            with self._opener(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                status = getattr(response, "status", 200)
                if not 200 <= status < 300:
                    raise AdapterError("source_unavailable", "Duolingo 暂时不可用，请稍后重试。")
                length = response.headers.get("Content-Length")
                if length and length.isdigit() and int(length) > MAX_RESPONSE_BYTES:
                    raise AdapterError("response_too_large", "Duolingo 响应超过安全读取上限。")
                body = response.read(MAX_RESPONSE_BYTES + 1)
        except AdapterError:
            raise
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise AdapterError("source_unavailable", "Duolingo 暂时不可用，请稍后重试。") from error
        if len(body) > MAX_RESPONSE_BYTES:
            raise AdapterError("response_too_large", "Duolingo 响应超过安全读取上限。")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AdapterError("invalid_response", "Duolingo 返回了无法识别的数据。") from error
        if not isinstance(payload, dict) or not isinstance(payload.get("users"), list):
            raise AdapterError("invalid_response", "Duolingo 返回结构不符合预期。")
        if not payload["users"]:
            raise AdapterError("profile_not_found", "未找到该 Duolingo 公开用户。")
        profile = payload["users"][0]
        if not isinstance(profile, dict):
            raise AdapterError("invalid_response", "Duolingo 用户资料结构不符合预期。")
        tags = self._normalize(profile)
        if not tags:
            raise AdapterError("no_supported_tags", "该公开资料暂时没有可安全映射的学习标签。")
        return tags

    def _normalize(self, profile: dict) -> list[ExternalTag]:
        tags: list[ExternalTag] = []
        courses = profile.get("courses") if isinstance(profile.get("courses"), list) else []
        normalized_courses: list[tuple[str, int | None]] = []
        for course in courses:
            if not isinstance(course, dict):
                continue
            language = _language_name(course)
            if language:
                normalized_courses.append((language, _non_negative_int(course.get("xp"))))
        languages = list(dict.fromkeys(language for language, _ in normalized_courses))
        if languages:
            tags.append(_tag("lang_learning", "学习", "在学语种", {"items": languages}, self.source, self.data_mode))
            tags.append(_tag("learning_course_count", "学习", "活跃课程数", {"count": len(languages)}, self.source, self.data_mode))
        course_xp = [f"{language} · {xp} XP" for language, xp in normalized_courses if xp is not None]
        if course_xp:
            tags.append(_tag("learning_course_xp", "学习", "课程经验值", {"items": course_xp}, self.source, self.data_mode))
        streak = _non_negative_int(profile.get("streak"))
        if streak is not None:
            consistency = "硬核" if streak >= 365 else "稳定" if streak >= 30 else "轻度"
            tags.append(_tag("lang_streak", "学习", "连续打卡天数", {"days": streak}, self.source, self.data_mode))
            tags.append(_tag("learning_consistency", "学习", "学习坚持度", {"level": consistency}, self.source, self.data_mode))
        total_xp = _non_negative_int(profile.get("totalXp"))
        if total_xp is not None:
            tags.append(_tag("learning_total_xp", "学习", "累计经验值", {"xp": total_xp}, self.source, self.data_mode))
        return tags


ADAPTERS: dict[str, DataSourceAdapter] = {
    "duolingo_fixture": FixtureDataSourceAdapter("duolingo"),
    "keep_fixture": FixtureDataSourceAdapter("keep"),
    "duolingo_live": DuolingoPublicDataSourceAdapter(),
}


def _refresh_derived_tags(db, user_id: str, updated_at: str) -> None:
    """Rebuild transparent inferences from normalized source tags only."""
    rows = db.execute(
        """SELECT tag_id, value_json, source
           FROM tags
           WHERE user_id = ? AND source IN ('duolingo', 'keep')""",
        (user_id,),
    ).fetchall()
    db.execute("DELETE FROM tags WHERE user_id = ? AND source = 'derived'", (user_id,))
    if not rows:
        return

    values = {row["tag_id"]: json.loads(row["value_json"]) for row in rows}
    sources = {row["source"] for row in rows}
    streak = _non_negative_int(values.get("lang_streak", {}).get("days")) or 0
    weekly_sport = _non_negative_int(values.get("sport_weekly", {}).get("times")) or 0
    discipline_score = sum((streak >= 30, streak >= 150, weekly_sport >= 2, weekly_sport >= 4))
    discipline = "高" if discipline_score >= 3 else "中" if discipline_score >= 1 else "低"

    active_hours: set[int] = set()
    for tag_id in ("learning_active_hours", "sport_active_hours"):
        for hour in values.get(tag_id, {}).get("hours", []):
            if isinstance(hour, int) and 0 <= hour <= 23:
                active_hours.add(hour)

    user = db.execute("SELECT purposes_json FROM users WHERE id = ?", (user_id,)).fetchone()
    purposes = set(json.loads(user["purposes_json"])) if user else set()
    purpose_supported = ("学习搭子" in purposes and "duolingo" in sources) or (
        "运动搭子" in purposes and "keep" in sources
    )
    derived = [
        ("self_discipline", "自律程度", {"level": discipline}),
        ("purpose_consistency", "目标行为一致性", {"level": "一致" if purpose_supported else "待积累"}),
    ]
    if active_hours:
        derived.append(("active_time_overlap", "活跃时间画像", {"hours": sorted(active_hours)}))
    for tag_id, name, value in derived:
        db.execute(
            """INSERT INTO tags
               (user_id, tag_id, category, name, value_json, source, data_mode, verified, visibility, updated_at)
               VALUES (?, ?, '复合', ?, ?, 'derived', 'derived', 0, 'self_only', ?)""",
            (user_id, tag_id, name, json.dumps(value, ensure_ascii=False), updated_at),
        )


def connect_source(
    user_id: str,
    source: str,
    authorization_code: str = "",
    *,
    mode: str = "fixture",
    identifier: str = "",
) -> int:
    adapter = ADAPTERS.get(f"{source}_{mode}")
    if adapter is None:
        raise AdapterError("unsupported_source", "暂不支持此数据源或同步模式。")
    authorization_input = identifier if mode == "live" else authorization_code
    fetch_context = adapter.authorize(authorization_input)
    tags = adapter.fetch_tags(fetch_context, user_id)
    if not tags or any(tag.source != source or tag.data_mode != mode for tag in tags):
        raise AdapterError("invalid_response", "数据源返回了不符合契约的标签。")

    from ..db import get_db, utcnow

    db = get_db()
    updated_at = utcnow()
    try:
        db.execute("DELETE FROM tags WHERE user_id = ? AND source = ?", (user_id, source))
        db.execute(
            """INSERT INTO external_connections
               (user_id, source, status, access_token, data_mode, refreshed_at)
               VALUES (?, ?, 'connected', NULL, ?, ?)
               ON CONFLICT(user_id, source) DO UPDATE SET
                   status = excluded.status,
                   access_token = NULL,
                   data_mode = excluded.data_mode,
                   refreshed_at = excluded.refreshed_at""",
            (user_id, source, mode, updated_at),
        )
        for tag in tags:
            db.execute(
                """INSERT INTO tags
                   (user_id, tag_id, category, name, value_json, source, data_mode, verified, visibility, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'self_only', ?)""",
                (
                    user_id,
                    tag.tag_id,
                    tag.category,
                    tag.name,
                    json.dumps(tag.value, ensure_ascii=False),
                    tag.source,
                    tag.data_mode,
                    int(tag.verified),
                    updated_at,
                ),
            )
        _refresh_derived_tags(db, user_id, updated_at)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return len(tags)
