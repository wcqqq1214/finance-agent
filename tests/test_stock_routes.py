"""Tests for stock quote route caching behavior."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.api.models.schemas import StockQuote
from app.api.routes.stocks import _QUOTE_CACHE, _fetch_single_quote


@pytest.mark.asyncio
async def test_fetch_single_quote_reuses_cache_within_285_seconds():
    """Cached quote younger than 285s should be reused without upstream call."""
    cached_quote = StockQuote(symbol="AAPL", name="Apple Inc.", price=123.45)
    _QUOTE_CACHE.clear()
    _QUOTE_CACHE["AAPL"] = (cached_quote, datetime.now() - timedelta(seconds=100))

    with patch(
        "app.mcp_client.finance_client._call_get_us_stock_quote_async",
        new=AsyncMock(return_value={"price": 999.99}),
    ) as mock_fetch:
        result = await _fetch_single_quote("AAPL")

    assert result is cached_quote
    mock_fetch.assert_not_awaited()


@pytest.mark.asyncio
async def test_fetch_single_quote_refreshes_cache_after_285_seconds():
    """Cached quote older than 285s should trigger upstream refresh."""
    stale_quote = StockQuote(symbol="AAPL", name="Apple Inc.", price=100.0)
    _QUOTE_CACHE.clear()
    _QUOTE_CACHE["AAPL"] = (stale_quote, datetime.now() - timedelta(seconds=286))

    with patch(
        "app.mcp_client.finance_client._call_get_us_stock_quote_async",
        new=AsyncMock(return_value={"price": 201.0, "change": 1.5, "change_percent": 0.7}),
    ) as mock_fetch:
        result = await _fetch_single_quote("AAPL")

    assert result.price == 201.0
    assert result.timestamp is not None
    mock_fetch.assert_awaited_once()

    # Cache should be updated with fresh result.
    cached_quote, cached_time = _QUOTE_CACHE["AAPL"]
    assert cached_quote.price == 201.0
    assert cached_time.tzinfo is None
