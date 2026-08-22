from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from flask import current_app, g
from werkzeug.security import generate_password_hash


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    anonymous_alias TEXT NOT NULL,
    birth_year INTEGER NOT NULL,
    gender TEXT NOT NULL,
    match_gender TEXT NOT NULL,
    city TEXT NOT NULL,
    purposes_json TEXT NOT NULL,
    interests_json TEXT NOT NULL,
    mbti TEXT NOT NULL,
    zodiac TEXT NOT NULL,
    schedule TEXT NOT NULL,
    phone_verified INTEGER NOT NULL DEFAULT 0,
    is_demo INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS external_connections (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    access_token TEXT,
    refreshed_at TEXT,
    data_mode TEXT NOT NULL DEFAULT 'fixture',
    external_subject TEXT,
    identity_assurance TEXT NOT NULL DEFAULT 'synthetic_fixture',
    last_state TEXT NOT NULL DEFAULT 'ready',
    last_error_code TEXT,
    last_attempted_at TEXT,
    mapping_version TEXT NOT NULL DEFAULT 'legacy-fixture-v1',
    PRIMARY KEY (user_id, source)
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tag_id TEXT NOT NULL,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    value_json TEXT NOT NULL,
    source TEXT NOT NULL,
    verified INTEGER NOT NULL DEFAULT 0,
    visibility TEXT NOT NULL DEFAULT 'self_only',
    updated_at TEXT NOT NULL,
    data_mode TEXT NOT NULL DEFAULT 'fixture',
    evidence_kind TEXT NOT NULL DEFAULT 'direct',
    identity_assurance TEXT NOT NULL DEFAULT 'synthetic_fixture',
    mapping_version TEXT NOT NULL DEFAULT 'legacy-fixture-v1'
);
CREATE INDEX IF NOT EXISTS idx_tags_user ON tags(user_id);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    host_type TEXT NOT NULL CHECK(host_type IN ('user', 'merchant')),
    host_id TEXT NOT NULL,
    title TEXT NOT NULL,
    poi_id TEXT NOT NULL,
    poi_name TEXT NOT NULL,
    poi_address TEXT NOT NULL,
    start_at TEXT NOT NULL,
    signup_deadline TEXT NOT NULL,
    min_size INTEGER NOT NULL,
    max_size INTEGER NOT NULL,
    budget_level TEXT NOT NULL,
    pay_type TEXT NOT NULL,
    required_tags_json TEXT NOT NULL,
    gender_policy TEXT NOT NULL,
    signup_mode TEXT NOT NULL,
    status TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    merchant_benefit_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS event_members (
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    membership_status TEXT NOT NULL,
    match_score INTEGER NOT NULL,
    common_tag_count INTEGER NOT NULL,
    checked_in INTEGER NOT NULL DEFAULT 0,
    joined_at TEXT NOT NULL,
    PRIMARY KEY(event_id, user_id)
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK(type IN ('direct', 'event_group')),
    event_id TEXT REFERENCES events(id) ON DELETE SET NULL,
    demo_progress_offset INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    archived_at TEXT
);

CREATE TABLE IF NOT EXISTS conversation_members (
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_alias TEXT,
    joined_at TEXT NOT NULL,
    PRIMARY KEY(conversation_id, user_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    message_type TEXT NOT NULL CHECK(message_type IN ('text', 'system_card')),
    content TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id);

CREATE TABLE IF NOT EXISTS event_coupons (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    benefit_json TEXT NOT NULL,
    redeem_code TEXT NOT NULL,
    status TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    redeemed_at TEXT
);

CREATE TABLE IF NOT EXISTS admins (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    reporter_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    handled_by TEXT REFERENCES admins(id) ON DELETE SET NULL,
    handling_note TEXT,
    handled_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS event_reviews (
    event_id TEXT PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK(status IN ('pending_review', 'approved', 'rejected')),
    submitted_at TEXT NOT NULL,
    reviewed_by TEXT REFERENCES admins(id) ON DELETE SET NULL,
    rejection_reason TEXT,
    reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id TEXT NOT NULL REFERENCES admins(id) ON DELETE RESTRICT,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_admin_audit_target
    ON admin_audit_logs(target_type, target_id, id);

CREATE TABLE IF NOT EXISTS blocks (
    blocker_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY(blocker_id, blocked_id)
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_: object | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(SCHEMA)
    _migrate_schema(db)
    db.commit()
    if current_app.config.get("DEMO_MODE", False):
        _seed_admin(db)
        db.commit()
        _seed_database(db)


def _migrate_schema(db: sqlite3.Connection) -> None:
    """Apply additive account and moderation migrations to existing databases."""
    user_columns = {row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()}
    if "is_demo" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0")
    db.execute(
        "UPDATE users SET is_demo = 1 WHERE id IN ('demo_001', 'demo_002', 'demo_003', 'demo_004')"
    )

    report_columns = {row["name"] for row in db.execute("PRAGMA table_info(reports)").fetchall()}
    additions = {
        "status": "TEXT NOT NULL DEFAULT 'pending'",
        "handled_by": "TEXT REFERENCES admins(id) ON DELETE SET NULL",
        "handling_note": "TEXT",
        "handled_at": "TEXT",
    }
    for name, definition in additions.items():
        if name not in report_columns:
            db.execute(f"ALTER TABLE reports ADD COLUMN {name} {definition}")
    db.execute("CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status, created_at)")

    connection_columns = {
        row["name"]: row for row in db.execute("PRAGMA table_info(external_connections)").fetchall()
    }
    connection_additions = {
        "data_mode": "TEXT NOT NULL DEFAULT 'fixture'",
        "external_subject": "TEXT",
        "identity_assurance": "TEXT NOT NULL DEFAULT 'synthetic_fixture'",
        "last_state": "TEXT NOT NULL DEFAULT 'ready'",
        "last_error_code": "TEXT",
        "last_attempted_at": "TEXT",
        "mapping_version": "TEXT NOT NULL DEFAULT 'legacy-fixture-v1'",
    }
    for name, definition in connection_additions.items():
        if name not in connection_columns:
            db.execute(f"ALTER TABLE external_connections ADD COLUMN {name} {definition}")
    connection_columns = {
        row["name"]: row for row in db.execute("PRAGMA table_info(external_connections)").fetchall()
    }
    if connection_columns["refreshed_at"]["notnull"]:
        _make_connection_refresh_nullable(db)
    # Public-source P0 never uses stored credentials, including legacy mock values.
    db.execute("UPDATE external_connections SET access_token = NULL WHERE access_token IS NOT NULL")

    tag_columns = {row["name"] for row in db.execute("PRAGMA table_info(tags)").fetchall()}
    tag_additions = {
        "data_mode": "TEXT NOT NULL DEFAULT 'fixture'",
        "evidence_kind": "TEXT NOT NULL DEFAULT 'direct'",
        "identity_assurance": "TEXT NOT NULL DEFAULT 'synthetic_fixture'",
        "mapping_version": "TEXT NOT NULL DEFAULT 'legacy-fixture-v1'",
    }
    for name, definition in tag_additions.items():
        if name not in tag_columns:
            db.execute(f"ALTER TABLE tags ADD COLUMN {name} {definition}")
    db.execute(
        """UPDATE tags
           SET data_mode = 'fixture', verified = 0,
               identity_assurance = 'synthetic_fixture', visibility = 'self_only',
               evidence_kind = CASE WHEN source = 'derived' THEN 'derived' ELSE 'direct' END
           WHERE mapping_version = 'legacy-fixture-v1'"""
    )


def _make_connection_refresh_nullable(db: sqlite3.Connection) -> None:
    """Rebuild the legacy table so a first failed attempt has no fake success time."""
    db.execute("DROP TABLE IF EXISTS external_connections_v2")
    db.execute(
        """CREATE TABLE external_connections_v2 (
               user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
               source TEXT NOT NULL,
               status TEXT NOT NULL,
               access_token TEXT,
               refreshed_at TEXT,
               data_mode TEXT NOT NULL DEFAULT 'fixture',
               external_subject TEXT,
               identity_assurance TEXT NOT NULL DEFAULT 'synthetic_fixture',
               last_state TEXT NOT NULL DEFAULT 'ready',
               last_error_code TEXT,
               last_attempted_at TEXT,
               mapping_version TEXT NOT NULL DEFAULT 'legacy-fixture-v1',
               PRIMARY KEY (user_id, source)
           )"""
    )
    db.execute(
        """INSERT INTO external_connections_v2 (
               user_id, source, status, access_token, refreshed_at, data_mode,
               external_subject, identity_assurance, last_state, last_error_code,
               last_attempted_at, mapping_version
           )
           SELECT user_id, source, status, access_token, refreshed_at, data_mode,
                  external_subject, identity_assurance, last_state, last_error_code,
                  last_attempted_at, mapping_version
           FROM external_connections"""
    )
    db.execute("DROP TABLE external_connections")
    db.execute("ALTER TABLE external_connections_v2 RENAME TO external_connections")


def _seed_admin(db: sqlite3.Connection) -> None:
    if db.execute("SELECT 1 FROM admins WHERE email = ?", ("admin@realtags.local",)).fetchone():
        return
    db.execute(
        """INSERT INTO admins (id, email, password_hash, display_name, is_active, created_at)
           VALUES ('admin_demo', ?, ?, '演示审核员', 1, ?)""",
        ("admin@realtags.local", generate_password_hash("admin-password"), utcnow()),
    )


def init_app(app) -> None:
    @app.before_request
    def refresh_due_events() -> None:
        # Request-time processing keeps the demo deterministic. Production must also
        # schedule `flask process-events` so deadlines are honored without traffic.
        from .services.events import refresh_event_statuses

        refresh_event_statuses()

    with app.app_context():
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)
        init_db()


def _insert_user(db: sqlite3.Connection, user: dict) -> None:
    db.execute(
        """INSERT INTO users (
            id, email, password_hash, anonymous_alias, birth_year, gender, match_gender,
            city, purposes_json, interests_json, mbti, zodiac, schedule, phone_verified, is_demo, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
        (
            user["id"], user["email"], generate_password_hash("demo-password"), user["alias"],
            user["birth_year"], user["gender"], user["match_gender"], user["city"],
            json.dumps(user["purposes"], ensure_ascii=False), json.dumps(user["interests"], ensure_ascii=False),
            user["mbti"], user["zodiac"], user["schedule"], 1, utcnow(),
        ),
    )


def _insert_tag(
    db: sqlite3.Connection,
    user_id: str,
    tag_id: str,
    category: str,
    name: str,
    value: object,
    source: str,
    *,
    evidence_kind: str = "direct",
    mapping_version: str = "legacy-fixture-v1",
) -> None:
    db.execute(
        """INSERT INTO tags (
               user_id, tag_id, category, name, value_json, source, verified,
               visibility, updated_at, data_mode, evidence_kind,
               identity_assurance, mapping_version
           ) VALUES (?, ?, ?, ?, ?, ?, 0, 'self_only', ?, 'fixture', ?,
                     'synthetic_fixture', ?)""",
        (
            user_id,
            tag_id,
            category,
            name,
            json.dumps(value, ensure_ascii=False, separators=(",", ":")),
            source,
            utcnow(),
            evidence_kind,
            mapping_version,
        ),
    )


def _seed_behavior_tags(db: sqlite3.Connection, user_id: str, languages: list[str], sports: list[str],
                        learning_hours: list[int], sport_hours: list[int], streak: int, weekly_times: int) -> None:
    """Seed a 12-tag source-labelled behavior profile; all tags remain self_only."""
    _insert_tag(db, user_id, "lang_learning", "学习", "在学语种", {"items": languages}, "duolingo")
    _insert_tag(db, user_id, "lang_streak", "学习", "连续打卡天数", {"days": streak}, "duolingo")
    _insert_tag(db, user_id, "learning_consistency", "学习", "学习坚持度", {"level": "硬核" if streak >= 200 else "稳定"}, "duolingo", evidence_kind="derived")
    _insert_tag(db, user_id, "learning_active_hours", "学习", "学习活跃时段", {"hours": learning_hours}, "duolingo", evidence_kind="derived")
    _insert_tag(db, user_id, "learning_level", "学习", "当前等级", {"level": max(3, streak // 40), "xp": streak * 52}, "duolingo", evidence_kind="derived")
    _insert_tag(db, user_id, "sport_primary", "运动", "主要运动类型", {"items": sports}, "keep")
    _insert_tag(db, user_id, "sport_weekly", "运动", "周运动频次", {"times": weekly_times}, "keep")
    _insert_tag(db, user_id, "sport_total", "运动", "累计运动量", {"km": weekly_times * 72}, "keep")
    _insert_tag(db, user_id, "sport_active_hours", "运动", "运动活跃时段", {"hours": sport_hours}, "keep")
    _insert_tag(db, user_id, "sport_intensity", "运动", "运动强度等级", {"level": "进阶" if weekly_times >= 3 else "入门"}, "keep")
    _insert_tag(db, user_id, "self_discipline", "复合", "自律程度", {"level": "高" if streak >= 150 else "中"}, "derived", evidence_kind="derived")
    _insert_tag(db, user_id, "active_time_overlap", "复合", "活跃时间画像", {"hours": sorted(set(learning_hours) | set(sport_hours))}, "derived", evidence_kind="derived")


def _seed_offline_fixture(db: sqlite3.Connection, user_id: str) -> None:
    from .services.data_sources.fixtures import OFFLINE_FIXTURE_VERSION, offline_fixture_tags

    tags = offline_fixture_tags(user_id)
    for tag in tags:
        _insert_tag(
            db,
            user_id,
            tag.tag_id,
            tag.category,
            tag.name,
            tag.value,
            tag.source,
            evidence_kind=tag.evidence_kind,
            mapping_version=tag.mapping_version,
        )

    loaded_at = utcnow()
    for source in sorted({tag.source for tag in tags}):
        db.execute(
            """INSERT INTO external_connections (
                   user_id, source, status, access_token, refreshed_at, data_mode,
                   external_subject, identity_assurance, last_state, last_error_code,
                   last_attempted_at, mapping_version
               ) VALUES (?, ?, 'connected', NULL, ?, 'fixture', NULL,
                         'synthetic_fixture', 'ready', NULL, ?, ?)""",
            (user_id, source, loaded_at, loaded_at, OFFLINE_FIXTURE_VERSION),
        )


def _upgrade_legacy_demo_fixture(db: sqlite3.Connection) -> None:
    from .services.data_sources.fixtures import OFFLINE_FIXTURE_VERSION

    snapshot_count = db.execute(
        "SELECT COUNT(*) AS count FROM tags WHERE user_id = 'demo_001' AND mapping_version = ?",
        (OFFLINE_FIXTURE_VERSION,),
    ).fetchone()["count"]
    live_count = db.execute(
        "SELECT COUNT(*) AS count FROM tags WHERE user_id = 'demo_001' AND data_mode = 'public_live'"
    ).fetchone()["count"]
    if snapshot_count >= 21 or live_count:
        return
    db.execute("DELETE FROM tags WHERE user_id = 'demo_001'")
    db.execute("DELETE FROM external_connections WHERE user_id = 'demo_001'")
    _seed_offline_fixture(db, "demo_001")


def _seed_database(db: sqlite3.Connection) -> None:
    if db.execute("SELECT 1 FROM users WHERE id = 'demo_001'").fetchone():
        # Keep the checked-in demo state repairable across schema/code updates.
        _upgrade_legacy_demo_fixture(db)
        if db.execute("SELECT 1 FROM events WHERE id = 'event_002'").fetchone():
            _ensure_seed_group_conversation(db, "event_002")
        db.commit()
        return

    users = (
        {"id": "demo_001", "email": "demo@realtags.local", "alias": "晨光旅人", "birth_year": 1998,
         "gender": "female", "match_gender": "any", "city": "上海", "purposes": ["学习搭子", "饭搭子"],
         "interests": ["人工智能", "阅读", "美食", "旅行"], "mbti": "INFP", "zodiac": "天秤", "schedule": "夜猫子"},
        {"id": "demo_002", "email": "sora@realtags.local", "alias": "夜航星", "birth_year": 1997,
         "gender": "male", "match_gender": "female", "city": "上海", "purposes": ["学习搭子", "兴趣同好"],
         "interests": ["人工智能", "阅读", "摄影", "美食"], "mbti": "INFJ", "zodiac": "水瓶", "schedule": "夜猫子"},
        {"id": "demo_003", "email": "run@realtags.local", "alias": "风中跑者", "birth_year": 1995,
         "gender": "male", "match_gender": "any", "city": "上海", "purposes": ["运动搭子", "饭搭子"],
         "interests": ["健身", "旅行", "美食"], "mbti": "ENTP", "zodiac": "双子", "schedule": "早鸟"},
        {"id": "demo_004", "email": "book@realtags.local", "alias": "纸页海", "birth_year": 1999,
         "gender": "female", "match_gender": "any", "city": "杭州", "purposes": ["聊天倾诉", "兴趣同好"],
         "interests": ["阅读", "影视", "二次元", "音乐"], "mbti": "INFP", "zodiac": "天秤", "schedule": "正常"},
    )
    for user in users:
        _insert_user(db, user)

    _seed_offline_fixture(db, "demo_001")
    _seed_behavior_tags(db, "demo_002", ["英语", "日语"], ["跑步", "力量训练"], [21, 22], [20, 21], 186, 4)
    _seed_behavior_tags(db, "demo_003", ["英语"], ["跑步", "骑行"], [7, 8], [6, 7], 83, 5)
    _seed_behavior_tags(db, "demo_004", ["韩语", "英语"], ["瑜伽"], [20, 21], [18, 19], 122, 2)
    start = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=5)
    _insert_seed_event(
        db, "event_001", "merchant", "merchant_001", "AI 从业者交流晚餐", "poi_001", start,
        3, 6, ["interest_ai", "lang_learning_en"], "first_come", "recruiting",
        {"type": "discount", "label": "到店全单 8 折", "value": "0.8"}, "和一桌对 AI 感兴趣的人聊聊正在做的事。",
    )
    _insert_seed_event(
        db, "event_002", "merchant", "merchant_002", "周末跑步后的早午餐", "poi_003", start + timedelta(days=2),
        3, 8, ["sport_running", "interest_food"], "review", "formed",
        {"type": "free_snack", "label": "到店赠送手作小食", "value": "1"}, "8 公里轻松跑后，认识同频运动伙伴。",
    )
    _insert_seed_event(
        db, "event_003", "user", "demo_004", "读书与独立电影分享局", "poi_002", start + timedelta(days=3),
        3, 5, ["interest_reading"], "review", "recruiting", None, "带一本最近最喜欢的书来。",
    )
    for event_id, user_id, role, score, common in (
        ("event_002", "demo_003", "host", 100, 2), ("event_002", "demo_001", "member", 84, 2),
        ("event_002", "demo_002", "member", 76, 1),
    ):
        db.execute(
            "INSERT INTO event_members (event_id, user_id, role, membership_status, match_score, common_tag_count, checked_in, joined_at) VALUES (?, ?, ?, 'approved', ?, ?, 0, ?)",
            (event_id, user_id, role, score, common, utcnow()),
        )
    _ensure_seed_group_conversation(db, "event_002")
    db.commit()


def _insert_seed_event(db: sqlite3.Connection, event_id: str, host_type: str, host_id: str, title: str,
                       poi_id: str, start: datetime, min_size: int, max_size: int, tags: list[str],
                       signup_mode: str, status: str, benefit: dict | None, description: str) -> None:
    poi = {"poi_001": ("知味里·静安店", "上海市静安区愚园路 88 号"),
           "poi_002": ("源野咖啡·徐汇店", "上海市徐汇区衡山路 214 号"),
           "poi_003": ("山海小馆·浦东店", "上海市浦东新区张杨路 501 号")}[poi_id]
    db.execute(
        """INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '50-100', 'AA', ?, 'balanced', ?, ?, ?, ?, ?)""",
        (event_id, host_type, host_id, title, poi_id, poi[0], poi[1], start.isoformat(),
         (start - timedelta(hours=2)).isoformat(), min_size, max_size, json.dumps(tags), signup_mode,
         status, description, json.dumps(benefit, ensure_ascii=False) if benefit else None, utcnow()),
    )


def _ensure_seed_group_conversation(db: sqlite3.Connection, event_id: str) -> None:
    conversation_id = f"group_{event_id}"
    existing = db.execute("SELECT id FROM conversations WHERE event_id = ? AND type = 'event_group'", (event_id,)).fetchone()
    if existing:
        conversation_id = existing["id"]
    else:
        db.execute(
            "INSERT INTO conversations (id, type, event_id, created_at) VALUES (?, 'event_group', ?, ?)",
            (conversation_id, event_id, utcnow()),
        )
    aliases = ("银杏", "星云", "海盐")
    members = db.execute("SELECT user_id FROM event_members WHERE event_id = ?", (event_id,)).fetchall()
    if not existing:
        for index, member in enumerate(members):
            db.execute(
                "INSERT INTO conversation_members (conversation_id, user_id, group_alias, joined_at) VALUES (?, ?, ?, ?)",
                (conversation_id, member["user_id"], aliases[index], utcnow()),
            )
        db.execute(
            """INSERT INTO messages (conversation_id, sender_id, message_type, content, metadata_json, created_at)
               VALUES (?, NULL, 'system_card', '饭局已成团：群内仍使用匿名代号。到店前请查看活动信息与权益。', '{}', ?)""",
            (conversation_id, utcnow()),
        )
    benefit_row = db.execute("SELECT merchant_benefit_json FROM events WHERE id = ?", (event_id,)).fetchone()
    benefit = json.loads(benefit_row["merchant_benefit_json"]) if benefit_row and benefit_row["merchant_benefit_json"] else None
    if benefit:
        for member in members:
            issued = db.execute(
                "SELECT 1 FROM event_coupons WHERE event_id = ? AND user_id = ?", (event_id, member["user_id"])
            ).fetchone()
            if not issued:
                db.execute(
                    """INSERT INTO event_coupons (id, event_id, user_id, benefit_json, redeem_code, status, issued_at)
                       VALUES (?, ?, ?, ?, ?, 'issued', ?)""",
                    (f"coupon_{uuid4().hex[:12]}", event_id, member["user_id"], json.dumps(benefit, ensure_ascii=False),
                     f"{event_id[-4:].upper()}-{member['user_id'][-4:].upper()}", utcnow()),
                )
