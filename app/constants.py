from __future__ import annotations

from decimal import Decimal

GENDERS = ("male", "female", "undisclosed")
MATCH_GENDERS = ("male", "female", "any")
CITIES = ("北京", "上海", "广州", "深圳", "杭州", "成都", "海外")
PURPOSES = ("学习搭子", "运动搭子", "聊天倾诉", "兴趣同好", "饭搭子", "随便聊聊")
INTERESTS = ("音乐", "影视", "游戏", "健身", "旅行", "摄影", "美食", "二次元", "阅读", "宠物", "人工智能", "创业")
MBTIS = ("不知道", "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP")
ZODIACS = ("不知道", "白羊", "金牛", "双子", "巨蟹", "狮子", "处女", "天秤", "天蝎", "射手", "摩羯", "水瓶", "双鱼")
SCHEDULES = ("早鸟", "正常", "夜猫子")
POIS = {
    "poi_001": {"name": "知味里·静安店", "address": "上海市静安区愚园路 88 号"},
    "poi_002": {"name": "源野咖啡·徐汇店", "address": "上海市徐汇区衡山路 214 号"},
    "poi_003": {"name": "山海小馆·浦东店", "address": "上海市浦东新区张杨路 501 号"},
}
EVENT_TAGS = {
    "interest_ai": "对人工智能感兴趣",
    "identity_startup": "创业中",
    "lang_learning_en": "正在学英语",
    "lang_learning_ja": "正在学日语",
    "sport_running": "跑步爱好者",
    "sport_yoga": "瑜伽爱好者",
    "interest_reading": "爱阅读",
    "interest_food": "美食探索者",
}

# This is server-only configuration. Do not expose it in templates or forms.
MATCH_WEIGHT_GROUPS = {
    "default": {
        "group_key": "default",
        "weights": {
            "purpose": Decimal("0.30"),
            "behavior": Decimal("0.25"),
            "interests": Decimal("0.20"),
            "active_time": Decimal("0.15"),
            "city": Decimal("0.05"),
            "mbti": Decimal("0.05"),
        },
    },
    "no_external_data": {
        "group_key": "no_external_data",
        "weights": {
            "purpose": Decimal("0.45"),
            "interests": Decimal("0.30"),
            "active_time": Decimal("0.15"),
            "city": Decimal("0.05"),
            "mbti": Decimal("0.05"),
        },
    },
}
