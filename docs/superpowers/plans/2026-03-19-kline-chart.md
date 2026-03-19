# K-Line Chart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add interactive K-line chart with 5-year historical data and time range selection.

**Architecture:** SQLite database stores OHLC data, FastAPI serves data via REST API, Next.js frontend renders chart using Lightweight Charts library, APScheduler handles daily updates.

**Tech Stack:** SQLite, FastAPI, APScheduler, Next.js, TypeScript, Lightweight Charts, Polygon API

---

## File Map

**Backend - New Files:**
- `app/data/` — Directory for SQLite database
- `app/database.py` — Database connection and CRUD operations
- `app/api/routes/ohlc.py` — OHLC API endpoints
- `app/tasks/update_ohlc.py` — Scheduled update task
- `app/scripts/init_ohlc_data.py` — Data initialization script

**Backend - Modified Files:**
- `app/api/main.py` — Register OHLC router, integrate APScheduler
- `app/api/routes/__init__.py` — Export OHLC router

**Frontend - New Files:**
- `frontend/src/components/chart/KLineChart.tsx` — Main chart component
- `frontend/src/components/chart/TimeRangeSelector.tsx` — Time range buttons

**Frontend - Modified Files:**
- `frontend/src/lib/api.ts` — Add getOHLC method
- `frontend/src/lib/types.ts` — Add OHLC types
- `frontend/src/app/page.tsx` — Integrate KLineChart
- `frontend/package.json` — Add lightweight-charts dependency

---
## Task 1: 后端 — 创建数据库模块

**Files:**
- Create: `app/database.py`
- Create: `app/data/.gitkeep`

- [ ] **Step 1: 创建 data 目录**

```bash
mkdir -p app/data
touch app/data/.gitkeep
```

- [ ] **Step 2: 创建 database.py**

```python
"""SQLite database operations for OHLC data."""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "data" / "finance.db"


def get_conn() -> sqlite3.Connection:
    """Get database connection with WAL mode for concurrent reads."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize database tables and indexes."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ohlc (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date)
        );

        CREATE INDEX IF NOT EXISTS idx_ohlc_symbol_date 
        ON ohlc(symbol, date);

        CREATE TABLE IF NOT EXISTS data_metadata (
            symbol TEXT PRIMARY KEY,
            last_update TEXT,
            data_start TEXT,
            data_end TEXT
        );
    """)
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {DB_PATH}")


def get_ohlc(symbol: str, start: str, end: str) -> List[Dict]:
    """Query OHLC data from database.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        start: Start date in YYYY-MM-DD format
        end: End date in YYYY-MM-DD format
    
    Returns:
        List of OHLC records as dictionaries
    """
    conn = get_conn()
    query = """
        SELECT date, open, high, low, close, volume
        FROM ohlc
        WHERE symbol = ? AND date >= ? AND date <= ?
        ORDER BY date ASC
    """
    rows = conn.execute(query, (symbol.upper(), start, end)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def upsert_ohlc(symbol: str, data: List[Dict]):
    """Insert or update OHLC data (batch operation).
    
    Args:
        symbol: Stock symbol
        data: List of dicts with keys: date, open, high, low, close, volume
    """
    if not data:
        return
    
    conn = get_conn()
    conn.executemany("""
        INSERT INTO ohlc (symbol, date, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, date) DO NOTHING
    """, [(symbol.upper(), d['date'], d['open'], d['high'], d['low'], d['close'], d['volume'])
          for d in data])
    conn.commit()
    conn.close()
    logger.info(f"Upserted {len(data)} records for {symbol}")


def update_metadata(symbol: str, start: str, end: str):
    """Update metadata after data sync.
    
    Args:
        symbol: Stock symbol
        start: Data start date
        end: Data end date
    """
    conn = get_conn()
    conn.execute("""
        INSERT INTO data_metadata (symbol, last_update, data_start, data_end)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            last_update = excluded.last_update,
            data_end = excluded.data_end
    """, (symbol.upper(), datetime.now().isoformat(), start, end))
    conn.commit()
    conn.close()


def get_metadata(symbol: str) -> Optional[Dict]:
    """Get metadata for a symbol."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM data_metadata WHERE symbol = ?",
        (symbol.upper(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
```

- [ ] **Step 3: 验证导入**

```bash
uv run python -c "from app.database import init_db; init_db(); print('✓ Database module OK')"
```
Expected: `✓ Database module OK` 且创建 `app/data/finance.db`

- [ ] **Step 4: Commit**

```bash
git add app/data/.gitkeep app/database.py
git commit -m "feat: add SQLite database module for OHLC data"
```

---

## Task 2: 后端 — 创建 OHLC API 端点

**Files:**
- Create: `app/api/routes/ohlc.py`

- [ ] **Step 1: 创建 ohlc.py**

```python
"""OHLC data API endpoints."""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_ohlc, get_metadata

logger = logging.getLogger(__name__)
router = APIRouter()


class OHLCRecord(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class OHLCResponse(BaseModel):
    symbol: str
    data: List[OHLCRecord]


class DataStatusResponse(BaseModel):
    symbol: str
    last_update: Optional[str]
    data_start: Optional[str]
    data_end: Optional[str]
    total_records: int


@router.get("/{symbol}/ohlc", response_model=OHLCResponse)
def get_stock_ohlc(
    symbol: str,
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Get OHLC data for a stock symbol."""
    # Default to 5 years if not specified
    if not end:
        end = datetime.now().date().isoformat()
    if not start:
        start = (datetime.now().date() - timedelta(days=5*365)).isoformat()
    
    # Validate date range
    try:
        start_date = datetime.fromisoformat(start).date()
        end_date = datetime.fromisoformat(end).date()
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="start date must be before end date")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    
    # Query database
    try:
        data = get_ohlc(symbol, start, end)
        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"No OHLC data found for {symbol}"
            )
        
        return OHLCResponse(
            symbol=symbol.upper(),
            data=[OHLCRecord(**record) for record in data]
        )
    except Exception as e:
        logger.error(f"Failed to fetch OHLC for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/{symbol}/data-status", response_model=DataStatusResponse)
def get_data_status(symbol: str):
    """Get data status for a stock symbol."""
    metadata = get_metadata(symbol)
    
    if not metadata:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for {symbol}"
        )
    
    # Count total records
    from app.database import get_conn
    conn = get_conn()
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM ohlc WHERE symbol = ?",
        (symbol.upper(),)
    ).fetchone()['cnt']
    conn.close()
    
    return DataStatusResponse(
        symbol=symbol.upper(),
        last_update=metadata.get('last_update'),
        data_start=metadata.get('data_start'),
        data_end=metadata.get('data_end'),
        total_records=count
    )
```

- [ ] **Step 2: 验证导入**

```bash
uv run python -c "from app.api.routes.ohlc import router; print('✓ OHLC router OK')"
```
Expected: `✓ OHLC router OK`

- [ ] **Step 3: Commit**

```bash
git add app/api/routes/ohlc.py
git commit -m "feat: add OHLC API endpoints"
```

---
## Task 3: 后端 — 注册 OHLC router

**Files:**
- Modify: `app/api/routes/__init__.py`
- Modify: `app/api/main.py`

- [ ] **Step 1: 更新 routes/__init__.py**

在现有导入中添加：
```python
from . import ohlc
```

在 `__all__` 中添加：
```python
"ohlc",
```

- [ ] **Step 2: 更新 main.py 注册 router**

在现有 router 注册后添加：
```python
from app.api.routes import ohlc
app.include_router(ohlc.router, prefix="/api/stocks", tags=["ohlc"])
```

- [ ] **Step 3: 验证端点可访问**

启动后端（如果未运行）：
```bash
uv run uvicorn app.api.main:app --port 8080 &
sleep 3
curl http://localhost:8080/docs | grep -q "ohlc" && echo "✓ OHLC endpoints registered"
```
Expected: `✓ OHLC endpoints registered`

- [ ] **Step 4: Commit**

```bash
git add app/api/routes/__init__.py app/api/main.py
git commit -m "feat: register OHLC router in FastAPI app"
```

---

## Task 4: 后端 — 创建数据初始化脚本

**Files:**
- Create: `app/scripts/__init__.py`
- Create: `app/scripts/init_ohlc_data.py`

- [ ] **Step 1: 创建 scripts 目录和 __init__.py**

```bash
mkdir -p app/scripts
touch app/scripts/__init__.py
```

- [ ] **Step 2: 创建 init_ohlc_data.py**

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']


def main():
    logger.info("=" * 60)
    logger.info("Initializing OHLC database with 5 years of data")
    logger.info("=" * 60)

    # Initialize database
    init_db()
    logger.info("✓ Database initialized")

    # Calculate date range (5 years)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=5*365)

    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Symbols: {', '.join(SYMBOLS)}")
    logger.info("")

    total_records = 0
    success_count = 0

    for i, symbol in enumerate(SYMBOLS, 1):
        logger.info(f"[{i}/{len(SYMBOLS)}] Fetching {symbol}...")

        try:
            data = fetch_ohlc(symbol, start_date.isoformat(), end_date.isoformat())

            if data:
                upsert_ohlc(symbol, data)
                update_metadata(symbol, start_date.isoformat(), end_date.isoformat())
                total_records += len(data)
                success_count += 1
                logger.info(f"  ✓ {symbol}: {len(data)} records inserted")
            else:
                logger.warning(f"  ✗ {symbol}: No data returned from API")

        except Exception as e:
            logger.error(f"  ✗ {symbol}: Failed - {e}")
            continue

    logger.info("")
    logger.info("=" * 60)
    logger.info("Initialization complete!")
    logger.info(f"Success: {success_count}/{len(SYMBOLS)} stocks")
    logger.info(f"Total records: {total_records:,}")
    logger.info(f"Database: {DB_PATH}")
    logger.info("=" * 60)


if __name__ == "__main__":
    from app.database import DB_PATH
    main()
```

- [ ] **Step 3: 测试脚本（不实际运行，仅验证导入）**

```bash
uv run python -c "from app.scripts.init_ohlc_data import main; print('✓ Init script OK')"
```
Expected: `✓ Init script OK`

- [ ] **Step 4: Commit**

```bash
git add app/scripts/__init__.py app/scripts/init_ohlc_data.py
git commit -m "feat: add OHLC data initialization script"
```

---

## Task 5: 后端 — 创建定时更新任务

**Files:**
- Create: `app/tasks/__init__.py`
- Create: `app/tasks/update_ohlc.py`

- [ ] **Step 1: 创建 tasks 目录和 __init__.py**

```bash
mkdir -p app/tasks
touch app/tasks/__init__.py
```

- [ ] **Step 2: 创建 update_ohlc.py**

```python
"""Scheduled task to update OHLC data daily."""

import logging
from datetime import datetime, timedelta
from app.polygon.client import fetch_ohlc
from app.database import upsert_ohlc, update_metadata

logger = logging.getLogger(__name__)

SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']


def update_daily_ohlc():
    """Update all stocks with latest data (yesterday and today)."""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    start_date = yesterday.isoformat()
    end_date = today.isoformat()

    logger.info(f"Starting daily OHLC update for {start_date} to {end_date}")

    success_count = 0
    total_records = 0

    for symbol in SYMBOLS:
        try:
            data = fetch_ohlc(symbol, start_date, end_date)
            if data:
                upsert_ohlc(symbol, data)
                update_metadata(symbol, start_date, end_date)
                total_records += len(data)
                success_count += 1
                logger.info(f"✓ Updated {symbol}: {len(data)} records")
            else:
                logger.warning(f"✗ No data returned for {symbol}")
        except Exception as e:
            logger.error(f"✗ Failed to update {symbol}: {e}")
            # Continue with other symbols

    logger.info(f"Daily update complete: {success_count}/{len(SYMBOLS)} stocks, {total_records} records")
```

- [ ] **Step 3: 验证导入**

```bash
uv run python -c "from app.tasks.update_ohlc import update_daily_ohlc; print('✓ Update task OK')"
```
Expected: `✓ Update task OK`

- [ ] **Step 4: Commit**

```bash
git add app/tasks/__init__.py app/tasks/update_ohlc.py
git commit -m "feat: add daily OHLC update task"
```

---
## Task 6: 后端 — 集成 APScheduler

**Files:**
- Modify: `app/api/main.py`

- [ ] **Step 1: 在 main.py 顶部添加导入**

```python
from apscheduler.schedulers.background import BackgroundScheduler
from app.tasks.update_ohlc import update_daily_ohlc
import logging

logger = logging.getLogger(__name__)
```

- [ ] **Step 2: 在 app 创建后添加 scheduler 初始化**

```python
# Create scheduler
scheduler = BackgroundScheduler()

@app.on_event("startup")
def start_scheduler():
    """Start scheduled tasks on app startup."""
    # Update daily after US market close (UTC 21:30 = EST 16:30)
    scheduler.add_job(
        update_daily_ohlc,
        'cron',
        hour=21,
        minute=30,
        id='daily_ohlc_update'
    )
    scheduler.start()
    logger.info("✓ Scheduler started: daily OHLC update at 21:30 UTC")

@app.on_event("shutdown")
def shutdown_scheduler():
    """Shutdown scheduler on app shutdown."""
    scheduler.shutdown()
    logger.info("✓ Scheduler stopped")
```

- [ ] **Step 3: 验证导入无误**

```bash
uv run python -c "from app.api.main import app; print('✓ APScheduler integrated')"
```
Expected: `✓ APScheduler integrated`

- [ ] **Step 4: Commit**

```bash
git add app/api/main.py
git commit -m "feat: integrate APScheduler for daily OHLC updates"
```

---

## Task 7: 前端 — 安装 lightweight-charts

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: 安装依赖**

```bash
cd frontend
pnpm add lightweight-charts
pnpm add -D @types/lightweight-charts
cd ..
```

- [ ] **Step 2: 验证安装**

```bash
grep -q "lightweight-charts" frontend/package.json && echo "✓ lightweight-charts installed"
```
Expected: `✓ lightweight-charts installed`

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml
git commit -m "feat: add lightweight-charts dependency"
```

---

## Task 8: 前端 — 新增 OHLC 类型定义

**Files:**
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: 在 types.ts 末尾添加类型**

```typescript
// OHLC Data Types
export interface OHLCRecord {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface OHLCResponse {
  symbol: string;
  data: OHLCRecord[];
}

export interface DataStatusResponse {
  symbol: string;
  last_update: string | null;
  data_start: string | null;
  data_end: string | null;
  total_records: number;
}

export type TimeRange = '1M' | '3M' | '6M' | '1Y' | '5Y';
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/types.ts
git commit -m "feat: add OHLC data types"
```

---

## Task 9: 前端 — 扩展 API 客户端

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: 在 import 中添加新类型**

```typescript
import type {
  ...,
  OHLCResponse,
  DataStatusResponse,
} from './types';
```

- [ ] **Step 2: 在 api 对象中添加方法**

```typescript
// Get OHLC data for a stock
getOHLC: (symbol: string, start?: string, end?: string) => {
  const params = new URLSearchParams();
  if (start) params.append('start', start);
  if (end) params.append('end', end);
  const query = params.toString();
  return fetchAPI<OHLCResponse>(
    `/api/stocks/${symbol}/ohlc${query ? `?${query}` : ''}`
  );
},

// Get data status for a stock
getDataStatus: (symbol: string) =>
  fetchAPI<DataStatusResponse>(`/api/stocks/${symbol}/data-status`),
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: add OHLC API methods to client"
```

---

## Task 10: 前端 — 创建 TimeRangeSelector 组件

**Files:**
- Create: `frontend/src/components/chart/TimeRangeSelector.tsx`

- [ ] **Step 1: 创建 TimeRangeSelector.tsx**

```tsx
'use client';

import { Button } from '@/components/ui/button';
import type { TimeRange } from '@/lib/types';

interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
  disabled?: boolean;
}

const TIME_RANGES: TimeRange[] = ['1M', '3M', '6M', '1Y', '5Y'];

export function TimeRangeSelector({ value, onChange, disabled }: TimeRangeSelectorProps) {
  return (
    <div className="flex gap-1">
      {TIME_RANGES.map((range) => (
        <Button
          key={range}
          variant={value === range ? 'default' : 'outline'}
          size="sm"
          onClick={() => onChange(range)}
          disabled={disabled}
          className="min-w-[50px]"
        >
          {range}
        </Button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/chart/TimeRangeSelector.tsx
git commit -m "feat: add TimeRangeSelector component"
```

---
## Task 11: 前端 — 创建 KLineChart 组件

**Files:**
- Create: `frontend/src/components/chart/KLineChart.tsx`

- [ ] **Step 1: 创建 KLineChart.tsx（第1部分：导入和类型）**

```tsx
'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, IChartApi, CandlestickData } from 'lightweight-charts';
import { TimeRangeSelector } from './TimeRangeSelector';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import type { TimeRange, OHLCRecord } from '@/lib/types';

interface KLineChartProps {
  selectedStock: string | null;
}

function calculateDateRange(range: TimeRange): { start: string; end: string } {
  const end = new Date();
  const start = new Date();

  switch (range) {
    case '1M':
      start.setMonth(start.getMonth() - 1);
      break;
    case '3M':
      start.setMonth(start.getMonth() - 3);
      break;
    case '6M':
      start.setMonth(start.getMonth() - 6);
      break;
    case '1Y':
      start.setFullYear(start.getFullYear() - 1);
      break;
    case '5Y':
      start.setFullYear(start.getFullYear() - 5);
      break;
  }

  return {
    start: start.toISOString().split('T')[0],
    end: end.toISOString().split('T')[0],
  };
}
```

- [ ] **Step 2: 创建 KLineChart.tsx（第2部分：组件主体）**

```tsx
export function KLineChart({ selectedStock }: KLineChartProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('3M');
  const [ohlcData, setOhlcData] = useState<OHLCRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const { toast } = useToast();

  // Fetch OHLC data
  const fetchData = useCallback(async () => {
    if (!selectedStock) {
      setOhlcData([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const { start, end } = calculateDateRange(timeRange);
      const response = await api.getOHLC(selectedStock, start, end);
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

  useEffect(() => {
    fetchData();
  }, [fetchData]);
```

- [ ] **Step 3: 创建 KLineChart.tsx（第3部分：图表渲染）**

```tsx
  // Create and update chart
  useEffect(() => {
    if (!chartContainerRef.current || ohlcData.length === 0) {
      return;
    }

    // Create chart
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
    const formattedData: CandlestickData[] = ohlcData.map((d) => ({
      time: d.date,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    candlestickSeries.setData(formattedData);
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
  }, [ohlcData]);
```

- [ ] **Step 4: 创建 KLineChart.tsx（第4部分：渲染 JSX）**

```tsx
  // Render
  if (!selectedStock) {
    return (
      <div className="h-full flex items-center justify-center border rounded-lg bg-card">
        <p className="text-sm text-muted-foreground">Select a stock to view chart</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex flex-col items-center justify-center border rounded-lg bg-card gap-2">
        <p className="text-sm text-destructive">{error}</p>
        <button
          onClick={fetchData}
          className="text-sm text-primary hover:underline"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col border rounded-lg bg-card p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold">
          {selectedStock} - K-Line Chart
        </h3>
        <TimeRangeSelector
          value={timeRange}
          onChange={setTimeRange}
          disabled={loading}
        />
      </div>

      {/* Chart */}
      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : ohlcData.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-muted-foreground">No data available</p>
        </div>
      ) : (
        <div ref={chartContainerRef} className="flex-1" />
      )}
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/chart/KLineChart.tsx
git commit -m "feat: add KLineChart component with Lightweight Charts"
```

---

## Task 12: 前端 — 集成 KLineChart 到 HomePage

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: 添加导入**

```typescript
import { KLineChart } from '@/components/chart/KLineChart';
```

- [ ] **Step 2: 替换 K-line chart placeholder**

将：
```tsx
{/* Bottom: K-line chart placeholder (60% height) */}
<div className="flex-1 border rounded-lg flex items-center justify-center text-muted-foreground text-sm">
  {selectedStock
    ? `${selectedStock} K-Line Chart (coming soon)`
    : 'Select a stock to view chart'}
</div>
```

改为：
```tsx
{/* Bottom: K-line chart (60% height) */}
<div className="flex-1 overflow-hidden">
  <KLineChart selectedStock={selectedStock} />
</div>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat: integrate KLineChart into HomePage"
```

---

## Task 13: 数据初始化（手动执行）

**Files:**
- None (manual execution)

- [ ] **Step 1: 运行初始化脚本**

```bash
uv run python -m app.scripts.init_ohlc_data
```

Expected: 成功下载 7 只股票的 5 年数据，显示进度和统计信息

- [ ] **Step 2: 验证数据库**

```bash
uv run python -c "
from app.database import get_conn
conn = get_conn()
count = conn.execute('SELECT COUNT(*) as cnt FROM ohlc').fetchone()['cnt']
print(f'✓ Total OHLC records: {count}')
conn.close()
"
```

Expected: `✓ Total OHLC records: 8000+`

- [ ] **Step 3: 测试 API 端点**

```bash
curl -s http://localhost:8080/api/stocks/AAPL/ohlc?start=2025-01-01 | python -m json.tool | head -20
```

Expected: 返回 AAPL 的 OHLC 数据 JSON

- [ ] **Step 4: 记录完成**

```bash
echo "Data initialization completed at $(date)" >> app/data/init.log
git add app/data/init.log
git commit -m "chore: complete OHLC data initialization"
```

---

## Verification

完成所有 Task 后，执行以下验证：

**后端验证：**
1. 数据库文件存在：`ls -lh app/data/finance.db`
2. API 端点可访问：`curl http://localhost:8080/api/stocks/AAPL/data-status`
3. 定时任务已注册：检查启动日志中的 "Scheduler started" 消息

**前端验证：**
1. 启动前端：`cd frontend && pnpm dev`
2. 访问 `http://localhost:3000`
3. 选择一个股票（如 AAPL）
4. 确认 K 线图正确显示
5. 切换时间范围（1M, 3M, 6M, 1Y, 5Y）
6. 验证图表数据更新
7. 测试缩放和平移交互
8. 测试错误状态（选择无数据的股票）

**性能验证：**
1. 图表渲染时间 < 500ms
2. 时间范围切换流畅
3. 图表交互 60fps

**集成验证：**
1. 选择不同股票，图表正确更新
2. 刷新页面，状态保持
3. 后端日志无错误
4. 前端控制台无错误
