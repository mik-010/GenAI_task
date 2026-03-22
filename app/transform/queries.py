"""Shared analytics query layer used by both the Dash dashboard and the FastAPI service.

All functions return pandas DataFrames for easy consumption in Plotly/Dash and
JSON serialisation in FastAPI.
"""

from typing import List, Optional

import pandas as pd
from sqlalchemy import text

from app.db import get_engine


def _read(sql: str, params: Optional[dict] = None) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


# ------------------------------------------------------------------
# Usage / cost trends
# ------------------------------------------------------------------

def daily_usage_trends(practice: Optional[str] = None, level: Optional[str] = None) -> pd.DataFrame:
    """Token & cost trends per day with optional practice/level filter."""
    where_clauses = []
    params: dict = {}
    if practice:
        where_clauses.append("practice = :practice")
        params["practice"] = practice
    if level:
        where_clauses.append("level = :level")
        params["level"] = level
    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    return _read(f"""
        SELECT day, practice, level, model,
               request_count, total_input_tokens, total_output_tokens,
               total_cache_read, total_cache_create,
               total_cost, avg_duration_ms,
               session_count, user_count
        FROM mv_daily_usage
        {where}
        ORDER BY day
    """, params)


def cost_by_practice() -> pd.DataFrame:
    return _read("""
        SELECT practice,
               SUM(total_cost) AS total_cost,
               SUM(request_count) AS total_requests,
               SUM(total_input_tokens + total_output_tokens) AS total_tokens
        FROM mv_daily_usage
        GROUP BY practice
        ORDER BY total_cost DESC
    """)


def cost_by_level() -> pd.DataFrame:
    return _read("""
        SELECT level,
               SUM(total_cost) AS total_cost,
               SUM(request_count) AS total_requests
        FROM mv_daily_usage
        GROUP BY level
        ORDER BY level
    """)


# ------------------------------------------------------------------
# Peak usage
# ------------------------------------------------------------------

def hourly_peak(practice: Optional[str] = None) -> pd.DataFrame:
    where = "WHERE practice = :practice" if practice else ""
    params = {"practice": practice} if practice else {}
    return _read(f"""
        SELECT dow, hour,
               SUM(request_count) AS request_count,
               SUM(total_cost) AS total_cost,
               SUM(unique_users) AS unique_users
        FROM mv_hourly_peak
        {where}
        GROUP BY dow, hour
        ORDER BY dow, hour
    """, params)


# ------------------------------------------------------------------
# Tool behaviour
# ------------------------------------------------------------------

def tool_behavior(practice: Optional[str] = None) -> pd.DataFrame:
    where = "WHERE practice = :practice" if practice else ""
    params = {"practice": practice} if practice else {}
    return _read(f"""
        SELECT tool_name, event_name,
               SUM(event_count) AS event_count,
               SUM(accept_count) AS accept_count,
               SUM(reject_count) AS reject_count,
               SUM(success_count) AS success_count,
               SUM(failure_count) AS failure_count,
               AVG(avg_duration_ms) AS avg_duration_ms,
               MAX(p95_duration_ms) AS p95_duration_ms
        FROM mv_tool_behavior
        {where}
        GROUP BY tool_name, event_name
        ORDER BY event_count DESC
    """, params)


def tool_usage_over_time() -> pd.DataFrame:
    return _read("""
        SELECT date_trunc('day', event_ts)::date AS day,
               tool_name,
               COUNT(*) AS usage_count
        FROM tool_usage_fact
        GROUP BY 1, 2
        ORDER BY 1, 2
    """)


# ------------------------------------------------------------------
# Model efficiency
# ------------------------------------------------------------------

def model_efficiency() -> pd.DataFrame:
    return _read("""
        SELECT model, request_count, avg_cost, avg_duration_ms,
               avg_output_tokens, total_cost,
               tokens_per_dollar, tokens_per_sec
        FROM mv_model_efficiency
        ORDER BY total_cost DESC
    """)


# ------------------------------------------------------------------
# Error rates
# ------------------------------------------------------------------

def error_rates_daily() -> pd.DataFrame:
    return _read("""
        SELECT day, model, status_code, error_count
        FROM mv_error_rates
        ORDER BY day
    """)


def error_summary() -> pd.DataFrame:
    return _read("""
        SELECT model, status_code,
               SUM(error_count) AS total_errors
        FROM mv_error_rates
        GROUP BY model, status_code
        ORDER BY total_errors DESC
    """)


# ------------------------------------------------------------------
# Session / user stats
# ------------------------------------------------------------------

def session_stats() -> pd.DataFrame:
    return _read("""
        SELECT e.practice, e.level,
               COUNT(DISTINCT ef.session_id) AS sessions,
               COUNT(DISTINCT ef.user_email) AS users,
               COUNT(*) AS total_events
        FROM events_fact ef
        JOIN employees_dim e ON e.email = ef.user_email
        GROUP BY e.practice, e.level
        ORDER BY total_events DESC
    """)


def user_leaderboard(limit: int = 20) -> pd.DataFrame:
    return _read("""
        SELECT ar.user_email, e.full_name, e.practice, e.level,
               COUNT(*) AS requests,
               SUM(ar.cost_usd) AS total_cost,
               SUM(ar.output_tokens) AS total_output_tokens,
               COUNT(DISTINCT ar.session_id) AS sessions
        FROM api_requests_fact ar
        JOIN employees_dim e ON e.email = ar.user_email
        GROUP BY ar.user_email, e.full_name, e.practice, e.level
        ORDER BY total_cost DESC
        LIMIT :limit
    """, {"limit": limit})


# ------------------------------------------------------------------
# Prompt stats
# ------------------------------------------------------------------

def prompt_length_distribution() -> pd.DataFrame:
    return _read("""
        SELECT
            CASE
                WHEN prompt_length < 50 THEN '0-49'
                WHEN prompt_length < 200 THEN '50-199'
                WHEN prompt_length < 500 THEN '200-499'
                WHEN prompt_length < 1000 THEN '500-999'
                WHEN prompt_length < 3000 THEN '1000-2999'
                ELSE '3000+'
            END AS bucket,
            COUNT(*) AS count
        FROM user_prompts_fact
        GROUP BY 1
        ORDER BY MIN(prompt_length)
    """)


# ------------------------------------------------------------------
# KPI summary (for top-bar cards)
# ------------------------------------------------------------------

def kpi_summary(practice: Optional[str] = None, level: Optional[str] = None) -> dict:
    where_clauses = []
    params: dict = {}
    join = ""
    if practice or level:
        join = "JOIN employees_dim e ON e.email = ar.user_email"
        if practice:
            where_clauses.append("e.practice = :practice")
            params["practice"] = practice
        if level:
            where_clauses.append("e.level = :level")
            params["level"] = level
    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    df = _read(f"""
        SELECT
            COUNT(*)                        AS total_requests,
            SUM(ar.cost_usd)                AS total_cost,
            SUM(ar.input_tokens + ar.output_tokens) AS total_tokens,
            COUNT(DISTINCT ar.session_id)   AS total_sessions,
            COUNT(DISTINCT ar.user_email)   AS total_users,
            AVG(ar.duration_ms)             AS avg_latency_ms
        FROM api_requests_fact ar
        {join}
        {where}
    """, params)
    return df.iloc[0].to_dict() if len(df) else {}


# ------------------------------------------------------------------
# Filter options (for dropdowns)
# ------------------------------------------------------------------

def distinct_practices() -> List[str]:
    df = _read("SELECT DISTINCT practice FROM employees_dim ORDER BY practice")
    return df["practice"].tolist()


def distinct_levels() -> List[str]:
    df = _read("SELECT DISTINCT level FROM employees_dim ORDER BY level")
    return df["level"].tolist()


def distinct_models() -> List[str]:
    df = _read("SELECT DISTINCT model FROM api_requests_fact ORDER BY model")
    return df["model"].tolist()


def distinct_tools() -> List[str]:
    df = _read("SELECT DISTINCT tool_name FROM tool_usage_fact ORDER BY tool_name")
    return df["tool_name"].tolist()


# ------------------------------------------------------------------
# Data freshness
# ------------------------------------------------------------------

def last_ingested_at() -> Optional[str]:
    df = _read("SELECT MAX(ingested_at) AS ts FROM events_fact")
    if len(df) and df.iloc[0]["ts"] is not None:
        return str(df.iloc[0]["ts"])
    return None
