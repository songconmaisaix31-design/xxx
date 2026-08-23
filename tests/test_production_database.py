from __future__ import annotations

import json
import sqlite3
import unittest

from app.db import SCHEMA
from tools.production_database import (
    APP_TABLES,
    InspectionError,
    TableSnapshot,
    assert_distinct_databases,
    build_copy_batch,
    database_settings,
    execute_atomic_copy,
    initialize_target_connection,
    inspect_connection,
    load_table_snapshots,
    read_table_schema,
    validate_schema_compatibility,
)


class ProductionDatabaseInspectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = sqlite3.connect(":memory:")
        self.database.executescript(SCHEMA)

    def tearDown(self) -> None:
        self.database.close()

    def test_empty_database_reports_only_aggregate_evidence(self) -> None:
        result = inspect_connection(self.database, "source")

        self.assertEqual(result["missing_tables"], [])
        self.assertEqual(result["table_counts"], {table: 0 for table in APP_TABLES})
        self.assertEqual(
            result["contamination_counts"],
            {
                "demo_users": 0,
                "demo_admins": 0,
                "fixture_tags": 0,
                "fixture_connections": 0,
                "merchant_events": 0,
            },
        )
        self.assertEqual(result["foreign_key_violations"], 0)
        self.assertTrue(result["integrity_ok"])

    def test_output_does_not_include_sensitive_row_values(self) -> None:
        sensitive_values = {
            "email": "private-person@example.test",
            "hash": "sensitive-password-hash",
            "alias": "private-alias",
        }
        self.database.execute(
            """INSERT INTO users (
                   id, email, password_hash, anonymous_alias, birth_year, gender,
                   match_gender, city, purposes_json, interests_json, mbti,
                   zodiac, schedule, phone_verified, is_demo, created_at
               ) VALUES (?, ?, ?, ?, 1998, 'male', 'female', 'Beijing', '[]',
                         '[]', 'INTJ', 'Libra', 'night', 0, 0, ?)""",
            (
                "private-user-id",
                sensitive_values["email"],
                sensitive_values["hash"],
                sensitive_values["alias"],
                "2026-08-23T00:00:00+00:00",
            ),
        )
        self.database.commit()

        encoded = json.dumps(inspect_connection(self.database, "source"), sort_keys=True)

        self.assertIn('"users": 1', encoded)
        for value in sensitive_values.values():
            self.assertNotIn(value, encoded)
        self.assertNotIn("private-user-id", encoded)

    def test_contamination_is_reported_as_counts(self) -> None:
        self.database.execute(
            """INSERT INTO users (
                   id, email, password_hash, anonymous_alias, birth_year, gender,
                   match_gender, city, purposes_json, interests_json, mbti,
                   zodiac, schedule, phone_verified, is_demo, created_at
               ) VALUES ('demo_001', 'demo@example.test', 'hash', 'demo', 1998,
                         'male', 'female', 'Beijing', '[]', '[]', 'INTJ',
                         'Libra', 'night', 0, 1, '2026-08-23T00:00:00+00:00')"""
        )
        self.database.commit()

        result = inspect_connection(self.database, "source")

        self.assertEqual(result["contamination_counts"]["demo_users"], 1)

    def test_settings_require_a_complete_credential_pair(self) -> None:
        with self.assertRaisesRegex(InspectionError, "missing_database_environment"):
            database_settings(
                "source",
                {"TURSO_DATABASE_URL": "libsql://database.example.test"},
            )

    def test_settings_reject_urls_with_embedded_credentials(self) -> None:
        with self.assertRaisesRegex(InspectionError, "invalid_database_url"):
            database_settings(
                "target",
                {
                    "NEXT_TURSO_DATABASE_URL": "https://user:password@database.example.test",
                    "NEXT_TURSO_AUTH_TOKEN": "opaque-token",
                },
            )

    def test_source_and_target_must_be_distinct(self) -> None:
        with self.assertRaisesRegex(InspectionError, "source_and_target_are_identical"):
            assert_distinct_databases(
                {
                    "TURSO_DATABASE_URL": "libsql://database.example.test",
                    "TURSO_AUTH_TOKEN": "source-token",
                    "NEXT_TURSO_DATABASE_URL": "https://database.example.test/",
                    "NEXT_TURSO_AUTH_TOKEN": "target-token",
                }
            )

    def test_fresh_target_initialization_is_idempotent_and_empty(self) -> None:
        target = sqlite3.connect(":memory:")
        try:
            first = initialize_target_connection(target)
            second = initialize_target_connection(target)
        finally:
            target.close()

        expected_counts = {table: 0 for table in APP_TABLES}
        self.assertEqual(first["table_counts"], expected_counts)
        self.assertEqual(second["table_counts"], expected_counts)
        self.assertEqual(first["missing_tables"], [])

    def test_schema_compatibility_ignores_column_order_but_rejects_extra_columns(self) -> None:
        target = sqlite3.connect(":memory:")
        target.executescript(SCHEMA)
        try:
            source_schema = read_table_schema(self.database)
            target_schema = read_table_schema(target)
            validate_schema_compatibility(source_schema, target_schema)

            target.execute("ALTER TABLE users ADD COLUMN unexpected TEXT")
            changed_target_schema = read_table_schema(target)
            with self.assertRaisesRegex(InspectionError, "source_target_schema_mismatch"):
                validate_schema_compatibility(source_schema, changed_target_schema)
        finally:
            target.close()

    def test_snapshot_loader_uses_canonical_columns_for_logical_equality(self) -> None:
        self.database.execute(
            """INSERT INTO users (
                   id, email, password_hash, anonymous_alias, birth_year, gender,
                   match_gender, city, purposes_json, interests_json, mbti,
                   zodiac, schedule, phone_verified, is_demo, created_at
               ) VALUES ('user-1', 'person@example.test', 'hash', 'alias', 1998,
                         'male', 'female', 'Beijing', '[]', '[]', 'INTJ',
                         'Libra', 'night', 0, 0, '2026-08-23T00:00:00+00:00')"""
        )
        self.database.commit()
        schema = read_table_schema(self.database)
        completed_tables = []

        snapshots = load_table_snapshots(
            self.database,
            schema,
            after_table=lambda: completed_tables.append(True),
        )

        users = next(snapshot for snapshot in snapshots if snapshot.name == "users")
        self.assertEqual(users.columns, tuple(sorted(users.columns)))
        self.assertEqual(len(users.rows), 1)
        self.assertEqual(len(completed_tables), len(APP_TABLES))

    def test_copy_batch_uses_bound_values_and_conditional_commit(self) -> None:
        sensitive_value = "private-person@example.test"
        snapshots = (
            TableSnapshot(
                name="users",
                columns=("id", "email"),
                rows=(("user-1", sensitive_value),),
            ),
        )

        steps = build_copy_batch(snapshots)
        sql_text = "\n".join(str(step["stmt"]["sql"]) for step in steps)

        self.assertNotIn(sensitive_value, sql_text)
        self.assertIn("VALUES (?, ?)", sql_text)
        self.assertEqual(steps[-1]["stmt"]["sql"], "COMMIT")
        self.assertEqual(steps[-1]["condition"], {"type": "ok", "step": 2})

    def test_atomic_copy_uses_one_successful_hrana_batch(self) -> None:
        class FakeSession:
            def __init__(self) -> None:
                self.requests = []

            def execute_pipeline(self, requests):
                self.requests = requests
                step_count = len(requests[0]["batch"]["steps"])
                return [
                    {
                        "type": "ok",
                        "response": {
                            "type": "batch",
                            "result": {
                                "step_errors": [None] * step_count,
                                "step_results": [{}] * step_count,
                            },
                        },
                    }
                ]

        class FakeConnection:
            def __init__(self) -> None:
                self._session = FakeSession()
                self.in_transaction = False

        connection = FakeConnection()
        snapshot = TableSnapshot("users", ("id",), (("user-1",),))

        execute_atomic_copy(connection, (snapshot,))

        self.assertEqual(len(connection._session.requests), 1)
        self.assertEqual(connection._session.requests[0]["type"], "batch")


if __name__ == "__main__":
    unittest.main()
