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

    @patch("app.transform.queries.error_rates_daily")
    def test_no_error_spikes_when_stable(self, mock_errors):
        dates = pd.date_range("2026-01-01", periods=30, freq="D")
        mock_errors.return_value = pd.DataFrame({
            "day": dates.date,
            "error_count": [5] * 30,
            "model": "m",
            "status_code": "500",
        })
        from app.ml.analytics import detect_error_spikes
        result = detect_error_spikes()
        assert result["is_spike"].sum() == 0


class TestTokenPercentiles:
    @patch("app.transform.queries.daily_usage_trends")
    def test_token_percentiles(self, mock_trends):
        dates = pd.date_range("2026-01-01", periods=30, freq="D")
        mock_trends.return_value = pd.DataFrame({
            "day": np.tile(dates.date, 2),
            "practice": ["ML"] * 30 + ["Frontend"] * 30,
            "total_input_tokens": np.random.randint(1000, 5000, 60),
            "total_output_tokens": np.random.randint(500, 2000, 60),
            "total_cost": np.random.uniform(5, 50, 60),
            "level": "L5",
            "model": "claude-opus-4-5",
            "request_count": 10,
            "total_cache_read": 0,
            "total_cache_create": 0,
            "avg_duration_ms": 5000,
            "session_count": 3,
            "user_count": 2,
        })
        from app.ml.analytics import token_percentiles_by_practice
        result = token_percentiles_by_practice()
        assert not result.empty
        assert "50%" in result.columns or "p50" in [c.lower() for c in result.columns]


class TestCohortVariance:
    @patch("app.db.get_engine")
    def test_cohort_cost_variance(self, mock_engine):
        from unittest.mock import MagicMock

        expected_df = pd.DataFrame({
            "practice": ["ML", "Frontend"],
            "level": ["L5", "L6"],
            "users": [5, 5],
            "avg_cost": [80.0, 90.0],
            "std_cost": [15.0, 20.0],
            "min_cost": [50.0, 55.0],
            "max_cost": [110.0, 125.0],
        })

        mock_conn = MagicMock()
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch("pandas.read_sql", return_value=expected_df):
            from app.ml.analytics import cohort_cost_variance
            result = cohort_cost_variance()
            assert not result.empty
            assert "avg_cost" in result.columns
            assert "std_cost" in result.columns
