# Stock Data Startup Catch-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically fill stock data gaps when API server restarts after downtime

**Architecture:** Non-blocking background task on startup checks database metadata, detects gaps, and fetches missing data with rate limiting to avoid Yahoo Finance bans. Follows same pattern as crypto hot cache warmup.

**Tech Stack:** FastAPI, asyncio, yfinance, SQLite, APScheduler

---

## File Structure

**Modified Files:**
- `app/config_manager.py` - Add stock catchup configuration
- `app/services/stock_updater.py` - Add catchup logic and force mode
- `app/api/main.py` - Integrate catchup task into startup
- `.env.example` - Document new environment variables

**New Files:**
- `tests/test_stock_catchup.py` - Unit tests for catchup mechanism

---

## Task 1: Add Configuration Management

**Files:**
- Modify: `app/config_manager.py`
- Modify: `.env.example`
- Test: Manual verification

- [ ] **Step 1: Read existing config_manager.py**

Read the file to understand current structure and patterns.

```bash
# Read the file
cat app/config_manager.py
```

- [ ] **Step 2: Add get_stock_catchup_config() method**

Add this method to `app/config_manager.py`:

```python
def get_stock_catchup_config() -> dict:
    """Get stock catch-up configuration from environment variables.
    
    Returns:
        dict with keys:
            - catchup_days: int - Maximum days to look back
            - rate_limit_delay: float - Delay between requests in seconds
            - enabled: bool - Whether catch-up is enabled
    """
    return {
        "catchup_days": int(os.getenv("STOCK_CATCHUP_DAYS", "5")),
        "rate_limit_delay": float(os.getenv("STOCK_RATE_LIMIT_DELAY", "1.5")),
        "enabled": os.getenv("STOCK_CATCHUP_ENABLED", "true").lower() == "true"
    }
```

- [ ] **Step 3: Add environment variables to .env.example**

Append to `.env.example`:

```bash
# Stock catch-up configuration
STOCK_CATCHUP_ENABLED=true
STOCK_CATCHUP_DAYS=5
STOCK_RATE_LIMIT_DELAY=1.5
```

- [ ] **Step 4: Verify configuration loads correctly**

Test in Python REPL:

```bash
uv run python -c "from app.config_manager import get_stock_catchup_config; import json; print(json.dumps(get_stock_catchup_config(), indent=2))"
```

Expected output:
```json
{
  "catchup_days": 5,
  "rate_limit_delay": 1.5,
  "enabled": true
}
```

- [ ] **Step 5: Commit configuration changes**

```bash
git add app/config_manager.py .env.example
git commit -m "feat: add stock catchup configuration"
```

## Task 2: Add Force Mode to Stock Updater

**Files:**
- Modify: `app/services/stock_updater.py`
- Test: Manual verification

- [ ] **Step 1: Read current update_stocks_intraday implementation**

```bash
# Read the function
grep -A 10 "async def update_stocks_intraday" app/services/stock_updater.py
```

- [ ] **Step 2: Modify update_stocks_intraday to support force parameter**

Update the function in `app/services/stock_updater.py`:

```python
async def update_stocks_intraday(force: bool = False) -> None:
    """Async wrapper for the intraday stock update.
    
    Args:
        force: If True, bypass trading hours check and update anyway
    """
    if not force and not should_update_stocks():
        logger.info("Skipping update: outside trading hours or holiday")
        return
        
    try:
        await asyncio.to_thread(update_stocks_intraday_sync)
    except Exception as exc:
        logger.error(f"Intraday update failed: {exc}", exc_info=True)
```

- [ ] **Step 3: Test force=False behavior (should skip outside trading hours)**

```bash
uv run python -c "
import asyncio
from app.services.stock_updater import update_stocks_intraday

async def test():
    await update_stocks_intraday(force=False)
    print('✓ Force=False test completed')

asyncio.run(test())
"
```

Expected: Log message "Skipping update: outside trading hours or holiday"

- [ ] **Step 4: Test force=True behavior (should bypass check)**

```bash
uv run python -c "
import asyncio
from app.services.stock_updater import update_stocks_intraday

async def test():
    await update_stocks_intraday(force=True)
    print('✓ Force=True test completed')

asyncio.run(test())
"
```

Expected: Attempts to fetch data (may fail due to rate limit, but should not skip)

- [ ] **Step 5: Commit force mode changes**

```bash
git add app/services/stock_updater.py
git commit -m "feat: add force parameter to bypass trading hours check"
```

## Task 3: Add Rate-Limited Fetch Function

**Files:**
- Modify: `app/services/stock_updater.py`
- Test: Manual verification

- [ ] **Step 1: Add _fetch_with_rate_limit function**

Add this function to `app/services/stock_updater.py` (before `update_stocks_intraday`):

```python
async def _fetch_with_rate_limit(
    symbols: List[str], 
    days: int, 
    delay: float
) -> Dict[str, List[Dict]]:
    """Fetch stock data with rate limiting to avoid Yahoo Finance ban.
    
    Args:
        symbols: List of stock symbols
        days: Number of days to fetch
        delay: Delay between requests in seconds
        
    Returns:
        Dict mapping symbol to list of OHLC records
    """
    result = {}
    
    for i, symbol in enumerate(symbols):
        try:
            # Add delay between requests (except first one)
            if i > 0:
                await asyncio.sleep(delay)
            
            # Fetch data for single symbol
            data = await asyncio.to_thread(
                fetch_recent_ohlc, 
                [symbol], 
                days
            )
            
            if symbol in data:
                result[symbol] = data[symbol]
                logger.debug(f"Fetched {len(data[symbol])} records for {symbol}")
            else:
                logger.warning(f"No data returned for {symbol}")
                
        except Exception as exc:
            logger.error(f"Failed to fetch {symbol}: {exc}")
            continue
    
    return result
```

- [ ] **Step 2: Verify imports are present**

Check that these imports exist at the top of `app/services/stock_updater.py`:

```python
from typing import Dict, List
```

If missing, add them.

- [ ] **Step 3: Test rate limiting with 2 symbols**

```bash
uv run python -c "
import asyncio
from app.services.stock_updater import _fetch_with_rate_limit
from datetime import datetime

async def test():
    start = datetime.now()
    result = await _fetch_with_rate_limit(['AAPL', 'MSFT'], days=2, delay=1.5)
    elapsed = (datetime.now() - start).total_seconds()
    
    print(f'Fetched {len(result)} symbols in {elapsed:.1f}s')
    print(f'Expected delay: ~1.5s, Actual: {elapsed:.1f}s')
    assert elapsed >= 1.5, 'Rate limiting not working'
    print('✓ Rate limiting verified')

asyncio.run(test())
"
```

Expected: Takes at least 1.5 seconds (delay between 2 symbols)

- [ ] **Step 4: Commit rate-limited fetch function**

```bash
git add app/services/stock_updater.py
git commit -m "feat: add rate-limited stock data fetcher"
```

## Task 4: Add Main Catchup Function

**Files:**
- Modify: `app/services/stock_updater.py`
- Test: Manual verification

- [ ] **Step 1: Add catchup_historical_stocks function**

Add this function to `app/services/stock_updater.py` (after `_fetch_with_rate_limit`):

```python
async def catchup_historical_stocks(days: int) -> dict:
    """Catch up missing historical stock data on startup.
    
    Args:
        days: Maximum number of days to look back
        
    Returns:
        Statistics dict with keys:
            - symbols_updated: int
            - records_added: int
            - date_range: tuple (start_date, end_date) or None
            - errors: list of error messages
    """
    from datetime import date, datetime
    from app.database.ohlc import get_metadata, upsert_ohlc_overwrite, update_metadata
    from app.config_manager import get_stock_catchup_config
    
    logger.info(f"Starting stock catch-up (max {days} days)...")
    
    # Check last update date from metadata
    # Use AAPL as sentinel - assumes all symbols are updated together
    # Trade-off: Fast startup vs. handling symbols added at different times
    metadata = get_metadata("AAPL")
    
    if metadata is None:
        logger.info(f"No metadata found, fetching last {days} days")
        fetch_days = days
    else:
        last_date = datetime.fromisoformat(metadata["data_end"]).date()
        today = date.today()
        gap_days = (today - last_date).days
        
        if gap_days <= 1:
            logger.info(f"Stock data is up to date (last: {last_date})")
            return {
                "symbols_updated": 0,
                "records_added": 0,
                "date_range": None,
                "errors": []
            }
        
        fetch_days = min(gap_days, days)
        logger.info(f"Gap detected: {gap_days} days, fetching last {fetch_days} days")
    
    # Fetch with rate limiting
    config = get_stock_catchup_config()
    data_by_symbol = await _fetch_with_rate_limit(
        SYMBOLS, 
        fetch_days, 
        config["rate_limit_delay"]
    )
    
    # Save to database
    stats = {
        "symbols_updated": 0,
        "records_added": 0,
        "date_range": None,
        "errors": []
    }
    
    for symbol, records in data_by_symbol.items():
        try:
            if records:
                upsert_ohlc_overwrite(symbol, records)
                dates = [r["date"] for r in records]
                update_metadata(symbol, min(dates), max(dates))
                stats["symbols_updated"] += 1
                stats["records_added"] += len(records)
                
                if stats["date_range"] is None:
                    stats["date_range"] = (min(dates), max(dates))
                    
                logger.info(f"✓ {symbol}: {len(records)} records | Latest: {records[-1]['date']}")
        except Exception as exc:
            error_msg = f"{symbol}: {exc}"
            stats["errors"].append(error_msg)
            logger.error(f"Failed to save {symbol}: {exc}")
    
    logger.info(f"✓ Catch-up completed: {stats['symbols_updated']}/{len(SYMBOLS)} symbols updated")
    return stats
```

- [ ] **Step 2: Test catchup with current database**

```bash
uv run python -c "
import asyncio
from app.services.stock_updater import catchup_historical_stocks

async def test():
    stats = await catchup_historical_stocks(days=5)
    print(f'Catchup stats: {stats}')
    print('✓ Catchup function works')

asyncio.run(test())
"
```

Expected: Returns statistics dict (may show "up to date" if data is current)

- [ ] **Step 3: Commit catchup function**

```bash
git add app/services/stock_updater.py
git commit -m "feat: add historical stock data catchup function"
```

## Task 5: Integrate Catchup into API Startup

**Files:**
- Modify: `app/api/main.py`
- Test: API restart verification

- [ ] **Step 1: Add background_stock_catchup function**

Add this function to `app/api/main.py` (after `background_cache_warmup`):

```python
async def background_stock_catchup():
    """Background task for stock data catch-up on startup."""
    from app.config_manager import get_stock_catchup_config
    from app.services.stock_updater import catchup_historical_stocks
    
    try:
        config = get_stock_catchup_config()
        if not config["enabled"]:
            logger.info("Stock catchup disabled by config")
            return
            
        logger.info(f"Starting stock catchup (max {config['catchup_days']} days)...")
        stats = await catchup_historical_stocks(days=config["catchup_days"])
        
        if stats["symbols_updated"] > 0:
            logger.info(
                f"✓ Stock catchup completed: {stats['symbols_updated']} symbols, "
                f"{stats['records_added']} records, range: {stats['date_range']}"
            )
        
        if stats["errors"]:
            logger.warning(f"Catchup errors: {stats['errors']}")
            
    except Exception as exc:
        logger.error(f"✗ Stock catchup failed: {exc}", exc_info=True)
```

- [ ] **Step 2: Add catchup task to lifespan startup**

In the `lifespan` function, after the `update_task` line, add:

```python
    # Start stock catchup as non-blocking background task
    catchup_task = asyncio.create_task(background_stock_catchup())
    logger.info("✓ Stock catchup started in background (non-blocking)")
```

- [ ] **Step 3: Add catchup task cancellation to lifespan shutdown**

In the `lifespan` function shutdown section, after the `update_task.cancel()` block, add:

```python
    # Cancel catchup task if still running
    if not catchup_task.done():
        logger.info("Cancelling stock catchup task...")
        catchup_task.cancel()
        try:
            await catchup_task
        except asyncio.CancelledError:
            logger.info("✓ Stock catchup task cancelled")
```

- [ ] **Step 4: Restart API and verify catchup runs**

```bash
# Stop API
pkill -f "uvicorn app.api.main:app"

# Start API
nohup uv run uvicorn app.api.main:app --host 0.0.0.0 --port 8080 > /tmp/api.log 2>&1 &

# Wait for startup
sleep 10

# Check logs for catchup
tail -50 /tmp/api.log | grep -i "stock catchup"
```

Expected logs:
```
INFO: Starting stock catchup (max 5 days)...
INFO: Stock data is up to date (last: 2026-03-26)
```
or
```
INFO: Gap detected: 3 days, fetching last 3 days
INFO: ✓ Stock catchup completed: 7 symbols, 21 records, range: ('2026-03-23', '2026-03-26')
```

- [ ] **Step 5: Commit API integration**

```bash
git add app/api/main.py
git commit -m "feat: integrate stock catchup into API startup"
```

## Task 6: Add Unit Tests

**Files:**
- Create: `tests/test_stock_catchup.py`
- Test: Run pytest

- [ ] **Step 1: Create test file with basic structure**

Create `tests/test_stock_catchup.py`:

```python
"""Unit tests for stock catchup mechanism."""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import date, datetime, timedelta


@pytest.fixture
def mock_metadata_current():
    """Mock metadata showing current data."""
    yesterday = date.today() - timedelta(days=1)
    return {
        "symbol": "AAPL",
        "last_update": datetime.now().isoformat(),
        "data_start": "2021-01-01",
        "data_end": yesterday.isoformat()
    }


@pytest.fixture
def mock_metadata_gap():
    """Mock metadata showing 3-day gap."""
    three_days_ago = date.today() - timedelta(days=3)
    return {
        "symbol": "AAPL",
        "last_update": datetime.now().isoformat(),
        "data_start": "2021-01-01",
        "data_end": three_days_ago.isoformat()
    }


@pytest.fixture
def mock_stock_data():
    """Mock stock OHLC data."""
    return {
        "AAPL": [
            {"date": "2026-03-24", "open": 180.0, "high": 182.0, "low": 179.0, "close": 181.0, "volume": 1000000},
            {"date": "2026-03-25", "open": 181.0, "high": 183.0, "low": 180.0, "close": 182.0, "volume": 1100000}
        ]
    }
```

- [ ] **Step 2: Add test for no gap scenario**

Add to `tests/test_stock_catchup.py`:

```python
@pytest.mark.asyncio
async def test_catchup_no_gap(mock_metadata_current):
    """Test catchup skips when data is current."""
    from app.services.stock_updater import catchup_historical_stocks
    
    with patch('app.services.stock_updater.get_metadata', return_value=mock_metadata_current):
        stats = await catchup_historical_stocks(days=5)
        
        assert stats["symbols_updated"] == 0
        assert stats["records_added"] == 0
        assert stats["date_range"] is None
        assert stats["errors"] == []
```

- [ ] **Step 3: Add test for gap detection**

Add to `tests/test_stock_catchup.py`:

```python
@pytest.mark.asyncio
async def test_catchup_with_gap(mock_metadata_gap, mock_stock_data):
    """Test catchup fills gap correctly."""
    from app.services.stock_updater import catchup_historical_stocks
    
    with patch('app.services.stock_updater.get_metadata', return_value=mock_metadata_gap), \
         patch('app.services.stock_updater._fetch_with_rate_limit', return_value=mock_stock_data), \
         patch('app.services.stock_updater.upsert_ohlc_overwrite'), \
         patch('app.services.stock_updater.update_metadata'), \
         patch('app.services.stock_updater.get_stock_catchup_config', return_value={"rate_limit_delay": 0.1}):
        
        stats = await catchup_historical_stocks(days=5)
        
        assert stats["symbols_updated"] == 1
        assert stats["records_added"] == 2
        assert stats["date_range"] == ("2026-03-24", "2026-03-25")
        assert stats["errors"] == []
```

- [ ] **Step 4: Add test for rate limiting**

Add to `tests/test_stock_catchup.py`:

```python
@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting delays between requests."""
    from app.services.stock_updater import _fetch_with_rate_limit
    
    mock_fetch = Mock(return_value={"AAPL": [{"date": "2026-03-26", "close": 180.0}]})
    
    with patch('app.services.stock_updater.fetch_recent_ohlc', mock_fetch):
        start = datetime.now()
        await _fetch_with_rate_limit(["AAPL", "MSFT"], days=2, delay=0.5)
        elapsed = (datetime.now() - start).total_seconds()
        
        # Should have at least 0.5s delay between 2 symbols
        assert elapsed >= 0.5, f"Expected >= 0.5s, got {elapsed}s"
```

- [ ] **Step 5: Add test for force bypass**

Add to `tests/test_stock_catchup.py`:

```python
@pytest.mark.asyncio
async def test_force_bypass():
    """Test force=True bypasses trading hours check."""
    from app.services.stock_updater import update_stocks_intraday
    
    with patch('app.services.stock_updater.should_update_stocks', return_value=False), \
         patch('app.services.stock_updater.update_stocks_intraday_sync') as mock_sync:
        
        # force=False should skip
        await update_stocks_intraday(force=False)
        mock_sync.assert_not_called()
        
        # force=True should proceed
        await update_stocks_intraday(force=True)
        mock_sync.assert_called_once()
```

- [ ] **Step 6: Run all tests**

```bash
uv run pytest tests/test_stock_catchup.py -v
```

Expected: All 4 tests pass

- [ ] **Step 7: Commit tests**

```bash
git add tests/test_stock_catchup.py
git commit -m "test: add unit tests for stock catchup mechanism"
```

---

## Verification Checklist

After completing all tasks, verify the implementation:

- [ ] Configuration loads correctly from environment variables
- [ ] Force mode bypasses trading hours check
- [ ] Rate limiting works (delays between requests)
- [ ] Catchup detects gaps correctly
- [ ] Catchup skips when data is current
- [ ] API starts without blocking
- [ ] Catchup runs in background on startup
- [ ] Logs show catchup progress
- [ ] All unit tests pass
- [ ] Stock quotes endpoint returns data after catchup

## Testing the Complete Flow

```bash
# 1. Set environment variables
export STOCK_CATCHUP_ENABLED=true
export STOCK_CATCHUP_DAYS=5

# 2. Delete recent stock data to create a gap
uv run python -c "
from app.database.schema import get_conn
conn = get_conn()
conn.execute(\"DELETE FROM ohlc WHERE symbol='AAPL' AND date >= '2026-03-24'\")
conn.commit()
conn.close()
print('✓ Created data gap')
"

# 3. Restart API
pkill -f "uvicorn app.api.main:app"
nohup uv run uvicorn app.api.main:app --host 0.0.0.0 --port 8080 > /tmp/api.log 2>&1 &

# 4. Wait and check logs
sleep 15
tail -100 /tmp/api.log | grep -A 5 "stock catchup"

# 5. Verify data was filled
uv run python -c "
from app.database.ohlc import get_metadata
import json
print(json.dumps(get_metadata('AAPL'), indent=2))
"

# 6. Test API endpoint
curl -s "http://localhost:8080/api/stocks/quotes?symbols=AAPL" | python -m json.tool
```

Expected: Catchup fills the gap, metadata shows current date, API returns quotes.
