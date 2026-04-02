"""End-to-end integration tests for MCP process management and API wiring."""

from __future__ import annotations

import asyncio
import json
import socket
import sys
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport

import app.api.main as api_main
import app.services.redis_client as redis_client
from app.api.routes.stocks import _QUOTE_CACHE
from app.mcp_client.config import clear_mcp_server_config_cache
from app.mcp_client.connection_manager import reset_mcp_connection_manager
from app.mcp_client.finance_client import _call_search_news_async, _call_search_news_tavily_async


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def _noop_async(*_args, **_kwargs) -> None:
    return None


@pytest.fixture
def fake_mcp_config(tmp_path, monkeypatch):
    """Write a temporary config file that launches test-local MCP servers."""

    market_port = _get_free_port()
    news_port = _get_free_port()
    server_script = Path(__file__).with_name("fake_mcp_server.py")
    config_path = tmp_path / "mcp_config.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "market_data": {
                        "transport": "streamable_http",
                        "url": f"http://127.0.0.1:{market_port}/mcp",
                        "health_url": f"http://127.0.0.1:{market_port}/health",
                        "command": sys.executable,
                        "args": [str(server_script), "market_data", str(market_port)],
                        "cwd": str(Path.cwd()),
                        "heartbeat_interval_seconds": 0.1,
                        "startup_timeout_seconds": 10.0,
                        "restart_backoff_seconds": 0.1,
                    },
                    "news_search": {
                        "transport": "streamable_http",
                        "url": f"http://127.0.0.1:{news_port}/mcp",
                        "health_url": f"http://127.0.0.1:{news_port}/health",
                        "command": sys.executable,
                        "args": [str(server_script), "news_search", str(news_port)],
                        "cwd": str(Path.cwd()),
                        "heartbeat_interval_seconds": 0.1,
                        "startup_timeout_seconds": 10.0,
                        "restart_backoff_seconds": 0.1,
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("MCP_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("MCP_MARKET_DATA_URL", f"http://127.0.0.1:{market_port}/mcp")
    monkeypatch.setenv("MCP_NEWS_SEARCH_URL", f"http://127.0.0.1:{news_port}/mcp")
    clear_mcp_server_config_cache()
    reset_mcp_connection_manager()
    _QUOTE_CACHE.clear()

    yield config_path

    _QUOTE_CACHE.clear()
    reset_mcp_connection_manager()
    clear_mcp_server_config_cache()


@pytest.fixture
def quiet_api_startup(monkeypatch):
    """Disable unrelated background work so the test stays focused on MCP."""

    monkeypatch.setattr(api_main, "create_arq_pool", _noop_async)
    monkeypatch.setattr(api_main, "close_arq_pool", _noop_async)
    monkeypatch.setattr(api_main, "background_cache_warmup", _noop_async)
    monkeypatch.setattr(api_main, "background_stock_catchup", _noop_async)
    monkeypatch.setattr(api_main, "update_hot_cache_loop", _noop_async)
    monkeypatch.setattr(api_main, "init_agent_history_db", lambda _path: None)
    monkeypatch.setattr(redis_client, "get_redis_client", _noop_async)
    monkeypatch.setattr(redis_client, "ping_redis", _noop_async)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_and_mcp_servers_restart_end_to_end(fake_mcp_config, quiet_api_startup):
    """Verify API startup, MCP tool execution, and managed restart behavior."""

    if api_main.scheduler.running:
        api_main.scheduler.shutdown(wait=False)

    async with api_main.app.router.lifespan_context(api_main.app):
        transport = ASGITransport(app=api_main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            status_before = (await client.get("/api/mcp/status")).json()
            assert status_before["market_data"]["available"] is True
            assert status_before["market_data"]["tool_count"] == 3
            assert status_before["market_data"]["pid"] is not None
            assert status_before["news_search"]["available"] is True
            assert status_before["news_search"]["tool_count"] == 2

            quote_response = await client.get("/api/stocks/quotes", params={"symbols": "AAPL"})
            quote_payload = quote_response.json()
            assert quote_response.status_code == 200
            assert quote_payload["quotes"][0]["symbol"] == "AAPL"
            assert quote_payload["quotes"][0]["price"] == 104.0

            ddg_articles = await _call_search_news_async("AAPL", 1)
            tavily_articles = await _call_search_news_tavily_async("AAPL", 1)
            assert ddg_articles[0]["source"] == "fake-duckduckgo"
            assert tavily_articles[0]["source"] == "fake-tavily"

            manager = api_main.app.state.mcp_connection_manager
            market_handle = manager._get_handle("market_data")
            pid_before = market_handle.pid
            restart_count_before = market_handle.restart_count
            assert market_handle.process is not None

            market_handle.process.kill()
            market_handle.process.wait(timeout=5)
            _QUOTE_CACHE.clear()

            restart_quote = await client.get("/api/stocks/quotes", params={"symbols": "MSFT"})
            restart_payload = restart_quote.json()
            assert restart_quote.status_code == 200
            assert restart_payload["quotes"][0]["symbol"] == "MSFT"
            assert restart_payload["quotes"][0]["price"] == 104.0

            status_after = (await client.get("/api/mcp/status")).json()
            assert status_after["market_data"]["available"] is True
            assert status_after["market_data"]["restart_count"] == restart_count_before + 1
            assert status_after["market_data"]["pid"] not in (None, pid_before)

    await asyncio.sleep(0)
