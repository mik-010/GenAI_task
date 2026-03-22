"""FastAPI service exposing analytics endpoints backed by the shared query layer."""

from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Claude Code Analytics API",
    version="1.0.0",
    description="Programmatic access to Claude Code telemetry analytics.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _df_to_records(df):
    """Convert a DataFrame to a list of dicts, handling NaN values."""
    return df.where(df.notna(), None).to_dict(orient="records")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics/usage-trends")
def usage_trends(
    practice: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
):
    """Daily token/cost trends with optional practice & level filter."""
    from app.transform.queries import daily_usage_trends
    try:
        df = daily_usage_trends(practice=practice, level=level)
        df["day"] = df["day"].astype(str)
        return {"data": _df_to_records(df)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/metrics/peak-times")
def peak_times(practice: Optional[str] = Query(None)):
    """Hourly request heatmap data."""
    from app.transform.queries import hourly_peak
    try:
        df = hourly_peak(practice=practice)
        return {"data": _df_to_records(df)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/metrics/tool-behavior")
def tool_behavior_endpoint(practice: Optional[str] = Query(None)):
    """Tool decision/result statistics."""
    from app.transform.queries import tool_behavior
    try:
        df = tool_behavior(practice=practice)
        return {"data": _df_to_records(df)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/metrics/model-efficiency")
def model_efficiency_endpoint():
    """Model cost/speed comparison."""
    from app.transform.queries import model_efficiency
    try:
        df = model_efficiency()
        return {"data": _df_to_records(df)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/metrics/errors")
def errors_endpoint():
    """Error rate summary."""
    from app.transform.queries import error_summary
    try:
        df = error_summary()
        return {"data": _df_to_records(df)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/metrics/anomalies")
def anomalies_endpoint():
    """Detected anomalies from the ML layer."""
    from app.ml.analytics import detect_cost_anomalies, detect_error_spikes
    try:
        cost_anomalies = detect_cost_anomalies()
        error_spikes = detect_error_spikes()
        return {
            "cost_anomalies": _df_to_records(cost_anomalies) if not cost_anomalies.empty else [],
            "error_spikes": _df_to_records(error_spikes) if not error_spikes.empty else [],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/metrics/forecast")
def forecast_endpoint(periods: int = Query(7, ge=1, le=60)):
    """Cost forecast for the next N days."""
    from app.ml.analytics import forecast_daily_cost
    try:
        df = forecast_daily_cost(periods=periods)
        df["day"] = df["day"].astype(str)
        return {"data": _df_to_records(df)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/metrics/kpi")
def kpi_endpoint():
    """High-level KPI summary."""
    from app.transform.queries import kpi_summary
    try:
        return kpi_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/metrics/leaderboard")
def leaderboard_endpoint(limit: int = Query(20, ge=1, le=100)):
    """Top users by cost."""
    from app.transform.queries import user_leaderboard
    try:
        df = user_leaderboard(limit=limit)
        return {"data": _df_to_records(df)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/data/freshness")
def freshness_endpoint():
    """Last ingested timestamp and lag."""
    from app.transform.queries import last_ingested_at
    try:
        ts = last_ingested_at()
        return {"last_ingested_at": ts}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
