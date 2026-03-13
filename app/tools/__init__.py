"""Tool collection package for the finance agent."""

from app.tools.finance_tools import (
    get_stock_data,
    search_financial_news,
    search_news_with_duckduckgo,
    get_us_stock_quote,
)

# Quant agent: technical data via MCP (get_stock_data: history + indicators).
QUANT_TOOLS = [get_stock_data]

# News agent: sentiment/news only.
NEWS_TOOLS = [search_financial_news]

# Legacy single-agent bundle (quote + news via MCP).
LEGACY_TOOLS = [get_us_stock_quote, search_news_with_duckduckgo]

__all__ = [
    "get_stock_data",
    "search_financial_news",
    "search_news_with_duckduckgo",
    "get_us_stock_quote",
    "QUANT_TOOLS",
    "NEWS_TOOLS",
    "LEGACY_TOOLS",
]
