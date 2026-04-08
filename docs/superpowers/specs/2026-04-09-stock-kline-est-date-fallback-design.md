# Stock K-Line EST Fallback Design

## Problem

Stock K-line charts are missing the latest daily candle when the local database lags behind the current US trading date. On April 9, 2026 at 00:06 UTC+8, the correct latest daily stock candle should be April 8, 2026 in America/New_York. The current system returned April 7, 2026 because:

- `app.services.stock_updater` relies on `yfinance`, which is rate-limited in this environment.
- `/api/stocks/{symbol}/ohlc` only reads persisted database rows and has no read-time freshness fallback.

Upstream MCP market-data history is still able to fetch April 8, 2026 data, so the defect is local update/read-path behavior rather than source availability.

## Goals

- Define the latest expected stock daily candle using America/New_York, regardless of the user's browser timezone.
- Remove the intraday stock updater's dependency on `yfinance` for daily refreshes.
- Add a lightweight route-level fallback so the stock OHLC endpoint can return the latest expected daily candle even if scheduled persistence has not caught up yet.
- Add regression coverage for EST date-boundary logic and fallback response merging.

## Non-Goals

- No frontend rendering redesign.
- No crypto OHLC route changes.
- No broader data vendor abstraction refactor.

## Chosen Approach

Use a hybrid fix:

1. Replace the stock updater's daily-fetch path with the existing MCP `call_get_stock_history` client.
2. Add a stock OHLC route helper that compares the latest persisted stock row against the current market date in America/New_York.
3. When the database lags, fetch a narrow MCP history window, merge in newer rows, and return the combined response. Persisting the fetched rows in the route is acceptable because the route is healing a stale cache/database condition rather than creating a separate derived view.

This fixes the root cause and keeps the chart resilient when background scheduling fails intermittently.

## Data Freshness Rule

- The authoritative "current stock date" is `datetime.now(ZoneInfo("America/New_York")).date()`.
- A daily stock OHLC response is fresh when its latest row date is greater than or equal to that market date, or when the market date is a non-trading day and the latest persisted trading date is already the most recent available market session.
- For this bugfix, the route fallback should only trigger when the database is strictly behind the current America/New_York calendar date and the MCP fetch returns newer daily rows.

## Component Changes

### `app/services/stock_updater.py`

- Add a small MCP-backed helper for recent stock daily history.
- Reuse it in the intraday update path instead of `yfinance`.
- Preserve existing DB overwrite semantics so the current day row can be refreshed repeatedly.

### `app/api/routes/ohlc.py`

- Add helpers to:
  - compute the current market date in America/New_York,
  - detect the latest persisted row date,
  - fetch newer rows from MCP when needed,
  - merge persisted and fallback rows without duplicates.
- Keep the existing route contract and response shape unchanged.

### Tests

- Add stock updater coverage proving the MCP helper is used and returns normalized daily rows.
- Add OHLC route coverage proving:
  - EST date calculation uses America/New_York rather than local timezone,
  - stale DB data is healed by fetching a newer row,
  - duplicate dates are not returned twice.

## Error Handling

- If the route fallback fetch fails, return the persisted DB result instead of failing the whole request.
- If the updater MCP fetch fails, log the error and keep existing failure semantics.
- The fallback must never hide a real 404 when neither DB nor MCP returns any rows.

## Verification

- Run focused pytest coverage for stock updater and stock OHLC route regression tests.
- Run scoped Ruff checks/format checks through the repo workflow helper.
