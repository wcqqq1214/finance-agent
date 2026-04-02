"""Minimal MCP server used by integration tests."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse


def _build_market_data_server() -> FastMCP:
    mcp = FastMCP("fake-market-data", json_response=True)

    @mcp.tool()
    def get_us_stock_quote(ticker: str) -> dict[str, Any]:
        normalized = ticker.strip().upper()
        base_price = 100.0 + float(len(normalized))
        return {
            "symbol": normalized,
            "currency": "USD",
            "price": base_price,
            "change": 1.5,
            "change_percent": 1.25,
            "previous_close": base_price - 1.5,
            "open": base_price - 0.75,
            "day_high": base_price + 2.0,
            "day_low": base_price - 2.0,
            "volume": 123456,
            "fifty_two_week_high": base_price + 10.0,
            "fifty_two_week_low": base_price - 10.0,
            "market_cap": 987654321,
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }

    @mcp.tool()
    def get_stock_data(ticker: str, period: str = "3mo") -> dict[str, Any]:
        normalized = ticker.strip().upper()
        return {
            "ticker": normalized,
            "last_close": 123.45,
            "sma_20": 120.0,
            "macd_line": 1.0,
            "macd_signal": 0.5,
            "macd_histogram": 0.5,
            "bb_middle": 121.0,
            "bb_upper": 125.0,
            "bb_lower": 117.0,
            "period_rows": 20,
            "period": period,
        }

    @mcp.tool()
    def get_stock_history(ticker: str, start_date: str, end_date: str) -> dict[str, Any]:
        normalized = ticker.strip().upper()
        return {
            "ticker": normalized,
            "data": [
                {
                    "date": start_date,
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.5,
                    "close": 100.5,
                    "volume": 1000,
                },
                {
                    "date": end_date,
                    "open": 101.0,
                    "high": 102.0,
                    "low": 100.5,
                    "close": 101.5,
                    "volume": 1100,
                },
            ],
        }

    return mcp


def _build_news_server() -> FastMCP:
    mcp = FastMCP("fake-news-search", json_response=True)

    @mcp.tool()
    def search_news_with_duckduckgo(query: str, limit: int = 5) -> dict[str, Any]:
        normalized = query.strip()
        return {
            "source": "duckduckgo",
            "articles": [
                {
                    "title": f"DDG article about {normalized}",
                    "url": f"https://example.com/ddg/{normalized.lower()}",
                    "source": "fake-duckduckgo",
                    "published_time": "2026-04-02T12:00:00+00:00",
                    "snippet": "Synthetic DuckDuckGo article for integration testing.",
                }
            ][:limit],
        }

    @mcp.tool()
    def search_news_with_tavily(query: str, limit: int = 5) -> dict[str, Any]:
        normalized = query.strip()
        return {
            "source": "tavily",
            "articles": [
                {
                    "title": f"Tavily article about {normalized}",
                    "url": f"https://example.com/tavily/{normalized.lower()}",
                    "source": "fake-tavily",
                    "published_time": "2026-04-02T13:00:00+00:00",
                    "snippet": "Synthetic Tavily article for integration testing.",
                }
            ][:limit],
        }

    return mcp


def build_app(server_kind: str) -> Starlette:
    """Return a Starlette app exposing fake MCP tools and health."""

    if server_kind == "market_data":
        mcp = _build_market_data_server()
    elif server_kind == "news_search":
        mcp = _build_news_server()
    else:
        raise ValueError(f"Unknown fake MCP server kind: {server_kind}")

    app = mcp.streamable_http_app()

    async def health(_request) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "server": server_kind,
                "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            }
        )

    app.add_route("/health", health, methods=["GET"])
    return app


def main() -> None:
    server_kind = sys.argv[1]
    port = int(sys.argv[2])
    uvicorn.run(build_app(server_kind), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
