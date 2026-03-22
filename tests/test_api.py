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
