"""Tests for the ML / analytics module (mocked query layer)."""

from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest


class TestForecast:
    @patch("app.transform.queries.daily_usage_trends")
    def test_forecast_returns_correct_periods(self, mock_trends):
        dates = pd.date_range("2026-01-01", periods=30, freq="D")
        mock_trends.return_value = pd.DataFrame({
            "day": dates.date,
            "total_cost": np.random.uniform(10, 50, 30),
            "total_input_tokens": np.random.randint(1000, 5000, 30),
            "total_output_tokens": np.random.randint(500, 2000, 30),
            "practice": "Platform Engineering",
            "level": "L5",
            "model": "claude-sonnet-4-5-20250929",
            "request_count": 10,
            "total_cache_read": 0,
            "total_cache_create": 0,
            "avg_duration_ms": 5000,
            "session_count": 3,
            "user_count": 2,
        })
        from app.ml.analytics import forecast_daily_cost
        result = forecast_daily_cost(periods=7)
        assert len(result) == 7
        assert "forecast_cost" in result.columns
        assert "lower" in result.columns
        assert "upper" in result.columns

    @patch("app.transform.queries.daily_usage_trends")
    def test_forecast_empty_data(self, mock_trends):
        mock_trends.return_value = pd.DataFrame()
        from app.ml.analytics import forecast_daily_cost
        result = forecast_daily_cost(periods=7)
        assert len(result) == 0


class TestAnomalyDetection:
    @patch("app.transform.queries.daily_usage_trends")
    def test_cost_anomalies(self, mock_trends):
        costs = [10.0] * 28 + [100.0, 200.0]
        dates = pd.date_range("2026-01-01", periods=30, freq="D")
        mock_trends.return_value = pd.DataFrame({
            "day": dates.date,
            "total_cost": costs,
            "total_input_tokens": 1000,
            "total_output_tokens": 500,
            "practice": "Platform Engineering",
            "level": "L5",
            "model": "claude-sonnet-4-5-20250929",
            "request_count": 10,
            "total_cache_read": 0,
            "total_cache_create": 0,
            "avg_duration_ms": 5000,
            "session_count": 3,
            "user_count": 2,
        })
        from app.ml.analytics import detect_cost_anomalies
        result = detect_cost_anomalies()
        assert "is_anomaly" in result.columns
        assert result["is_anomaly"].sum() >= 1

    @patch("app.transform.queries.error_rates_daily")
    def test_error_spikes(self, mock_errors):
        counts = [5] * 28 + [50, 100]
        dates = pd.date_range("2026-01-01", periods=30, freq="D")
        mock_errors.return_value = pd.DataFrame({
            "day": dates.date,
            "error_count": counts,
            "model": "m",
            "status_code": "500",
        })
        from app.ml.analytics import detect_error_spikes
        result = detect_error_spikes()
        assert result["is_spike"].sum() >= 1
