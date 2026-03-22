-- Claude Code Analytics – PostgreSQL Schema
-- Normalized fact/dimension tables for telemetry analytics

-- ============================================================
-- Dimension: employees
-- ============================================================
CREATE TABLE IF NOT EXISTS employees_dim (
    email           TEXT PRIMARY KEY,
    full_name       TEXT NOT NULL,
    practice        TEXT NOT NULL,
    level           TEXT NOT NULL,
    location        TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_emp_practice ON employees_dim(practice);
CREATE INDEX IF NOT EXISTS idx_emp_level ON employees_dim(level);

-- ============================================================
-- Fact: all raw events (base table)
-- ============================================================
CREATE TABLE IF NOT EXISTS events_fact (
    id              BIGSERIAL PRIMARY KEY,
    event_type      TEXT NOT NULL,         -- e.g. claude_code.api_request
    event_name      TEXT NOT NULL,         -- e.g. api_request
    event_ts        TIMESTAMPTZ NOT NULL,
    session_id      TEXT NOT NULL,
    user_email      TEXT NOT NULL,
    user_id         TEXT,
    account_uuid    TEXT,
    organization_id TEXT,
    terminal_type   TEXT,
    host_arch       TEXT,
    host_name       TEXT,
    os_type         TEXT,
    os_version      TEXT,
    service_version TEXT,
    raw_attributes  JSONB NOT NULL DEFAULT '{}',
    ingested_at     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON events_fact(event_ts);
CREATE INDEX IF NOT EXISTS idx_events_type ON events_fact(event_type);
CREATE INDEX IF NOT EXISTS idx_events_session ON events_fact(session_id);
CREATE INDEX IF NOT EXISTS idx_events_user ON events_fact(user_email);

-- ============================================================
-- Fact: API requests (derived from api_request events)
-- ============================================================
CREATE TABLE IF NOT EXISTS api_requests_fact (
    id              BIGSERIAL PRIMARY KEY,
    event_id        BIGINT REFERENCES events_fact(id),
    event_ts        TIMESTAMPTZ NOT NULL,
    session_id      TEXT NOT NULL,
    user_email      TEXT NOT NULL,
    model           TEXT NOT NULL,
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    output_tokens   INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens   INTEGER NOT NULL DEFAULT 0,
    cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd        DOUBLE PRECISION NOT NULL DEFAULT 0,
    duration_ms     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_apireq_ts ON api_requests_fact(event_ts);
CREATE INDEX IF NOT EXISTS idx_apireq_model ON api_requests_fact(model);
CREATE INDEX IF NOT EXISTS idx_apireq_user ON api_requests_fact(user_email);

-- ============================================================
-- Fact: tool usage (decision + result paired)
-- ============================================================
CREATE TABLE IF NOT EXISTS tool_usage_fact (
    id              BIGSERIAL PRIMARY KEY,
    event_id        BIGINT REFERENCES events_fact(id),
    event_ts        TIMESTAMPTZ NOT NULL,
    event_name      TEXT NOT NULL,          -- tool_decision or tool_result
    session_id      TEXT NOT NULL,
    user_email      TEXT NOT NULL,
    tool_name       TEXT NOT NULL,
    decision        TEXT,                   -- accept / reject (decision events)
    decision_source TEXT,
    success         BOOLEAN,               -- tool_result only
    duration_ms     INTEGER DEFAULT 0,
    result_size_bytes INTEGER
);

CREATE INDEX IF NOT EXISTS idx_tool_ts ON tool_usage_fact(event_ts);
CREATE INDEX IF NOT EXISTS idx_tool_name ON tool_usage_fact(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_user ON tool_usage_fact(user_email);

-- ============================================================
-- Fact: API errors
-- ============================================================
CREATE TABLE IF NOT EXISTS api_errors_fact (
    id              BIGSERIAL PRIMARY KEY,
    event_id        BIGINT REFERENCES events_fact(id),
    event_ts        TIMESTAMPTZ NOT NULL,
    session_id      TEXT NOT NULL,
    user_email      TEXT NOT NULL,
    model           TEXT,
    error_message   TEXT,
    status_code     TEXT,
    attempt         INTEGER DEFAULT 1,
    duration_ms     INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_apierr_ts ON api_errors_fact(event_ts);
CREATE INDEX IF NOT EXISTS idx_apierr_model ON api_errors_fact(model);

-- ============================================================
-- Fact: user prompts
-- ============================================================
CREATE TABLE IF NOT EXISTS user_prompts_fact (
    id              BIGSERIAL PRIMARY KEY,
    event_id        BIGINT REFERENCES events_fact(id),
    event_ts        TIMESTAMPTZ NOT NULL,
    session_id      TEXT NOT NULL,
    user_email      TEXT NOT NULL,
    prompt_length   INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_prompt_ts ON user_prompts_fact(event_ts);
CREATE INDEX IF NOT EXISTS idx_prompt_user ON user_prompts_fact(user_email);

-- ============================================================
-- Metadata: ingestion tracking
-- ============================================================
CREATE TABLE IF NOT EXISTS ingestion_log (
    id              BIGSERIAL PRIMARY KEY,
    file_name       TEXT NOT NULL,
    records_total   INTEGER DEFAULT 0,
    records_ok      INTEGER DEFAULT 0,
    records_failed  INTEGER DEFAULT 0,
    started_at      TIMESTAMPTZ DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT DEFAULT 'running'
);
