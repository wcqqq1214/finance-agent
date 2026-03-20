# Chart Time Granularity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform K-line chart from time-span view (1M/3M/6M/1Y/5Y) to time-granularity view (D/W/M/Y) with backend aggregation support

**Architecture:** Add optional `interval` parameter to existing OHLC API endpoint with SQL aggregation logic for week/month/year granularities. Frontend updates TimeRange type and components to use new granularity model. Maintains backward compatibility.

**Tech Stack:** Python (FastAPI, SQLite), TypeScript (React, Next.js), lightweight-charts

---

## File Structure

### Backend Files
- **Modify**: `app/database/ohlc.py` - Add `get_ohlc_aggregated()` function with SQL aggregation logic
- **Modify**: `app/database/__init__.py` - Export new function
- **Modify**: `app/api/routes/ohlc.py` - Update endpoint to accept `interval` parameter
- **Create**: `tests/test_ohlc_aggregation.py` - Unit tests for aggregation logic

### Frontend Files
- **Modify**: `frontend/src/lib/types.ts` - Update `TimeRange` type definition
- **Modify**: `frontend/src/lib/api.ts` - Add `interval` parameter to `getOHLC()`
- **Modify**: `frontend/src/components/chart/TimeRangeSelector.tsx` - Update button labels and values
- **Modify**: `frontend/src/components/chart/KLineChart.tsx` - Update time window calculation and API calls

---

## Task 1: Backend - Database Aggregation Function

**Files:**
- Modify: `app/database/ohlc.py`
- Test: `tests/test_ohlc_aggregation.py` (create)

- [ ] **Step 1: Write failing test for day interval**

Create `tests/test_ohlc_aggregation.py`:

```python
import pytest
from app.database.ohlc import get_ohlc_aggregated
from app.database.schema import get_conn

@pytest.fixture
def sample_data():
    """Insert sample OHLC data for testing."""
    conn = get_conn()
    conn.executescript("""
        DELETE FROM ohlc WHERE symbol = 'TEST';
        INSERT INTO ohlc (symbol, date, open, high, low, close, volume) VALUES
        ('TEST', '2024-01-02', 100.0, 105.0, 99.0, 103.0, 1000000),
        ('TEST', '2024-01-03', 103.0, 108.0, 102.0, 107.0, 1100000),
        ('TEST', '2024-01-04', 107.0, 110.0, 106.0, 109.0, 1200000);
    """)
    conn.commit()
    conn.close()
    yield
    conn = get_conn()
    conn.execute("DELETE FROM ohlc WHERE symbol = 'TEST'")
    conn.commit()
    conn.close()

def test_get_ohlc_aggregated_day(sample_data):
    """Test day interval returns daily data unchanged."""
    result = get_ohlc_aggregated('TEST', '2024-01-02', '2024-01-04', 'day')
    assert len(result) == 3
    assert result[0]['date'] == '2024-01-02'
    assert result[0]['open'] == 100.0
    assert result[0]['close'] == 103.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ohlc_aggregation.py::test_get_ohlc_aggregated_day -v`
Expected: FAIL with "ImportError: cannot import name 'get_ohlc_aggregated'"

- [ ] **Step 3: Implement get_ohlc_aggregated function - day interval**

In `app/database/ohlc.py`, add after `get_ohlc()`:

```python
def get_ohlc_aggregated(symbol: str, start: str, end: str, interval: str) -> List[Dict]:
    """Query aggregated OHLC data from database.

    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        start: Start date in YYYY-MM-DD format
        end: End date in YYYY-MM-DD format
        interval: Time granularity ('day', 'week', 'month', 'year')

    Returns:
        List of aggregated OHLC records as dictionaries
    """
    from app.database.schema import get_conn
    conn = get_conn()

    if interval == 'day':
        # Direct query, no aggregation needed
        query = """
            SELECT date, open, high, low, close, volume
            FROM ohlc
            WHERE symbol = ? AND date >= ? AND date <= ?
            ORDER BY date ASC
        """
        params = (symbol.upper(), start, end)
    else:
        conn.close()
        raise ValueError(f"Invalid interval: {interval}")

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_ohlc_aggregation.py::test_get_ohlc_aggregated_day -v`
Expected: PASS

- [ ] **Step 5: Commit day interval implementation**

```bash
git add app/database/ohlc.py tests/test_ohlc_aggregation.py
git commit -m "feat(backend): add get_ohlc_aggregated with day interval support"
```

---

## Task 2: Backend - Week Aggregation

**Files:**
- Modify: `app/database/ohlc.py`
- Modify: `tests/test_ohlc_aggregation.py`

- [ ] **Step 1: Write failing test for week interval**

Add to `tests/test_ohlc_aggregation.py`:

```python
def test_get_ohlc_aggregated_week(sample_data):
    """Test week interval aggregates by ISO week."""
    # Sample data spans one week (2024-01-02 to 2024-01-04 are Tue-Thu)
    result = get_ohlc_aggregated('TEST', '2024-01-01', '2024-01-07', 'week')
    assert len(result) == 1
    # Week should start on Monday 2024-01-01
    assert result[0]['date'] == '2024-01-01'
    assert result[0]['open'] == 100.0  # First day's open
    assert result[0]['high'] == 110.0  # Max of all highs
    assert result[0]['low'] == 99.0    # Min of all lows
    assert result[0]['close'] == 109.0 # Last day's close
    assert result[0]['volume'] == 3300000  # Sum of volumes
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ohlc_aggregation.py::test_get_ohlc_aggregated_week -v`
Expected: FAIL with "ValueError: Invalid interval: week"

- [ ] **Step 3: Implement week aggregation logic**

In `app/database/ohlc.py`, update `get_ohlc_aggregated()` to add week case before the else clause:

```python
    elif interval == 'week':
        # Aggregate by ISO week (Monday to Sunday)
        query = """
            SELECT
                date(date, 'weekday 0', '-6 days') as date,
                (SELECT open FROM ohlc o2
                 WHERE o2.symbol = ohlc.symbol
                 AND date(o2.date, 'weekday 0', '-6 days') = date(ohlc.date, 'weekday 0', '-6 days')
                 ORDER BY o2.date ASC LIMIT 1) as open,
                MAX(high) as high,
                MIN(low) as low,
                (SELECT close FROM ohlc o3
                 WHERE o3.symbol = ohlc.symbol
                 AND date(o3.date, 'weekday 0', '-6 days') = date(ohlc.date, 'weekday 0', '-6 days')
                 ORDER BY o3.date DESC LIMIT 1) as close,
                SUM(volume) as volume
            FROM ohlc
            WHERE symbol = ? AND date >= ? AND date <= ?
            GROUP BY date(date, 'weekday 0', '-6 days')
            ORDER BY date ASC
        """
        params = (symbol.upper(), start, end)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_ohlc_aggregation.py::test_get_ohlc_aggregated_week -v`
Expected: PASS

- [ ] **Step 5: Commit week aggregation**

```bash
git add app/database/ohlc.py tests/test_ohlc_aggregation.py
git commit -m "feat(backend): add week interval aggregation to get_ohlc_aggregated"
```

---

## Task 3: Backend - Month and Year Aggregation

**Files:**
- Modify: `app/database/ohlc.py`
- Modify: `tests/test_ohlc_aggregation.py`

- [ ] **Step 1: Write failing tests for month and year intervals**

Add to `tests/test_ohlc_aggregation.py`:

```python
@pytest.fixture
def multi_month_data():
    """Insert data spanning multiple months."""
    conn = get_conn()
    conn.executescript("""
        DELETE FROM ohlc WHERE symbol = 'TEST2';
        INSERT INTO ohlc (symbol, date, open, high, low, close, volume) VALUES
        ('TEST2', '2024-01-15', 100.0, 105.0, 99.0, 103.0, 1000000),
        ('TEST2', '2024-01-31', 103.0, 108.0, 102.0, 107.0, 1100000),
        ('TEST2', '2024-02-01', 107.0, 110.0, 106.0, 109.0, 1200000),
        ('TEST2', '2024-02-29', 109.0, 115.0, 108.0, 113.0, 1300000);
    """)
    conn.commit()
    conn.close()
    yield
    conn = get_conn()
    conn.execute("DELETE FROM ohlc WHERE symbol = 'TEST2'")
    conn.commit()
    conn.close()

def test_get_ohlc_aggregated_month(multi_month_data):
    """Test month interval aggregates by calendar month."""
    result = get_ohlc_aggregated('TEST2', '2024-01-01', '2024-02-29', 'month')
    assert len(result) == 2
    # January
    assert result[0]['date'] == '2024-01-01'
    assert result[0]['open'] == 100.0
    assert result[0]['high'] == 108.0
    assert result[0]['low'] == 99.0
    assert result[0]['close'] == 107.0
    assert result[0]['volume'] == 2100000
    # February
    assert result[1]['date'] == '2024-02-01'
    assert result[1]['open'] == 107.0
    assert result[1]['close'] == 113.0

def test_get_ohlc_aggregated_year(multi_month_data):
    """Test year interval aggregates by calendar year."""
    result = get_ohlc_aggregated('TEST2', '2024-01-01', '2024-12-31', 'year')
    assert len(result) == 1
    assert result[0]['date'] == '2024-01-01'
    assert result[0]['open'] == 100.0
    assert result[0]['high'] == 115.0
    assert result[0]['low'] == 99.0
    assert result[0]['close'] == 113.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_ohlc_aggregation.py::test_get_ohlc_aggregated_month -v`
Run: `uv run pytest tests/test_ohlc_aggregation.py::test_get_ohlc_aggregated_year -v`
Expected: Both FAIL with "ValueError: Invalid interval"

- [ ] **Step 3: Implement month and year aggregation logic**

In `app/database/ohlc.py`, update `get_ohlc_aggregated()` to add month and year cases:

```python
    elif interval == 'month':
        # Aggregate by calendar month
        query = """
            SELECT
                strftime('%Y-%m-01', date) as date,
                (SELECT open FROM ohlc o2
                 WHERE o2.symbol = ohlc.symbol
                 AND strftime('%Y-%m', o2.date) = strftime('%Y-%m', ohlc.date)
                 ORDER BY o2.date ASC LIMIT 1) as open,
                MAX(high) as high,
                MIN(low) as low,
                (SELECT close FROM ohlc o3
                 WHERE o3.symbol = ohlc.symbol
                 AND strftime('%Y-%m', o3.date) = strftime('%Y-%m', ohlc.date)
                 ORDER BY o3.date DESC LIMIT 1) as close,
                SUM(volume) as volume
            FROM ohlc
            WHERE symbol = ? AND date >= ? AND date <= ?
            GROUP BY strftime('%Y-%m', date)
            ORDER BY date ASC
        """
        params = (symbol.upper(), start, end)

    elif interval == 'year':
        # Aggregate by calendar year
        query = """
            SELECT
                strftime('%Y-01-01', date) as date,
                (SELECT open FROM ohlc o2
                 WHERE o2.symbol = ohlc.symbol
                 AND strftime('%Y', o2.date) = strftime('%Y', ohlc.date)
                 ORDER BY o2.date ASC LIMIT 1) as open,
                MAX(high) as high,
                MIN(low) as low,
                (SELECT close FROM ohlc o3
                 WHERE o3.symbol = ohlc.symbol
                 AND strftime('%Y', o3.date) = strftime('%Y', ohlc.date)
                 ORDER BY o3.date DESC LIMIT 1) as close,
                SUM(volume) as volume
            FROM ohlc
            WHERE symbol = ? AND date >= ? AND date <= ?
            GROUP BY strftime('%Y', date)
            ORDER BY date ASC
        """
        params = (symbol.upper(), start, end)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_ohlc_aggregation.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit month and year aggregation**

```bash
git add app/database/ohlc.py tests/test_ohlc_aggregation.py
git commit -m "feat(backend): add month and year interval aggregation"
```

---

## Task 4: Backend - Export Function and Update API

**Files:**
- Modify: `app/database/__init__.py`
- Modify: `app/api/routes/ohlc.py`

- [ ] **Step 1: Export get_ohlc_aggregated from database module**

In `app/database/__init__.py`, update imports and __all__:

```python
from app.database.ohlc import get_ohlc, get_metadata, upsert_ohlc, update_metadata, get_ohlc_aggregated

__all__ = [
    "get_conn",
    "init_db",
    "DEFAULT_DB_PATH",
    "get_ohlc",
    "get_ohlc_aggregated",
    "get_metadata",
    "upsert_ohlc",
    "update_metadata",
]
```

- [ ] **Step 2: Update API route to use get_ohlc_aggregated**

In `app/api/routes/ohlc.py`, modify the `get_stock_ohlc` function:

1. Add import at top:
```python
from app.database import get_ohlc_aggregated
```

2. Update function signature to add interval parameter:
```python
@router.get("/{symbol}/ohlc", response_model=OHLCResponse)
def get_stock_ohlc(
    symbol: str,
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    interval: str = Query("day", description="Time granularity: day, week, month, year"),
):
    """Get OHLC data for a stock symbol with optional time aggregation."""
```

3. Add interval validation after the docstring:
```python
    # Validate interval
    valid_intervals = ["day", "week", "month", "year"]
    if interval not in valid_intervals:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid interval. Must be one of: {', '.join(valid_intervals)}"
        )
```

4. Replace the `data = get_ohlc(...)` call with:
```python
        data = get_ohlc_aggregated(symbol, start, end, interval)
```

5. Add ValueError handling in the except block before the generic Exception:
```python
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 3: Test API endpoint manually**

Start backend:
```bash
cd /home/wcqqq21/finance-agent
uv run uvicorn app.api.main:app --port 8080
```

Test in another terminal:
```bash
# Test day interval (default)
curl "http://localhost:8080/stocks/AAPL/ohlc?start=2024-01-01&end=2024-01-31"

# Test week interval
curl "http://localhost:8080/stocks/AAPL/ohlc?start=2024-01-01&end=2024-01-31&interval=week"

# Test invalid interval
curl "http://localhost:8080/stocks/AAPL/ohlc?interval=invalid"
```

Expected:
- Day and week return valid JSON with aggregated data
- Invalid interval returns 400 error

- [ ] **Step 4: Commit API changes**

```bash
git add app/database/__init__.py app/api/routes/ohlc.py
git commit -m "feat(backend): integrate get_ohlc_aggregated into API endpoint"
```

---

## Task 5: Frontend - Update Type Definitions

**Files:**
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: Update TimeRange type definition**

In `frontend/src/lib/types.ts`, find and replace the TimeRange type:

```typescript
// Change from:
export type TimeRange = '1M' | '3M' | '6M' | '1Y' | '5Y';

// To:
export type TimeRange = 'D' | 'W' | 'M' | 'Y';
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npm run build`
Expected: Build may show errors in components using TimeRange (we'll fix those next)

- [ ] **Step 3: Commit type definition change**

```bash
git add frontend/src/lib/types.ts
git commit -m "feat(frontend): update TimeRange type to use granularity (D/W/M/Y)"
```

---

## Task 6: Frontend - Update API Client

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Update getOHLC function signature**

In `frontend/src/lib/api.ts`, find the `getOHLC` method and update it:

```typescript
  async getOHLC(
    symbol: string,
    start: string,
    end: string,
    interval: string = 'day'
  ): Promise<OHLCResponse> {
    const params = new URLSearchParams({
      start,
      end,
      interval,
    });
    const response = await fetch(
      `${API_BASE_URL}/stocks/${symbol}/ohlc?${params}`,
      {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      }
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch OHLC data: ${response.statusText}`);
    }
    return response.json();
  },
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npm run build`
Expected: No errors in api.ts

- [ ] **Step 3: Commit API client changes**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat(frontend): add interval parameter to getOHLC API call"
```

---

## Task 7: Frontend - Update TimeRangeSelector Component

**Files:**
- Modify: `frontend/src/components/chart/TimeRangeSelector.tsx`

- [ ] **Step 1: Update TIME_RANGES array and add labels**

In `frontend/src/components/chart/TimeRangeSelector.tsx`, replace the content:

```typescript
'use client';

import { Button } from '@/components/ui/button';
import type { TimeRange } from '@/lib/types';

interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
  disabled?: boolean;
}

const TIME_RANGES: TimeRange[] = ['D', 'W', 'M', 'Y'];

export function TimeRangeSelector({ value, onChange, disabled }: TimeRangeSelectorProps) {
  const labels: Record<TimeRange, string> = {
    'D': 'Day',
    'W': 'Week',
    'M': 'Month',
    'Y': 'Year',
  };

  return (
    <div className="flex gap-1">
      {TIME_RANGES.map((range) => (
        <Button
          key={range}
          variant={value === range ? 'default' : 'outline'}
          size="sm"
          onClick={() => onChange(range)}
          disabled={disabled}
          className="min-w-[60px]"
        >
          {labels[range]}
        </Button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npm run build`
Expected: No errors in TimeRangeSelector.tsx

- [ ] **Step 3: Commit TimeRangeSelector changes**

```bash
git add frontend/src/components/chart/TimeRangeSelector.tsx
git commit -m "feat(frontend): update TimeRangeSelector to show D/W/M/Y buttons"
```

---

## Task 8: Frontend - Update KLineChart Component

**Files:**
- Modify: `frontend/src/components/chart/KLineChart.tsx`

- [ ] **Step 1: Update calculateDateRange function**

In `frontend/src/components/chart/KLineChart.tsx`, replace the `calculateDateRange` function:

```typescript
function calculateDateRange(range: TimeRange): { start: string; end: string } {
  const end = new Date();
  const start = new Date();

  switch (range) {
    case 'D':
      // Day: show last 3 months of daily data (~60-90 bars)
      start.setMonth(start.getMonth() - 3);
      break;
    case 'W':
      // Week: show last 1 year of weekly data (~52 bars)
      start.setFullYear(start.getFullYear() - 1);
      break;
    case 'M':
      // Month: show last 3 years of monthly data (~36 bars)
      start.setFullYear(start.getFullYear() - 3);
      break;
    case 'Y':
      // Year: show all available yearly data (5 years, ~5 bars)
      start.setFullYear(start.getFullYear() - 5);
      break;
  }

  return {
    start: start.toISOString().split('T')[0],
    end: end.toISOString().split('T')[0],
  };
}
```

- [ ] **Step 2: Update fetchData to pass interval parameter**

In the same file, update the `fetchData` callback to add interval mapping:

```typescript
  const fetchData = useCallback(async () => {
    if (!selectedStock) {
      setOhlcData([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const { start, end } = calculateDateRange(timeRange);

      // Map frontend TimeRange to backend interval parameter
      const intervalMap: Record<TimeRange, string> = {
        'D': 'day',
        'W': 'week',
        'M': 'month',
        'Y': 'year',
      };

      const response = await api.getOHLC(
        selectedStock,
        start,
        end,
        intervalMap[timeRange]
      );
      setOhlcData(response.data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load chart data';
      setError(message);
      toast({
        title: 'Failed to load chart',
        description: 'Unable to fetch OHLC data',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [selectedStock, timeRange, toast]);
```

- [ ] **Step 3: Update default timeRange value**

Find the useState line and change the default:

```typescript
  const [timeRange, setTimeRange] = useState<TimeRange>('W');
```

- [ ] **Step 4: Verify TypeScript compilation**

Run: `cd frontend && npm run build`
Expected: No errors, successful build

- [ ] **Step 5: Commit KLineChart changes**

```bash
git add frontend/src/components/chart/KLineChart.tsx
git commit -m "feat(frontend): update KLineChart to use time granularity with interval API"
```

---

## Task 9: Integration Testing

**Files:**
- None (manual testing)

- [ ] **Step 1: Start backend server**

```bash
cd /home/wcqqq21/finance-agent
uv run uvicorn app.api.main:app --port 8080
```

- [ ] **Step 2: Start frontend dev server**

In another terminal:
```bash
cd /home/wcqqq21/finance-agent/frontend
npm run dev
```

- [ ] **Step 3: Manual testing checklist**

Open browser to `http://localhost:3000` and test:

1. Select a stock (e.g., AAPL)
2. Click "Day" button - verify chart shows ~3 months of daily bars
3. Click "Week" button - verify chart shows ~1 year of weekly bars
4. Click "Month" button - verify chart shows ~3 years of monthly bars
5. Click "Year" button - verify chart shows ~5 years of yearly bars
6. Test zoom: scroll mouse wheel on chart - verify zoom works
7. Test pan: click and drag on chart - verify panning works
8. Switch between different stocks - verify data updates correctly
9. Check browser console - verify no errors

Expected: All interactions work smoothly, chart displays correct granularity

- [ ] **Step 4: Performance testing**

Open browser DevTools Network tab:
1. Select AAPL
2. Click each time range button
3. Check API response times in Network tab

Expected: All `/stocks/AAPL/ohlc` requests complete in < 500ms

- [ ] **Step 5: Document test results**

Create a simple test summary (no commit needed, just for verification):
- All time ranges work: ✓/✗
- Chart interactions work: ✓/✗
- Performance < 500ms: ✓/✗
- No console errors: ✓/✗

---

## Task 10: Final Verification and Documentation

**Files:**
- None (verification only)

- [ ] **Step 1: Run all backend tests**

```bash
cd /home/wcqqq21/finance-agent
uv run pytest tests/test_ohlc_aggregation.py -v
```

Expected: All tests PASS

- [ ] **Step 2: Verify backward compatibility**

Test that existing API calls without interval parameter still work:

```bash
curl "http://localhost:8080/stocks/AAPL/ohlc?start=2024-01-01&end=2024-01-31"
```

Expected: Returns daily data (same as before the change)

- [ ] **Step 3: Check TypeScript compilation**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no errors

- [ ] **Step 4: Review all commits**

```bash
git log --oneline -10
```

Expected: See all feature commits in logical order

- [ ] **Step 5: Create final summary commit (if needed)**

If any documentation or minor fixes are needed:

```bash
git add .
git commit -m "docs: update chart time granularity feature implementation"
```

---

## Success Criteria

✅ Backend API accepts `interval` parameter (day/week/month/year)
✅ SQL aggregation correctly groups data by time period
✅ Frontend displays D/W/M/Y buttons instead of 1M/3M/6M/1Y/5Y
✅ Chart shows correct granularity when switching time ranges
✅ Backward compatibility maintained (no interval = daily data)
✅ All tests pass
✅ Performance < 500ms for all intervals
✅ Chart zoom and pan still work correctly

## Notes

- Use @superpowers:test-driven-development for TDD discipline
- Use @superpowers:verification-before-completion before claiming tasks complete
- Commit after each passing test
- If performance issues arise, refer to spec section 5.3 for optimization strategies
