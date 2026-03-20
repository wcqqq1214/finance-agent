# yfinance Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate from Polygon.io to yfinance for OHLC/quote data, fix K-line chart localization, remove logo functionality, obtain 5 years of historical data.

**Architecture:** Extend MCP market_data server with `get_stock_history` tool, update backend to use MCP client for all data fetching, add English localization to frontend chart, remove logo-related code.

**Tech Stack:** Python (yfinance, FastMCP), TypeScript/React (lightweight-charts), SQLite

---

## Task 2: Add MCP Client History Functions

**Files:**
- Modify: `app/mcp_client/finance_client.py:219` (end of file)

- [ ] **Step 1: Add async implementation function**

Append to end of file:

```python


async def _call_get_stock_history_async(
    ticker: str,
    start_date: str,
    end_date: str,
    url: str
) -> List[dict[str, Any]]:
    """Call the get_stock_history tool on the MCP server."""
    async with streamable_http_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "get_stock_history",
                arguments={
                    "ticker": ticker,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            if result.isError:
                error_msg = "Unknown MCP error"
                if result.content:
                    for part in result.content:
                        if isinstance(part, TextContent):
                            error_msg = part.text
                            break
                raise RuntimeError(f"MCP tool error: {error_msg}")
            if not result.content:
                raise RuntimeError("MCP tool returned empty content")
            text = ""
            for part in result.content:
                if isinstance(part, TextContent):
                    text = part.text
                    break
            if not text:
                raise RuntimeError("MCP tool returned no text content")
            data = json.loads(text)
            # Return the data array from response
            return data.get("data", [])


def call_get_stock_history(
    ticker: str,
    start_date: str,
    end_date: str
) -> List[dict[str, Any]]:
    """Call the MCP server's get_stock_history tool.

    Args:
        ticker: Stock symbol (e.g., AAPL, MSFT)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        List of dicts with date, open, high, low, close, volume

    Raises:
        RuntimeError: If the MCP server is unreachable or returns an error
    """
    url = os.environ.get("MCP_MARKET_DATA_URL", DEFAULT_MARKET_DATA_URL)
    return asyncio.run(_call_get_stock_history_async(ticker, start_date, end_date, url))
```

- [ ] **Step 2: Verify no syntax errors**

Run:
```bash
uv run python -c "from app.mcp_client.finance_client import call_get_stock_history; print('Import successful')"
```

Expected: "Import successful"

- [ ] **Step 3: Commit MCP client changes**

```bash
git add app/mcp_client/finance_client.py
git commit -m "feat(mcp-client): add call_get_stock_history function"
```

---

## File Structure

### Backend Files
- **Create**: None (all modifications)
- **Modify**:
  - `mcp_servers/market_data/main.py` - Add `get_stock_history` tool
  - `app/mcp_client/finance_client.py` - Add history fetch functions
  - `app/scripts/init_ohlc_data.py` - Switch to MCP client, add rate limiting
  - `app/tasks/update_ohlc.py` - Switch to MCP client
  - `app/api/routes/stocks.py` - Remove logo fetching
  - `app/api/models/schemas.py` - Make logo optional
  - `app/polygon/client.py` - Add comment about usage

### Frontend Files
- **Modify**:
  - `frontend/src/components/chart/KLineChart.tsx` - Add localization config
  - `frontend/src/lib/types.ts` - Make logo optional

### Database
- No schema changes, data re-initialization only

---

## Task 2: Add MCP Client History Functions

**Files:**
- Modify: `app/mcp_client/finance_client.py:219` (end of file)

- [ ] **Step 1: Add async implementation function**

Append to end of file:

```python


async def _call_get_stock_history_async(
    ticker: str,
    start_date: str,
    end_date: str,
    url: str
) -> List[dict[str, Any]]:
    """Call the get_stock_history tool on the MCP server."""
    async with streamable_http_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "get_stock_history",
                arguments={
                    "ticker": ticker,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            if result.isError:
                error_msg = "Unknown MCP error"
                if result.content:
                    for part in result.content:
                        if isinstance(part, TextContent):
                            error_msg = part.text
                            break
                raise RuntimeError(f"MCP tool error: {error_msg}")
            if not result.content:
                raise RuntimeError("MCP tool returned empty content")
            text = ""
            for part in result.content:
                if isinstance(part, TextContent):
                    text = part.text
                    break
            if not text:
                raise RuntimeError("MCP tool returned no text content")
            data = json.loads(text)
            # Return the data array from response
            return data.get("data", [])


def call_get_stock_history(
    ticker: str,
    start_date: str,
    end_date: str
) -> List[dict[str, Any]]:
    """Call the MCP server's get_stock_history tool.

    Args:
        ticker: Stock symbol (e.g., AAPL, MSFT)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        List of dicts with date, open, high, low, close, volume

    Raises:
        RuntimeError: If the MCP server is unreachable or returns an error
    """
    url = os.environ.get("MCP_MARKET_DATA_URL", DEFAULT_MARKET_DATA_URL)
    return asyncio.run(_call_get_stock_history_async(ticker, start_date, end_date, url))
```

- [ ] **Step 2: Verify no syntax errors**

Run:
```bash
uv run python -c "from app.mcp_client.finance_client import call_get_stock_history; print('Import successful')"
```

Expected: "Import successful"

- [ ] **Step 3: Commit MCP client changes**

```bash
git add app/mcp_client/finance_client.py
git commit -m "feat(mcp-client): add call_get_stock_history function"
```

---

## Task 1: Extend MCP Server with Historical Data Tool

**Files:**
- Modify: `mcp_servers/market_data/main.py:362` (after `get_stock_data` function)

- [ ] **Step 1: Add get_stock_history implementation function**

Insert after line 361 (after `get_stock_data` function):

```python
def _get_stock_history_impl(
    ticker: str, start_date: str, end_date: str
) -> dict[str, Any]:
    """Fetch historical OHLC data via yfinance."""
    normalized = (ticker or "").strip().upper()
    if not normalized:
        return {"ticker": "", "error": "Empty ticker."}

    try:
        t = yf.Ticker(normalized)
        hist = t.history(start=start_date, end=end_date, auto_adjust=False)

        if hist is None or hist.empty:
            return {
                "ticker": normalized,
                "data": [],
                "error": f"No data available for {normalized} in range {start_date} to {end_date}",
            }

        # Convert DataFrame to list of dicts
        data = []
        for date_idx, row in hist.iterrows():
            data.append({
                "date": date_idx.strftime("%Y-%m-%d"),
                "open": _round_or_none(float(row["Open"]), 3),
                "high": _round_or_none(float(row["High"]), 3),
                "low": _round_or_none(float(row["Low"]), 3),
                "close": _round_or_none(float(row["Close"]), 3),
                "volume": int(row["Volume"]) if pd.notna(row["Volume"]) else 0,
            })

        return {
            "ticker": normalized,
            "data": data,
        }
    except Exception as exc:
        return {
            "ticker": normalized,
            "data": [],
            "error": f"{type(exc).__name__}: {exc}",
        }
```

- [ ] **Step 2: Add MCP tool decorator**

Insert after the implementation function:

```python
@mcp.tool()
def get_stock_history(
    ticker: str, start_date: str, end_date: str
) -> dict[str, Any]:
    """Fetch historical OHLC data for a ticker over a date range.

    Use this to retrieve daily open, high, low, close, and volume data
    for backtesting, charting, or historical analysis.

    Args:
        ticker: Stock symbol (e.g., AAPL, MSFT, GOOGL)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Dict with:
        - ticker: str - The normalized ticker symbol
        - data: List[dict] - Array of OHLC records with keys:
            date, open, high, low, close, volume
        - error: str (optional) - Error message if fetch failed
    """
    return _get_stock_history_impl(ticker, start_date, end_date)
```

- [ ] **Step 3: Test MCP server starts without errors**

Run:
```bash
cd /home/wcqqq21/finance-agent
uv run python mcp_servers/market_data/main.py
```

Expected: Server starts on port 8000, no import errors

Press Ctrl+C to stop after verification.

- [ ] **Step 4: Commit MCP server changes**

```bash
git add mcp_servers/market_data/main.py
git commit -m "feat(mcp): add get_stock_history tool for OHLC data"
```

---

## Task 2: Add MCP Client History Functions

**Files:**
- Modify: `app/mcp_client/finance_client.py:219` (end of file)

- [ ] **Step 1: Add async implementation function**

Append to end of file:

```python


async def _call_get_stock_history_async(
    ticker: str,
    start_date: str,
    end_date: str,
    url: str
) -> List[dict[str, Any]]:
    """Call the get_stock_history tool on the MCP server."""
    async with streamable_http_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "get_stock_history",
                arguments={
                    "ticker": ticker,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            if result.isError:
                error_msg = "Unknown MCP error"
                if result.content:
                    for part in result.content:
                        if isinstance(part, TextContent):
                            error_msg = part.text
                            break
                raise RuntimeError(f"MCP tool error: {error_msg}")
            if not result.content:
                raise RuntimeError("MCP tool returned empty content")
            text = ""
            for part in result.content:
                if isinstance(part, TextContent):
                    text = part.text
                    break
            if not text:
                raise RuntimeError("MCP tool returned no text content")
            data = json.loads(text)
            # Return the data array from response
            return data.get("data", [])


def call_get_stock_history(
    ticker: str,
    start_date: str,
    end_date: str
) -> List[dict[str, Any]]:
    """Call the MCP server's get_stock_history tool.

    Args:
        ticker: Stock symbol (e.g., AAPL, MSFT)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        List of dicts with date, open, high, low, close, volume

    Raises:
        RuntimeError: If the MCP server is unreachable or returns an error
    """
    url = os.environ.get("MCP_MARKET_DATA_URL", DEFAULT_MARKET_DATA_URL)
    return asyncio.run(_call_get_stock_history_async(ticker, start_date, end_date, url))
```

- [ ] **Step 2: Verify no syntax errors**

Run:
```bash
uv run python -c "from app.mcp_client.finance_client import call_get_stock_history; print('Import successful')"
```

Expected: "Import successful"

- [ ] **Step 3: Commit MCP client changes**

```bash
git add app/mcp_client/finance_client.py
git commit -m "feat(mcp-client): add call_get_stock_history function"
```

---


## Task 3: Update OHLC Initialization Script

**Files:**
- Modify: `app/scripts/init_ohlc_data.py:12,23,50`

- [ ] **Step 1: Update imports**

Replace line 12:
```python
# Before
from app.polygon.client import fetch_ohlc

# After
from app.mcp_client.finance_client import call_get_stock_history
import time
```

- [ ] **Step 2: Update data fetching logic**

Replace lines 49-54 (inside the for loop):
```python
# Before
data = fetch_ohlc(symbol, start_date.isoformat(), end_date.isoformat())

# After
data = call_get_stock_history(symbol, start_date.isoformat(), end_date.isoformat())

# Add rate limiting delay (respectful to Yahoo Finance)
if i < len(SYMBOLS):  # Don't sleep after last symbol
    time.sleep(0.5)
```

- [ ] **Step 3: Test import**

Run:
```bash
uv run python -c "from app.scripts.init_ohlc_data import main; print('Import successful')"
```

Expected: "Import successful"

- [ ] **Step 4: Commit initialization script changes**

```bash
git add app/scripts/init_ohlc_data.py
git commit -m "feat(init): switch to MCP client for OHLC data fetching"
```

---

## Task 4: Update OHLC Update Task

**Files:**
- Modify: `app/tasks/update_ohlc.py`

- [ ] **Step 1: Read current file to understand structure**

Run:
```bash
cat app/tasks/update_ohlc.py
```

- [ ] **Step 2: Update imports**

Replace Polygon import with MCP client:
```python
# Before
from app.polygon.client import fetch_ohlc

# After
from app.mcp_client.finance_client import call_get_stock_history
```

- [ ] **Step 3: Update fetch logic**

Find the line calling `fetch_ohlc` and replace with:
```python
# Before
data = fetch_ohlc(symbol, start_date, end_date)

# After
data = call_get_stock_history(symbol, start_date, end_date)
```

- [ ] **Step 4: Test import**

Run:
```bash
uv run python -c "from app.tasks.update_ohlc import update_ohlc_task; print('Import successful')"
```

Expected: "Import successful"

- [ ] **Step 5: Commit update task changes**

```bash
git add app/tasks/update_ohlc.py
git commit -m "feat(tasks): switch to MCP client for OHLC updates"
```

---


## Task 5: Fix K-Line Chart Localization

**Files:**
- Modify: `frontend/src/components/chart/KLineChart.tsx:95`

- [ ] **Step 1: Add localization config to chart**

Find line 95 (the `createChart` call) and add `localization` property:

```typescript
// Before (line 95-113)
const chart = createChart(chartContainerRef.current, {
  width: chartContainerRef.current.clientWidth,
  height: 400,
  layout: {
    background: { color: 'transparent' },
    textColor: '#d1d5db',
  },
  // ... rest

// After
const chart = createChart(chartContainerRef.current, {
  width: chartContainerRef.current.clientWidth,
  height: 400,
  localization: {
    locale: 'en-US',
    dateFormat: 'yyyy-MM-dd',
  },
  layout: {
    background: { color: 'transparent' },
    textColor: '#d1d5db',
  },
  // ... rest
```

- [ ] **Step 2: Verify TypeScript compiles**

Run:
```bash
cd frontend && npm run build
```

Expected: Build succeeds with no errors

- [ ] **Step 3: Commit frontend localization fix**

```bash
git add frontend/src/components/chart/KLineChart.tsx
git commit -m "fix(chart): force English localization for K-line chart"
```

---

## Task 6: Remove Logo Fetching (Keep Logo Field)

**Files:**
- Modify: `app/api/routes/stocks.py:31,45`

**Note:** Keep logo field in schema for future manual import. Only remove automatic fetching from Polygon.

- [ ] **Step 1: Remove logo fetching in stocks route**

In `app/api/routes/stocks.py`:
- Remove import on line 31: `from app.polygon.client import fetch_ticker_details`
- Remove lines 44-45 (logo fetching):
```python
# Remove these lines
logo = await asyncio.to_thread(fetch_ticker_details, symbol)
```
- Update StockQuote creation (set logo to None):
```python
quote = StockQuote(
    symbol=symbol,
    name=name,
    price=data.get("price"),
    change=data.get("change"),
    change_percent=data.get("change_percent"),
    logo=None,  # No longer auto-fetching, can be set manually later
    timestamp=datetime.now(timezone.utc).isoformat(),
)
```

- [ ] **Step 2: Test backend imports**

Run:
```bash
uv run python -c "from app.api.models.schemas import StockQuote; from app.api.routes.stocks import router; print('Import successful')"
```

Expected: "Import successful"

- [ ] **Step 3: Commit logo fetching removal**

```bash
git add app/api/routes/stocks.py
git commit -m "refactor: remove automatic logo fetching from Polygon

Logo field retained in schema for future manual import"
```

---


## Task 7: Add Documentation Comments

**Files:**
- Modify: `app/polygon/client.py:1`

- [ ] **Step 1: Add usage comment to Polygon client**

Add comment at top of file after docstring:

```python
"""Polygon API client with strict rate limiting.

This module provides functions to fetch OHLC and news data from Polygon.io
with built-in rate limiting to respect the free tier limit of 5 requests/minute.

NOTE: As of 2026-03-20, only fetch_news() is actively used.
OHLC data fetching has been migrated to yfinance via MCP server.
"""
```

- [ ] **Step 2: Commit documentation**

```bash
git add app/polygon/client.py
git commit -m "docs: clarify Polygon client usage (news only)"
```

---

## Task 8: Database Re-initialization

**Files:**
- Database: `app/data/finance.db`

- [ ] **Step 1: Ensure MCP server is running**

Start MCP server in background:
```bash
cd /home/wcqqq21/finance-agent
uv run python mcp_servers/market_data/main.py &
MCP_PID=$!
echo "MCP server PID: $MCP_PID"
```

Wait 5 seconds for server to start.

- [ ] **Step 2: Stop backend server if running**

```bash
pkill -f "uvicorn app.api.main:app" || true
```

- [ ] **Step 3: Backup existing database**

```bash
cp app/data/finance.db app/data/finance.db.polygon-backup-$(date +%Y%m%d)
ls -lh app/data/finance.db*
```

Expected: Backup file created

- [ ] **Step 4: Clear existing OHLC data**

```bash
uv run python -c "from app.database import get_conn; conn = get_conn(); conn.execute('DELETE FROM ohlc'); conn.execute('DELETE FROM metadata'); conn.commit(); print(f'Cleared {conn.total_changes} records'); conn.close()"
```

Expected: "Cleared X records"

- [ ] **Step 5: Run initialization script**

```bash
uv run python -m app.scripts.init_ohlc_data
```

Expected: 
- Fetches 7 symbols
- Each symbol: ~1,260 records
- Total: ~8,820 records
- Completes in < 5 minutes

- [ ] **Step 6: Verify data quality**

```bash
uv run python -c "from app.database import get_conn; conn = get_conn(); result = conn.execute('SELECT symbol, COUNT(*) as cnt, MIN(date) as earliest, MAX(date) as latest FROM ohlc GROUP BY symbol').fetchall(); print('\\n'.join([f\"{r['symbol']}: {r['cnt']} records, {r['earliest']} to {r['latest']}\" for r in result])); conn.close()"
```

Expected output (approximately):
```
AAPL: 1260 records, 2021-03-22 to 2026-03-19
MSFT: 1260 records, 2021-03-22 to 2026-03-19
GOOGL: 1260 records, 2021-03-22 to 2026-03-19
AMZN: 1260 records, 2021-03-22 to 2026-03-19
NVDA: 1260 records, 2021-03-22 to 2026-03-19
META: 1260 records, 2021-03-22 to 2026-03-19
TSLA: 1260 records, 2021-03-22 to 2026-03-19
```

- [ ] **Step 7: Check database size**

```bash
ls -lh app/data/finance.db
```

Expected: < 50MB

- [ ] **Step 8: Stop MCP server**

```bash
kill $MCP_PID
```

- [ ] **Step 9: Commit database re-initialization note**

```bash
git add -A
git commit -m "data: re-initialize OHLC with 5 years of yfinance data" --allow-empty
```

---


## Task 9: Integration Testing

**Files:**
- N/A (testing only)

- [ ] **Step 1: Start MCP server**

```bash
cd /home/wcqqq21/finance-agent
uv run python mcp_servers/market_data/main.py &
MCP_PID=$!
sleep 3
```

- [ ] **Step 2: Start backend server**

```bash
uv run uvicorn app.api.main:app --port 8080 &
BACKEND_PID=$!
sleep 3
```

- [ ] **Step 3: Test stock quotes API (no logo)**

```bash
curl -s http://localhost:8080/api/stocks/quotes?symbols=AAPL | python -m json.tool
```

Expected: JSON response with AAPL quote, no "logo" field

- [ ] **Step 4: Test OHLC API (5 years of data)**

```bash
curl -s "http://localhost:8080/api/AAPL/ohlc?start=2021-03-20&end=2026-03-20" | python -c "import sys, json; data=json.load(sys.stdin); print(f\"Symbol: {data['symbol']}, Records: {len(data['data'])}, First: {data['data'][0]['date']}, Last: {data['data'][-1]['date']}\")"
```

Expected: "Symbol: AAPL, Records: ~1260, First: 2021-03-22, Last: 2026-03-19"

- [ ] **Step 5: Test OHLC API response time**

```bash
time curl -s "http://localhost:8080/api/AAPL/ohlc?start=2021-03-20&end=2026-03-20" > /dev/null
```

Expected: < 500ms

- [ ] **Step 6: Start frontend dev server**

```bash
cd frontend
npm run dev &
FRONTEND_PID=$!
sleep 5
```

- [ ] **Step 7: Manual frontend testing**

Open browser to http://localhost:3000

Test checklist:
- [ ] K-line chart displays English dates (set browser locale to zh-CN to verify)
- [ ] Chart tooltip shows "yyyy-MM-dd" format
- [ ] Stock cards display without logo (shows fallback)
- [ ] Select AAPL → chart loads with 5 years of data
- [ ] Chart zoom and pan work correctly
- [ ] Select different stocks sequentially - all load correctly
- [ ] No console errors related to missing logo

- [ ] **Step 8: Stop all servers**

```bash
kill $MCP_PID $BACKEND_PID $FRONTEND_PID
```

- [ ] **Step 9: Create integration test summary**

Document test results in commit message or separate file.

---

## Task 10: Final Verification and Cleanup

**Files:**
- N/A (verification only)

- [ ] **Step 1: Verify all commits are present**

```bash
git log --oneline --since="2026-03-20" | head -10
```

Expected commits:
1. feat(mcp): add get_stock_history tool for OHLC data
2. feat(mcp-client): add call_get_stock_history function
3. feat(init): switch to MCP client for OHLC data fetching
4. feat(tasks): switch to MCP client for OHLC updates
5. fix(chart): force English localization for K-line chart
6. refactor: remove logo fetching functionality
7. docs: clarify Polygon client usage (news only)
8. data: re-initialize OHLC with 5 years of yfinance data

- [ ] **Step 2: Run full test suite (if exists)**

```bash
cd /home/wcqqq21/finance-agent
uv run pytest tests/ -v
```

Expected: All tests pass (or skip if no tests exist)

- [ ] **Step 3: Check for any remaining Polygon OHLC references**

```bash
grep -r "fetch_ohlc" app/ --exclude-dir=__pycache__ | grep -v "# Before" | grep -v ".pyc"
```

Expected: Only references in `app/polygon/client.py` (the function definition)

- [ ] **Step 4: Verify success criteria**

Review checklist:
- [ ] K-line chart displays English dates only (verified in zh-CN locale)
- [ ] Database contains 5 years of OHLC data (2021-2026)
- [ ] Each symbol has ~1,260 trading day records
- [ ] Stock quotes display correctly without logos
- [ ] All 7 stocks load successfully
- [ ] No Polygon API calls for OHLC or quotes
- [ ] Polygon news functionality unchanged (not tested, assumed working)
- [ ] No regressions in existing features
- [ ] Initialization completes in < 5 minutes
- [ ] OHLC API responds in < 500ms for 5-year range
- [ ] Database size < 50MB after initialization

- [ ] **Step 5: Create final summary commit**

```bash
git add -A
git commit -m "chore: complete yfinance migration

- Migrated OHLC data from Polygon to yfinance via MCP
- Fixed K-line chart to display English dates
- Removed logo fetching functionality
- Database now contains 5 years of historical data
- All integration tests passing" --allow-empty
```

- [ ] **Step 6: Push to remote (if applicable)**

```bash
git push origin wcq
```

---

## Rollback Procedure

If any issues arise during implementation:

### Quick Rollback (< 5 minutes)

```bash
# Restore code
git checkout HEAD~8 -- app/ mcp_servers/ frontend/

# Restore database
cp app/data/finance.db.polygon-backup-YYYYMMDD app/data/finance.db

# Restart servers
pkill -f "uvicorn\|python mcp_servers"
```

### Partial Rollback

Keep frontend localization fix (independent):
```bash
git checkout HEAD -- frontend/src/components/chart/KLineChart.tsx
```

Revert backend changes only:
```bash
git checkout HEAD~7 -- app/ mcp_servers/
```

---

## Success Criteria Summary

✅ All tasks completed
✅ K-line chart displays English dates
✅ 5 years of OHLC data in database
✅ Stock quotes work without logos
✅ All 7 stocks load successfully
✅ Performance targets met
✅ No regressions
✅ All commits pushed

---

## Notes

- MCP server must be running for backend to function
- Rate limiting (0.5s delay) prevents Yahoo Finance blocks
- Frontend already handles missing logos gracefully
- Polygon client retained for news functionality only

