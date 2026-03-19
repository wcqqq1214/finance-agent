# K-Line Chart Feature Design

**Date:** 2026-03-19
**Status:** Approved
**Approach:** Lightweight Implementation (Option A)

## Overview

Add K-line (candlestick) chart functionality to the Home page. When a stock is selected, display its historical OHLC data in an interactive chart with time range selection. Use Lightweight Charts library for rendering, SQLite for data storage, and Polygon API for data fetching.

## Requirements

### Functional Requirements

1. **K-Line Chart Display**
   - Display candlestick chart for selected stock
   - Show 5 years of historical daily data
   - Support time range selection: 1M, 3M, 6M, 1Y, 5Y
   - Basic interactions: zoom, pan, crosshair
   - No technical indicators (MA, MACD, etc.) in initial version

2. **Data Management**
   - Pre-load 5 years of historical data for 7 stocks (AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA)
   - Store data in SQLite database
   - Daily automatic updates via scheduled task
   - Fetch data from Polygon API

3. **User Experience**
   - Loading states during data fetch
   - Error handling with user-friendly messages
   - Empty state when no stock selected
   - Responsive chart sizing

### Non-Functional Requirements

1. **Performance**
   - Chart renders within 500ms for 1 year of data
   - Smooth interactions (60fps)
   - Efficient database queries with indexes

2. **Reliability**
   - Handle API rate limits gracefully
   - Retry failed requests
   - Continue operation if one stock update fails

3. **Maintainability**
   - Reuse existing Polygon client
   - Follow existing code patterns
   - Clear separation of concerns

## Architecture

### System Architecture

```
Frontend (Next.js)              Backend (FastAPI)              External
+-------------------+          +--------------------+         +-----------+
| HomePage          |          | /api/stocks/       |         | Polygon   |
| ├─ StockSelector  |          |   {symbol}/ohlc    |-------->| API       |
| ├─ KLineChart ----+--------->|                    |         +-----------+
| └─ ChatPanel      |          | SQLite DB          |
|                   |          | ├─ ohlc table      |
| Time Selector     |          | └─ metadata        |
| [1M|3M|6M|1Y|5Y]  |          |                    |
+-------------------+          | APScheduler        |
                               | └─ daily_update    |
                               +--------------------+
```

### Data Flow

**1. Initialization (one-time):**
```
Management Script -> Polygon API -> Batch Download -> SQLite
```

**2. Daily Update (scheduled):**
```
APScheduler (21:30 UTC) -> Polygon API -> Incremental Update -> SQLite
```

**3. User Query:**
```
Frontend (select stock + time range) -> API -> SQLite -> Return OHLC -> Render Chart
```

### Component Hierarchy

```
HomePage
├── StockSelector (existing)
├── KLineChart (new)
│   ├── Chart Container (lightweight-charts)
│   ├── TimeRangeSelector (1M/3M/6M/1Y/5Y)
│   └── LoadingState
└── ChatPanel (existing)
```

## Database Design

### SQLite Schema

```sql
-- OHLC data table
CREATE TABLE ohlc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,  -- YYYY-MM-DD
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date)
);

CREATE INDEX idx_ohlc_symbol_date ON ohlc(symbol, date);

-- Metadata table (track update status)
CREATE TABLE data_metadata (
    symbol TEXT PRIMARY KEY,
    last_update TEXT,  -- Last update timestamp
    data_start TEXT,   -- Data start date
    data_end TEXT      -- Data end date
);
```

### Database Location

```
/home/wcqqq21/finance-agent/
├── app/
│   └── data/
│       └── finance.db  (SQLite database file)
```

### Data Volume Estimation (5 years)

- 7 stocks × 252 trading days/year × 5 years = 8,820 records
- Each record ~100 bytes
- Total ~880 KB (very lightweight)

### SQLite Configuration

- Use WAL mode for concurrent reads
- Enable foreign keys
- Set reasonable cache size

## Backend API Design

### New Endpoints

**1. Get OHLC Data**
```
GET /api/stocks/{symbol}/ohlc?start=YYYY-MM-DD&end=YYYY-MM-DD

Query Parameters:
- start (optional): Start date, defaults to 5 years ago
- end (optional): End date, defaults to today

Response:
{
  "symbol": "AAPL",
  "data": [
    {
      "date": "2021-01-04",
      "open": 133.52,
      "high": 133.61,
      "low": 126.76,
      "close": 129.41,
      "volume": 143301900
    },
    ...
  ]
}

Error Responses:
- 404: Stock not found or no data available
- 400: Invalid date range
- 500: Database error
```

**2. Get Data Status (optional)**
```
GET /api/stocks/{symbol}/data-status

Response:
{
  "symbol": "AAPL",
  "last_update": "2026-03-19T10:30:00Z",
  "data_start": "2021-03-19",
  "data_end": "2026-03-19",
  "total_records": 1260
}
```

### Database Module

**File:** `app/database.py`

```python
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

DB_PATH = Path(__file__).parent / "data" / "finance.db"

def get_conn() -> sqlite3.Connection:
    """Get database connection with WAL mode"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    """Initialize database tables and indexes"""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ohlc (...);
        CREATE INDEX IF NOT EXISTS idx_ohlc_symbol_date ON ohlc(symbol, date);
        CREATE TABLE IF NOT EXISTS data_metadata (...);
    """)
    conn.commit()
    conn.close()

def get_ohlc(symbol: str, start: str, end: str) -> List[Dict]:
    """Query OHLC data from database"""
    conn = get_conn()
    query = """
        SELECT date, open, high, low, close, volume
        FROM ohlc
        WHERE symbol = ? AND date >= ? AND date <= ?
        ORDER BY date ASC
    """
    rows = conn.execute(query, (symbol, start, end)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def upsert_ohlc(symbol: str, data: List[Dict]):
    """Insert or update OHLC data (batch operation)"""
    conn = get_conn()
    conn.executemany("""
        INSERT INTO ohlc (symbol, date, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, date) DO NOTHING
    """, [(symbol, d['date'], d['open'], d['high'], d['low'], d['close'], d['volume'])
          for d in data])
    conn.commit()
    conn.close()

def update_metadata(symbol: str, start: str, end: str):
    """Update metadata after data sync"""
    conn = get_conn()
    conn.execute("""
        INSERT INTO data_metadata (symbol, last_update, data_start, data_end)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            last_update = excluded.last_update,
            data_end = excluded.data_end
    """, (symbol, datetime.now().isoformat(), start, end))
    conn.commit()
    conn.close()
```

### Scheduled Task

**Integration with FastAPI:**

```python
# app/api/main.py
from apscheduler.schedulers.background import BackgroundScheduler
from app.tasks.update_ohlc import update_daily_ohlc

scheduler = BackgroundScheduler()

@app.on_event("startup")
def start_scheduler():
    # Update daily after US market close (UTC 21:30 = EST 16:30)
    scheduler.add_job(update_daily_ohlc, 'cron', hour=21, minute=30)
    scheduler.start()
    logger.info("Scheduler started: daily OHLC update at 21:30 UTC")

@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
```

**Update Task:** `app/tasks/update_ohlc.py`

```python
import logging
from datetime import datetime, timedelta
from app.polygon.client import fetch_ohlc
from app.database import upsert_ohlc, update_metadata

logger = logging.getLogger(__name__)

SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']

def update_daily_ohlc():
    """Update all stocks with latest data"""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    start_date = yesterday.isoformat()
    end_date = today.isoformat()

    logger.info(f"Starting daily OHLC update for {start_date} to {end_date}")

    for symbol in SYMBOLS:
        try:
            data = fetch_ohlc(symbol, start_date, end_date)
            if data:
                upsert_ohlc(symbol, data)
                update_metadata(symbol, start_date, end_date)
                logger.info(f"Updated {symbol}: {len(data)} records")
            else:
                logger.warning(f"No data returned for {symbol}")
        except Exception as e:
            logger.error(f"Failed to update {symbol}: {e}")
            # Continue with other symbols

    logger.info("Daily OHLC update completed")
```

## Frontend Component Design

### KLineChart Component

**File:** `frontend/src/components/chart/KLineChart.tsx`

**Props Interface:**
```typescript
interface KLineChartProps {
  selectedStock: string | null;  // Selected stock symbol
}
```

**State Management:**
```typescript
const [timeRange, setTimeRange] = useState<'1M' | '3M' | '6M' | '1Y' | '5Y'>('3M');
const [ohlcData, setOhlcData] = useState<OHLCData[]>([]);
const [loading, setLoading] = useState(false);
const [error, setError] = useState<string | null>(null);
const chartContainerRef = useRef<HTMLDivElement>(null);
const chartRef = useRef<IChartApi | null>(null);
```

**Data Types:**
```typescript
interface OHLCData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface CandlestickData {
  time: string;  // YYYY-MM-DD
  open: number;
  high: number;
  low: number;
  close: number;
}
```

**Time Range Selector:**
```tsx
<div className="flex gap-1 mb-2">
  {(['1M', '3M', '6M', '1Y', '5Y'] as const).map(range => (
    <Button
      key={range}
      variant={timeRange === range ? 'default' : 'outline'}
      size="sm"
      onClick={() => setTimeRange(range)}
      disabled={loading || !selectedStock}
    >
      {range}
    </Button>
  ))}
</div>
```

**Lightweight Charts Integration:**
```typescript
useEffect(() => {
  if (!selectedStock || !chartContainerRef.current) return;

  // Create chart instance
  const chart = createChart(chartContainerRef.current, {
    width: chartContainerRef.current.clientWidth,
    height: 400,
    layout: {
      background: { color: 'transparent' },
      textColor: '#d1d5db',
    },
    grid: {
      vertLines: { color: '#334155' },
      horzLines: { color: '#334155' },
    },
    timeScale: {
      borderColor: '#334155',
      timeVisible: true,
    },
    rightPriceScale: {
      borderColor: '#334155',
    },
  });

  // Add candlestick series
  const candlestickSeries = chart.addCandlestickSeries({
    upColor: '#22c55e',
    downColor: '#ef4444',
    borderVisible: false,
    wickUpColor: '#22c55e',
    wickDownColor: '#ef4444',
  });

  // Convert and set data
  const formattedData: CandlestickData[] = ohlcData.map(d => ({
    time: d.date,
    open: d.open,
    high: d.high,
    low: d.low,
    close: d.close,
  }));

  candlestickSeries.setData(formattedData);

  // Fit content to visible range
  chart.timeScale().fitContent();

  // Handle resize
  const handleResize = () => {
    if (chartContainerRef.current) {
      chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    }
  };
  window.addEventListener('resize', handleResize);

  chartRef.current = chart;

  return () => {
    window.removeEventListener('resize', handleResize);
    chart.remove();
  };
}, [selectedStock, ohlcData]);
```

**Data Fetching:**
```typescript
useEffect(() => {
  if (!selectedStock) {
    setOhlcData([]);
    return;
  }

  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      const { start, end } = calculateDateRange(timeRange);
      const response = await api.getOHLC(selectedStock, start, end);
      setOhlcData(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chart data');
      toast({
        title: 'Failed to load chart',
        description: 'Unable to fetch OHLC data',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  fetchData();
}, [selectedStock, timeRange]);

function calculateDateRange(range: string): { start: string; end: string } {
  const end = new Date();
  const start = new Date();

  switch (range) {
    case '1M': start.setMonth(start.getMonth() - 1); break;
    case '3M': start.setMonth(start.getMonth() - 3); break;
    case '6M': start.setMonth(start.getMonth() - 6); break;
    case '1Y': start.setFullYear(start.getFullYear() - 1); break;
    case '5Y': start.setFullYear(start.getFullYear() - 5); break;
  }

  return {
    start: start.toISOString().split('T')[0],
    end: end.toISOString().split('T')[0],
  };
}
```

### API Client Extension

**File:** `frontend/src/lib/api.ts`

```typescript
// Add to existing api object
getOHLC: (symbol: string, start?: string, end?: string) => {
  const params = new URLSearchParams();
  if (start) params.append('start', start);
  if (end) params.append('end', end);
  return fetchAPI<{ symbol: string; data: OHLCData[] }>(
    `/api/stocks/${symbol}/ohlc?${params}`
  );
},
```

### Layout Integration

**Update:** `frontend/src/app/page.tsx`

```tsx
{/* Bottom: K-line chart (60% height) */}
<div className="flex-1 overflow-hidden">
  <KLineChart selectedStock={selectedStock} />
</div>
```

## Data Initialization

### Initialization Script

**File:** `app/scripts/init_ohlc_data.py`

```python
"""
Initialize OHLC database with 5 years of historical data.

Usage:
    uv run python -m app.scripts.init_ohlc_data
"""

import logging
from datetime import datetime, timedelta
from app.database import init_db, upsert_ohlc, update_metadata
from app.polygon.client import fetch_ohlc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']

def main():
    logger.info("Initializing OHLC database...")

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Calculate date range (5 years)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=5*365)

    logger.info(f"Fetching data from {start_date} to {end_date}")

    total_records = 0

    for i, symbol in enumerate(SYMBOLS, 1):
        logger.info(f"[{i}/{len(SYMBOLS)}] Fetching {symbol}...")

        try:
            data = fetch_ohlc(symbol, start_date.isoformat(), end_date.isoformat())

            if data:
                upsert_ohlc(symbol, data)
                update_metadata(symbol, start_date.isoformat(), end_date.isoformat())
                total_records += len(data)
                logger.info(f"  ✓ {symbol}: {len(data)} records")
            else:
                logger.warning(f"  ✗ {symbol}: No data returned")

        except Exception as e:
            logger.error(f"  ✗ {symbol}: Failed - {e}")
            continue

    logger.info(f"\nInitialization complete!")
    logger.info(f"Total records: {total_records}")
    logger.info(f"Database location: {DB_PATH}")

if __name__ == "__main__":
    main()
```

## Error Handling

### Frontend Error Handling

**1. No Data Situations**
- Stock not selected: Display "Select a stock to view chart"
- No database data: Display "No historical data available"
- API error: Display error message + retry button

**2. Loading States**
- Show skeleton or spinner
- Disable time range selector during load

**3. Chart Responsiveness**
- Monitor container size changes
- Redraw chart on resize

### Backend Error Handling

**1. Database Errors**
- Database file missing: Auto-create on first access
- Query failure: Return 500 error + log

**2. Polygon API Errors**
- Rate limiting: Use existing rate_limit() and retry mechanism
- Invalid symbol: Return 404
- Invalid API key: Log error, return 503

**3. Date Range Validation**
- start > end: Return 400 error
- Future dates: Auto-adjust to today

### Edge Cases

**1. Market Holidays**
- Weekends and holidays have no data, chart displays available trading days only

**2. Newly Listed Stocks**
- Less than 5 years of data: Display actual available data

**3. Update Failures**
- Log error, don't affect existing data queries
- Retry on next scheduled run

**4. Concurrent Requests**
- SQLite WAL mode supports concurrent reads
- Write operations use transactions for consistency

## Performance Optimization

**1. Database Queries**
- Use indexes for fast lookups
- Limit result set (max 5 years)

**2. Frontend Rendering**
- Lightweight Charts auto-optimizes large datasets
- Debounce time range switching (300ms)

**3. Caching Strategy**
- Frontend caches loaded data by (symbol + timeRange)
- Avoid duplicate requests

**4. Data Transfer**
- Compress API responses (gzip)
- Only return requested date range

## Dependencies

### Backend New Dependencies

```
# requirements.txt or pyproject.toml
APScheduler==3.10.4  # For scheduled tasks
```

### Frontend New Dependencies

```json
// package.json
{
  "dependencies": {
    "lightweight-charts": "^4.1.0"
  },
  "devDependencies": {
    "@types/lightweight-charts": "^3.8.0"
  }
}
```

## Implementation Phases

### Phase 1: Backend Foundation (Priority)

1. Create database module (`app/database.py`)
2. Initialize database schema
3. Create OHLC API endpoint (`/api/stocks/{symbol}/ohlc`)
4. Write initialization script
5. Test with one stock

### Phase 2: Data Population

1. Run initialization script for all 7 stocks
2. Verify data integrity
3. Test API endpoint with various date ranges

### Phase 3: Scheduled Updates

1. Create update task module
2. Integrate APScheduler with FastAPI
3. Test daily update logic

### Phase 4: Frontend Component

1. Install lightweight-charts
2. Create KLineChart component
3. Implement time range selector
4. Add loading and error states
5. Integrate with HomePage

### Phase 5: Testing & Polish

1. Test all time ranges
2. Test error scenarios
3. Verify scheduled updates
4. Performance testing
5. Documentation

## Testing Strategy

### Backend Tests

- Database operations (CRUD)
- API endpoint responses
- Date range calculations
- Error handling

### Frontend Tests

- Component rendering
- Time range switching
- Data fetching
- Error states

### Integration Tests

- End-to-end data flow
- Scheduled task execution
- API + database integration

## Success Metrics

- Chart renders within 500ms for 1 year data
- Database queries < 100ms
- Scheduled updates complete within 5 minutes
- Zero data loss during updates
- Smooth chart interactions (60fps)

## Future Enhancements

1. **Technical Indicators** - MA, MACD, RSI, etc.
2. **Volume Chart** - Display volume bars below candlesticks
3. **More Stocks** - Support adding custom stocks
4. **Export Data** - Download OHLC data as CSV
5. **Real-time Updates** - WebSocket for intraday data
6. **Chart Annotations** - Mark important events on chart

## Conclusion

This design provides a lightweight, efficient K-line chart feature that integrates seamlessly with the existing stock selector. By using Lightweight Charts and SQLite, we achieve fast rendering and reliable data storage with minimal complexity. The scheduled update mechanism ensures data stays current without manual intervention.
