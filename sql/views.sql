-- Claude Code Analytics – Materialized views for dashboards / API

-- ============================================================
-- Usage trends by day, practice, and model
-- ============================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_usage AS
SELECT
    date_trunc('day', ar.event_ts)::date AS day,
    e.practice,
    e.level,
    ar.model,
    COUNT(*)                            AS request_count,
    SUM(ar.input_tokens)                AS total_input_tokens,
    SUM(ar.output_tokens)               AS total_output_tokens,
    SUM(ar.cache_read_tokens)           AS total_cache_read,
    SUM(ar.cache_creation_tokens)       AS total_cache_create,
    SUM(ar.cost_usd)                    AS total_cost,
    AVG(ar.duration_ms)                 AS avg_duration_ms,
    COUNT(DISTINCT ar.session_id)       AS session_count,
    COUNT(DISTINCT ar.user_email)       AS user_count
FROM api_requests_fact ar
JOIN employees_dim e ON e.email = ar.user_email
GROUP BY 1, 2, 3, 4;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_daily_pk
    ON mv_daily_usage(day, practice, level, model);

-- ============================================================
-- Peak usage by hour of day
-- ============================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_hourly_peak AS
SELECT
    EXTRACT(DOW FROM ar.event_ts)::int   AS dow,
    EXTRACT(HOUR FROM ar.event_ts)::int  AS hour,
    e.practice,
    COUNT(*)                              AS request_count,
    SUM(ar.cost_usd)                     AS total_cost,
    COUNT(DISTINCT ar.user_email)        AS unique_users
FROM api_requests_fact ar
JOIN employees_dim e ON e.email = ar.user_email
GROUP BY 1, 2, 3;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_hourly_pk
    ON mv_hourly_peak(dow, hour, practice);

-- ============================================================
-- Tool behavior summary
-- ============================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_tool_behavior AS
SELECT
    tu.tool_name,
    e.practice,
    tu.event_name,
    COUNT(*)                                        AS event_count,
    COUNT(*) FILTER (WHERE tu.decision = 'accept')  AS accept_count,
    COUNT(*) FILTER (WHERE tu.decision = 'reject')  AS reject_count,
    COUNT(*) FILTER (WHERE tu.success = true)       AS success_count,
    COUNT(*) FILTER (WHERE tu.success = false)      AS failure_count,
    AVG(tu.duration_ms) FILTER (WHERE tu.event_name = 'tool_result') AS avg_duration_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY tu.duration_ms)
        FILTER (WHERE tu.event_name = 'tool_result') AS p95_duration_ms
FROM tool_usage_fact tu
JOIN employees_dim e ON e.email = tu.user_email
GROUP BY 1, 2, 3;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_tool_pk
    ON mv_tool_behavior(tool_name, practice, event_name);

-- ============================================================
-- Model efficiency comparison
-- ============================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_model_efficiency AS
SELECT
    ar.model,
    COUNT(*)                                AS request_count,
    AVG(ar.cost_usd)                       AS avg_cost,
    AVG(ar.duration_ms)                    AS avg_duration_ms,
    AVG(ar.output_tokens)                  AS avg_output_tokens,
    SUM(ar.cost_usd)                       AS total_cost,
    SUM(ar.output_tokens)::double precision
        / NULLIF(SUM(ar.cost_usd), 0)      AS tokens_per_dollar,
    AVG(ar.output_tokens::double precision
        / NULLIF(ar.duration_ms, 0) * 1000) AS tokens_per_sec
FROM api_requests_fact ar
GROUP BY 1;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_model_pk
    ON mv_model_efficiency(model);

-- ============================================================
-- Error rate summary by model and day
-- ============================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_error_rates AS
SELECT
    date_trunc('day', ae.event_ts)::date AS day,
    ae.model,
    ae.status_code,
    COUNT(*)                              AS error_count
FROM api_errors_fact ae
GROUP BY 1, 2, 3;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_error_pk
    ON mv_error_rates(day, model, status_code);

-- ============================================================
-- Helper function to refresh all materialized views
-- ============================================================
CREATE OR REPLACE FUNCTION refresh_analytics_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_usage;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hourly_peak;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_tool_behavior;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_model_efficiency;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_error_rates;
END;
$$ LANGUAGE plpgsql;
