"""Load parsed events into PostgreSQL fact tables."""

import csv
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import text

from app.db import get_engine

logger = logging.getLogger(__name__)


def load_employees(csv_path: str) -> int:
    """Upsert employees from CSV into employees_dim. Returns row count."""
    engine = get_engine()
    count = 0
    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        with engine.begin() as conn:
            for row in reader:
                conn.execute(
                    text("""
                        INSERT INTO employees_dim (email, full_name, practice, level, location)
                        VALUES (:email, :full_name, :practice, :level, :location)
                        ON CONFLICT (email) DO UPDATE SET
                            full_name = EXCLUDED.full_name,
                            practice  = EXCLUDED.practice,
                            level     = EXCLUDED.level,
                            location  = EXCLUDED.location
                    """),
                    {
                        "email": row["email"],
                        "full_name": row["full_name"],
                        "practice": row["practice"],
                        "level": row["level"],
                        "location": row["location"],
                    },
                )
                count += 1
    logger.info("Upserted %d employees", count)
    return count


def _insert_event(conn, event: dict) -> int:
    """Insert base event and return the generated event id."""
    raw_json = json.dumps(event["raw_attributes"], default=str)
    result = conn.execute(
        text("""
            INSERT INTO events_fact
                (event_type, event_name, event_ts, session_id, user_email,
                 user_id, account_uuid, organization_id, terminal_type,
                 host_arch, host_name, os_type, os_version, service_version,
                 raw_attributes)
            VALUES
                (:event_type, :event_name, :event_ts, :session_id, :user_email,
                 :user_id, :account_uuid, :organization_id, :terminal_type,
                 :host_arch, :host_name, :os_type, :os_version, :service_version,
                 CAST(:raw_attributes AS jsonb))
            RETURNING id
        """),
        {
            "event_type": event["event_type"],
            "event_name": event["event_name"],
            "event_ts": event["event_ts"],
            "session_id": event["session_id"],
            "user_email": event["user_email"],
            "user_id": event.get("user_id"),
            "account_uuid": event.get("account_uuid"),
            "organization_id": event.get("organization_id"),
            "terminal_type": event.get("terminal_type"),
            "host_arch": event.get("host_arch"),
            "host_name": event.get("host_name"),
            "os_type": event.get("os_type"),
            "os_version": event.get("os_version"),
            "service_version": event.get("service_version"),
            "raw_attributes": raw_json,
        },
    )
    return result.fetchone()[0]


def _insert_api_request(conn, event_id: int, event: dict):
    ar = event["api_request"]
    conn.execute(
        text("""
            INSERT INTO api_requests_fact
                (event_id, event_ts, session_id, user_email, model,
                 input_tokens, output_tokens, cache_read_tokens,
                 cache_creation_tokens, cost_usd, duration_ms)
            VALUES
                (:event_id, :event_ts, :session_id, :user_email, :model,
                 :input_tokens, :output_tokens, :cache_read_tokens,
                 :cache_creation_tokens, :cost_usd, :duration_ms)
        """),
        {
            "event_id": event_id,
            "event_ts": event["event_ts"],
            "session_id": event["session_id"],
            "user_email": event["user_email"],
            **ar,
        },
    )


def _insert_tool_usage(conn, event_id: int, event: dict):
    tu = event["tool_usage"]
    conn.execute(
        text("""
            INSERT INTO tool_usage_fact
                (event_id, event_ts, event_name, session_id, user_email,
                 tool_name, decision, decision_source, success,
                 duration_ms, result_size_bytes)
            VALUES
                (:event_id, :event_ts, :event_name, :session_id, :user_email,
                 :tool_name, :decision, :decision_source, :success,
                 :duration_ms, :result_size_bytes)
        """),
        {
            "event_id": event_id,
            "event_ts": event["event_ts"],
            "event_name": event["event_name"],
            "session_id": event["session_id"],
            "user_email": event["user_email"],
            **tu,
        },
    )


def _insert_api_error(conn, event_id: int, event: dict):
    ae = event["api_error"]
    conn.execute(
        text("""
            INSERT INTO api_errors_fact
                (event_id, event_ts, session_id, user_email,
                 model, error_message, status_code, attempt, duration_ms)
            VALUES
                (:event_id, :event_ts, :session_id, :user_email,
                 :model, :error_message, :status_code, :attempt, :duration_ms)
        """),
        {
            "event_id": event_id,
            "event_ts": event["event_ts"],
            "session_id": event["session_id"],
            "user_email": event["user_email"],
            **ae,
        },
    )


def _insert_user_prompt(conn, event_id: int, event: dict):
    up = event["user_prompt"]
    conn.execute(
        text("""
            INSERT INTO user_prompts_fact
                (event_id, event_ts, session_id, user_email, prompt_length)
            VALUES
                (:event_id, :event_ts, :session_id, :user_email, :prompt_length)
        """),
        {
            "event_id": event_id,
            "event_ts": event["event_ts"],
            "session_id": event["session_id"],
            "user_email": event["user_email"],
            **up,
        },
    )


def load_events(events, batch_size: int = 500) -> dict:
    """Load parsed events into all fact tables.

    Returns {"ok": int, "failed": int}.
    """
    engine = get_engine()
    ok = failed = 0
    batch = []

    def flush(batch):
        nonlocal ok, failed
        with engine.begin() as conn:
            for event in batch:
                try:
                    event_id = _insert_event(conn, event)
                    etype = event["event_type"]
                    if "api_request" in event:
                        _insert_api_request(conn, event_id, event)
                    if "tool_usage" in event:
                        _insert_tool_usage(conn, event_id, event)
                    if "api_error" in event:
                        _insert_api_error(conn, event_id, event)
                    if "user_prompt" in event:
                        _insert_user_prompt(conn, event_id, event)
                    ok += 1
                except Exception:
                    logger.exception("Failed to insert event")
                    failed += 1

    for event in events:
        batch.append(event)
        if len(batch) >= batch_size:
            flush(batch)
            batch = []
    if batch:
        flush(batch)

    return {"ok": ok, "failed": failed}


def refresh_views():
    """Refresh all materialized views after ingestion."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("SELECT refresh_analytics_views()"))
    logger.info("Materialized views refreshed")


def record_ingestion(file_name: str, total: int, ok: int, failed: int, status: str = "done"):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO ingestion_log (file_name, records_total, records_ok, records_failed, finished_at, status)
                VALUES (:f, :t, :o, :fa, now(), :s)
            """),
            {"f": file_name, "t": total, "o": ok, "fa": failed, "s": status},
        )
