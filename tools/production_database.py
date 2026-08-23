from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Callable, Protocol
from urllib.parse import urlsplit

import turso_serverless
from turso_serverless.protocol import build_batch_step

from app.db import SCHEMA


APP_TABLES = (
    "users",
    "external_connections",
    "tags",
    "events",
    "event_members",
    "conversations",
    "conversation_members",
    "messages",
    "event_coupons",
    "admins",
    "reports",
    "event_reviews",
    "admin_audit_logs",
    "blocks",
)

COPY_ORDER = (
    "users",
    "admins",
    "external_connections",
    "tags",
    "events",
    "conversations",
    "event_members",
    "conversation_members",
    "messages",
    "event_coupons",
    "reports",
    "event_reviews",
    "admin_audit_logs",
    "blocks",
)

CONTAMINATION_QUERIES = {
    "demo_users": "SELECT COUNT(*) FROM users WHERE is_demo = 1 OR id LIKE 'demo_%'",
    "demo_admins": "SELECT COUNT(*) FROM admins WHERE id = 'admin_demo'",
    "fixture_tags": "SELECT COUNT(*) FROM tags WHERE data_mode = 'fixture'",
    "fixture_connections": (
        "SELECT COUNT(*) FROM external_connections WHERE data_mode = 'fixture'"
    ),
    "merchant_events": "SELECT COUNT(*) FROM events WHERE host_type = 'merchant'",
}

ROLE_ENVIRONMENT = {
    "source": ("TURSO_DATABASE_URL", "TURSO_AUTH_TOKEN"),
    "target": ("NEXT_TURSO_DATABASE_URL", "NEXT_TURSO_AUTH_TOKEN"),
}

IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
MAX_BATCH_PAYLOAD_BYTES = 32 * 1024 * 1024


class Cursor(Protocol):
    description: Sequence[Sequence[object]] | None

    def fetchone(self) -> object: ...

    def fetchall(self) -> list[object]: ...


class Connection(Protocol):
    in_transaction: bool

    def execute(
        self,
        sql: str,
        parameters: Sequence[object] | Mapping[str, object] = (),
    ) -> Cursor: ...

    def executescript(self, sql_script: str) -> Cursor: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class ColumnDefinition:
    name: str
    declared_type: str
    not_null: bool
    primary_key_position: int


@dataclass(frozen=True)
class TableSnapshot:
    name: str
    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]


class InspectionError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _first_value(row: object) -> object:
    if isinstance(row, Mapping):
        return next(iter(row.values()))
    return row[0]  # type: ignore[index]


def _cell(row: object, index: int) -> object:
    if isinstance(row, Mapping):
        return tuple(row.values())[index]
    return row[index]  # type: ignore[index]


def _validate_database_url(value: str) -> None:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"https", "libsql", "turso"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise InspectionError("invalid_database_url")


def database_settings(
    role: str, environ: Mapping[str, str] | None = None
) -> tuple[str, str]:
    source = environ if environ is not None else os.environ
    try:
        url_name, token_name = ROLE_ENVIRONMENT[role]
    except KeyError as error:
        raise InspectionError("invalid_role") from error

    database_url = source.get(url_name, "")
    auth_token = source.get(token_name, "")
    if not database_url or not auth_token:
        raise InspectionError("missing_database_environment")
    if not auth_token.strip():
        raise InspectionError("blank_auth_token")
    _validate_database_url(database_url)
    return database_url, auth_token


def assert_distinct_databases(environ: Mapping[str, str] | None = None) -> None:
    source_url, _ = database_settings("source", environ)
    target_url, _ = database_settings("target", environ)
    if _database_identity(source_url) == _database_identity(target_url):
        raise InspectionError("source_and_target_are_identical")


def _database_identity(value: str) -> tuple[str, int, str]:
    parsed = urlsplit(value)
    hostname = (parsed.hostname or "").lower()
    port = parsed.port or 443
    return hostname, port, parsed.path.rstrip("/")


def connect_database(role: str) -> Connection:
    database_url, auth_token = database_settings(role)
    return turso_serverless.connect(database_url, auth_token=auth_token)


def connect_database_pair() -> tuple[Connection, Connection]:
    source = connect_database("source")
    try:
        target = connect_database("target")
    except Exception:
        source.close()
        raise
    return source, target


def _collect_inspection(
    connection: Connection,
    role: str,
    progress: Callable[[str], None],
) -> dict[str, object]:
    progress("read_table_inventory")
    existing_tables = {
        str(_first_value(row))
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    table_counts: dict[str, int | None] = {table: None for table in APP_TABLES}
    contamination_counts: dict[str, int | None] = {
        name: None for name in CONTAMINATION_QUERIES
    }
    aggregate_queries: list[tuple[str, str, str]] = [
        ("table", table, f"SELECT COUNT(*) FROM {table}")
        for table in APP_TABLES
        if table in existing_tables
    ]
    aggregate_queries.extend(
        ("contamination", name, query)
        for name, query in CONTAMINATION_QUERIES.items()
        if _contamination_table(name) in existing_tables
    )
    if aggregate_queries:
        progress("read_aggregate_counts")
        aggregate_row = connection.execute(
            "SELECT " + ", ".join(f"({query})" for _, _, query in aggregate_queries)
        ).fetchone()
        for index, (kind, name, _) in enumerate(aggregate_queries):
            count = int(_cell(aggregate_row, index))
            if kind == "table":
                table_counts[name] = count
            else:
                contamination_counts[name] = count
    progress("check_foreign_keys")
    foreign_key_violations = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    progress("check_integrity")
    integrity_rows = connection.execute("PRAGMA integrity_check").fetchall()
    integrity_ok = bool(integrity_rows) and all(
        _first_value(row) == "ok" for row in integrity_rows
    )
    progress("hash_schema")
    schema_rows = connection.execute(
        """SELECT type, name, sql
           FROM sqlite_master
           WHERE name NOT LIKE 'sqlite_%'
           ORDER BY type, name"""
    ).fetchall()
    schema_material = "\n".join(
        "\x1f".join(str(_cell(row, index) or "") for index in range(3))
        for row in schema_rows
    )
    return {
        "role": role,
        "table_counts": table_counts,
        "missing_tables": [table for table, count in table_counts.items() if count is None],
        "contamination_counts": contamination_counts,
        "foreign_key_violations": foreign_key_violations,
        "integrity_ok": integrity_ok,
        "schema_sha256": hashlib.sha256(schema_material.encode("utf-8")).hexdigest(),
    }


def inspect_connection(
    connection: Connection,
    role: str,
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    if role not in ROLE_ENVIRONMENT:
        raise InspectionError("invalid_role")

    report_progress = progress or (lambda _: None)
    report_progress("begin_snapshot")
    connection.execute("BEGIN")
    try:
        return _collect_inspection(connection, role, report_progress)
    finally:
        connection.rollback()


def _contamination_table(name: str) -> str:
    return {
        "demo_users": "users",
        "demo_admins": "admins",
        "fixture_tags": "tags",
        "fixture_connections": "external_connections",
        "merchant_events": "events",
    }[name]


def _require_clean_database(
    inspection: Mapping[str, object],
    *,
    require_all_tables: bool,
    require_empty: bool,
) -> None:
    if not inspection["integrity_ok"]:
        raise InspectionError("database_integrity_failed")
    if int(inspection["foreign_key_violations"]):
        raise InspectionError("foreign_key_violations_detected")
    missing_tables = inspection["missing_tables"]
    if require_all_tables and missing_tables:
        raise InspectionError("application_tables_missing")
    contamination = inspection["contamination_counts"]
    if not isinstance(contamination, Mapping):
        raise InspectionError("invalid_inspection_result")
    if any(value not in (None, 0) for value in contamination.values()):
        raise InspectionError("prohibited_data_detected")
    if require_empty:
        table_counts = inspection["table_counts"]
        if not isinstance(table_counts, Mapping):
            raise InspectionError("invalid_inspection_result")
        if any(value not in (None, 0) for value in table_counts.values()):
            raise InspectionError("target_database_not_empty")


def inspect_role(
    role: str, progress: Callable[[str], None] | None = None
) -> dict[str, object]:
    if progress:
        progress("connect")
    connection = connect_database(role)
    try:
        if progress:
            progress("connected")
        return inspect_connection(connection, role, progress)
    finally:
        connection.close()


def initialize_target_connection(
    connection: Connection,
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    report_progress = progress or (lambda _: None)
    report_progress("inspect_target_before_initialization")
    before = inspect_connection(connection, "target", report_progress)
    _require_clean_database(before, require_all_tables=False, require_empty=True)
    report_progress("initialize_target_schema")
    connection.executescript(SCHEMA)
    report_progress("inspect_target_after_initialization")
    after = inspect_connection(connection, "target", report_progress)
    _require_clean_database(after, require_all_tables=True, require_empty=True)
    return after


def initialize_target(
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    assert_distinct_databases()
    connection = connect_database("target")
    try:
        return initialize_target_connection(connection, progress)
    finally:
        connection.close()


def read_table_schema(connection: Connection) -> dict[str, tuple[ColumnDefinition, ...]]:
    query = " UNION ALL ".join(
        f"""SELECT '{table}' AS table_name, cid, name, type, [notnull], pk
            FROM pragma_table_info('{table}')"""
        for table in APP_TABLES
    )
    rows = connection.execute(query).fetchall()
    schema: dict[str, list[ColumnDefinition]] = {table: [] for table in APP_TABLES}
    for row in rows:
        table = str(_cell(row, 0))
        name = str(_cell(row, 2))
        if table not in schema or not IDENTIFIER_PATTERN.fullmatch(name):
            raise InspectionError("unsafe_schema_identifier")
        schema[table].append(
            ColumnDefinition(
                name=name,
                declared_type=" ".join(str(_cell(row, 3) or "").upper().split()),
                not_null=bool(_cell(row, 4)),
                primary_key_position=int(_cell(row, 5)),
            )
        )
    if any(not columns for columns in schema.values()):
        raise InspectionError("application_tables_missing")
    return {table: tuple(columns) for table, columns in schema.items()}


def validate_schema_compatibility(
    source: Mapping[str, tuple[ColumnDefinition, ...]],
    target: Mapping[str, tuple[ColumnDefinition, ...]],
) -> None:
    for table in APP_TABLES:
        source_columns = {column.name: column for column in source.get(table, ())}
        target_columns = {column.name: column for column in target.get(table, ())}
        if source_columns.keys() != target_columns.keys():
            raise InspectionError("source_target_schema_mismatch")
        for name, source_column in source_columns.items():
            target_column = target_columns[name]
            if (
                source_column.declared_type != target_column.declared_type
                or source_column.not_null != target_column.not_null
                or source_column.primary_key_position != target_column.primary_key_position
            ):
                raise InspectionError("source_target_schema_mismatch")


def load_table_snapshots(
    connection: Connection,
    schema: Mapping[str, tuple[ColumnDefinition, ...]],
    canonical_columns: Mapping[str, tuple[str, ...]] | None = None,
    *,
    role: str = "database",
    progress: Callable[[str], None] | None = None,
    after_table: Callable[[], None] | None = None,
) -> tuple[TableSnapshot, ...]:
    report_progress = progress or (lambda _: None)
    snapshots = []
    for table in COPY_ORDER:
        definitions = schema[table]
        available = {column.name for column in definitions}
        columns = (
            canonical_columns[table]
            if canonical_columns is not None
            else tuple(sorted(available))
        )
        if set(columns) != available or any(
            not IDENTIFIER_PATTERN.fullmatch(column) for column in columns
        ):
            raise InspectionError("source_target_schema_mismatch")
        primary_key = tuple(
            column.name
            for column in sorted(
                (column for column in definitions if column.primary_key_position),
                key=lambda column: column.primary_key_position,
            )
        )
        if not primary_key:
            raise InspectionError("table_without_primary_key")
        select_columns = ", ".join(_quote_identifier(column) for column in columns)
        order_columns = ", ".join(_quote_identifier(column) for column in primary_key)
        report_progress(f"read_{role}_table_{table}")
        try:
            cursor = connection.execute(
                f"SELECT {select_columns} FROM {_quote_identifier(table)} "
                f"ORDER BY {order_columns}"
            )
            rows = tuple(tuple(row) for row in cursor.fetchall())
        except Exception:
            raise InspectionError(f"{role}_snapshot_read_failed_{table}") from None
        snapshots.append(TableSnapshot(table, columns, rows))
        if after_table is not None:
            after_table()
    return tuple(snapshots)


def _quote_identifier(value: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise InspectionError("unsafe_schema_identifier")
    return f'"{value}"'


def build_copy_batch(snapshots: Sequence[TableSnapshot]) -> list[dict[str, object]]:
    steps: list[dict[str, object]] = [
        build_batch_step("PRAGMA foreign_keys = ON", want_rows=False)
    ]
    previous_step = 0
    steps.append(
        build_batch_step(
            "BEGIN IMMEDIATE",
            want_rows=False,
            condition={"type": "ok", "step": previous_step},
        )
    )
    previous_step = 1
    for snapshot in snapshots:
        columns = ", ".join(_quote_identifier(column) for column in snapshot.columns)
        placeholders = ", ".join("?" for _ in snapshot.columns)
        sql = (
            f"INSERT INTO {_quote_identifier(snapshot.name)} ({columns}) "
            f"VALUES ({placeholders})"
        )
        for row in snapshot.rows:
            if len(row) != len(snapshot.columns):
                raise InspectionError("invalid_snapshot_row")
            steps.append(
                build_batch_step(
                    sql,
                    args=list(row),
                    want_rows=False,
                    condition={"type": "ok", "step": previous_step},
                )
            )
            previous_step = len(steps) - 1
    steps.append(
        build_batch_step(
            "COMMIT",
            want_rows=False,
            condition={"type": "ok", "step": previous_step},
        )
    )
    return steps


def execute_atomic_copy(connection: Connection, snapshots: Sequence[TableSnapshot]) -> None:
    session = getattr(connection, "_session", None)
    execute_pipeline = getattr(session, "execute_pipeline", None)
    if not callable(execute_pipeline):
        raise InspectionError("driver_batch_unavailable")

    # The pinned DB-API driver's executemany sends one HTTP request per row.
    # A single conditional Hrana batch keeps this one-off copy atomic and bounded.
    results = execute_pipeline(
        [{"type": "batch", "batch": {"steps": build_copy_batch(snapshots)}}]
    )
    if len(results) != 1 or results[0].get("type") != "ok":
        raise InspectionError("target_batch_failed")
    response = results[0].get("response") or {}
    if response.get("type") != "batch":
        raise InspectionError("target_batch_failed")
    batch_result = response.get("result") or {}
    step_errors = batch_result.get("step_errors") or []
    step_results = batch_result.get("step_results") or []
    if any(error is not None for error in step_errors) or not step_results:
        raise InspectionError("target_batch_failed")
    if step_results[-1] is None or connection.in_transaction:
        raise InspectionError("target_batch_not_committed")


def _snapshot_counts(snapshots: Sequence[TableSnapshot]) -> dict[str, int]:
    return {snapshot.name: len(snapshot.rows) for snapshot in snapshots}


def _snapshot_payload_bytes(snapshots: Sequence[TableSnapshot]) -> int:
    total = 0
    for snapshot in snapshots:
        for row in snapshot.rows:
            for value in row:
                if isinstance(value, str):
                    total += len(value.encode("utf-8"))
                elif isinstance(value, (bytes, bytearray)):
                    total += len(value)
                elif value is not None:
                    total += 8
    return total


def _canonical_columns(
    snapshots: Sequence[TableSnapshot],
) -> dict[str, tuple[str, ...]]:
    return {snapshot.name: snapshot.columns for snapshot in snapshots}


def _assert_snapshot_equality(
    source: Sequence[TableSnapshot], target: Sequence[TableSnapshot]
) -> None:
    if tuple(source) != tuple(target):
        raise InspectionError("source_target_data_mismatch")


def _keep_source_lock_alive(source: Connection) -> None:
    _keep_connection_alive(
        source,
        error_code="source_write_lock_lost",
        require_transaction=True,
    )


def _keep_target_connection_alive(target: Connection) -> None:
    _keep_connection_alive(
        target,
        error_code="target_connection_lost",
        require_transaction=False,
    )


def _keep_connection_alive(
    connection: Connection,
    *,
    error_code: str,
    require_transaction: bool,
) -> None:
    try:
        connection.execute("SELECT 1").fetchone()
    except Exception:
        raise InspectionError(error_code) from None
    if require_transaction and not connection.in_transaction:
        raise InspectionError(error_code)


def _close_connection(connection: Connection, *, rollback: bool) -> None:
    try:
        if rollback and connection.in_transaction:
            connection.rollback()
    except Exception:
        # Closing the Hrana stream also releases or expires its transaction.
        # Cleanup failure must not hide an already verified migration result.
        pass
    finally:
        connection.close()


def check_readiness(
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    assert_distinct_databases()
    report_progress = progress or (lambda _: None)
    source, target = connect_database_pair()
    try:
        report_progress("inspect_source_readiness")
        source_inspection = inspect_connection(source, "source", report_progress)
        report_progress("inspect_target_readiness")
        target_inspection = inspect_connection(target, "target", report_progress)
        _require_clean_database(
            source_inspection, require_all_tables=True, require_empty=False
        )
        _require_clean_database(
            target_inspection, require_all_tables=True, require_empty=True
        )
        report_progress("validate_schema_compatibility")
        validate_schema_compatibility(
            read_table_schema(source),
            read_table_schema(target),
        )
        return {
            "source_table_counts": source_inspection["table_counts"],
            "target_table_counts": target_inspection["table_counts"],
            "source_integrity_ok": source_inspection["integrity_ok"],
            "target_integrity_ok": target_inspection["integrity_ok"],
            "schema_compatible": True,
        }
    finally:
        target.close()
        source.close()


def migrate_databases(
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    if os.environ.get("DATABASE_MAINTENANCE_MODE") != "1":
        raise InspectionError("maintenance_mode_required")
    assert_distinct_databases()
    report_progress = progress or (lambda _: None)
    source, target = connect_database_pair()
    source_locked = False
    try:
        report_progress("inspect_empty_target")
        target_before = inspect_connection(target, "target", report_progress)
        _require_clean_database(
            target_before, require_all_tables=True, require_empty=True
        )

        report_progress("lock_source_writes")
        source.execute("BEGIN IMMEDIATE")
        source_locked = True
        source_inspection = _collect_inspection(source, "source", report_progress)
        _require_clean_database(
            source_inspection, require_all_tables=True, require_empty=False
        )

        report_progress("validate_schema_compatibility")
        source_schema = read_table_schema(source)
        target_schema = read_table_schema(target)
        validate_schema_compatibility(source_schema, target_schema)

        report_progress("read_source_snapshot")
        source_snapshots = load_table_snapshots(
            source,
            source_schema,
            role="source",
            progress=report_progress,
            after_table=lambda: _keep_target_connection_alive(target),
        )
        source_counts = _snapshot_counts(source_snapshots)
        if source_counts != source_inspection["table_counts"]:
            raise InspectionError("source_snapshot_count_mismatch")
        payload_bytes = _snapshot_payload_bytes(source_snapshots)
        if payload_bytes > MAX_BATCH_PAYLOAD_BYTES:
            raise InspectionError("migration_payload_too_large")

        report_progress("copy_snapshot_to_target")
        execute_atomic_copy(target, source_snapshots)

        report_progress("verify_target_snapshot")
        target_inspection = inspect_connection(target, "target", report_progress)
        _require_clean_database(
            target_inspection, require_all_tables=True, require_empty=False
        )
        if source_counts != target_inspection["table_counts"]:
            raise InspectionError("source_target_count_mismatch")
        target_snapshots = load_table_snapshots(
            target,
            target_schema,
            _canonical_columns(source_snapshots),
            role="target",
            progress=report_progress,
            after_table=lambda: _keep_source_lock_alive(source),
        )
        report_progress("compare_logical_snapshots")
        _assert_snapshot_equality(source_snapshots, target_snapshots)
        return {
            "source_table_counts": source_counts,
            "target_table_counts": _snapshot_counts(target_snapshots),
            "payload_bytes": payload_bytes,
            "logical_data_equal": True,
            "source_integrity_ok": source_inspection["integrity_ok"],
            "target_integrity_ok": target_inspection["integrity_ok"],
        }
    finally:
        _close_connection(target, rollback=True)
        _close_connection(source, rollback=source_locked)


def verify_pair(
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    if os.environ.get("DATABASE_MAINTENANCE_MODE") != "1":
        raise InspectionError("maintenance_mode_required")
    assert_distinct_databases()
    report_progress = progress or (lambda _: None)
    source, target = connect_database_pair()
    source_locked = False
    try:
        report_progress("lock_source_for_pair_verification")
        source.execute("BEGIN IMMEDIATE")
        source_locked = True
        source_inspection = _collect_inspection(source, "source", report_progress)
        target_inspection = inspect_connection(target, "target", report_progress)
        _require_clean_database(
            source_inspection, require_all_tables=True, require_empty=False
        )
        _require_clean_database(
            target_inspection, require_all_tables=True, require_empty=False
        )
        source_schema = read_table_schema(source)
        target_schema = read_table_schema(target)
        validate_schema_compatibility(source_schema, target_schema)
        report_progress("read_pair_snapshots")
        source_snapshots = load_table_snapshots(
            source,
            source_schema,
            role="source",
            progress=report_progress,
            after_table=lambda: _keep_target_connection_alive(target),
        )
        target_snapshots = load_table_snapshots(
            target,
            target_schema,
            _canonical_columns(source_snapshots),
            role="target",
            progress=report_progress,
            after_table=lambda: _keep_source_lock_alive(source),
        )
        report_progress("compare_logical_snapshots")
        _assert_snapshot_equality(source_snapshots, target_snapshots)
        return {
            "source_table_counts": _snapshot_counts(source_snapshots),
            "target_table_counts": _snapshot_counts(target_snapshots),
            "logical_data_equal": True,
            "source_integrity_ok": source_inspection["integrity_ok"],
            "target_integrity_ok": target_inspection["integrity_ok"],
        }
    finally:
        _close_connection(target, rollback=False)
        _close_connection(source, rollback=source_locked)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage a production database cutover with sanitized output only."
    )
    parser.add_argument(
        "command",
        choices=(
            "inspect-source",
            "inspect-target",
            "initialize-target",
            "check-readiness",
            "migrate",
            "verify-pair",
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    def report_progress(stage: str) -> None:
        print(
            json.dumps({"status": "progress", "stage": stage}),
            file=sys.stderr,
            flush=True,
        )

    try:
        if args.command.startswith("inspect-"):
            result = inspect_role(args.command.removeprefix("inspect-"), report_progress)
        elif args.command == "initialize-target":
            result = initialize_target(report_progress)
        elif args.command == "check-readiness":
            result = check_readiness(report_progress)
        elif args.command == "migrate":
            result = migrate_databases(report_progress)
        else:
            result = verify_pair(report_progress)
    except InspectionError as error:
        print(json.dumps({"status": "error", "error_code": error.code}, sort_keys=True))
        raise SystemExit(1) from None
    except Exception:
        print(json.dumps({"status": "error", "error_code": "database_operation_failed"}))
        raise SystemExit(1) from None
    print(json.dumps({"status": "ok", **result}, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
