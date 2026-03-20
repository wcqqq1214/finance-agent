# 前端 Home 页面 Crypto 资产切换功能设计文档

## 1. 概述

### 1.1 需求背景
用户希望在前端 Home 页面中点击 Crypto 按钮，能够切换到 Crypto 模式，显示 BTC、ETH 等加密货币资产，并在 K线图中展示这些资产的价格走势。项目已有 OKX API 集成，需要利用 OKX 获取加密货币的实时行情数据。

### 1.2 功能目标
- 在 Home 页面的 AssetSelector 中支持 Stocks/Crypto 模式切换
- Crypto 模式下显示 BTC、ETH 资产卡片（初期支持这两个）
- 点击加密货币资产后，K线图显示从 OKX 获取的实时行情数据
- 支持加密货币特有的时间周期（15M、1H、4H、1D、1W、1M、1Y）

### 1.3 技术方案
采用**统一 OHLC 接口**方案：
- 扩展现有 `/api/stocks/{symbol}/ohlc` 接口支持加密货币
- 后端根据 symbol 格式自动识别并路由到相应数据源
- 前端保持统一的 API 调用方式，降低改动成本

## 2. 整体架构

### 2.1 数据流设计

```
用户操作 → AssetSelector → KLineChart → Backend API → OKX/Database
   ↓           ↓              ↓              ↓            ↓
点击Crypto  显示BTC/ETH   调用getOHLC   识别symbol   获取K线数据
   ↓           ↓              ↓              ↓            ↓
选择BTC    传递BTC-USDT  传递时间参数   路由到OKX   转换格式返回
```

### 2.2 Symbol 格式约定
- **股票格式**: `AAPL`, `MSFT` (纯大写字母，无特殊字符)
- **加密货币格式**: `BTC-USDT`, `ETH-USDT` (包含连字符 "-")
- **识别规则**: 后端通过检查 symbol 中是否包含 "-" 来判断资产类型

### 2.3 时间周期设计

**Stocks 时间周期**:
- 前端选项: `D` | `W` | `M` | `Y`
- 后端映射: `day` | `week` | `month` | `year`
- 默认值: `D`

**Crypto 时间周期**:
- 前端选项: `15M` | `1H` | `4H` | `1D` | `1W` | `1M` | `1Y`
- 后端映射: `15m` | `1H` | `4H` | `1D` | `1W` | `1M` | `1Y` (OKX 格式)
- 默认值: `15M`

## 3. 前端实现设计

### 3.1 AssetSelector 组件改造

**现状**: 已支持 Stocks/Crypto 标签切换，但 Crypto 模式下仍显示股票数据

**改造内容**:

1. **定义加密货币列表**
```typescript
const CRYPTO_SYMBOLS = [
  { symbol: 'BTC-USDT', name: 'Bitcoin' },
  { symbol: 'ETH-USDT', name: 'Ethereum' }
];
```

2. **根据 assetType 渲染不同资产**
- `assetType === 'stocks'`: 调用 `api.getStockQuotes()` 获取股票数据
- `assetType === 'crypto'`: 调用新增的 `api.getCryptoQuotes()` 获取加密货币实时价格

3. **资产卡片数据结构统一**
```typescript
interface AssetInfo {
  symbol: string;      // BTC-USDT 或 AAPL
  name: string;        // Bitcoin 或 Apple Inc.
  price: number;
  change: number;      // 涨跌幅百分比
  changeAmount: number;
}
```

### 3.2 KLineChart 组件改造

**现状**: 只支持股票数据，时间周期固定为 D/W/M/Y

**改造内容**:

1. **接收 assetType 参数**
```typescript
interface KLineChartProps {
  selectedStock: string | null;
  assetType: 'crypto' | 'stocks';  // 新增
}
```

2. **根据 assetType 设置默认时间周期**
```typescript
const defaultTimeRange = assetType === 'crypto' ? '15M' : 'D';
const [timeRange, setTimeRange] = useState<TimeRange>(defaultTimeRange);
```

3. **API 调用保持不变**
```typescript
// 无论是 AAPL 还是 BTC-USDT，都调用同一个接口
const response = await api.getOHLC(
  selectedStock,
  start,
  end,
  intervalMap[timeRange]
);
```

### 3.3 TimeRangeSelector 组件改造

**现状**: 固定显示 D/W/M/Y 四个选项

**改造内容**:

1. **接收 assetType 参数**
```typescript
interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
  disabled?: boolean;
  assetType: 'crypto' | 'stocks';  // 新增
}
```

2. **根据 assetType 渲染不同选项**
```typescript
const stockRanges: TimeRange[] = ['D', 'W', 'M', 'Y'];
const cryptoRanges: TimeRange[] = ['15M', '1H', '4H', '1D', '1W', '1M', '1Y'];
const ranges = assetType === 'crypto' ? cryptoRanges : stockRanges;
```

### 3.4 类型定义扩展

**文件**: `frontend/src/lib/types.ts`

```typescript
// 扩展 TimeRange 类型
export type TimeRange = 'D' | 'W' | 'M' | 'Y' | '15M' | '1H' | '4H' | '1D' | '1W' | '1M' | '1Y';

// 新增加密货币报价响应类型
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

### 3.5 API 客户端扩展

**文件**: `frontend/src/lib/api.ts`

```typescript
// 新增获取加密货币报价接口
getCryptoQuotes: (symbols: string[]) =>
  fetchAPI<CryptoQuotesResponse>(
    `/api/crypto/quotes?symbols=${symbols.join(',')}`
  ),
```

## 4. 后端实现设计

### 4.1 OKXTradingClient 扩展

**文件**: `app/okx/trading_client.py`

**新增方法 1: 获取 K线数据**
```python
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
        List of candle data:
        [
          {
            "ts": "1597026383085",      # 时间戳
            "o": "3.721",                # 开盘价
            "h": "3.743",                # 最高价
            "l": "3.677",                # 最低价
            "c": "3.708",                # 收盘价
            "vol": "8422410"             # 成交量
          },
          ...
        ]
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

        return candles
    except Exception as e:
        logger.error(f"Failed to get candles: {e}")
        raise
```

**新增方法 2: 获取实时行情**
```python
async def get_ticker(self, inst_id: str) -> Dict[str, Any]:
    """获取单个产品行情信息

    Args:
        inst_id: 产品ID，如 BTC-USDT

    Returns:
        {
          "instId": "BTC-USDT",
          "last": "50000.5",        # 最新成交价
          "lastSz": "0.1",          # 最新成交量
          "askPx": "50001",         # 卖一价
          "bidPx": "50000",         # 买一价
          "open24h": "49500",       # 24h开盘价
          "high24h": "51000",       # 24h最高价
          "low24h": "49000",        # 24h最低价
          "vol24h": "12345.67",     # 24h成交量
          ...
        }
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

        return data[0]
    except Exception as e:
        logger.error(f"Failed to get ticker: {e}")
        raise
```

### 4.2 OHLC 路由改造

**文件**: `app/api/routes/ohlc.py`

**改造现有路由**:

```python
@router.get("/{symbol}/ohlc", response_model=OHLCResponse)
async def get_stock_ohlc(
    symbol: str,
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    interval: str = Query("day", description="Time granularity"),
):
    """获取 OHLC 数据（支持股票和加密货币）
    
    - 股票 symbol: AAPL, MSFT (从数据库获取)
    - 加密货币 symbol: BTC-USDT, ETH-USDT (从 OKX 获取)
    """
    # 判断是否为加密货币（包含连字符）
    if "-" in symbol:
        return await get_crypto_ohlc(symbol, start, end, interval)
    else:
        return get_stock_ohlc_from_db(symbol, start, end, interval)


async def get_crypto_ohlc(
    symbol: str,
    start: Optional[str],
    end: Optional[str],
    interval: str
) -> OHLCResponse:
    """从 OKX 获取加密货币 OHLC 数据"""
    
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
    
    try:
        # 获取 OKX 客户端（使用 demo 模式）
        from app.okx import get_okx_client
        client = get_okx_client("demo")
        
        # 获取 K线数据
        candles = await client.get_candles(
            inst_id=symbol,
            bar=bar,
            limit=300
        )
        
        # 转换为统一格式
        ohlc_records = []
        for candle in candles:
            # OKX 时间戳是毫秒，转换为日期字符串
            timestamp = int(candle["ts"]) / 1000
            date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
            
            ohlc_records.append(OHLCRecord(
                date=date_str,
                open=float(candle["o"]),
                high=float(candle["h"]),
                low=float(candle["l"]),
                close=float(candle["c"]),
                volume=float(candle["vol"])
            ))
        
        # 按日期排序（从旧到新）
        ohlc_records.sort(key=lambda x: x.date)
        
        return OHLCResponse(symbol=symbol, data=ohlc_records)
        
    except Exception as e:
        logger.error(f"Failed to fetch crypto OHLC for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch crypto data: {str(e)}"
        )
```

### 4.3 新增加密货币报价路由

**文件**: `app/api/routes/crypto.py` (新建)

```python
"""加密货币报价 API 端点"""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List

from app.okx import get_okx_client

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
        
        return CryptoQuotesResponse(quotes=quotes)
        
    except Exception as e:
        logger.error(f"Failed to fetch crypto quotes: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch crypto quotes: {str(e)}"
        )
```

### 4.4 注册新路由

**文件**: `app/api/main.py`

```python
# 导入加密货币路由
from app.api.routes import crypto

# 注册路由
app.include_router(crypto.router, prefix="/api/crypto", tags=["crypto"])
```

## 5. 数据格式转换

### 5.1 OKX K线数据格式

**OKX 原始返回**:
```json
{
  "code": "0",
  "data": [
    [
      "1597026383085",  // 时间戳（毫秒）
      "3.721",          // 开盘价
      "3.743",          // 最高价
      "3.677",          // 最低价
      "3.708",          // 收盘价
      "8422410",        // 成交量（张）
      "22698348.04",    // 成交量（币）
      ...
    ]
  ]
}
```

**转换后统一格式**:
```json
{
  "symbol": "BTC-USDT",
  "data": [
    {
      "date": "2024-03-21",
      "open": 50000.5,
      "high": 51000.0,
      "low": 49500.0,
      "close": 50500.0,
      "volume": 12345.67
    }
  ]
}
```

### 5.2 时间处理注意事项

1. **OKX 时间戳**: 毫秒级，需除以 1000 转换为秒
2. **日期格式**: 统一使用 `YYYY-MM-DD` 格式
3. **时区**: OKX 返回 UTC 时间，需根据需求决定是否转换为本地时间
4. **排序**: 确保数据按时间从旧到新排序，以便图表正确渲染

## 6. 错误处理

### 6.1 后端错误处理

```python
# OKX API 错误
try:
    candles = await client.get_candles(...)
except OKXAuthError:
    raise HTTPException(status_code=401, detail="OKX authentication failed")
except OKXRateLimitError:
    raise HTTPException(status_code=429, detail="Rate limit exceeded")
except OKXError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

### 6.2 前端错误处理

```typescript
try {
  const response = await api.getOHLC(symbol, start, end, interval);
  setOhlcData(response.data);
} catch (err) {
  if (err instanceof APIError) {
    if (err.status === 429) {
      toast({ title: "请求过于频繁", description: "请稍后再试" });
    } else {
      toast({ title: "加载失败", description: err.message });
    }
  }
}
```

## 7. 测试计划

### 7.1 单元测试

**后端测试**:
- `test_okx_get_candles()`: 测试 OKX K线数据获取
- `test_okx_get_ticker()`: 测试 OKX 行情数据获取
- `test_crypto_ohlc_route()`: 测试加密货币 OHLC 路由
- `test_symbol_type_detection()`: 测试 symbol 类型识别逻辑

**前端测试**:
- 测试 AssetSelector 在 crypto 模式下的渲染
- 测试 TimeRangeSelector 显示正确的时间周期选项
- 测试 KLineChart 正确调用 API

### 7.2 集成测试

1. **完整流程测试**:
   - 切换到 Crypto 模式
   - 选择 BTC
   - 验证 K线图显示正确数据
   - 切换时间周期（15M → 1H → 1D）
   - 验证数据正确更新

2. **边界情况测试**:
   - OKX API 返回空数据
   - OKX API 超时
   - 无效的 symbol
   - 无效的时间周期

### 7.3 手动测试清单

- [ ] Crypto 标签切换正常
- [ ] BTC/ETH 卡片显示实时价格
- [ ] 点击 BTC 后 K线图加载
- [ ] 时间周期选项显示 15M/1H/4H/1D/1W/1M/1Y
- [ ] 切换时间周期后数据正确更新
- [ ] 从 Crypto 切换回 Stocks 功能正常
- [ ] 错误提示友好且准确

## 8. 实现顺序

### 阶段 1: 后端基础功能
1. 在 `OKXTradingClient` 中添加 `get_candles()` 和 `get_ticker()` 方法
2. 编写单元测试验证 OKX API 调用
3. 创建 `app/api/routes/crypto.py` 实现报价接口
4. 改造 `app/api/routes/ohlc.py` 支持加密货币

### 阶段 2: 前端类型和 API
1. 扩展 `types.ts` 添加 Crypto 相关类型
2. 在 `api.ts` 中添加 `getCryptoQuotes()` 方法
3. 编写前端 API 调用测试

### 阶段 3: 前端组件改造
1. 改造 `TimeRangeSelector` 支持 crypto 时间周期
2. 改造 `KLineChart` 接收 `assetType` 参数
3. 改造 `AssetSelector` 支持 crypto 资产显示
4. 更新 `page.tsx` 传递 `assetType` 参数

### 阶段 4: 测试和优化
1. 端到端测试完整流程
2. 性能优化（缓存、防抖等）
3. 错误处理完善
4. UI/UX 细节调整

## 9. 注意事项

### 9.1 OKX API 限制
- **频率限制**: 公共接口 20 次/2秒，需要实现请求限流
- **数据量限制**: 单次最多返回 300 条 K线数据
- **历史数据**: 不同周期的历史数据可用范围不同

### 9.2 性能优化
- 实现前端数据缓存，避免重复请求
- 使用防抖处理时间周期切换
- 考虑使用 WebSocket 获取实时数据（后续优化）

### 9.3 安全考虑
- OKX API 密钥不应暴露到前端
- 使用 demo 模式进行开发测试
- 生产环境需要配置真实的 API 密钥

### 9.4 用户体验
- 加载状态提示清晰
- 错误信息友好易懂
- 切换模式时保持界面流畅
- 首次加载使用合理的默认值

## 10. 未来扩展

### 10.1 更多加密货币
- 支持用户自定义添加加密货币
- 支持搜索功能
- 支持收藏功能

### 10.2 实时数据
- 使用 WebSocket 获取实时 K线数据
- 实时价格更新
- 实时成交量显示

### 10.3 高级功能
- 技术指标（MA、MACD、RSI 等）
- 多图表对比
- 交易功能集成
- 价格提醒

