from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime
from uuid import uuid4

from ..db import get_db, utcnow
from .matching import calculate_match, is_hard_filter_match
from .users import ValidationError, get_user, profile_tags


TASK_CARDS = {
    "学习": [
        "说出你最近最想学的一项新技能，并约定一个 10 分钟的开始动作。",
        "分享一次你坚持最久的学习习惯，以及它为什么没有中断。",
        "用三个词描述一个你想去深入了解的领域。",
        "给对方推荐一个你正在使用的学习工具。",
        "假如只能保留一门正在学习的知识，你会选什么？",
        "各自说一个最近纠正过的错误认知。",
    ],
    "运动": [
        "讲一次让你想继续运动下去的瞬间。",
        "设计一场 30 分钟、零器械的双人运动挑战。",
        "你最愿意和搭子一起完成哪项运动？",
        "说出你的运动前仪式感。",
        "分享一首最适合运动时听的歌。",
        "互相猜猜对方更偏晨练还是夜练，然后公布答案。",
    ],
    "生活": [
        "用一道食物形容最近的生活状态，并解释原因。",
        "分享一个你会反复去的小店或城市角落。",
        "如果明天完全不用工作，你会如何安排 24 小时？",
        "说说最近让你小小开心的一件事。",
        "各自列出一个想戒掉和一个想保留的小习惯。",
        "给对方出一道你觉得很有代表性的生活选择题。",
    ],
    "脑洞": [
        "如果可以瞬移到任何地方吃晚餐，你会选哪里？",
        "给彼此的匿名代号编一个超能力设定。",
        "如果你们要共同做一档播客，第一期主题是什么？",
        "只用三样东西，如何度过一个没有网络的周末？",
        "为你们的聊天取一个电影片名。",
        "假如一天有 30 小时，你会把多出的 6 小时花在哪里？",
    ],
    "价值观": [
        "你认为一段舒服的关系最重要的一条规则是什么？",
        "讲一件别人给过你、你一直记得的善意。",
        "你更在意被理解，还是被支持？为什么？",
        "如果只能带走一种成长能力，你会带走什么？",
        "你如何判断一件事值得长期投入？",
        "分享一个你希望未来的自己仍然保持的特质。",
    ],
}
DICE_TOPICS = {
    1: "最近一次让你觉得“今天值了”的小事是什么？",
    2: "你想和搭子一起养成什么习惯？",
    3: "如果周末只选一个活动，你会选什么？",
    4: "分享一部想二刷的电影或一本书。",
    5: "你最想把哪项技能点亮到专业级？",
    6: "说一个朋友经常误解你的地方。",
}


def _members(conversation_id: str) -> list[dict]:
    rows = get_db().execute(
        """SELECT cm.user_id, cm.group_alias, u.anonymous_alias, u.city, u.birth_year, u.interests_json, u.is_demo
           FROM conversation_members cm JOIN users u ON u.id = cm.user_id
           WHERE cm.conversation_id = ? ORDER BY cm.joined_at""", (conversation_id,)
    ).fetchall()
    members = []
    for row in rows:
        member = dict(row)
        member["interests"] = json.loads(member.pop("interests_json"))
        members.append(member)
    return members


def _conversation_row(conversation_id: str):
    return get_db().execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()


def _ensure_member(conversation_id: str, user_id: str):
    if not get_db().execute(
        "SELECT 1 FROM conversation_members WHERE conversation_id = ? AND user_id = ?", (conversation_id, user_id)
    ).fetchone():
        raise ValidationError("你不是此会话成员。")


def _is_direct_blocked(conversation_id: str) -> bool:
    row = _conversation_row(conversation_id)
    if not row or row["type"] != "direct":
        return False
    member_ids = [member["user_id"] for member in _members(conversation_id)]
    if len(member_ids) != 2:
        return False
    left_id, right_id = member_ids
    return bool(
        get_db().execute(
            """SELECT 1 FROM blocks
               WHERE (blocker_id = ? AND blocked_id = ?)
                  OR (blocker_id = ? AND blocked_id = ?)
               LIMIT 1""",
            (left_id, right_id, right_id, left_id),
        ).fetchone()
    )


def _is_cross_pool_direct(conversation_id: str) -> bool:
    row = _conversation_row(conversation_id)
    if not row or row["type"] != "direct":
        return False
    members = _members(conversation_id)
    return len(members) == 2 and bool(members[0]["is_demo"]) != bool(members[1]["is_demo"])


def _ensure_interactive(conversation_id: str, user_id: str):
    _ensure_member(conversation_id, user_id)
    conversation = _conversation_row(conversation_id)
    if conversation["archived_at"]:
        raise ValidationError("该会话已归档，不能继续互动。")
    if _is_cross_pool_direct(conversation_id):
        raise ValidationError("该历史会话已停用，不能继续互动。")
    if _is_direct_blocked(conversation_id):
        raise ValidationError("这段会话已停止联系，不能继续互动。")
    return conversation


def _insert_system(conversation_id: str, content: str, metadata: dict | None = None) -> None:
    get_db().execute(
        """INSERT INTO messages (conversation_id, sender_id, message_type, content, metadata_json, created_at)
           VALUES (?, NULL, 'system_card', ?, ?, ?)""",
        (conversation_id, content, json.dumps(metadata or {}, ensure_ascii=False), utcnow()),
    )


def start_direct_conversation(viewer_id: str, candidate_id: str) -> str:
    viewer, candidate = get_user(viewer_id), get_user(candidate_id)
    if (
        viewer_id == candidate_id
        or not viewer
        or not candidate
        or bool(viewer["is_demo"]) != bool(candidate["is_demo"])
        or not is_hard_filter_match(viewer, candidate)
    ):
        raise ValidationError("该匿名匹配已不可用。")
    if get_db().execute(
        "SELECT 1 FROM blocks WHERE (blocker_id = ? AND blocked_id = ?) OR (blocker_id = ? AND blocked_id = ?)",
        (viewer_id, candidate_id, candidate_id, viewer_id),
    ).fetchone():
        raise ValidationError("该会话不可建立。")
    existing = get_db().execute(
        """SELECT c.id FROM conversations c
           JOIN conversation_members a ON a.conversation_id = c.id AND a.user_id = ?
           JOIN conversation_members b ON b.conversation_id = c.id AND b.user_id = ?
           WHERE c.type = 'direct' LIMIT 1""", (viewer_id, candidate_id),
    ).fetchone()
    if existing:
        return existing["id"]

    pair_key = ":".join(sorted((viewer_id, candidate_id)))
    conversation_id = f"direct_{hashlib.sha256(pair_key.encode()).hexdigest()[:20]}"
    db = get_db()
    created = db.execute(
        "INSERT OR IGNORE INTO conversations (id, type, event_id, created_at) VALUES (?, 'direct', NULL, ?)",
        (conversation_id, utcnow()),
    ).rowcount
    for user_id in (viewer_id, candidate_id):
        db.execute(
            "INSERT OR IGNORE INTO conversation_members (conversation_id, user_id, group_alias, joined_at) VALUES (?, ?, NULL, ?)",
            (conversation_id, user_id, utcnow()),
        )
    if created:
        score = calculate_match(viewer, candidate)
        _insert_system(conversation_id, f"匿名会话已建立。你们的匹配度为 {score['display_score']}%，先从一个问题开始吧。", {"kind": "match_started"})
    db.commit()
    return conversation_id


def conversation_list(user_id: str) -> list[dict]:
    rows = get_db().execute(
        """SELECT c.* FROM conversations c JOIN conversation_members cm ON cm.conversation_id = c.id
           WHERE cm.user_id = ? ORDER BY c.created_at DESC""", (user_id,)
    ).fetchall()
    conversations = []
    for row in rows:
        conversation = dict(row)
        if conversation["type"] == "direct":
            other = next(member for member in _members(conversation["id"]) if member["user_id"] != user_id)
            conversation["display_name"] = other["anonymous_alias"]
            conversation["subtitle"] = "匿名一对一会话"
        else:
            event = get_db().execute("SELECT title FROM events WHERE id = ?", (conversation["event_id"],)).fetchone()
            conversation["display_name"] = event["title"] if event else "已归档饭局群聊"
            conversation["subtitle"] = "3–10 人临时群聊"
        last = get_db().execute(
            "SELECT content, created_at FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT 1", (conversation["id"],)
        ).fetchone()
        conversation["last_message"] = dict(last) if last else None
        conversations.append(conversation)
    return conversations


def _shared_points(left_id: str, right_id: str) -> list[str]:
    left, right = get_user(left_id), get_user(right_id)
    points = []
    common_purpose = set(left["purposes"]) & set(right["purposes"])
    common_interests = set(left["interests"]) & set(right["interests"])
    if common_purpose:
        points.append(f"你们都在寻找「{sorted(common_purpose)[0]}」")
    if common_interests:
        points.append(f"共同兴趣：{sorted(common_interests)[0]}")
    left_tags = {tag["tag_id"]: tag["value"] for tag in profile_tags(left_id)}
    right_tags = {tag["tag_id"]: tag["value"] for tag in profile_tags(right_id)}
    languages = set(left_tags.get("lang_learning", {}).get("items", [])) & set(right_tags.get("lang_learning", {}).get("items", []))
    sports = set(left_tags.get("sport_primary", {}).get("items", [])) & set(right_tags.get("sport_primary", {}).get("items", []))
    if languages:
        points.append(f"都在学：{sorted(languages)[0]}")
    if sports:
        points.append(f"共同运动：{sorted(sports)[0]}")
    if left["city"] == right["city"]:
        points.append("你们在同一座城市")
    return points or ["你们都愿意从匿名对话开始认识彼此"]


def relationship_progress(conversation_id: str) -> dict:
    conversation = _conversation_row(conversation_id)
    if not conversation or conversation["type"] != "direct":
        return {"level": 0, "label": "群聊", "next_requirement": "使用破冰工具，让全桌都能自然开口。", "unlocked_points": []}
    members = _members(conversation_id)
    member_ids = [member["user_id"] for member in members]
    activity = {member_id: set() for member_id in member_ids}
    message_counts = {member_id: 0 for member_id in member_ids}
    text_rows = get_db().execute(
        """SELECT sender_id, substr(created_at, 1, 10) AS active_day
           FROM messages WHERE conversation_id = ? AND message_type = 'text'""",
        (conversation_id,),
    ).fetchall()
    for row in text_rows:
        if row["sender_id"] in activity:
            activity[row["sender_id"]].add(row["active_day"])
            message_counts[row["sender_id"]] += 1
    text_count = sum(message_counts.values())
    both_spoke = all(message_counts[member_id] > 0 for member_id in member_ids)
    mutual_active_days = len(set.intersection(*(activity[member_id] for member_id in member_ids))) if members else 0
    tool_count = get_db().execute(
        "SELECT COUNT(*) AS count FROM messages WHERE conversation_id = ? AND message_type = 'system_card' AND json_extract(metadata_json, '$.kind') IN ('dice', 'task_card', 'match_point')",
        (conversation_id,),
    ).fetchone()["count"]
    heat = text_count + tool_count * 3
    natural_level = 0
    if both_spoke and mutual_active_days >= 1 and text_count >= 10:
        natural_level = 1
    if mutual_active_days >= 3:
        natural_level = 2
    if mutual_active_days >= 7:
        natural_level = 3
    unlocked = get_db().execute(
        "SELECT content FROM messages WHERE conversation_id = ? AND json_extract(metadata_json, '$.kind') = 'match_point' ORDER BY id",
        (conversation_id,),
    ).fetchall()
    target_points = _shared_points(members[0]["user_id"], members[1]["user_id"])
    offset = conversation["demo_progress_offset"]
    level = max(natural_level, offset)
    if len(unlocked) >= len(target_points):
        level = max(level, 4)
    labels = ("L0 完全匿名", "L1 初识", "L2 熟悉", "L3 熟络", "L4 走出产品")
    next_requirements = (
        "双方发言并累积 10 点互动热度，解锁第一个匹配点。",
        "共同活跃满 3 天，解锁更多兴趣线索。",
        "共同活跃满 7 天，解锁完整兴趣线索。",
        "解锁全部匹配点，开放联系方式交换。",
        "你们已完成全部解锁。",
    )
    return {
        "level": min(level, 4), "label": labels[min(level, 4)], "next_requirement": next_requirements[min(level, 4)],
        "heat": heat,
        "mutual_active_days": mutual_active_days,
        "unlocked_points": [row["content"] for row in unlocked],
        "total_point_count": len(target_points),
    }


def _visible_counterpart(viewer_id: str, conversation_id: str, progress: dict) -> dict:
    other = next(member for member in _members(conversation_id) if member["user_id"] != viewer_id)
    visible = {"anonymous_alias": other["anonymous_alias"], "level": progress["level"]}
    if progress["level"] >= 1:
        visible["city"] = other["city"]
        age = datetime.now().year - other["birth_year"]
        visible["age_range"] = "18–24" if age < 25 else "25–29" if age < 30 else "30–34" if age < 35 else "35+"
    if progress["level"] >= 2:
        visible["interest_category"] = other["interests"][0] if other["interests"] else "兴趣探索中"
        visible["avatar_mode"] = "blur"
    if progress["level"] >= 3:
        visible["interests"] = other["interests"]
        visible["avatar_mode"] = "clear_placeholder"
    if progress["level"] >= 4:
        visible["contact_exchange_available"] = True
    return visible


def get_conversation(conversation_id: str, viewer_id: str) -> dict:
    _ensure_member(conversation_id, viewer_id)
    row = _conversation_row(conversation_id)
    if row is None:
        raise ValidationError("会话不存在。")
    conversation = dict(row)
    conversation["is_archived"] = bool(conversation["archived_at"])
    conversation["is_disabled"] = _is_cross_pool_direct(conversation_id)
    conversation["is_blocked"] = _is_direct_blocked(conversation_id)
    messages = []
    for message in get_db().execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id", (conversation_id,)
    ).fetchall():
        item = dict(message)
        item["metadata"] = json.loads(item.pop("metadata_json"))
        messages.append(item)
    conversation["messages"] = messages
    if conversation["type"] == "direct":
        progress = relationship_progress(conversation_id)
        conversation["progress"] = progress
        conversation["counterpart"] = _visible_counterpart(viewer_id, conversation_id, progress)
        conversation["members"] = []
    else:
        event = get_db().execute("SELECT * FROM events WHERE id = ?", (conversation["event_id"],)).fetchone()
        conversation["event"] = ({
            "title": event["title"], "start_at": event["start_at"], "poi_name": event["poi_name"],
            "poi_address": event["poi_address"],
        } if event else None)
        # Group aliases plus 1–2 interests are the only member information exposed.
        conversation["members"] = [
            {"alias": member["group_alias"], "interest_tags": member["interests"][:2]}
            for member in _members(conversation_id)
        ]
        conversation["progress"] = relationship_progress(conversation_id)
    return conversation


def send_message(conversation_id: str, sender_id: str, content: str) -> None:
    _ensure_interactive(conversation_id, sender_id)
    content = content.strip()
    if not content or len(content) > 500:
        raise ValidationError("消息需为 1–500 个字符。")
    get_db().execute(
        "INSERT INTO messages (conversation_id, sender_id, message_type, content, metadata_json, created_at) VALUES (?, ?, 'text', ?, '{}', ?)",
        (conversation_id, sender_id, content, utcnow()),
    )
    get_db().commit()


def use_tool(conversation_id: str, user_id: str, tool: str) -> str:
    _ensure_interactive(conversation_id, user_id)
    if tool == "dice":
        point = random.randint(1, 6)
        content = f"摇骰子结果：{point} 点｜{DICE_TOPICS[point]}"
        metadata = {"kind": "dice", "point": point}
    elif tool == "task_card":
        category = random.choice(tuple(TASK_CARDS))
        content = f"任务卡 · {category}｜{random.choice(TASK_CARDS[category])}"
        metadata = {"kind": "task_card", "category": category}
    elif tool == "unlock":
        row = _conversation_row(conversation_id)
        if row["type"] == "event_group":
            content, metadata = "匹配点解锁任务：轮流说一个你愿意带到饭局的话题。", {"kind": "group_unlock_task"}
        else:
            members = _members(conversation_id)
            points = _shared_points(members[0]["user_id"], members[1]["user_id"])
            db = get_db()
            unlocked_count = db.execute(
                """SELECT COUNT(*) AS count FROM messages
                   WHERE conversation_id = ? AND json_extract(metadata_json, '$.kind') = 'match_point'""",
                (conversation_id,),
            ).fetchone()["count"]
            if unlocked_count >= len(points):
                raise ValidationError("全部匹配点已经解锁。")
            latest_task = db.execute(
                """SELECT id FROM messages
                   WHERE conversation_id = ? AND json_extract(metadata_json, '$.kind') = 'match_point_task'
                   ORDER BY id DESC LIMIT 1""",
                (conversation_id,),
            ).fetchone()
            latest_point = db.execute(
                """SELECT id FROM messages
                   WHERE conversation_id = ? AND json_extract(metadata_json, '$.kind') = 'match_point'
                   ORDER BY id DESC LIMIT 1""",
                (conversation_id,),
            ).fetchone()
            if not latest_task or (latest_point and latest_point["id"] > latest_task["id"]):
                prompt = random.choice(TASK_CARDS["价值观"] + TASK_CARDS["生活"])
                content = f"匹配点协作任务：{prompt} 双方回答后再点击解锁。"
                metadata = {"kind": "match_point_task", "index": unlocked_count}
            else:
                responders = db.execute(
                    """SELECT COUNT(DISTINCT sender_id) AS count FROM messages
                       WHERE conversation_id = ? AND message_type = 'text' AND id > ?""",
                    (conversation_id, latest_task["id"]),
                ).fetchone()["count"]
                if responders < 2:
                    raise ValidationError("匹配点任务需要双方都回答后才能解锁。")
                progress = relationship_progress(conversation_id)
                allowed_count = 0 if progress["level"] == 0 else 1 if progress["level"] == 1 else 2 if progress["level"] == 2 else len(points)
                if unlocked_count >= allowed_count:
                    raise ValidationError("继续积累共同活跃日后才能解锁下一个匹配点。")
                content = f"匹配点已解锁：{points[unlocked_count]}"
                metadata = {"kind": "match_point", "index": unlocked_count}
    else:
        raise ValidationError("未知的破冰工具。")
    _insert_system(conversation_id, content, metadata)
    get_db().commit()
    return content


def advance_demo_progress(conversation_id: str, user_id: str) -> int:
    row = _ensure_interactive(conversation_id, user_id)
    if row["type"] != "direct":
        raise ValidationError("只有一对一会话可推进关系阶段。")
    if row["demo_progress_offset"] >= 3:
        return 3
    next_level = row["demo_progress_offset"] + 1
    get_db().execute("UPDATE conversations SET demo_progress_offset = ? WHERE id = ?", (next_level, conversation_id))
    _insert_system(conversation_id, f"演示模式：关系阶段已推进至 L{next_level}。", {"kind": "demo_progress"})
    get_db().commit()
    return next_level


def demo_unlock_point(conversation_id: str, user_id: str) -> str:
    from flask import current_app

    if not current_app.config["DEMO_MODE"]:
        raise ValidationError("演示解锁只在 DEMO_MODE 中可用。")
    row = _ensure_interactive(conversation_id, user_id)
    if row["type"] != "direct":
        raise ValidationError("只有一对一会话可演示解锁匹配点。")
    progress = relationship_progress(conversation_id)
    if progress["level"] < 1:
        raise ValidationError("请先把演示关系推进到 L1。")
    members = _members(conversation_id)
    points = _shared_points(members[0]["user_id"], members[1]["user_id"])
    unlocked_count = len(progress["unlocked_points"])
    if unlocked_count >= len(points):
        raise ValidationError("全部匹配点已经解锁。")
    content = f"演示模式 · 匹配点已解锁：{points[unlocked_count]}"
    _insert_system(
        conversation_id,
        content,
        {"kind": "match_point", "index": unlocked_count, "demo": True},
    )
    get_db().commit()
    return content


def report_subject(reporter_id: str, subject_type: str, subject_id: str, reason: str) -> None:
    reason = reason.strip()
    if subject_type not in ("event", "conversation") or not 1 <= len(reason) <= 200:
        raise ValidationError("请填写 1–200 字的举报原因。")
    if subject_type == "conversation":
        _ensure_member(subject_id, reporter_id)
    elif not get_db().execute("SELECT 1 FROM events WHERE id = ?", (subject_id,)).fetchone():
        raise ValidationError("举报对象不存在。")
    get_db().execute(
        "INSERT INTO reports (id, reporter_id, subject_type, subject_id, reason, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (f"report_{uuid4().hex[:12]}", reporter_id, subject_type, subject_id, reason, utcnow()),
    )
    get_db().commit()


def block_counterpart(blocker_id: str, conversation_id: str) -> None:
    row = _conversation_row(conversation_id)
    if not row or row["type"] != "direct":
        raise ValidationError("只能拉黑一对一会话中的对方。")
    _ensure_member(conversation_id, blocker_id)
    other = next(member for member in _members(conversation_id) if member["user_id"] != blocker_id)
    get_db().execute(
        "INSERT OR IGNORE INTO blocks (blocker_id, blocked_id, created_at) VALUES (?, ?, ?)",
        (blocker_id, other["user_id"], utcnow()),
    )
    get_db().commit()
