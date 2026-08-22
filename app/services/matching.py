from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from ..constants import MATCH_WEIGHT_GROUPS
from ..db import get_db
from .users import get_user, profile_tags


def validate_weight_groups() -> None:
    for group in MATCH_WEIGHT_GROUPS.values():
        total = sum(group["weights"].values(), Decimal("0"))
        if total != Decimal("1.00"):
            raise AssertionError(f"Match weight group {group['group_key']} must total 1.00, got {total}")


validate_weight_groups()


def _set_similarity(left: Iterable[str], right: Iterable[str]) -> float:
    left_set, right_set = set(left), set(right)
    union = left_set | right_set
    return len(left_set & right_set) / len(union) if union else 0.0


def _numeric_similarity(left: int | float | None, right: int | float | None, upper_bound: float) -> float:
    if left is None or right is None or upper_bound <= 0:
        return 0.0
    return max(0.0, 1.0 - abs(float(left) - float(right)) / upper_bound)


def _tier_similarity(left: str | None, right: str | None, levels: tuple[str, ...]) -> float:
    if left not in levels or right not in levels or len(levels) < 2:
        return 0.0
    return 1.0 - abs(levels.index(left) - levels.index(right)) / (len(levels) - 1)


def _time_similarity(left: Iterable[int], right: Iterable[int]) -> float:
    return _set_similarity(left, right)


def _tag_values(user_id: str) -> dict[str, dict]:
    values = {}
    for tag in profile_tags(user_id):
        values[tag["tag_id"]] = tag["value"]
    return values


def _list_value(tags: dict[str, dict], key: str) -> list[str]:
    return tags.get(key, {}).get("items", [])


def _hours(user: dict, tags: dict[str, dict]) -> list[int]:
    values = set(tags.get("learning_active_hours", {}).get("hours", []))
    values.update(tags.get("sport_active_hours", {}).get("hours", []))
    if not values:
        fallback = {"早鸟": [7, 8], "正常": [12, 19], "夜猫子": [21, 22]}
        values.update(fallback[user["schedule"]])
    return list(values)


def _mbti_similarity(left: str, right: str) -> float:
    if "不知道" in (left, right):
        return 0.0
    return sum(a == b for a, b in zip(left, right)) / 4


def _active_time_similarity(left: dict, left_tags: dict, right: dict, right_tags: dict) -> float:
    return _time_similarity(_hours(left, left_tags), _hours(right, right_tags))


def _number_value(tags: dict[str, dict], tag_id: str, key: str) -> int | float | None:
    value = tags.get(tag_id, {}).get(key)
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _behavior_similarity(left_tags: dict[str, dict], right_tags: dict[str, dict]) -> float:
    components: list[float] = []
    for tag_id in ("lang_learning", "sport_primary"):
        left, right = _list_value(left_tags, tag_id), _list_value(right_tags, tag_id)
        if left or right:
            components.append(_set_similarity(left, right))
    numeric_tags = (
        ("lang_streak", "days", 1000.0),
        ("sport_weekly", "times", 7.0),
        ("sport_total", "km", 1000.0),
    )
    for tag_id, key, upper_bound in numeric_tags:
        left = _number_value(left_tags, tag_id, key)
        right = _number_value(right_tags, tag_id, key)
        if left is not None or right is not None:
            components.append(_numeric_similarity(left, right, upper_bound))
    tier_tags = (
        ("learning_consistency", ("轻度", "稳定", "硬核")),
        ("sport_intensity", ("入门", "进阶", "资深")),
    )
    for tag_id, levels in tier_tags:
        left = left_tags.get(tag_id, {}).get("level")
        right = right_tags.get(tag_id, {}).get("level")
        if left is not None or right is not None:
            components.append(_tier_similarity(left, right, levels))
    return sum(components) / len(components) if components else 0.0


def _has_external_tags(user_id: str) -> bool:
    return bool(
        get_db().execute(
            "SELECT 1 FROM tags WHERE user_id = ? AND source IN ('duolingo', 'keep') LIMIT 1",
            (user_id,),
        ).fetchone()
    )


def is_hard_filter_match(viewer: dict, candidate: dict) -> bool:
    viewer_age = date.today().year - viewer["birth_year"]
    candidate_age = date.today().year - candidate["birth_year"]
    if not (18 <= viewer_age <= 100 and 18 <= candidate_age <= 100):
        return False
    if not viewer["match_age_min"] <= candidate_age <= viewer["match_age_max"]:
        return False
    if not candidate["match_age_min"] <= viewer_age <= candidate["match_age_max"]:
        return False
    viewer_accepts = viewer["match_gender"] == "any" or viewer["match_gender"] == candidate["gender"]
    candidate_accepts = candidate["match_gender"] == "any" or candidate["match_gender"] == viewer["gender"]
    return viewer_accepts and candidate_accepts


def calculate_match(viewer: dict, candidate: dict) -> dict:
    viewer_tags, candidate_tags = _tag_values(viewer["id"]), _tag_values(candidate["id"])
    behavior = _behavior_similarity(viewer_tags, candidate_tags)
    similarities = {
        "purpose": _set_similarity(viewer["purposes"], candidate["purposes"]),
        "behavior": behavior,
        "interests": _set_similarity(viewer["interests"], candidate["interests"]),
        "active_time": _active_time_similarity(viewer, viewer_tags, candidate, candidate_tags),
        "city": 1.0 if viewer["city"] == candidate["city"] else 0.0,
        "mbti": _mbti_similarity(viewer["mbti"], candidate["mbti"]),
    }
    group = MATCH_WEIGHT_GROUPS["default" if _has_external_tags(viewer["id"]) else "no_external_data"]
    raw = sum(float(weight) * similarities[key] for key, weight in group["weights"].items())
    raw = max(0.0, min(1.0, raw))
    return {
        "raw_score": raw,
        "display_score": round(60 + raw * 38),
        "common_point_count": max(1, round(sum(value > 0 for value in similarities.values()))),
    }


def ranked_matches(viewer_id: str) -> list[dict]:
    viewer = get_user(viewer_id)
    rows = get_db().execute(
        """SELECT candidate.id
           FROM users AS candidate
           WHERE candidate.id != ?
             AND candidate.is_demo = ?
             AND NOT EXISTS (
               SELECT 1 FROM blocks
               WHERE (blocker_id = ? AND blocked_id = candidate.id)
                  OR (blocker_id = candidate.id AND blocked_id = ?)
             )""",
        (viewer_id, int(bool(viewer["is_demo"])), viewer_id, viewer_id),
    ).fetchall()
    matches = []
    for row in rows:
        candidate = get_user(row["id"])
        if not is_hard_filter_match(viewer, candidate):
            continue
        score = calculate_match(viewer, candidate)
        matches.append({"candidate": candidate, **score})
    return sorted(matches, key=lambda item: item["raw_score"], reverse=True)


def event_match_score(user_id: str, required_tags: list[str]) -> dict:
    """Event matching reuses normalized tag identifiers and the presentation smoothing policy."""
    user = get_user(user_id)
    behavior_tags = _tag_values(user_id)
    known = set(user["interests"])
    interest_map = {
        "人工智能": "interest_ai",
        "创业": "identity_startup",
        "阅读": "interest_reading",
        "美食": "interest_food",
    }
    known.update(interest_map[item] for item in user["interests"] if item in interest_map)
    language_map = {"英语": "lang_learning_en", "日语": "lang_learning_ja"}
    sport_map = {"跑步": "sport_running", "瑜伽": "sport_yoga"}
    known.update(language_map.get(item) for item in _list_value(behavior_tags, "lang_learning"))
    known.update(sport_map.get(item) for item in _list_value(behavior_tags, "sport_primary"))
    known.discard(None)
    matches = known & set(required_tags)
    def weight(tag_id: str) -> float:
        if tag_id.startswith("identity_"):
            return 0.30
        if tag_id.startswith(("lang_", "sport_")):
            return 0.25
        return 0.20

    total_weight = sum(weight(tag_id) for tag_id in required_tags)
    raw = sum(weight(tag_id) for tag_id in matches) / total_weight if total_weight else 0.0
    return {"raw_score": raw, "display_score": round(60 + raw * 38), "common_tag_count": len(matches)}


def event_required_tags(event_row) -> list[str]:
    return json.loads(event_row["required_tags_json"])
