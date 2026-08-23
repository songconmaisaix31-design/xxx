from __future__ import annotations

import io
import re
import tempfile
import unittest
from pathlib import Path

from app import create_app
from app.config import Config
from app.db import get_db
from app.services.matching import NO_PHOTO_STANDBY_FACTOR, calculate_match, ranked_matches
from app.services.users import MAX_AVATAR_BYTES, get_user


PNG_FIXTURE = b"\x89PNG\r\n\x1a\n" + (b"avatar" * 12)


class AvatarMatchingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        config = type(
            "AvatarMatchingConfig",
            (Config,),
            {
                "TESTING": True,
                "DATABASE": str(Path(self.temp_dir.name) / "avatar.sqlite3"),
                "SECRET_KEY": "avatar-test",
                "DEMO_MODE": False,
                "REAL_USER_ONLY": False,
                "AI_FALLBACK_ENABLED": False,
            },
        )
        self.app = create_app(config)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def register(
        self,
        email: str,
        alias: str,
        *,
        with_avatar: bool,
        photo_preference: str = "photo_or_standby",
        interests: list[str] | None = None,
    ):
        client = self.app.test_client()
        data = {
            "email": email,
            "password": "avatar-test-password",
            "anonymous_alias": alias,
            "birth_year": "1998",
            "gender": "male",
            "match_gender": "any",
            "city": "北京",
            "purposes": ["随便聊聊"],
            "interests": interests or ["阅读"],
            "photo_match_preference": photo_preference,
        }
        if with_avatar:
            data["avatar"] = (io.BytesIO(PNG_FIXTURE), "ignored-avatar.png")
        response = client.post("/register", data=data, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 302, response.get_data(as_text=True))
        with client.session_transaction() as flask_session:
            user_id = flask_session["user_id"]
        return client, user_id

    def test_avatar_persists_with_truthful_mock_status_and_renders_in_result(self) -> None:
        viewer, viewer_id = self.register(
            "avatar-viewer@example.test", "头像查看者", with_avatar=True
        )
        _, candidate_id = self.register(
            "avatar-candidate@example.test",
            "头像候选人",
            with_avatar=True,
            photo_preference="photo_only",
        )

        with self.app.app_context():
            candidate = get_user(candidate_id)
            self.assertTrue(candidate["avatar_data_url"].startswith("data:image/png;base64,"))
            self.assertEqual(candidate["avatar_face_check"], "mock_placeholder")
            self.assertEqual(candidate["photo_match_preference"], "photo_only")

        profile = self.app.test_client()
        with profile.session_transaction() as flask_session:
            flask_session["user_id"] = candidate_id
        profile_html = profile.get("/profile").get_data(as_text=True)
        self.assertIn("人脸核验：Mock 占位，未真实验证", profile_html)
        self.assertIn("data:image/png;base64,", profile_html)

        started = viewer.post("/matches/search/start")
        searching = viewer.get(started.headers["Location"]).get_data(as_text=True)
        attempt_id = re.search(
            r'name="attempt_id" value="([^"]+)"', searching
        ).group(1)
        completed = viewer.post("/matches/search/complete", data={"attempt_id": attempt_id})
        result = viewer.get(completed.headers["Location"]).get_data(as_text=True)
        self.assertIn("PHOTO PRIMARY", result)
        self.assertIn("人脸核验为 Mock 占位，尚未真实验证", result)
        self.assertIn("data:image/png;base64,", result)
        self.assertNotIn("avatar-candidate@example.test", result)
        self.assertNotIn(candidate_id, result)
        self.assertNotIn(viewer_id, result)

    def test_no_photo_candidates_are_lowered_standby_only(self) -> None:
        _, viewer_id = self.register(
            "priority-viewer@example.test", "优先查看者", with_avatar=True
        )
        _, primary_id = self.register(
            "priority-photo@example.test", "有头像候选", with_avatar=True, interests=["旅行"]
        )
        _, standby_id = self.register(
            "priority-standby@example.test", "无头像候补", with_avatar=False
        )

        with self.app.app_context():
            self.assertEqual(
                [item["candidate"]["id"] for item in ranked_matches(viewer_id)],
                [primary_id],
            )
            get_db().execute("DELETE FROM users WHERE id = ?", (primary_id,))
            get_db().commit()
            standby = ranked_matches(viewer_id)
            baseline = calculate_match(get_user(viewer_id), get_user(standby_id))["raw_score"]
            self.assertEqual([item["candidate"]["id"] for item in standby], [standby_id])
            self.assertTrue(standby[0]["is_photo_standby"])
            self.assertAlmostEqual(standby[0]["raw_score"], baseline * NO_PHOTO_STANDBY_FACTOR)

            get_db().execute(
                "UPDATE users SET photo_match_preference = 'photo_only' WHERE id = ?",
                (viewer_id,),
            )
            get_db().commit()
            self.assertEqual(ranked_matches(viewer_id), [])

    def test_avatar_upload_rejects_unsupported_and_oversized_files(self) -> None:
        for email, payload, filename in (
            ("bad-avatar@example.test", b"not-an-image", "avatar.svg"),
            (
                "large-avatar@example.test",
                b"\xff\xd8\xff" + (b"x" * MAX_AVATAR_BYTES),
                "avatar.jpg",
            ),
        ):
            with self.subTest(email=email):
                client = self.app.test_client()
                response = client.post(
                    "/register",
                    data={
                        "email": email,
                        "password": "avatar-test-password",
                        "anonymous_alias": "无效头像",
                        "birth_year": "1998",
                        "gender": "male",
                        "match_gender": "any",
                        "city": "北京",
                        "purposes": ["随便聊聊"],
                        "avatar": (io.BytesIO(payload), filename),
                    },
                    content_type="multipart/form-data",
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn("头像", response.get_data(as_text=True))
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"], 0)


if __name__ == "__main__":
    unittest.main()
