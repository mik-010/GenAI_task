"""ML / advanced statistics module — forecasting, anomaly detection, and statistical summaries."""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Forecast: simple linear trend + seasonal (day-of-week) model
# ------------------------------------------------------------------

def forecast_daily_cost(periods: int = 7) -> pd.DataFrame:
    """Forecast daily cost for the next `periods` days using a trend+seasonal model.

    Uses OLS with day-of-week dummies. Falls back to simple linear
    extrapolation when statsmodels is unavailable or data is too sparse.
    """
    from app.transform.queries import daily_usage_trends

    df = daily_usage_trends()
    if df.empty:
        return pd.DataFrame(columns=["day", "forecast_cost", "lower", "upper"])

    daily = df.groupby("day")["total_cost"].sum().reset_index()
    daily = daily.sort_values("day").reset_index(drop=True)
    daily["t"] = np.arange(len(daily))
    daily["dow"] = pd.to_datetime(daily["day"]).dt.dayofweek

    try:
        import statsmodels.api as sm

        X = pd.get_dummies(daily["dow"], prefix="dow", drop_first=True, dtype=float)
        X["t"] = daily["t"].astype(float)
        X = sm.add_constant(X)
        y = daily["total_cost"].astype(float)

        model = sm.OLS(y, X).fit()
        residual_std = float(model.resid.std())

        last_day = pd.to_datetime(daily["day"].iloc[-1])
        future_days = [last_day + pd.Timedelta(days=i + 1) for i in range(periods)]
        future_t = np.arange(len(daily), len(daily) + periods)
        future_dow = [d.dayofweek for d in future_days]

        X_future = pd.get_dummies(pd.Series(future_dow), prefix="dow", drop_first=True, dtype=float)
        for col in X.columns:
            if col not in X_future.columns and col not in ("const", "t"):
                X_future[col] = 0.0
        X_future["t"] = future_t.astype(float)
        X_future = sm.add_constant(X_future)
        X_future = X_future[X.columns]

        preds = model.predict(X_future)
        return pd.DataFrame({
            "day": [d.date() for d in future_days],
            "forecast_cost": preds.values,
            "lower": (preds - 1.96 * residual_std).values,
            "upper": (preds + 1.96 * residual_std).values,
        })

    except Exception:
        logger.warning("statsmodels forecast failed, falling back to linear extrapolation")
        coeffs = np.polyfit(daily["t"], daily["total_cost"], 1)
        last_day = pd.to_datetime(daily["day"].iloc[-1])
        future_days = [last_day + pd.Timedelta(days=i + 1) for i in range(periods)]
        future_t = np.arange(len(daily), len(daily) + periods)
        preds = np.polyval(coeffs, future_t)
        return pd.DataFrame({
            "day": [d.date() for d in future_days],
            "forecast_cost": preds,
            "lower": preds * 0.8,
            "upper": preds * 1.2,
        })


# ------------------------------------------------------------------
# Anomaly detection: cost outliers using IQR method
# ------------------------------------------------------------------

def detect_cost_anomalies(threshold: float = 1.5) -> pd.DataFrame:
    """Flag daily cost values outside the IQR fence."""
    from app.transform.queries import daily_usage_trends

    df = daily_usage_trends()
    if df.empty:
        return pd.DataFrame(columns=["day", "total_cost", "is_anomaly"])

    daily = df.groupby("day")["total_cost"].sum().reset_index()
    q1 = daily["total_cost"].quantile(0.25)
    q3 = daily["total_cost"].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - threshold * iqr
    upper = q3 + threshold * iqr
    daily["is_anomaly"] = (daily["total_cost"] < lower) | (daily["total_cost"] > upper)
    daily["lower_fence"] = lower
    daily["upper_fence"] = upper
    return daily


# ------------------------------------------------------------------
# Anomaly detection: error spikes using z-score
# ------------------------------------------------------------------

def detect_error_spikes(z_threshold: float = 2.0) -> pd.DataFrame:
    """Flag days where error count exceeds z_threshold standard deviations."""
    from app.transform.queries import error_rates_daily

    df = error_rates_daily()
    if df.empty:
        return pd.DataFrame(columns=["day", "error_count", "is_spike"])

    daily = df.groupby("day")["error_count"].sum().reset_index()
    mean = daily["error_count"].mean()
    std = daily["error_count"].std()
    if std == 0:
        daily["z_score"] = 0.0
    else:
        daily["z_score"] = (daily["error_count"] - mean) / std
    daily["is_spike"] = daily["z_score"].abs() > z_threshold
    return daily


# ------------------------------------------------------------------
# Advanced stats: percentile summary of token usage per practice
# ------------------------------------------------------------------

def token_percentiles_by_practice() -> pd.DataFrame:
    """Compute p50, p75, p90, p99 of daily token usage per practice."""
    from app.transform.queries import daily_usage_trends

    df = daily_usage_trends()
    if df.empty:
        return pd.DataFrame()

    df["total_tokens"] = df["total_input_tokens"] + df["total_output_tokens"]
    daily_practice = df.groupby(["day", "practice"])["total_tokens"].sum().reset_index()

    stats = daily_practice.groupby("practice")["total_tokens"].describe(
        percentiles=[0.5, 0.75, 0.9, 0.99]
    ).reset_index()
    return stats


# ------------------------------------------------------------------
# Advanced stats: cohort variance (level x practice)
# ------------------------------------------------------------------

def cohort_cost_variance() -> pd.DataFrame:
    """Per-user cost variance within each practice-level cohort."""
    from app.db import get_engine
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text("""
            SELECT e.practice, e.level,
                   COUNT(DISTINCT ar.user_email)  AS users,
                   AVG(user_cost)                  AS avg_cost,
                   STDDEV(user_cost)               AS std_cost,
                   MIN(user_cost)                  AS min_cost,
                   MAX(user_cost)                  AS max_cost
            FROM (
                SELECT user_email, SUM(cost_usd) AS user_cost
                FROM api_requests_fact
                GROUP BY user_email
            ) ar
            JOIN employees_dim e ON e.email = ar.user_email
            GROUP BY e.practice, e.level
            ORDER BY e.practice, e.level
        """), conn)
