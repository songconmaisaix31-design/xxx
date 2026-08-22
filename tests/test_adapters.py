from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.config import Config
from app.db import get_db
from app.services.adapters import (
    ADAPTERS,
    AdapterError,
    DuolingoPublicDataSourceAdapter,
    FixtureDataSourceAdapter,
    connect_source,
)


class FakeResponse:
    def __init__(self, payload: bytes, *, status: int = 200, content_length: int | None = None):
        self.payload = payload
        self.status = status
        self.headers = {"Content-Length": str(content_length if content_length is not None else len(payload))}

    def read(self, _: int = -1) -> bytes:
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class RecordingOpener:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.requests = []

    def __call__(self, request, *, timeout: int):
        self.requests.append((request, timeout))
        return self.response


class AdapterContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        config = type(
            "AdapterTestConfig",
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

    def test_fixture_sources_are_deterministic_and_never_verified(self) -> None:
        for source in ("duolingo", "keep"):
            with self.subTest(source=source):
                adapter = FixtureDataSourceAdapter(source)
                context = adapter.authorize("demo-authorized")
                first = adapter.fetch_tags(context, "user-example")
                second = adapter.fetch_tags(context, "user-example")
                self.assertEqual(first, second)
                self.assertGreaterEqual(len(first), 10)
                self.assertTrue(all(tag.data_mode == "fixture" for tag in first))
                self.assertTrue(all(not tag.verified for tag in first))

    def test_duolingo_live_maps_only_supported_fields(self) -> None:
        payload = json.dumps(
            {
                "users": [
                    {
                        "streak": 971,
                        "totalXp": 48000,
                        "courses": [
                            {"title": "Japanese", "learningLanguage": "ja", "xp": 30000},
                            {"title": "English", "learningLanguage": "en", "xp": 18000},
                        ],
                    }
                ]
            }
        ).encode()
        opener = RecordingOpener(FakeResponse(payload))
        adapter = DuolingoPublicDataSourceAdapter(opener=opener)
        identifier = adapter.authorize(" public_user ")
        tags = adapter.fetch_tags(identifier, "unused-user-id")

        self.assertEqual(identifier, "public_user")
        self.assertTrue(all(tag.data_mode == "live" and tag.verified for tag in tags))
        values = {tag.tag_id: tag.value for tag in tags}
        self.assertEqual(values["lang_streak"], {"days": 971})
        self.assertEqual(values["learning_total_xp"], {"xp": 48000})
        self.assertEqual(values["learning_course_count"], {"count": 2})
        self.assertEqual(opener.requests[0][1], 5)
        self.assertIn("username=public_user", opener.requests[0][0].full_url)
        self.assertEqual(opener.requests[0][0].full_url.split("?", 1)[0], "https://www.duolingo.com/2017-06-30/users")

    def test_duolingo_live_rejects_bad_identifier_and_oversized_response(self) -> None:
        adapter = DuolingoPublicDataSourceAdapter(opener=RecordingOpener(FakeResponse(b"{}")))
        with self.assertRaises(AdapterError) as invalid:
            adapter.authorize("bad username!")
        self.assertEqual(invalid.exception.code, "invalid_identifier")

        oversized = DuolingoPublicDataSourceAdapter(
            opener=RecordingOpener(FakeResponse(b"{}", content_length=256 * 1024 + 1))
        )
        with self.assertRaises(AdapterError) as too_large:
            oversized.fetch_tags("public_user", "unused")
        self.assertEqual(too_large.exception.code, "response_too_large")

    def test_live_sync_persists_only_normalized_data_and_mode(self) -> None:
        payload = json.dumps({"users": [{"streak": 42, "totalXp": 900, "courses": [{"title": "English", "xp": 900}]}]}).encode()
        adapter = DuolingoPublicDataSourceAdapter(opener=RecordingOpener(FakeResponse(payload)))
        with self.app.app_context(), patch.dict(ADAPTERS, {"duolingo_live": adapter}, clear=False):
            count = connect_source(
                "demo_001",
                "duolingo",
                mode="live",
                identifier="public_user",
            )
            connection = get_db().execute(
                "SELECT status, access_token, data_mode FROM external_connections WHERE user_id = 'demo_001' AND source = 'duolingo'"
            ).fetchone()
            rows = get_db().execute(
                "SELECT data_mode, verified FROM tags WHERE user_id = 'demo_001' AND source = 'duolingo'"
            ).fetchall()
            derived = get_db().execute(
                "SELECT data_mode, verified FROM tags WHERE user_id = 'demo_001' AND source = 'derived'"
            ).fetchall()
        self.assertGreaterEqual(count, 1)
        self.assertEqual(dict(connection), {"status": "connected", "access_token": None, "data_mode": "live"})
        self.assertTrue(all(row["data_mode"] == "live" and row["verified"] == 1 for row in rows))
        self.assertGreaterEqual(len(derived), 2)
        self.assertTrue(all(row["data_mode"] == "derived" and row["verified"] == 0 for row in derived))


if __name__ == "__main__":
    unittest.main()
