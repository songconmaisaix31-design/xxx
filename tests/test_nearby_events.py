from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app import create_app
from app.config import Config
from app.services.events import POI_LOCATIONS, list_events
from app.services.users import ValidationError


class NearbyEventsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        config = type(
            "NearbyTestConfig",
            (Config,),
            {"TESTING": True, "DATABASE": str(Path(self.temp_dir.name) / "test.sqlite3"), "SECRET_KEY": "test"},
        )
        self.app = create_app(config)
        self.client = self.app.test_client()
        self.client.post("/demo/login")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_location_query_filters_and_sorts_by_estimated_distance(self) -> None:
        origin = POI_LOCATIONS["poi_001"]
        args = {
            "lat": str(origin["lat"]),
            "lng": str(origin["lng"]),
            "radius": "50",
            "sort": "distance",
        }
        with self.app.app_context():
            events = list_events("demo_001", args)
            one_km = list_events("demo_001", {**args, "radius": "1"})

        self.assertEqual([event["poi_id"] for event in events], ["poi_001", "poi_002", "poi_003"])
        self.assertEqual([event["distance_km"] for event in events], sorted(event["distance_km"] for event in events))
        self.assertEqual([event["poi_id"] for event in one_km], ["poi_001"])

        response = self.client.get("/events", query_string=args)
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertLess(html.index("AI 从业者交流晚餐"), html.index("读书与独立电影分享局"))
        self.assertLess(html.index("读书与独立电影分享局"), html.index("周末跑步后的早午餐"))
        self.assertEqual(html.count('class="distance-chip"'), 3)
        self.assertIn("距离为估算值", html)
        self.assertIn('method="get" action="/events"', html)
        with self.client.session_transaction() as flask_session:
            self.assertNotIn("lat", flask_session)
            self.assertNotIn("lng", flask_session)

    def test_invalid_location_and_radius_are_rejected_then_page_falls_back(self) -> None:
        invalid_queries = (
            {"lat": "91", "lng": "121", "radius": "5"},
            {"lat": "31", "lng": "181", "radius": "5"},
            {"lat": "31", "radius": "5"},
            {"lat": "31", "lng": "121", "radius": "0"},
            {"lat": "31", "lng": "121", "radius": "50.1"},
            {"lat": "nan", "lng": "121", "radius": "5"},
        )
        with self.app.app_context():
            for query in invalid_queries:
                with self.subTest(query=query), self.assertRaises(ValidationError):
                    list_events("demo_001", query)

        response = self.client.get(
            "/events", query_string={"lat": "91", "lng": "121", "radius": "5", "sort": "distance"}
        )
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("已回退为城市与全部活动筛选", html)
        for title in ("AI 从业者交流晚餐", "周末跑步后的早午餐", "读书与独立电影分享局"):
            self.assertIn(title, html)
        self.assertNotIn('class="distance-chip"', html)

    def test_denied_or_unsupported_location_keeps_city_and_all_events(self) -> None:
        html = self.client.get("/events").get_data(as_text=True)
        self.assertIn('name="city"', html)
        self.assertIn("全部城市", html)
        self.assertIn("使用当前位置", html)
        self.assertIn("尚未使用定位", html)
        for title in ("AI 从业者交流晚餐", "周末跑步后的早午餐", "读书与独立电影分享局"):
            self.assertIn(title, html)

        script_response = self.client.get("/static/js/nearby-events.js")
        script = script_response.get_data(as_text=True)
        script_response.close()
        self.assertLess(script.index('addEventListener("click"'), script.index("getCurrentPosition"))
        self.assertIn("已保留城市筛选和全部活动", script)
        self.assertNotIn("fetch(", script)
        self.assertNotIn("localStorage", script)

    def test_unlocated_listing_preserves_the_existing_service_contract(self) -> None:
        with self.app.app_context():
            events = list_events("demo_001", {})
        self.assertEqual(len(events), 3)
        for event in events:
            self.assertTrue({"id", "title", "display_score", "status_label", "required_tag_labels"} <= event.keys())
            self.assertNotIn("distance_km", event)

        city_html = self.client.get("/events", query_string={"city": "上海"}).get_data(as_text=True)
        self.assertIn("AI 从业者交流晚餐", city_html)
        self.assertIn("周末跑步后的早午餐", city_html)


if __name__ == "__main__":
    unittest.main()
