"""Tests for crypto K-lines API endpoint."""

from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_cold_data():
    """Mock cold data from database."""
    return [
        {
            "symbol": "BTCUSDT",
            "timestamp": 1000,
            "date": "2024-01-01T00:00:00+00:00",
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "volume": 1000.0,
            "bar": "1m",
        }
    ]


@pytest.fixture
def mock_hot_data():
    """Mock hot data from cache as DataFrame."""
    return pd.DataFrame(
        [
            {
                "timestamp": 2000,
                "date": "2024-01-01T00:01:00+00:00",
                "open": 100.5,
                "high": 102.0,
                "low": 100.0,
                "close": 101.5,
                "volume": 1100.0,
            }
        ]
    )


class TestCryptoKlinesEndpoint:
    """Tests for /api/crypto/klines endpoint."""

    def test_get_klines_merges_cold_and_hot_data(self, mock_cold_data, mock_hot_data):
        """测试合并冷热数据"""
        from app.api.main import app

        with patch("app.api.routes.crypto_klines.get_crypto_ohlc") as mock_cold:
            with patch("app.api.routes.crypto_klines.get_hot_cache") as mock_hot:
                mock_cold.return_value = mock_cold_data
                mock_hot.return_value = mock_hot_data

                client = TestClient(app)
                response = client.get("/api/crypto/klines?symbol=BTCUSDT&interval=1d")

                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                assert data[0]["timestamp"] == 1000
                assert data[1]["timestamp"] == 2000
                assert mock_cold.call_args.kwargs["bar"] == "1d"

    def test_get_klines_deduplicates_overlapping_data(self):
        """测试去重重叠数据（冷仓占优）"""
        from app.api.main import app

        cold_data = [
            {
                "symbol": "BTCUSDT",
                "timestamp": 1000,
                "date": "2024-01-01T00:00:00+00:00",
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1000.0,
                "bar": "1m",
            }
        ]
        hot_data = pd.DataFrame(
            [
                {
                    "timestamp": 1000,
                    "date": "2024-01-01T00:00:00+00:00",
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 102.0,
                    "volume": 1000.0,
                }  # Same timestamp, different close
            ]
        )

        with patch("app.api.routes.crypto_klines.get_crypto_ohlc") as mock_cold:
            with patch("app.api.routes.crypto_klines.get_hot_cache") as mock_hot:
                mock_cold.return_value = cold_data
                mock_hot.return_value = hot_data

                client = TestClient(app)
                response = client.get("/api/crypto/klines?symbol=BTCUSDT&interval=1d")

                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["close"] == 100.5  # Cold data wins on overlap

    def test_get_klines_requires_symbol_and_interval(self):
        """测试必需参数"""
        from app.api.main import app

        client = TestClient(app)
        response = client.get("/api/crypto/klines")

        assert response.status_code == 422  # Validation error

    def test_get_klines_supports_date_range(self):
        """测试日期范围过滤"""
        from app.api.main import app

        with patch("app.api.routes.crypto_klines.get_crypto_ohlc") as mock_cold:
            with patch("app.api.routes.crypto_klines.get_hot_cache") as mock_hot:
                mock_cold.return_value = []
                mock_hot.return_value = pd.DataFrame()

                client = TestClient(app)
                response = client.get(
                    "/api/crypto/klines?symbol=BTCUSDT&interval=1d&start=2024-01-01T00:00:00Z&end=2024-01-02T00:00:00Z"
                )

                assert response.status_code == 200
                # Verify cold data was queried with date range
                mock_cold.assert_called_once()
                call_args = mock_cold.call_args
                assert call_args[1]["start"] == "2024-01-01T00:00:00Z"
                assert call_args[1]["end"] == "2024-01-02T00:00:00Z"

    def test_get_klines_rejects_unsupported_interval(self):
        """Unsupported public intervals return 400 with an invalid interval detail."""
        from app.api.main import app

        client = TestClient(app)
        response = client.get("/api/crypto/klines?symbol=BTCUSDT&interval=1m")

        assert response.status_code == 400
        payload = response.json()
        assert isinstance(payload, dict)
        assert payload.get("detail", "").startswith("Invalid interval")

    def test_get_klines_supports_intraday_interval(self, mock_cold_data, mock_hot_data):
        """15m 请求映射到 source bar=1m 并调用聚合器"""
        from app.api.main import app

        with patch("app.api.routes.crypto_klines.aggregate_ohlc") as mock_aggregate:
            mock_aggregate.return_value = [
                mock_cold_data[0],
                mock_hot_data.iloc[0].to_dict(),
            ]
            with patch("app.api.routes.crypto_klines.get_crypto_ohlc") as mock_cold:
                with patch("app.api.routes.crypto_klines.get_hot_cache") as mock_hot:
                    mock_cold.return_value = mock_cold_data
                    mock_hot.return_value = mock_hot_data

                    client = TestClient(app)
                    response = client.get("/api/crypto/klines?symbol=BTCUSDT&interval=15m")

                    assert response.status_code == 200
                    mock_cold.assert_called_once()
                    assert mock_cold.call_args.kwargs["bar"] == "1m"
                    mock_aggregate.assert_called_once()
                    assert mock_aggregate.call_args[0][1] == "15m"
