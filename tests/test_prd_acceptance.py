from __future__ import annotations

import json
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from werkzeug.datastructures import MultiDict

from app import create_app
from app.config import Config
from app.db import get_db
from app.services.chat import relationship_progress, send_message, start_direct_conversation, use_tool
from app.services.events import create_user_event, redeem_coupon, refresh_event_statuses, signup_for_event, viewer_coupon
from app.services.matching import _numeric_similarity, _tier_similarity, _time_similarity, is_hard_filter_match
from app.services.users import ValidationError, get_user, profile_tags


class PrdAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        config = type(
            "PrdAcceptanceConfig",
            (Config,),
            {
                "TESTING": True,
                "DATABASE": str(Path(self.temp_dir.name) / "test.sqlite3"),
                "SECRET_KEY": "test",
                "DEMO_MODE": True,
                "CSRF_ENABLED": False,
            },
        )
        self.app = create_app(config)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @staticmethod
    def _event_form() -> MultiDict:
        start = (datetime.now(timezone.utc) + timedelta(days=4)).replace(minute=0, second=0, microsecond=0)
        return MultiDict(
            {
                "title": "PRD 安全边界测试饭局",
                "description": "仅用于自动化验收。",
                "poi_id": "poi_001",
                "start_at": start.isoformat(),
                "min_size": "3",
                "max_size": "6",
                "budget_level": "50-100",
                "pay_type": "AA",
                "gender_policy": "any",
                "signup_mode": "first_come",
                "required_tags": "interest_ai",
            }
        )

    def test_production_requires_an_explicit_secret(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = type(
                "MissingSecretConfig",
                (Config,),
                {
                    "TESTING": False,
                    "DATABASE": str(Path(directory) / "production.sqlite3"),
                    "SECRET_KEY": None,
                    "DEMO_MODE": False,
                },
            )
            with self.assertRaises(RuntimeError):
                create_app(config)

    def test_csrf_rejects_missing_token_and_accepts_session_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = type(
                "CsrfConfig",
                (Config,),
                {
                    "TESTING": True,
                    "DATABASE": str(Path(directory) / "csrf.sqlite3"),
                    "SECRET_KEY": "csrf-test",
                    "DEMO_MODE": True,
                    "CSRF_ENABLED": True,
                },
            )
            client = create_app(config).test_client()
            self.assertEqual(client.post("/demo/login").status_code, 400)
            with client.session_transaction() as flask_session:
                flask_session["_csrf_token"] = "known-token"
            self.assertEqual(
                client.post("/demo/login", data={"_csrf_token": "known-token"}).status_code,
                302,
            )

    def test_every_post_form_renders_a_csrf_field(self) -> None:
        template_root = Path(self.app.root_path) / "templates"
        pattern = re.compile(r"<form\b(?=[^>]*\bmethod=[\"']post[\"'])[^>]*>.*?</form>", re.I | re.S)
        checked = 0
        for template in template_root.glob("*.html"):
            for form in pattern.findall(template.read_text(encoding="utf-8")):
                checked += 1
                self.assertIn('name="_csrf_token"', form, template.name)
        self.assertGreaterEqual(checked, 20)

    def test_prd_visual_tokens_and_hard_shadow_rules_are_canonical(self) -> None:
        css_root = Path(self.app.root_path) / "static" / "css"
        foundation = (css_root / "brutalist-foundation.css").read_text(encoding="utf-8")
        for declaration in (
            "--bg: #FFFCF0;",
            "--surface: #FFFFFF;",
            "--surface2: #FFE95C;",
            "--text: #17150F;",
            "--dim: #6B675A;",
            "--primary: #5B4DFF;",
            "--accent: #58CC02;",
            "--hot: #FF5A36;",
            "--border: 2.5px solid #17150F;",
            "--shadow: 6px 7px 0 #17150F;",
            "--card-shadow: 4px 5px 0 #17150F;",
        ):
            self.assertIn(declaration, foundation)
        all_css = "\n".join(path.read_text(encoding="utf-8") for path in css_root.glob("*.css"))
        self.assertNotRegex(all_css, r"backdrop-filter:\s*blur")
        self.assertNotRegex(all_css, r"box-shadow:[^;]*rgba")
        self.assertNotRegex(all_css, r"box-shadow:[^;]*var\(--neo-(?:purple|yellow|green|coral)\)")
        self.assertIn("@media (prefers-reduced-motion: reduce)", all_css)
        self.assertRegex(all_css, r"min-(?:height|width):\s*44px")
        contract = (css_root / "prd-contract.css").read_text(encoding="utf-8")
        self.assertIn("font-size: 23px !important;", contract)
        self.assertIn("font-size: 68px;", contract)
        self.assertIn("background-image: none;", contract)
        self.assertIn("grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);", contract)
        self.assertIn(
            "grid-template-columns: minmax(0, 0.65fr) minmax(0, 1.35fr) minmax(0, 0.65fr);",
            contract,
        )
        self.assertRegex(contract, r"body \.privacy-boundary \{\s*background-color: var\(--surface\);")
        self.assertRegex(contract, r"body \.large-points span \{\s*background-color: var\(--surface2\);")
        self.assertRegex(
            contract,
            r"body\.nearby-events-page \.nearby-panel \{\s*background-color: var\(--surface\);",
        )
        base = (Path(self.app.root_path) / "templates" / "base.html").read_text(encoding="utf-8")
        self.assertGreater(base.index("prd-contract.css"), base.index("nearby-events.css"))

    def test_profile_has_eight_self_tags_and_twenty_fixture_behavior_tags(self) -> None:
        with self.app.app_context():
            tags = profile_tags("demo_001")
        self_tags = [tag for tag in tags if tag["source"] == "self_reported"]
        fixture_tags = [tag for tag in tags if tag["data_mode"] == "fixture"]
        self.assertEqual(len(self_tags), 8)
        self.assertGreaterEqual(len(fixture_tags), 20)
        self.assertTrue(all(not tag["verified"] for tag in fixture_tags))
        self.assertTrue(all(tag["visibility"] == "self_only" for tag in tags))

    def test_age_preferences_are_a_bidirectional_hard_filter(self) -> None:
        with self.app.app_context():
            viewer = get_user("demo_001")
            candidate = get_user("demo_002")
        viewer.update({"match_age_min": 18, "match_age_max": 25})
        candidate.update({"match_age_min": 18, "match_age_max": 100})
        self.assertFalse(is_hard_filter_match(viewer, candidate))

    def test_similarity_functions_cover_numeric_tier_and_time_values(self) -> None:
        self.assertAlmostEqual(_numeric_similarity(4, 5, 7), 6 / 7)
        self.assertEqual(_numeric_similarity(0, 1000, 100), 0)
        self.assertEqual(_tier_similarity("稳定", "硬核", ("轻度", "稳定", "硬核")), 0.5)
        self.assertAlmostEqual(_time_similarity([22, 23], [23, 0]), 1 / 3)

    def test_unverified_user_cannot_create_an_event(self) -> None:
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE users SET phone_verified = 0 WHERE id = 'demo_001'")
            db.commit()
            with self.assertRaisesRegex(ValidationError, "手机号验证"):
                create_user_event("demo_001", self._event_form())

    def test_same_gender_event_rejects_a_different_gender(self) -> None:
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE events SET gender_policy = 'same_gender', status = 'recruiting' WHERE id = 'event_003'")
            db.commit()
            with self.assertRaisesRegex(ValidationError, "同性别"):
                signup_for_event("event_003", "demo_003")

    def test_coupon_cannot_be_redeemed_before_the_event_window(self) -> None:
        with self.app.app_context():
            coupon = viewer_coupon("event_002", "demo_001")
            self.assertIsNotNone(coupon)
            with self.assertRaisesRegex(ValidationError, "时间窗口"):
                redeem_coupon("event_002", "demo_001", coupon["redeem_code"])

    def test_formed_event_uses_one_redeem_code_for_the_whole_table(self) -> None:
        with self.app.app_context():
            codes = get_db().execute(
                "SELECT DISTINCT redeem_code FROM event_coupons WHERE event_id = 'event_002'"
            ).fetchall()
        self.assertEqual(len(codes), 1)

    def test_ended_event_group_is_archived_after_seven_days(self) -> None:
        now = datetime.now(timezone.utc)
        with self.app.app_context():
            db = get_db()
            db.execute(
                "UPDATE events SET status = 'ended', start_at = ? WHERE id = 'event_002'",
                ((now - timedelta(days=8)).isoformat(),),
            )
            db.commit()
            refresh_event_statuses(now)
            archived_at = db.execute(
                "SELECT archived_at FROM conversations WHERE event_id = 'event_002'"
            ).fetchone()["archived_at"]
        self.assertIsNotNone(archived_at)

    def test_relation_days_count_only_days_when_both_people_spoke(self) -> None:
        with self.app.app_context():
            conversation_id = start_direct_conversation("demo_001", "demo_002")
            db = get_db()
            now = datetime.now(timezone.utc).replace(microsecond=0)
            for day in range(3):
                timestamp = (now - timedelta(days=day)).isoformat()
                for index in range(5):
                    db.execute(
                        """INSERT INTO messages
                           (conversation_id, sender_id, message_type, content, metadata_json, created_at)
                           VALUES (?, 'demo_001', 'text', ?, '{}', ?)""",
                        (conversation_id, f"A-{day}-{index}", timestamp),
                    )
            for index in range(5):
                db.execute(
                    """INSERT INTO messages
                       (conversation_id, sender_id, message_type, content, metadata_json, created_at)
                       VALUES (?, 'demo_002', 'text', ?, '{}', ?)""",
                    (conversation_id, f"B-{index}", now.isoformat()),
                )
            db.commit()
            progress = relationship_progress(conversation_id)
        self.assertEqual(progress["mutual_active_days"], 1)
        self.assertEqual(progress["level"], 1)

    def test_unlock_creates_a_collaboration_task_before_revealing_a_point(self) -> None:
        with self.app.app_context():
            conversation_id = start_direct_conversation("demo_001", "demo_002")
            result = use_tool(conversation_id, "demo_001", "unlock")
            kinds = [
                json.loads(row["metadata_json"]).get("kind")
                for row in get_db().execute(
                    "SELECT metadata_json FROM messages WHERE conversation_id = ? ORDER BY id",
                    (conversation_id,),
                ).fetchall()
            ]
        self.assertIn("任务", result)
        self.assertIn("match_point_task", kinds)
        self.assertNotIn("match_point", kinds)

    def test_unlock_reveals_one_point_after_both_people_complete_the_task(self) -> None:
        with self.app.app_context():
            conversation_id = start_direct_conversation("demo_001", "demo_002")
            use_tool(conversation_id, "demo_001", "unlock")
            for index in range(5):
                send_message(conversation_id, "demo_001", f"A-{index}")
                send_message(conversation_id, "demo_002", f"B-{index}")
            result = use_tool(conversation_id, "demo_002", "unlock")
            unlocked = get_db().execute(
                """SELECT COUNT(*) AS count FROM messages
                   WHERE conversation_id = ? AND json_extract(metadata_json, '$.kind') = 'match_point'""",
                (conversation_id,),
            ).fetchone()["count"]
        self.assertIn("已解锁", result)
        self.assertEqual(unlocked, 1)


if __name__ == "__main__":
    unittest.main()
