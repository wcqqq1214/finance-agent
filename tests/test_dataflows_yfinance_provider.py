# tests/test_dataflows_yfinance_provider.py
import pytest
from datetime import datetime
from app.dataflows.providers.yfinance_provider import YFinanceProvider
from app.dataflows.models import StockCandle

@pytest.mark.asyncio
async def test_yfinance_provider_get_stock_data():
    """Test yfinance provider returns standardized StockCandle"""
    config = {}
    provider = YFinanceProvider(config)

    result = await provider.get_stock_data(
        "AAPL",
        datetime(2024, 1, 1),
        datetime(2024, 1, 31)
    )

    assert isinstance(result, list)
    assert len(result) > 0
    assert isinstance(result[0], StockCandle)
    assert result[0].symbol == "AAPL"
