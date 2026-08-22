from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..db import get_db, utcnow


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
    verified: bool = True


class DataSourceAdapter(ABC):
    """All real and mock sources obey this boundary; routes never call source APIs directly."""

    source: str

    @abstractmethod
    def authorize(self, authorization_code: str) -> str:
        """Return a source access token or raise AdapterError with a stable error code."""

    @abstractmethod
    def fetch_tags(self, access_token: str, user_id: str) -> list[ExternalTag]:
        """Return normalized tags with source and verification metadata."""


class MockDataSourceAdapter(DataSourceAdapter):
    def __init__(self, source: str):
        self.source = source

    def authorize(self, authorization_code: str) -> str:
        if authorization_code != "demo-authorized":
            raise AdapterError("authorization_denied", "模拟授权未完成，请重新确认授权。")
        return f"mock-{self.source}-{hashlib.sha256(authorization_code.encode()).hexdigest()[:12]}"

    def fetch_tags(self, access_token: str, user_id: str) -> list[ExternalTag]:
        if not access_token.startswith(f"mock-{self.source}-"):
            raise AdapterError("invalid_token", "授权已失效，请重新连接数据源。")
        seed = int(hashlib.sha256(f"{self.source}:{user_id}".encode()).hexdigest()[:4], 16)
        if self.source == "duolingo":
            languages = [["英语", "日语"], ["英语", "韩语"], ["日语"]][seed % 3]
            streak = 90 + seed % 600
            hours = [20 + seed % 3, 22 + seed % 2]
            return [
                ExternalTag("lang_learning", "学习", "在学语种", {"items": languages}, self.source),
                ExternalTag("lang_streak", "学习", "连续打卡天数", {"days": streak}, self.source),
                ExternalTag("learning_consistency", "学习", "学习坚持度", {"level": "硬核" if streak > 250 else "稳定"}, self.source),
                ExternalTag("learning_active_hours", "学习", "学习活跃时段", {"hours": hours}, self.source),
                ExternalTag("learning_level", "学习", "当前等级", {"level": max(3, streak // 40), "xp": streak * 52}, self.source),
            ]
        sports = [["跑步", "瑜伽"], ["骑行", "力量训练"], ["跑步"]][seed % 3]
        weekly = 2 + seed % 5
        hours = [6 + seed % 2, 19 + seed % 3]
        return [
            ExternalTag("sport_primary", "运动", "主要运动类型", {"items": sports}, self.source),
            ExternalTag("sport_weekly", "运动", "周运动频次", {"times": weekly}, self.source),
            ExternalTag("sport_total", "运动", "累计运动量", {"km": weekly * 72}, self.source),
            ExternalTag("sport_active_hours", "运动", "运动活跃时段", {"hours": hours}, self.source),
            ExternalTag("sport_intensity", "运动", "运动强度等级", {"level": "进阶" if weekly >= 3 else "入门"}, self.source),
        ]


ADAPTERS: dict[str, DataSourceAdapter] = {
    "duolingo": MockDataSourceAdapter("duolingo"),
    "keep": MockDataSourceAdapter("keep"),
}


def connect_source(user_id: str, source: str, authorization_code: str) -> int:
    adapter = ADAPTERS.get(source)
    if adapter is None:
        raise AdapterError("unsupported_source", "暂不支持此数据源。")
    token = adapter.authorize(authorization_code)
    tags = adapter.fetch_tags(token, user_id)
    db = get_db()
    db.execute("DELETE FROM tags WHERE user_id = ? AND source = ?", (user_id, source))
    db.execute(
        """INSERT INTO external_connections (user_id, source, status, access_token, refreshed_at)
           VALUES (?, ?, 'connected', ?, ?)
           ON CONFLICT(user_id, source) DO UPDATE SET status = excluded.status, access_token = excluded.access_token, refreshed_at = excluded.refreshed_at""",
        (user_id, source, token, utcnow()),
    )
    for tag in tags:
        db.execute(
            """INSERT INTO tags (user_id, tag_id, category, name, value_json, source, verified, visibility, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'self_only', ?)""",
            (user_id, tag.tag_id, tag.category, tag.name, __import__("json").dumps(tag.value, ensure_ascii=False),
             tag.source, int(tag.verified), utcnow()),
        )
    db.commit()
    return len(tags)
