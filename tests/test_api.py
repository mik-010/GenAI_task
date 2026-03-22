"""Tests for the FastAPI endpoints (mocked DB layer)."""

from unittest.mock import patch
import pandas as pd
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.api.main import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestKPIEndpoint:
    @patch("app.transform.queries.kpi_summary")
    def test_kpi(self, mock_kpi, client):
        mock_kpi.return_value = {
            "total_requests": 1000,
            "total_cost": 50.0,
            "total_tokens": 500000,
            "total_sessions": 100,
            "total_users": 10,
            "avg_latency_ms": 8000.0,
        }
        resp = client.get("/metrics/kpi")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_requests"] == 1000


class TestUsageTrends:
    @patch("app.transform.queries.daily_usage_trends")
    def test_trends(self, mock_trends, client):
        mock_trends.return_value = pd.DataFrame({
            "day": ["2026-01-15"],
            "practice": ["Platform Engineering"],
            "level": ["L5"],
            "model": ["claude-sonnet-4-5-20250929"],
            "request_count": [10],
            "total_input_tokens": [1000],
            "total_output_tokens": [500],
            "total_cache_read": [200],
            "total_cache_create": [50],
            "total_cost": [1.5],
            "avg_duration_ms": [5000],
            "session_count": [3],
            "user_count": [2],
        })
        resp = client.get("/metrics/usage-trends")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1


class TestPeakTimes:
    @patch("app.transform.queries.hourly_peak")
    def test_peak(self, mock_peak, client):
        mock_peak.return_value = pd.DataFrame({
            "dow": [1], "hour": [10],
            "request_count": [50], "total_cost": [5.0], "unique_users": [3],
        })
        resp = client.get("/metrics/peak-times")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1


class TestFreshnessEndpoint:
    @patch("app.transform.queries.last_ingested_at")
    def test_freshness(self, mock_ts, client):
        mock_ts.return_value = "2026-01-15 12:00:00+00:00"
        resp = client.get("/data/freshness")
        assert resp.status_code == 200
        assert "last_ingested_at" in resp.json()


class TestToolBehaviorEndpoint:
    @patch("app.transform.queries.tool_behavior")
    def test_tool_behavior(self, mock_tb, client):
        mock_tb.return_value = pd.DataFrame({
            "tool_name": ["Read", "Bash"],
            "event_name": ["tool_decision", "tool_decision"],
            "event_count": [100, 80],
            "accept_count": [90, 70],
            "reject_count": [10, 10],
            "success_count": [0, 0],
            "failure_count": [0, 0],
            "avg_duration_ms": [None, None],
            "p95_duration_ms": [None, None],
        })
        resp = client.get("/metrics/tool-behavior")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

    @patch("app.transform.queries.tool_behavior")
    def test_tool_behavior_with_practice(self, mock_tb, client):
        mock_tb.return_value = pd.DataFrame()
        resp = client.get("/metrics/tool-behavior?practice=ML+Engineering")
        assert resp.status_code == 200
        mock_tb.assert_called_once_with(practice="ML Engineering")


class TestModelEfficiencyEndpoint:
    @patch("app.transform.queries.model_efficiency")
    def test_model_efficiency(self, mock_me, client):
        mock_me.return_value = pd.DataFrame({
            "model": ["claude-opus-4-5"],
            "request_count": [1000],
            "avg_cost": [0.05],
            "avg_duration_ms": [8000],
            "avg_output_tokens": [500],
            "total_cost": [50.0],
            "tokens_per_dollar": [10000],
            "tokens_per_sec": [62.5],
        })
        resp = client.get("/metrics/model-efficiency")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1


class TestErrorsEndpoint:
    @patch("app.transform.queries.error_summary")
    def test_errors(self, mock_es, client):
        mock_es.return_value = pd.DataFrame({
            "model": ["claude-opus-4-5"],
            "status_code": ["429"],
            "total_errors": [15],
        })
        resp = client.get("/metrics/errors")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1


class TestAnomaliesEndpoint:
    @patch("app.ml.analytics.detect_error_spikes")
    @patch("app.ml.analytics.detect_cost_anomalies")
    def test_anomalies(self, mock_cost, mock_err, client):
        mock_cost.return_value = pd.DataFrame({
            "day": ["2026-01-15"],
            "daily_cost": [200.0],
            "is_anomaly": [True],
            "upper_fence": [100.0],
        })
        mock_err.return_value = pd.DataFrame({
            "day": ["2026-01-20"],
            "error_count": [50],
            "is_spike": [True],
            "z_score": [3.5],
        })
        resp = client.get("/metrics/anomalies")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["cost_anomalies"]) == 1
        assert len(data["error_spikes"]) == 1


class TestForecastEndpoint:
    @patch("app.ml.analytics.forecast_daily_cost")
    def test_forecast(self, mock_fc, client):
        mock_fc.return_value = pd.DataFrame({
            "day": pd.date_range("2026-02-01", periods=7).date,
            "forecast_cost": [90.0] * 7,
            "lower": [70.0] * 7,
            "upper": [110.0] * 7,
        })
        resp = client.get("/metrics/forecast?periods=7")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 7


class TestLeaderboardEndpoint:
    @patch("app.transform.queries.user_leaderboard")
    def test_leaderboard(self, mock_lb, client):
        mock_lb.return_value = pd.DataFrame({
            "user_email": ["a@test.com"],
            "full_name": ["Alice Test"],
            "practice": ["ML Engineering"],
            "level": ["L5"],
            "requests": [500],
            "total_cost": [120.0],
            "total_output_tokens": [250000],
            "sessions": [50],
        })
        resp = client.get("/metrics/leaderboard?limit=10")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1


class TestKPIWithFilters:
    @patch("app.transform.queries.kpi_summary")
    def test_kpi_with_practice(self, mock_kpi, client):
        mock_kpi.return_value = {"total_requests": 500, "total_cost": 25.0}
        resp = client.get("/metrics/kpi?practice=ML+Engineering&level=L5")
        assert resp.status_code == 200
        mock_kpi.assert_called_once_with(practice="ML Engineering", level="L5")
