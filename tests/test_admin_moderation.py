from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from werkzeug.datastructures import MultiDict
from werkzeug.security import check_password_hash

from app import create_app
from app.config import Config
from app.db import get_db
from app.routes.admin import bp as admin_bp
from app.services.chat import report_subject
from app.services.events import create_user_event
from app.services.moderation import authenticate_admin


class AdminModerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        config = type(
            "AdminTestConfig",
            (Config,),
            {
                "TESTING": True,
                "DATABASE": str(Path(self.temp_dir.name) / "test.sqlite3"),
                "SECRET_KEY": "admin-test",
                "DEMO_MODE": True,
                "CSRF_ENABLED": False,
            },
        )
        self.app = create_app(config)
        if "admin" not in self.app.blueprints:
            self.app.register_blueprint(admin_bp)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _login_admin(self, password: str = "admin-password"):
        return self.client.post(
            "/admin/login",
            data={"email": "admin@realtags.local", "password": password},
        )

    def _create_pending_event(self, title: str = "待审核的真实饭局") -> str:
        start = (datetime.now(timezone(timedelta(hours=8))) + timedelta(days=3)).replace(
            hour=19, minute=0, second=0, microsecond=0
        )
        form = MultiDict(
            [
                ("title", title),
                ("description", "审核描述"),
                ("poi_id", "poi_001"),
                ("start_at", start.strftime("%Y-%m-%dT%H:%M")),
                ("min_size", "3"),
                ("max_size", "6"),
                ("budget_level", "50-100"),
                ("pay_type", "AA"),
                ("gender_policy", "any"),
                ("signup_mode", "review"),
                ("required_tags", "interest_ai"),
            ]
        )
        with self.app.app_context():
            event_id = create_user_event("demo_001", form)
            status = get_db().execute("SELECT status FROM events WHERE id = ?", (event_id,)).fetchone()["status"]
        self.assertEqual(status, "pending_review")
        return event_id

    def test_seeded_admin_login_is_hashed_and_does_not_expose_hash(self) -> None:
        with self.app.app_context():
            row = get_db().execute(
                "SELECT password_hash FROM admins WHERE email = ?", ("admin@realtags.local",)
            ).fetchone()
            password_hash = row["password_hash"]
            admin = authenticate_admin("ADMIN@REALTAGS.LOCAL", "admin-password")
        self.assertNotEqual(password_hash, "admin-password")
        self.assertTrue(check_password_hash(password_hash, "admin-password"))
        self.assertNotIn("password_hash", admin)

        failed = self._login_admin("wrong-password")
        self.assertEqual(failed.status_code, 302)
        with self.client.session_transaction() as flask_session:
            self.assertNotIn("admin_id", flask_session)

        logged_in = self._login_admin()
        self.assertEqual(logged_in.status_code, 302)
        dashboard = self.client.get("/admin/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertNotIn(password_hash, dashboard.get_data(as_text=True))

    def test_normal_user_session_cannot_access_or_become_admin(self) -> None:
        guest = self.client.get("/admin/")
        self.assertEqual(guest.status_code, 302)
        self.assertTrue(guest.headers["Location"].endswith("/admin/login"))

        self.client.post("/demo/login")
        with self.client.session_transaction() as flask_session:
            self.assertIn("user_id", flask_session)
            self.assertNotIn("admin_id", flask_session)
        user_attempt = self.client.get("/admin/")
        self.assertEqual(user_attempt.status_code, 302)
        self.assertTrue(user_attempt.headers["Location"].endswith("/admin/login"))

        self._login_admin()
        with self.client.session_transaction() as flask_session:
            self.assertEqual(flask_session.get("admin_id"), "admin_demo")
            self.assertNotIn("user_id", flask_session)

    def test_dashboard_lists_limited_registered_accounts_and_supports_search(self) -> None:
        self._login_admin()
        with self.app.app_context():
            password_hash = get_db().execute(
                "SELECT password_hash FROM users WHERE id = ?", ("demo_001",)
            ).fetchone()["password_hash"]

        dashboard = self.client.get("/admin/").get_data(as_text=True)
        self.assertIn("注册账户（4）", dashboard)
        self.assertIn("demo@realtags.local", dashboard)
        self.assertIn("晨光旅人", dashboard)
        self.assertIn("演示账户", dashboard)
        self.assertIn("已授权数据源", dashboard)
        self.assertNotIn(password_hash, dashboard)
        self.assertNotIn("mock-duolingo-token", dashboard)
        self.assertNotIn("mock-keep-token", dashboard)

        searched = self.client.get("/admin/?q=%E5%A4%9C%E8%88%AA").get_data(as_text=True)
        self.assertIn("注册账户（1）", searched)
        self.assertIn("sora@realtags.local", searched)
        self.assertNotIn("demo@realtags.local", searched)

    def test_admin_approves_pending_event_once_and_audits_it(self) -> None:
        event_id = self._create_pending_event()
        self._login_admin()
        review_page = self.client.get(f"/admin/events/{event_id}").get_data(as_text=True)
        self.assertIn("待审核的真实饭局", review_page)

        response = self.client.post(
            f"/admin/events/{event_id}/review", data={"decision": "approve"}
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            event = get_db().execute("SELECT status FROM events WHERE id = ?", (event_id,)).fetchone()
            review = get_db().execute("SELECT * FROM event_reviews WHERE event_id = ?", (event_id,)).fetchone()
            logs = get_db().execute(
                "SELECT * FROM admin_audit_logs WHERE target_type = 'event' AND target_id = ?", (event_id,)
            ).fetchall()
        self.assertEqual(event["status"], "recruiting")
        self.assertEqual((review["status"], review["reviewed_by"]), ("approved", "admin_demo"))
        self.assertEqual(len(logs), 1)
        self.assertEqual((logs[0]["old_status"], logs[0]["new_status"]), ("pending_review", "recruiting"))

        self.client.post(
            f"/admin/events/{event_id}/review",
            data={"decision": "reject", "rejection_reason": "重复决定"},
        )
        with self.app.app_context():
            self.assertEqual(
                get_db().execute("SELECT COUNT(*) AS count FROM admin_audit_logs WHERE target_id = ?", (event_id,)).fetchone()["count"],
                1,
            )

    def test_event_rejection_requires_reason_and_rejects_illegal_decision(self) -> None:
        event_id = self._create_pending_event("需要拒绝的活动")
        self._login_admin()
        for data in ({"decision": "publish"}, {"decision": "reject", "rejection_reason": "  "}):
            response = self.client.post(f"/admin/events/{event_id}/review", data=data)
            self.assertEqual(response.status_code, 302)
            with self.app.app_context():
                status = get_db().execute("SELECT status FROM events WHERE id = ?", (event_id,)).fetchone()["status"]
            self.assertEqual(status, "pending_review")

        self.client.post(
            f"/admin/events/{event_id}/review",
            data={"decision": "reject", "rejection_reason": "地点描述无法核验"},
        )
        with self.app.app_context():
            event_status = get_db().execute("SELECT status FROM events WHERE id = ?", (event_id,)).fetchone()["status"]
            review = get_db().execute("SELECT rejection_reason FROM event_reviews WHERE event_id = ?", (event_id,)).fetchone()
        self.assertEqual(event_status, "rejected")
        self.assertEqual(review["rejection_reason"], "地点描述无法核验")

    def test_admin_resolves_report_with_actor_note_time_and_rejects_second_transition(self) -> None:
        with self.app.app_context():
            report_subject("demo_002", "event", "event_001", "活动描述疑似误导")
            report_id = get_db().execute("SELECT id FROM reports ORDER BY created_at DESC LIMIT 1").fetchone()["id"]
        self._login_admin()
        dashboard = self.client.get("/admin/").get_data(as_text=True)
        self.assertIn("活动描述疑似误导", dashboard)
        self.assertIn("AI 从业者交流晚餐", dashboard)

        response = self.client.post(
            f"/admin/reports/{report_id}/review",
            data={"decision": "resolved", "note": "已联系发起人并完成核验"},
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            report = get_db().execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
            audit_count = get_db().execute(
                "SELECT COUNT(*) AS count FROM admin_audit_logs WHERE target_type = 'report' AND target_id = ?",
                (report_id,),
            ).fetchone()["count"]
        self.assertEqual(report["status"], "resolved")
        self.assertEqual(report["handled_by"], "admin_demo")
        self.assertEqual(report["handling_note"], "已联系发起人并完成核验")
        self.assertTrue(report["handled_at"])
        self.assertEqual(audit_count, 1)

        self.client.post(
            f"/admin/reports/{report_id}/review", data={"decision": "dismissed", "note": "重复处理"}
        )
        with self.app.app_context():
            report = get_db().execute("SELECT status FROM reports WHERE id = ?", (report_id,)).fetchone()
            audit_count = get_db().execute(
                "SELECT COUNT(*) AS count FROM admin_audit_logs WHERE target_type = 'report' AND target_id = ?",
                (report_id,),
            ).fetchone()["count"]
        self.assertEqual(report["status"], "resolved")
        self.assertEqual(audit_count, 1)

    def test_legacy_reports_table_is_migrated_in_place(self) -> None:
        legacy_dir = tempfile.TemporaryDirectory()
        self.addCleanup(legacy_dir.cleanup)
        database = Path(legacy_dir.name) / "legacy.sqlite3"
        db = sqlite3.connect(database)
        db.execute(
            """CREATE TABLE reports (
                   id TEXT PRIMARY KEY, reporter_id TEXT NOT NULL, subject_type TEXT NOT NULL,
                   subject_id TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL
               )"""
        )
        db.commit()
        db.close()
        config = type(
            "LegacyAdminTestConfig",
            (Config,),
            {
                "TESTING": True,
                "DATABASE": str(database),
                "SECRET_KEY": "legacy-test",
                "DEMO_MODE": True,
                "CSRF_ENABLED": False,
            },
        )
        legacy_app = create_app(config)
        with legacy_app.app_context():
            columns = {row["name"] for row in get_db().execute("PRAGMA table_info(reports)").fetchall()}
            admin = get_db().execute("SELECT email FROM admins WHERE id = 'admin_demo'").fetchone()
        self.assertTrue({"status", "handled_by", "handling_note", "handled_at"} <= columns)
        self.assertEqual(admin["email"], "admin@realtags.local")


if __name__ == "__main__":
    unittest.main()
