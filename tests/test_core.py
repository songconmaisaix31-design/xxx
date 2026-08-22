from __future__ import annotations

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

from app import create_app
from app.config import Config
from app.db import get_db, utcnow
from app.services.chat import get_conversation, start_direct_conversation
from app.services.events import get_event, refresh_event_statuses, signup_for_event, viewer_coupon
from app.services.matching import ranked_matches
from app.services.users import ValidationError
from tools.harness_cli import build_parser, verification_stages


class CoreFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        config = type(
            "TestConfig",
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
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _login_demo(self) -> None:
        response = self.client.post("/demo/login")
        self.assertEqual(response.status_code, 302)

    def test_server_rendered_pages_are_reachable(self) -> None:
        self._login_demo()
        for path in ("/profile", "/profile/connections", "/matches", "/conversations", "/events", "/events/new"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_v2_shell_assets_and_mobile_navigation_are_server_rendered(self) -> None:
        guest_html = self.client.get("/").get_data(as_text=True)
        self.assertIn('data-auth="guest"', guest_html)
        self.assertNotIn('class="mobile-dock"', guest_html)
        for asset in (
            "/static/css/brutalist-foundation.css",
            "/static/css/brutalist-components.css",
            "/static/css/brutalist-mobile.css",
            "/static/css/match-flow.css",
            "/static/js/motion.js",
            "/static/js/match-flow.js",
            "/static/img/paper-dot-grid.png",
            "/static/img/brand-mark.png",
        ):
            with self.subTest(asset=asset):
                response = self.client.get(asset)
                self.assertEqual(response.status_code, 200)
                response.close()

        self._login_demo()
        profile_html = self.client.get("/profile").get_data(as_text=True)
        self.assertIn('data-auth="signed-in"', profile_html)
        self.assertIn('class="mobile-dock"', profile_html)
        self.assertIn('href="/matches"', profile_html)
        self.assertNotIn('href="#/', profile_html)

    def test_match_flow_is_server_owned_and_cancel_invalidates_stale_completion(self) -> None:
        self._login_demo()
        home = self.client.get("/").get_data(as_text=True)
        self.assertIn("开始一次匿名匹配", home)

        idle = self.client.get("/matches").get_data(as_text=True)
        self.assertIn('data-match-state="idle"', idle)
        self.assertIn('action="/matches/search/start"', idle)

        start = self.client.post("/matches/search/start")
        self.assertEqual(start.status_code, 302)
        self.assertTrue(start.headers["Location"].endswith("/matches/searching"))
        with self.client.session_transaction() as flask_session:
            first_flow = dict(flask_session["match_flow"])
        self.assertEqual(first_flow["phase"], "searching")

        duplicate = self.client.post("/matches/search/start")
        self.assertEqual(duplicate.status_code, 302)
        with self.client.session_transaction() as flask_session:
            self.assertEqual(flask_session["match_flow"]["attempt_id"], first_flow["attempt_id"])

        searching = self.client.get("/matches/searching").get_data(as_text=True)
        self.assertIn('data-match-state="searching"', searching)
        self.assertIn('aria-busy="true"', searching)
        self.assertIn('role="status" aria-live="polite"', searching)
        for step in ("filter", "similarity", "ranking"):
            self.assertIn(f'data-match-step="{step}"', searching)
        for private_value in (first_flow["candidate_id"], "夜航星", "raw_score", "display_score"):
            self.assertNotIn(private_value, searching)

        cancelled = self.client.post(
            "/matches/search/cancel", data={"attempt_id": first_flow["attempt_id"]}
        )
        self.assertEqual(cancelled.status_code, 302)
        with self.client.session_transaction() as flask_session:
            self.assertNotIn("match_flow", flask_session)

        stale = self.client.post(
            "/matches/search/complete", data={"attempt_id": first_flow["attempt_id"]}
        )
        self.assertEqual(stale.status_code, 302)
        self.assertTrue(stale.headers["Location"].endswith("/matches"))
        self.assertEqual(self.client.get("/matches/searching").status_code, 302)

    def test_match_retry_uses_a_new_attempt_and_rejects_old_page_completion(self) -> None:
        self._login_demo()
        self.client.post("/matches/search/start")
        with self.client.session_transaction() as flask_session:
            first_flow = dict(flask_session["match_flow"])

        completed = self.client.post(
            "/matches/search/complete", data={"attempt_id": first_flow["attempt_id"]}
        )
        self.assertEqual(completed.status_code, 302)
        self.assertTrue(completed.headers["Location"].endswith(first_flow["candidate_id"]))
        result = self.client.get(completed.headers["Location"]).get_data(as_text=True)
        self.assertIn('data-match-state="result"', result)
        self.assertIn('action="/matches/search/retry"', result)

        retry = self.client.post(
            "/matches/search/retry", data={"attempt_id": first_flow["attempt_id"]}
        )
        self.assertEqual(retry.status_code, 302)
        with self.client.session_transaction() as flask_session:
            second_flow = dict(flask_session["match_flow"])
        self.assertEqual(second_flow["phase"], "searching")
        self.assertNotEqual(second_flow["attempt_id"], first_flow["attempt_id"])
        self.assertNotEqual(second_flow["candidate_id"], first_flow["candidate_id"])
        self.assertIn(first_flow["candidate_id"], second_flow["seen_ids"])

        stale = self.client.post(
            "/matches/search/complete", data={"attempt_id": first_flow["attempt_id"]}
        )
        self.assertEqual(stale.status_code, 302)
        with self.client.session_transaction() as flask_session:
            self.assertEqual(flask_session["match_flow"]["attempt_id"], second_flow["attempt_id"])
            self.assertEqual(flask_session["match_flow"]["phase"], "searching")

        second_complete = self.client.post(
            "/matches/search/complete", data={"attempt_id": second_flow["attempt_id"]}
        )
        self.assertEqual(second_complete.status_code, 302)
        self.assertTrue(second_complete.headers["Location"].endswith(second_flow["candidate_id"]))

    def test_direct_conversation_does_not_expose_hidden_profile_fields_at_l0(self) -> None:
        with self.app.app_context():
            match = next(item for item in ranked_matches("demo_001") if item["candidate"]["id"] == "demo_002")
            self.assertGreaterEqual(match["display_score"], 60)
            conversation_id = start_direct_conversation("demo_001", "demo_002")
            conversation = get_conversation(conversation_id, "demo_001")
        self.assertEqual(conversation["progress"]["level"], 0)
        self.assertEqual(set(conversation["counterpart"]), {"anonymous_alias", "level"})
        self.assertNotIn("tags", conversation["counterpart"])

    def test_direct_conversation_creation_is_unique_in_both_directions(self) -> None:
        def start(left_id: str, right_id: str) -> str:
            with self.app.app_context():
                return start_direct_conversation(left_id, right_id)

        with ThreadPoolExecutor(max_workers=2) as executor:
            conversation_ids = {
                future.result()
                for future in (
                    executor.submit(start, "demo_001", "demo_002"),
                    executor.submit(start, "demo_002", "demo_001"),
                )
            }
        self.assertEqual(len(conversation_ids), 1)
        with self.app.app_context():
            conversation_id = conversation_ids.pop()
            self.assertEqual(
                get_db().execute(
                    "SELECT COUNT(*) AS count FROM conversation_members WHERE conversation_id = ?",
                    (conversation_id,),
                ).fetchone()["count"],
                2,
            )
            self.assertEqual(
                get_db().execute(
                    """SELECT COUNT(*) AS count FROM messages
                       WHERE conversation_id = ? AND json_extract(metadata_json, '$.kind') = 'match_started'""",
                    (conversation_id,),
                ).fetchone()["count"],
                1,
            )
            with self.assertRaises(ValidationError):
                start_direct_conversation("demo_001", "demo_001")

    def test_demo_sessions_are_invalidated_when_demo_mode_is_disabled(self) -> None:
        production_config = type(
            "ProductionSessionConfig",
            (Config,),
            {
                "TESTING": True,
                "DATABASE": self.app.config["DATABASE"],
                "SECRET_KEY": "test",
                "DEMO_MODE": False,
                "CSRF_ENABLED": False,
            },
        )
        production_app = create_app(production_config)
        user_client = production_app.test_client()
        with user_client.session_transaction() as flask_session:
            flask_session["user_id"] = "demo_001"
        profile = user_client.get("/profile")
        self.assertEqual(profile.status_code, 302)
        self.assertTrue(profile.headers["Location"].endswith("/login"))
        with user_client.session_transaction() as flask_session:
            self.assertNotIn("user_id", flask_session)

        admin_client = production_app.test_client()
        with admin_client.session_transaction() as flask_session:
            flask_session["admin_id"] = "admin_demo"
        self.assertEqual(admin_client.get("/admin/").status_code, 302)
        with admin_client.session_transaction() as flask_session:
            self.assertNotIn("admin_id", flask_session)
        self.assertEqual(admin_client.post("/demo/login").status_code, 404)

        real_client = production_app.test_client()
        registration = real_client.post(
            "/register",
            data={
                "email": "legacy-real@example.test",
                "password": "strong-test-password",
                "anonymous_alias": "历史真实用户",
                "birth_year": "1998",
                "gender": "male",
                "match_gender": "any",
                "city": "北京",
                "purposes": ["随便聊聊"],
                "interests": ["阅读"],
            },
        )
        self.assertEqual(registration.status_code, 302)
        with real_client.session_transaction() as flask_session:
            real_user_id = flask_session["user_id"]
        legacy_conversation_id = "legacy_cross_pool_direct"
        with production_app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO conversations (id, type, event_id, created_at) VALUES (?, 'direct', NULL, ?)",
                (legacy_conversation_id, utcnow()),
            )
            for user_id in (real_user_id, "demo_001"):
                db.execute(
                    """INSERT INTO conversation_members
                       (conversation_id, user_id, group_alias, joined_at) VALUES (?, ?, NULL, ?)""",
                    (legacy_conversation_id, user_id, utcnow()),
                )
            db.commit()
        disabled = real_client.get(f"/conversations/{legacy_conversation_id}").get_data(as_text=True)
        self.assertIn("该历史会话已停用", disabled)
        self.assertNotIn('id="composer"', disabled)
        real_client.post(
            f"/conversations/{legacy_conversation_id}/messages",
            data={"content": "跨池历史会话不应继续写入"},
        )
        with production_app.app_context():
            self.assertEqual(
                get_db().execute(
                    "SELECT COUNT(*) AS count FROM messages WHERE conversation_id = ?",
                    (legacy_conversation_id,),
                ).fetchone()["count"],
                0,
            )

    def test_deadline_forms_merchant_event_and_issues_coupon(self) -> None:
        with self.app.app_context():
            for user_id in ("demo_001", "demo_002", "demo_003"):
                signup_for_event("event_001", user_id)
            event = get_event("event_001", "demo_001")
            refresh_event_statuses(datetime.fromisoformat(event["signup_deadline"]) + timedelta(minutes=1))
            formed = get_event("event_001", "demo_001")
            coupon = viewer_coupon("event_001", "demo_001")
        self.assertEqual(formed["status"], "formed")
        self.assertTrue(formed["group_conversation_id"])
        self.assertEqual(coupon["status"], "issued")

    def test_cli_defaults_to_complete_isolated_pipeline(self) -> None:
        args = build_parser().parse_args([])
        self.assertEqual((args.command, args.suite), ("run", "all"))
        labels = [stage.label for stage in verification_stages(args.suite)]
        self.assertEqual(
            labels,
            ["Preflight", "Syntax", "Match motion", "Core checks", "Feature checks", "E2E harness"],
        )


if __name__ == "__main__":
    unittest.main()
