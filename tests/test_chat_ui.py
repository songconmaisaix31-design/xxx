from __future__ import annotations

import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from app import create_app
from app.config import Config
from app.db import get_db, utcnow
from app.services.chat import start_direct_conversation


class ChatContractParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.elements: list[tuple[str, dict[str, str | None]]] = []
        self.forms: list[dict] = []
        self._open_forms: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        self.elements.append((tag, attributes))
        if tag == "form":
            form = {"attrs": attributes, "controls": []}
            self.forms.append(form)
            self._open_forms.append(form)
        elif self._open_forms and tag in {"button", "input", "textarea"}:
            self._open_forms[-1]["controls"].append((tag, attributes))

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self._open_forms:
            self._open_forms.pop()

    def elements_with(self, attribute: str, value: str | None = None):
        return [
            (tag, attrs)
            for tag, attrs in self.elements
            if attribute in attrs and (value is None or attrs[attribute] == value)
        ]


class ChatMissionDeckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        config = type(
            "ChatUiTestConfig",
            (Config,),
            {
                "TESTING": True,
                "DATABASE": str(Path(self.temp_dir.name) / "test.sqlite3"),
                "SECRET_KEY": "test",
                "DEMO_MODE": True,
            },
        )
        self.app = create_app(config)
        self.client = self.app.test_client()
        self.assertEqual(self.client.post("/demo/login").status_code, 302)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _parse(self, path: str) -> tuple[str, ChatContractParser]:
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        parser = ChatContractParser()
        parser.feed(html)
        return html, parser

    @staticmethod
    def _classes(attrs: dict[str, str | None]) -> set[str]:
        return set((attrs.get("class") or "").split())

    def test_direct_chat_whitelists_system_metadata_and_keeps_real_form_contracts(self) -> None:
        with self.app.app_context():
            conversation_id = start_direct_conversation("demo_001", "demo_002")
            db = get_db()
            system_messages = (
                ("dice", "摇骰子结果：4 点｜理想中的周末", {"kind": "dice", "point": 4}),
                ("task_card", "任务卡 · 运动｜定一个共同目标", {"kind": "task_card", "category": "运动"}),
                ("match_point", "匹配点已解锁：都在学英语", {"kind": "match_point", "index": 0}),
                ("group_unlock_task", "轮流说一个愿意带到饭局的话题", {"kind": "group_unlock_task"}),
                ("demo_progress", "演示模式：关系阶段已推进至 L1。", {"kind": "demo_progress"}),
                ("future_kind", "未来类型应安全降级为普通通知", {"kind": "future_kind"}),
            )
            for _, content, metadata in system_messages:
                db.execute(
                    """INSERT INTO messages
                       (conversation_id, sender_id, message_type, content, metadata_json, created_at)
                       VALUES (?, NULL, 'system_card', ?, ?, ?)""",
                    (conversation_id, content, json.dumps(metadata, ensure_ascii=False), utcnow()),
                )
            for content in ("第一条连续消息", "第二条连续消息"):
                db.execute(
                    """INSERT INTO messages
                       (conversation_id, sender_id, message_type, content, metadata_json, created_at)
                       VALUES (?, 'demo_001', 'text', ?, '{}', ?)""",
                    (conversation_id, content, utcnow()),
                )
            db.commit()

        html, dom = self._parse(f"/conversations/{conversation_id}")

        logs = [(tag, attrs) for tag, attrs in dom.elements_with("role", "log") if tag == "div"]
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0][1].get("aria-live"), "polite")
        self.assertEqual(logs[0][1].get("tabindex"), "0")

        expected_classes = {
            "match_started": "system-match",
            "dice": "system-dice",
            "task_card": "system-task",
            "match_point": "system-unlock",
            "group_unlock_task": "system-group-task",
            "demo_progress": "system-demo",
            "notice": "system-notice",
        }
        rendered_systems = {
            attrs["data-system-kind"]: self._classes(attrs)
            for tag, attrs in dom.elements_with("data-system-kind")
            if tag == "article"
        }
        self.assertEqual(set(rendered_systems), set(expected_classes))
        for kind, class_name in expected_classes.items():
            with self.subTest(kind=kind):
                self.assertIn(class_name, rendered_systems[kind])
        self.assertNotIn('data-system-kind="future_kind"', html)

        message_groups = [attrs["data-message-group"] for _, attrs in dom.elements_with("data-message-group")]
        self.assertEqual(message_groups[-2:], ["start", "continuation"])

        post_forms = [form for form in dom.forms if form["attrs"].get("method", "get").lower() == "post"]
        actions = [form["attrs"].get("action") for form in post_forms]
        required_actions = (
            f"/conversations/{conversation_id}/messages",
            f"/conversations/{conversation_id}/tools/dice",
            f"/conversations/{conversation_id}/tools/task_card",
            f"/conversations/{conversation_id}/tools/unlock",
            f"/conversations/{conversation_id}/demo/advance",
            f"/conversations/{conversation_id}/report",
            f"/conversations/{conversation_id}/block",
        )
        for action in required_actions:
            with self.subTest(action=action):
                self.assertIn(action, actions)

        message_form = next(form for form in post_forms if form["attrs"].get("action", "").endswith("/messages"))
        content = next(attrs for tag, attrs in message_form["controls"] if tag == "textarea" and attrs.get("name") == "content")
        self.assertEqual(content.get("maxlength"), "500")
        self.assertIn("required", content)

        report_forms = [form for form in post_forms if form["attrs"].get("action", "").endswith("/report")]
        self.assertEqual(len(report_forms), 2)
        for form in report_forms:
            reason = next(attrs for _, attrs in form["controls"] if attrs.get("name") == "reason")
            self.assertEqual(reason.get("maxlength"), "200")
            self.assertIn("required", reason)

        dialog_ids = {attrs.get("id") for tag, attrs in dom.elements if tag == "dialog"}
        self.assertEqual({"report-dialog", "block-dialog"}, dialog_ids)
        for _, attrs in dom.elements_with("id"):
            if attrs.get("id") in dialog_ids:
                self.assertIn("hidden", attrs)
        self.assertTrue(dom.elements_with("id", "safety-fallback"))

        canvas = [
            attrs
            for tag, attrs in dom.elements
            if tag == "section" and "conversation-canvas" in self._classes(attrs)
        ]
        self.assertEqual(len(canvas), 1)

        chat_css = (Path(self.app.root_path) / "static" / "css" / "chat-mission-deck.css").read_text(encoding="utf-8")
        chat_js = (Path(self.app.root_path) / "static" / "js" / "chat-mission-deck.js").read_text(encoding="utf-8")
        self.assertIn(".safety-dialog:not([open])", chat_css)
        self.assertIn(".mission-workspace", chat_css)
        self.assertIn("grid-template-columns: minmax(0, 1fr);", chat_css)
        self.assertIn("overflow-y: auto;", chat_css)
        self.assertIn("height: clamp(26rem, 60dvh, 42rem);", chat_css)
        self.assertIn("data-message-log", html)
        self.assertIn("messageLog.scrollTop = messageLog.scrollHeight;", chat_js)
        self.assertIn("dialog.hidden = false;", chat_js)
        self.assertIn("dialog.hidden = true;", chat_js)
        self.assertRegex(chat_css, r"\.safety-launch\s*\{[^}]*color:\s*var\(--neo-ink\);")
        self.assertIn('.report-launch[aria-expanded="true"]', chat_css)
        self.assertIn('button.setAttribute("aria-expanded", String(isOpen));', chat_js)

        launchers = {
            attrs.get("data-dialog-open"): attrs
            for tag, attrs in dom.elements_with("data-dialog-open")
            if tag == "button"
        }
        self.assertEqual(set(launchers), {"report-dialog", "block-dialog"})
        self.assertEqual(launchers["report-dialog"].get("aria-controls"), "report-dialog")
        self.assertEqual(launchers["report-dialog"].get("aria-expanded"), "false")
        self.assertEqual(launchers["report-dialog"].get("aria-haspopup"), "dialog")

        tool_forms = {
            form["attrs"].get("data-tool"): form["attrs"]
            for form in dom.forms
            if form["attrs"].get("data-tool")
        }
        self.assertEqual(set(tool_forms), {"dice", "task_card", "unlock"})
        self.assertIn("tool-dice", self._classes(tool_forms["dice"]))
        self.assertIn("tool-task", self._classes(tool_forms["task_card"]))
        self.assertIn("tool-unlock", self._classes(tool_forms["unlock"]))
        self.assertEqual(tool_forms["dice"].get("data-tool-state"), "ready")
        self.assertEqual(tool_forms["task_card"].get("data-tool-state"), "random")

        tool_images = {
            attrs.get("src"): attrs
            for tag, attrs in dom.elements
            if tag == "img" and "tool-visual" in self._classes(attrs)
        }
        expected_images = {
            "/static/img/chat-tool-dice.webp",
            "/static/img/chat-tool-task.webp",
            "/static/img/chat-tool-unlock.webp",
        }
        self.assertEqual(set(tool_images), expected_images)
        for image_url in expected_images:
            image_path = Path(self.app.root_path) / "static" / image_url.removeprefix("/static/")
            with self.subTest(image=image_url):
                self.assertTrue(image_path.is_file())
                image_header = image_path.read_bytes()[:12]
                self.assertEqual(image_header[:4], b"RIFF")
                self.assertEqual(image_header[8:12], b"WEBP")
                self.assertEqual(tool_images[image_url].get("alt"), "")
                self.assertEqual(tool_images[image_url].get("loading"), "lazy")
                self.assertEqual(tool_images[image_url].get("decoding"), "async")
                self.assertEqual(tool_images[image_url].get("width"), "720")
                self.assertEqual(tool_images[image_url].get("height"), "720")

    def test_group_block_is_absent_and_archived_chat_is_read_only(self) -> None:
        with self.app.app_context():
            row = get_db().execute(
                """SELECT c.id FROM conversations c
                   JOIN conversation_members cm ON cm.conversation_id = c.id
                   WHERE c.type = 'event_group' AND cm.user_id = 'demo_001' LIMIT 1"""
            ).fetchone()
            self.assertIsNotNone(row)
            conversation_id = row["id"]

        self.assertEqual(
            self.client.post(f"/conversations/{conversation_id}/tools/unlock").status_code,
            302,
        )
        _, group_dom = self._parse(f"/conversations/{conversation_id}")
        self.assertTrue(group_dom.elements_with("data-system-kind", "group_unlock_task"))
        self.assertFalse(any(form["attrs"].get("action", "").endswith("/block") for form in group_dom.forms))
        self.assertFalse(group_dom.elements_with("id", "block-dialog"))

        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE conversations SET archived_at = ? WHERE id = ?", (utcnow(), conversation_id))
            db.commit()
            archived_message_count = db.execute(
                "SELECT COUNT(*) AS count FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()["count"]

        self.assertEqual(
            self.client.post(f"/conversations/{conversation_id}/tools/dice").status_code,
            302,
        )
        self.assertEqual(
            self.client.post(
                f"/conversations/{conversation_id}/messages",
                data={"content": "归档后不应写入"},
            ).status_code,
            302,
        )
        with self.app.app_context():
            self.assertEqual(
                get_db().execute(
                    "SELECT COUNT(*) AS count FROM messages WHERE conversation_id = ?",
                    (conversation_id,),
                ).fetchone()["count"],
                archived_message_count,
            )

        html, archived_dom = self._parse(f"/conversations/{conversation_id}")
        self.assertNotIn('id="composer"', html)
        self.assertFalse(any(form["attrs"].get("data-tool") for form in archived_dom.forms))
        self.assertIn("该群聊已归档", html)
        self.assertTrue(any(form["attrs"].get("action", "").endswith("/report") for form in archived_dom.forms))


if __name__ == "__main__":
    unittest.main()
