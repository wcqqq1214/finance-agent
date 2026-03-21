# Crypto 资产切换功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Home 页面支持 Crypto/Stocks 模式切换，Crypto 模式下显示 BTC、ETH 并从 OKX 获取 K线数据

**Architecture:** 扩展现有 OHLC 接口支持加密货币，后端根据 symbol 格式（包含"-"）自动路由到 OKX API，前端组件接收 assetType 参数以支持不同时间周期和数据源

**Tech Stack:** FastAPI, OKX SDK, Next.js, TypeScript, lightweight-charts

**Spec:** `docs/superpowers/specs/2026-03-21-crypto-asset-toggle-design.md`

---

## File Structure

### Backend Files
- **Modify:** `app/okx/trading_client.py` - 添加 `get_candles()` 和 `get_ticker()` 方法
- **Create:** `app/api/routes/crypto.py` - 新建加密货币报价路由
- **Modify:** `app/api/routes/ohlc.py` - 扩展支持加密货币 OHLC
- **Modify:** `app/api/main.py` - 注册 crypto 路由
- **Create:** `tests/test_okx_market_data.py` - OKX 市场数据测试
- **Create:** `tests/test_crypto_routes.py` - 加密货币路由测试

### Frontend Files
- **Modify:** `frontend/src/lib/types.ts` - 扩展类型定义
- **Modify:** `frontend/src/lib/api.ts` - 添加 crypto API 方法
- **Modify:** `frontend/src/components/chart/TimeRangeSelector.tsx` - 支持 crypto 时间周期
- **Modify:** `frontend/src/components/chart/KLineChart.tsx` - 接收 assetType 参数
- **Modify:** `frontend/src/components/asset/AssetSelector.tsx` - 支持 crypto 资产显示
- **Modify:** `frontend/src/app/page.tsx` - 传递 assetType 参数

---


## Task 1: OKXTradingClient - 添加 get_candles() 方法

**Files:**
- Modify: `app/okx/trading_client.py:100-end`
- Test: `tests/test_okx_market_data.py` (new)

- [ ] **Step 1: 编写 get_candles() 测试**

```python
# tests/test_okx_market_data.py
import pytest
from app.okx.trading_client import OKXTradingClient
from app.okx.exceptions import OKXError

@pytest.mark.asyncio
async def test_get_candles_success():
    """测试成功获取K线数据"""
    client = OKXTradingClient(
        api_key="test_key",
        secret_key="test_secret",
        passphrase="test_pass",
        is_demo=True
    )
    
    candles = await client.get_candles(
        inst_id="BTC-USDT",
        bar="1H",
        limit=10
    )
    
    assert isinstance(candles, list)
    assert len(candles) > 0
    assert "ts" in candles[0]
    assert "o" in candles[0]
    assert "h" in candles[0]
    assert "l" in candles[0]
    assert "c" in candles[0]
    assert "vol" in candles[0]

@pytest.mark.asyncio
async def test_get_candles_invalid_symbol():
    """测试无效symbol"""
    client = OKXTradingClient(
        api_key="test_key",
        secret_key="test_secret",
        passphrase="test_pass",
        is_demo=True
    )
    
    with pytest.raises(OKXError):
        await client.get_candles(inst_id="INVALID", bar="1H")
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/wcqqq21/finance-agent
uv run pytest tests/test_okx_market_data.py::test_get_candles_success -v
```

Expected: FAIL - "AttributeError: 'OKXTradingClient' object has no attribute 'get_candles'"

- [ ] **Step 3: 实现 get_candles() 方法**

```python
# app/okx/trading_client.py (在类中添加)
async def get_candles(
    self,
    inst_id: str,
    bar: str = "15m",
    limit: int = 300,
    after: str = "",
    before: str = ""
) -> List[Dict[str, Any]]:
    """获取K线数据

    Args:
        inst_id: 产品ID，如 BTC-USDT
        bar: K线周期 (15m, 1H, 4H, 1D, 1W, 1M, 1Y)
        limit: 返回数据条数，最大300
        after: 请求此时间戳之前的数据
        before: 请求此时间戳之后的数据

    Returns:
        List of candle data with keys: ts, o, h, l, c, vol
    """
    try:
        result = await asyncio.to_thread(
            self.market_api.get_candlesticks,
            instId=inst_id,
            bar=bar,
            limit=str(limit),
            after=after,
            before=before
        )

        if result.get("code") != "0":
            raise OKXError(f"Failed to get candles: {result.get('msg')}")

        # 转换数据格式
        candles = []
        for item in result.get("data", []):
            candles.append({
                "ts": item[0],
                "o": item[1],
                "h": item[2],
                "l": item[3],
                "c": item[4],
                "vol": item[5]
            })

        logger.info(f"[OKX-{'DEMO' if self.is_demo else 'LIVE'}] Got {len(candles)} candles for {inst_id}")
        return candles
        
    except OKXError:
        raise
    except Exception as e:
        logger.error(f"Failed to get candles for {inst_id}: {e}")
        raise OKXError(f"Failed to get candles: {str(e)}")
```

- [ ] **Step 4: 运行测试验证通过**

```bash
uv run pytest tests/test_okx_market_data.py::test_get_candles_success -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add app/okx/trading_client.py tests/test_okx_market_data.py
git commit -m "feat(okx): add get_candles method to OKXTradingClient"
```

---

## Task 2: OKXTradingClient - 添加 get_ticker() 方法

**Files:**
- Modify: `app/okx/trading_client.py` (after get_candles)
- Test: `tests/test_okx_market_data.py`

- [ ] **Step 1: 编写 get_ticker() 测试**

```python
# tests/test_okx_market_data.py (追加)
@pytest.mark.asyncio
async def test_get_ticker_success():
    """测试成功获取ticker数据"""
    client = OKXTradingClient(
        api_key="test_key",
        secret_key="test_secret",
        passphrase="test_pass",
        is_demo=True
    )
    
    ticker = await client.get_ticker("BTC-USDT")
    
    assert isinstance(ticker, dict)
    assert "instId" in ticker
    assert "last" in ticker
    assert "open24h" in ticker
    assert "high24h" in ticker
    assert "low24h" in ticker
    assert "vol24h" in ticker

@pytest.mark.asyncio
async def test_get_ticker_no_data():
    """测试无数据情况"""
    client = OKXTradingClient(
        api_key="test_key",
        secret_key="test_secret",
        passphrase="test_pass",
        is_demo=True
    )
    
    with pytest.raises(OKXError, match="No ticker data"):
        await client.get_ticker("INVALID-PAIR")
```

- [ ] **Step 2: 运行测试验证失败**

```bash
uv run pytest tests/test_okx_market_data.py::test_get_ticker_success -v
```

Expected: FAIL - "AttributeError: 'OKXTradingClient' object has no attribute 'get_ticker'"

- [ ] **Step 3: 实现 get_ticker() 方法**

```python
# app/okx/trading_client.py (在 get_candles 后添加)
async def get_ticker(self, inst_id: str) -> Dict[str, Any]:
    """获取单个产品行情信息

    Args:
        inst_id: 产品ID，如 BTC-USDT

    Returns:
        Ticker data with keys: instId, last, open24h, high24h, low24h, vol24h, etc.
    """
    try:
        result = await asyncio.to_thread(
            self.market_api.get_ticker,
            instId=inst_id
        )

        if result.get("code") != "0":
            raise OKXError(f"Failed to get ticker: {result.get('msg')}")

        data = result.get("data", [])
        if not data:
            raise OKXError(f"No ticker data for {inst_id}")

        logger.info(f"[OKX-{'DEMO' if self.is_demo else 'LIVE'}] Got ticker for {inst_id}")
        return data[0]
        
    except OKXError:
        raise
    except Exception as e:
        logger.error(f"Failed to get ticker for {inst_id}: {e}")
        raise OKXError(f"Failed to get ticker: {str(e)}")
```

- [ ] **Step 4: 运行测试验证通过**

```bash
uv run pytest tests/test_okx_market_data.py::test_get_ticker_success -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add app/okx/trading_client.py tests/test_okx_market_data.py
git commit -m "feat(okx): add get_ticker method to OKXTradingClient"
```

---

## Task 3: 创建加密货币报价路由

**Files:**
- Create: `app/api/routes/crypto.py`
- Test: `tests/test_crypto_routes.py` (new)
- Modify: `app/api/main.py`

- [ ] **Step 1: 编写路由测试**

```python
# tests/test_crypto_routes.py
import pytest
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

def test_get_crypto_quotes_success():
    """测试成功获取加密货币报价"""
    response = client.get("/api/crypto/quotes?symbols=BTC-USDT,ETH-USDT")
    
    assert response.status_code == 200
    data = response.json()
    assert "quotes" in data
    assert len(data["quotes"]) == 2
    
    btc_quote = data["quotes"][0]
    assert btc_quote["symbol"] == "BTC-USDT"
    assert btc_quote["name"] == "Bitcoin"
    assert "price" in btc_quote
    assert "change" in btc_quote
    assert "volume24h" in btc_quote

def test_get_crypto_quotes_missing_symbols():
    """测试缺少symbols参数"""
    response = client.get("/api/crypto/quotes")
    assert response.status_code == 422  # Validation error
```

- [ ] **Step 2: 运行测试验证失败**

```bash
uv run pytest tests/test_crypto_routes.py::test_get_crypto_quotes_success -v
```

Expected: FAIL - "404 Not Found" (路由不存在)

- [ ] **Step 3: 创建 crypto.py 路由文件**

```python
# app/api/routes/crypto.py
"""加密货币报价 API 端点"""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List

from app.okx import get_okx_client
from app.okx.exceptions import OKXError, OKXAuthError, OKXRateLimitError

logger = logging.getLogger(__name__)
router = APIRouter()


class CryptoQuote(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    changeAmount: float
    volume24h: float
    high24h: float
    low24h: float


class CryptoQuotesResponse(BaseModel):
    quotes: List[CryptoQuote]


# 加密货币名称映射
CRYPTO_NAMES = {
    "BTC-USDT": "Bitcoin",
    "ETH-USDT": "Ethereum"
}


@router.get("/quotes", response_model=CryptoQuotesResponse)
async def get_crypto_quotes(
    symbols: str = Query(..., description="Comma-separated crypto symbols (e.g., BTC-USDT,ETH-USDT)")
):
    """获取加密货币实时报价"""
    symbol_list = [s.strip() for s in symbols.split(",")]
    
    try:
        client = get_okx_client("demo")
        quotes = []
        
        for symbol in symbol_list:
            ticker = await client.get_ticker(symbol)
            
            # 计算涨跌幅
            last_price = float(ticker["last"])
            open_price = float(ticker["open24h"])
            change_amount = last_price - open_price
            change_percent = (change_amount / open_price) * 100 if open_price > 0 else 0
            
            quotes.append(CryptoQuote(
                symbol=symbol,
                name=CRYPTO_NAMES.get(symbol, symbol),
                price=last_price,
                change=change_percent,
                changeAmount=change_amount,
                volume24h=float(ticker["vol24h"]),
                high24h=float(ticker["high24h"]),
                low24h=float(ticker["low24h"])
            ))
        
        logger.info(f"Successfully fetched quotes for {len(quotes)} crypto symbols")
        return CryptoQuotesResponse(quotes=quotes)
        
    except OKXAuthError as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except OKXRateLimitError as e:
        logger.error(f"Rate limit error: {e}")
        raise HTTPException(status_code=429, detail=str(e))
    except OKXError as e:
        logger.error(f"OKX error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch crypto quotes: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch crypto quotes: {str(e)}"
        )
```

- [ ] **Step 4: 在 main.py 中注册路由**

```python
# app/api/main.py (在现有路由注册后添加)
from app.api.routes import crypto

app.include_router(crypto.router, prefix="/api/crypto", tags=["crypto"])
```

- [ ] **Step 5: 运行测试验证通过**

```bash
uv run pytest tests/test_crypto_routes.py::test_get_crypto_quotes_success -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add app/api/routes/crypto.py app/api/main.py tests/test_crypto_routes.py
git commit -m "feat(api): add crypto quotes endpoint"
```



## Task 4: 创建 crypto_ohlc 数据表

**Files:**
- Modify: `app/database/schema.py`
- Create: `app/database/crypto_ohlc.py`

- [ ] **Step 1: 在 schema.py 中添加 crypto_ohlc 表定义**

在 SCHEMA 字符串的 ohlc 表定义后添加：

```python
CREATE TABLE IF NOT EXISTS crypto_ohlc (
    symbol        TEXT NOT NULL,
    timestamp     INTEGER NOT NULL,
    date          TEXT NOT NULL,
    open          REAL,
    high          REAL,
    low           REAL,
    close         REAL,
    volume        REAL,
    bar           TEXT NOT NULL,
    PRIMARY KEY (symbol, timestamp, bar)
);
CREATE INDEX IF NOT EXISTS idx_crypto_ohlc_symbol_date ON crypto_ohlc(symbol, date DESC);
CREATE INDEX IF NOT EXISTS idx_crypto_ohlc_symbol_bar ON crypto_ohlc(symbol, bar, date DESC);

CREATE TABLE IF NOT EXISTS crypto_metadata (
    symbol TEXT NOT NULL,
    bar TEXT NOT NULL,
    last_update TEXT,
    data_start TEXT,
    data_end TEXT,
    total_records INTEGER,
    PRIMARY KEY (symbol, bar)
);
```

- [ ] **Step 2: 创建 crypto_ohlc.py 数据操作模块**

```python
# app/database/crypto_ohlc.py
"""Crypto OHLC data operations for the database."""

import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime

from app.database.schema import get_conn

logger = logging.getLogger(__name__)


def get_crypto_ohlc(symbol: str, bar: str, start: str, end: str) -> List[Dict]:
    """Query crypto OHLC data from database."""
    conn = get_conn()
    query = """
        SELECT timestamp, date, open, high, low, close, volume
        FROM crypto_ohlc
        WHERE symbol = ? AND bar = ? AND date >= ? AND date <= ?
        ORDER BY timestamp ASC
    """
    rows = conn.execute(query, (symbol, bar, start, end)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def upsert_crypto_ohlc(symbol: str, bar: str, data: List[Dict]):
    """Insert or update crypto OHLC data (batch operation)."""
    if not data:
        return
    conn = get_conn()
    conn.executemany("""
        INSERT INTO crypto_ohlc (symbol, timestamp, date, open, high, low, close, volume, bar)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, timestamp, bar) DO UPDATE SET
            open = excluded.open,
            high = excluded.high,
            low = excluded.low,
            close = excluded.close,
            volume = excluded.volume,
            date = excluded.date
    """, [(symbol, d["timestamp"], d["date"], d["open"], d["high"], d["low"], d["close"], d["volume"], bar)
          for d in data])
    conn.commit()
    conn.close()
    logger.info(f"Upserted {len(data)} records for {symbol} ({bar})")


def update_crypto_metadata(symbol: str, bar: str, start: str, end: str, total_records: int):
    """Update metadata after crypto data sync."""
    conn = get_conn()
    conn.execute("""
        INSERT INTO crypto_metadata (symbol, bar, last_update, data_start, data_end, total_records)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, bar) DO UPDATE SET
            last_update = excluded.last_update,
            data_end = excluded.data_end,
            total_records = excluded.total_records
    """, (symbol, bar, datetime.now().isoformat(), start, end, total_records))
    conn.commit()
    conn.close()


def get_crypto_metadata(symbol: str, bar: str) -> Optional[Dict]:
    """Get metadata for a crypto symbol and bar."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM crypto_metadata WHERE symbol = ? AND bar = ?",
        (symbol, bar)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
```

- [ ] **Step 3: 运行数据库迁移**

```bash
cd /home/wcqqq21/finance-agent
uv run python -c "from app.database.schema import init_db; init_db()"
```

Expected: Tables created successfully

- [ ] **Step 4: 提交**

```bash
git add app/database/schema.py app/database/crypto_ohlc.py
git commit -m "feat(db): add crypto_ohlc table and operations"
```


---

## Task 5: 创建 OKX 数据抓取脚本

**Files:**
- Create: `scripts/fetch_crypto_ohlc.py`

- [ ] **Step 1: 创建数据抓取脚本**

```python
# scripts/fetch_crypto_ohlc.py
"""Fetch crypto OHLC data from OKX and store in database."""

import asyncio
import logging
from datetime import datetime

from app.okx import get_okx_client
from app.database.crypto_ohlc import upsert_crypto_ohlc, update_crypto_metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CRYPTO_SYMBOLS = ["BTC-USDT", "ETH-USDT"]
TIME_BARS = ["15m", "1H", "4H", "1D", "1W", "1M"]


async def fetch_and_store(symbol: str, bar: str, limit: int = 300):
    """Fetch OHLC data for a symbol and bar, then store in database."""
    try:
        logger.info(f"Fetching {symbol} {bar} data...")
        client = get_okx_client("demo")
        
        candles = await client.get_candles(
            inst_id=symbol,
            bar=bar,
            limit=limit
        )
        
        if not candles:
            logger.warning(f"No data returned for {symbol} {bar}")
            return
        
        records = []
        for candle in candles:
            timestamp = int(candle["ts"])
            date_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
            
            records.append({
                "timestamp": timestamp,
                "date": date_str,
                "open": float(candle["o"]),
                "high": float(candle["h"]),
                "low": float(candle["l"]),
                "close": float(candle["c"]),
                "volume": float(candle["vol"])
            })
        
        upsert_crypto_ohlc(symbol, bar, records)
        
        dates = [r["date"] for r in records]
        update_crypto_metadata(
            symbol=symbol,
            bar=bar,
            start=min(dates),
            end=max(dates),
            total_records=len(records)
        )
        
        logger.info(f"Successfully stored {len(records)} records for {symbol} {bar}")
        
    except Exception as e:
        logger.error(f"Failed to fetch {symbol} {bar}: {e}")


async def fetch_all():
    """Fetch data for all symbols and bars."""
    for symbol in CRYPTO_SYMBOLS:
        for bar in TIME_BARS:
            await fetch_and_store(symbol, bar)
            await asyncio.sleep(0.5)  # Rate limiting


if __name__ == "__main__":
    asyncio.run(fetch_all())
```
- [ ] **Step 2: 测试脚本运行**

```bash
cd /home/wcqqq21/finance-agent
uv run python scripts/fetch_crypto_ohlc.py
```

Expected: Data fetched and stored successfully for all symbols and bars

- [ ] **Step 3: 验证数据**

```bash
uv run python -c "
from app.database.crypto_ohlc import get_crypto_metadata
print('BTC-USDT 1H:', get_crypto_metadata('BTC-USDT', '1H'))
print('ETH-USDT 1D:', get_crypto_metadata('ETH-USDT', '1D'))
"
```

Expected: Metadata 显示成功，包含 total_records

- [ ] **Step 4: 提交**

```bash
git add scripts/fetch_crypto_ohlc.py
git commit -m "feat(scripts): add crypto OHLC data fetching script"
```

---

## Task 6: 修改 OHLC 路由从数据库读取

**Files:**
- Modify: `app/api/routes/ohlc.py`
- Test: `tests/test_crypto_routes.py`

- [ ] **Step 1: 编写 crypto OHLC 测试**

```python
# tests/test_crypto_routes.py (追加)
def test_get_crypto_ohlc_success():
    """测试成功获取加密货币OHLC数据"""
    response = client.get("/api/stocks/BTC-USDT/ohlc?interval=1h")
    
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTC-USDT"
    assert "data" in data
    assert len(data["data"]) > 0

def test_get_stock_ohlc_still_works():
    """测试股票OHLC仍然正常工作"""
    response = client.get("/api/stocks/AAPL/ohlc?interval=day")
    assert response.status_code == 200

def test_get_crypto_ohlc_invalid_interval():
    """测试无效的时间周期"""
    response = client.get("/api/stocks/BTC-USDT/ohlc?interval=invalid")
    assert response.status_code == 400
```

- [ ] **Step 2: 运行测试验证失败**

```bash
uv run pytest tests/test_crypto_routes.py::test_get_crypto_ohlc_success -v
```

Expected: FAIL - 路由尝试从 stocks 表查询 BTC-USDT

- [ ] **Step 3: 添加 get_crypto_ohlc_from_db 函数**

```python
# app/api/routes/ohlc.py
# 在文件顶部添加导入
from app.database.crypto_ohlc import get_crypto_ohlc
from datetime import datetime, timedelta

# 在 get_stock_ohlc_from_db 后添加此函数
def get_crypto_ohlc_from_db(
    symbol: str,
    start: Optional[str],
    end: Optional[str],
    interval: str
) -> OHLCResponse:
    """从数据库获取加密货币 OHLC 数据"""
    
    # 时间周期映射
    interval_map = {
        "15m": "15m",
        "1h": "1H",
        "4h": "4H",
        "1d": "1D",
        "day": "1D",
        "1w": "1W",
        "week": "1W",
        "1m": "1M",
        "month": "1M",
        "1y": "1Y",
        "year": "1Y"
    }
    
    bar = interval_map.get(interval.lower())
    if not bar:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid interval for crypto: {interval}"
        )
    
    # Default to recent data if not specified
    if not end:
        end = datetime.now().date().isoformat()
    if not start:
        if bar in ["15m", "1H"]:
            start = (datetime.now().date() - timedelta(days=7)).isoformat()
        elif bar in ["4H", "1D"]:
            start = (datetime.now().date() - timedelta(days=90)).isoformat()
        else:
            start = (datetime.now().date() - timedelta(days=365)).isoformat()
    
    try:
        data = get_crypto_ohlc(symbol, bar, start, end)
        
        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"No OHLC data found for {symbol}. Run fetch script first."
            )
        
        ohlc_records = [
            OHLCRecord(
                date=record["date"],
                open=record["open"],
                high=record["high"],
                low=record["low"],
                close=record["close"],
                volume=record["volume"]
            )
            for record in data
        ]
        
        logger.info(f"Fetched {len(ohlc_records)} OHLC records for {symbol}")
        return OHLCResponse(symbol=symbol, data=ohlc_records)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch crypto OHLC for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch crypto data: {str(e)}"
        )
```

- [ ] **Step 4: 修改路由函数添加分发逻辑**

```python
@router.get("/{symbol}/ohlc", response_model=OHLCResponse)
def get_stock_ohlc(...):
    """获取 OHLC 数据（支持股票和加密货币）"""
    if "-" in symbol:
        return get_crypto_ohlc_from_db(symbol, start, end, interval)
    else:
        return get_stock_ohlc_from_db(symbol, start, end, interval)
```

- [ ] **Step 5: 运行测试验证通过**

```bash
uv run pytest tests/test_crypto_routes.py::test_get_crypto_ohlc_success -v
uv run pytest tests/test_crypto_routes.py::test_get_stock_ohlc_still_works -v
```

Expected: PASS (both tests)

- [ ] **Step 6: 提交**

```bash
git add app/api/routes/ohlc.py tests/test_crypto_routes.py
git commit -m "feat(api): extend OHLC route to support crypto from database"
```

## Task 7: 扩展前端类型定义

**Files:**
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: 扩展 TimeRange 类型**

```typescript
// frontend/src/lib/types.ts
// 找到现有的 TimeRange 定义并替换
export type TimeRange = 
  | 'D' | 'W' | 'M' | 'Y'           // Stocks
  | '15M' | '1H' | '4H'              // Crypto short-term
  | '1D' | '1W' | '1M' | '1Y';       // Crypto long-term
```

- [ ] **Step 2: 添加 CryptoQuote 类型**

```typescript
// frontend/src/lib/types.ts (在文件末尾添加)
export interface CryptoQuote {
  symbol: string;      // BTC-USDT
  name: string;        // Bitcoin
  price: number;
  change: number;
  changeAmount: number;
  volume24h: number;
  high24h: number;
  low24h: number;
}

export interface CryptoQuotesResponse {
  quotes: CryptoQuote[];
}
```

- [ ] **Step 3: 验证类型定义**

```bash
cd /home/wcqqq21/finance-agent/frontend
pnpm run type-check
```

Expected: No type errors

- [ ] **Step 4: 提交**

```bash
git add frontend/src/lib/types.ts
git commit -m "feat(frontend): extend types for crypto support"
```

---

## Task 8: 扩展 API 客户端

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: 添加 getCryptoQuotes 方法**

```typescript
// frontend/src/lib/api.ts
// 在 api 对象中添加新方法（在 getDataStatus 后）
export const api = {
  // ... 现有方法 ...

  // Get crypto quotes
  getCryptoQuotes: (symbols: string[]) =>
    fetchAPI<CryptoQuotesResponse>(
      `/api/crypto/quotes?symbols=${symbols.join(',')}`
    ),
};
```

- [ ] **Step 2: 验证 API 类型**

```bash
cd /home/wcqqq21/finance-agent/frontend
pnpm run type-check
```

Expected: No type errors

- [ ] **Step 3: 提交**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat(frontend): add getCryptoQuotes API method"
```


## Task 9: 改造 TimeRangeSelector 组件

**Files:**
- Modify: `frontend/src/components/chart/TimeRangeSelector.tsx`

- [ ] **Step 1: 更新组件 Props 接口**

```typescript
// frontend/src/components/chart/TimeRangeSelector.tsx
interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
  disabled?: boolean;
  assetType: 'crypto' | 'stocks';  // 新增
}
```

- [ ] **Step 2: 根据 assetType 渲染不同选项**

```typescript
// frontend/src/components/chart/TimeRangeSelector.tsx
export function TimeRangeSelector({ 
  value, 
  onChange, 
  disabled,
  assetType 
}: TimeRangeSelectorProps) {
  // 根据资产类型定义时间周期选项
  const stockRanges: TimeRange[] = ['D', 'W', 'M', 'Y'];
  const cryptoRanges: TimeRange[] = ['15M', '1H', '4H', '1D', '1W', '1M', '1Y'];
  const ranges = assetType === 'crypto' ? cryptoRanges : stockRanges;

  return (
    <div className="flex gap-1">
      {ranges.map((range) => (
        <button
          key={range}
          onClick={() => onChange(range)}
          disabled={disabled}
          className={`px-2 py-1 text-xs rounded transition-colors ${
            value === range
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted hover:bg-muted/80 text-muted-foreground'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          {range}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: 验证类型检查**

```bash
cd /home/wcqqq21/finance-agent/frontend
pnpm run type-check
```

Expected: No type errors

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/chart/TimeRangeSelector.tsx
git commit -m "feat(frontend): add assetType support to TimeRangeSelector"
```

---

## Task 10: 改造 KLineChart 组件

**Files:**
- Modify: `frontend/src/components/chart/KLineChart.tsx`

- [ ] **Step 1: 更新组件 Props 接口**

```typescript
// frontend/src/components/chart/KLineChart.tsx
interface KLineChartProps {
  selectedStock: string | null;
  assetType: 'crypto' | 'stocks';  // 新增
}
```

- [ ] **Step 2: 根据 assetType 设置默认时间周期**

```typescript
// frontend/src/components/chart/KLineChart.tsx
export function KLineChart({ selectedStock, assetType }: KLineChartProps) {
  // 根据资产类型设置默认时间周期
  const defaultTimeRange: TimeRange = assetType === 'crypto' ? '15M' : 'D';
  const [timeRange, setTimeRange] = useState<TimeRange>(defaultTimeRange);
  
  // ... 其余代码保持不变
```

- [ ] **Step 3: 更新 TimeRangeSelector 调用**

```typescript
// frontend/src/components/chart/KLineChart.tsx
// 在 JSX 中找到 TimeRangeSelector 并添加 assetType prop
<TimeRangeSelector
  value={timeRange}
  onChange={setTimeRange}
  disabled={loading}
  assetType={assetType}  // 新增
/>
```

- [ ] **Step 4: 更新 interval 映射以支持 crypto**

```typescript
// frontend/src/components/chart/KLineChart.tsx
// 在 fetchData 函数中更新 intervalMap
const intervalMap: Record<TimeRange, string> = {
  // Stocks
  'D': 'day',
  'W': 'week',
  'M': 'month',
  'Y': 'year',
  // Crypto
  '15M': '15m',
  '1H': '1h',
  '4H': '4h',
  '1D': '1d',
  '1W': '1w',
  '1M': '1m',
  '1Y': '1y',
};
```

- [ ] **Step 5: 添加 assetType 变化时重置时间周期的效果**

```typescript
// frontend/src/components/chart/KLineChart.tsx
// 在组件中添加 useEffect
useEffect(() => {
  // 当 assetType 变化时，重置为默认时间周期
  const newDefault: TimeRange = assetType === 'crypto' ? '15M' : 'D';
  setTimeRange(newDefault);
}, [assetType]);
```

- [ ] **Step 6: 验证类型检查**

```bash
cd /home/wcqqq21/finance-agent/frontend
pnpm run type-check
```

Expected: No type errors

- [ ] **Step 7: 提交**

```bash
git add frontend/src/components/chart/KLineChart.tsx
git commit -m "feat(frontend): add assetType support to KLineChart"
```

---

## Task 11: 改造 AssetSelector 组件

**Files:**
- Modify: `frontend/src/components/asset/AssetSelector.tsx`

- [ ] **Step 1: 定义加密货币常量**

```typescript
// frontend/src/components/asset/AssetSelector.tsx
// 在文件顶部添加
const CRYPTO_SYMBOLS = [
  { symbol: 'BTC-USDT', name: 'Bitcoin' },
  { symbol: 'ETH-USDT', name: 'Ethereum' }
];
```

- [ ] **Step 2: 添加 crypto 数据状态**

```typescript
// frontend/src/components/asset/AssetSelector.tsx
// 在组件中添加状态
const [cryptos, setCryptos] = useState<CryptoQuote[]>([]);
```

- [ ] **Step 3: 创建 fetchCryptoQuotes 函数**

```typescript
// frontend/src/components/asset/AssetSelector.tsx
const fetchCryptoQuotes = useCallback(async (isManual = false) => {
  if (isManual) setRefreshing(true);
  try {
    const symbols = CRYPTO_SYMBOLS.map(c => c.symbol);
    const data = await api.getCryptoQuotes(symbols);
    setCryptos(data.quotes);
  } catch (err) {
    console.error('Failed to fetch crypto quotes:', err);
    toast({
      title: 'Failed to refresh crypto data',
      description: 'Unable to fetch latest quotes',
      variant: 'destructive',
    });
  } finally {
    setLoading(false);
    setRefreshing(false);
  }
}, [toast]);
```

- [ ] **Step 4: 根据 assetType 调用不同的 fetch 函数**

```typescript
// frontend/src/components/asset/AssetSelector.tsx
// 修改 useEffect
useEffect(() => {
  const fetchData = assetType === 'crypto' ? fetchCryptoQuotes : fetchQuotes;
  fetchData();

  const interval = setInterval(() => {
    if (document.visibilityState === 'visible') {
      fetchData();
    }
  }, REFRESH_INTERVAL);

  const handleVisibility = () => {
    if (document.visibilityState === 'visible') fetchData();
  };
  document.addEventListener('visibilitychange', handleVisibility);

  return () => {
    clearInterval(interval);
    document.removeEventListener('visibilitychange', handleVisibility);
  };
}, [fetchQuotes, fetchCryptoQuotes, assetType]);
```

- [ ] **Step 5: 更新渲染逻辑**

```typescript
// frontend/src/components/asset/AssetSelector.tsx
// 在 JSX 中更新渲染
<div className="grid grid-cols-2 gap-1.5">
  {loading
    ? (assetType === 'crypto' ? CRYPTO_SYMBOLS : SYMBOLS).map((s) => (
        <Skeleton key={typeof s === 'string' ? s : s.symbol} className="h-12 w-full rounded-lg" />
      ))
    : assetType === 'crypto'
    ? cryptos.map((crypto) => (
        <StockCard
          key={crypto.symbol}
          stock={{
            symbol: crypto.symbol,
            name: crypto.name,
            price: crypto.price,
            change: crypto.change,
            changeAmount: crypto.changeAmount
          }}
          selected={selectedAsset === crypto.symbol}
          onClick={() => onAssetSelect(crypto.symbol)}
        />
      ))
    : stocks.map((stock) => (
        <StockCard
          key={stock.symbol}
          stock={stock}
          selected={selectedAsset === stock.symbol}
          onClick={() => onAssetSelect(stock.symbol)}
        />
      ))}
</div>
```

- [ ] **Step 6: 更新刷新按钮逻辑**

```typescript
// frontend/src/components/asset/AssetSelector.tsx
// 更新刷新按钮的 onClick
<Button
  variant="ghost"
  size="icon"
  className="h-6 w-6"
  onClick={() => {
    const fetchData = assetType === 'crypto' ? fetchCryptoQuotes : fetchQuotes;
    fetchData(true);
  }}
  disabled={refreshing}
>
  <RefreshCw className={`h-3 w-3 ${refreshing ? 'animate-spin' : ''}`} />
</Button>
```

- [ ] **Step 7: 验证类型检查**

```bash
cd /home/wcqqq21/finance-agent/frontend
pnpm run type-check
```

Expected: No type errors

- [ ] **Step 8: 提交**

```bash
git add frontend/src/components/asset/AssetSelector.tsx
git commit -m "feat(frontend): add crypto asset support to AssetSelector"
```

---

## Task 12: 更新 Home 页面传递 assetType

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: 传递 assetType 到 KLineChart**

```typescript
// frontend/src/app/page.tsx
// 找到 KLineChart 组件并添加 assetType prop
<KLineChart 
  selectedStock={selectedAsset} 
  assetType={assetType}  // 新增
/>
```

- [ ] **Step 2: 验证类型检查**

```bash
cd /home/wcqqq21/finance-agent/frontend
pnpm run type-check
```

Expected: No type errors

- [ ] **Step 3: 提交**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat(frontend): pass assetType to KLineChart in Home page"
```

