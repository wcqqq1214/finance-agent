# Stock Selector & Chat Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Home 页面左侧添加美股七姐妹实时股票选择器，右侧改造为单次问答对话界面。

**Architecture:** 后端新增 `/api/stocks/quotes` 批量报价端点，前端拆分为 `StockSelector`、`StockCard`、`ChatPanel`、`ResultCard` 四个新组件，通过 props 传递选中股票状态。

**Tech Stack:** FastAPI, asyncio, Polygon.io, Next.js, TypeScript, Tailwind CSS, SSE

---

## File Map

**新建：**
- `app/api/routes/stocks.py` — 批量报价 API 端点
- `frontend/src/components/stock/StockSelector.tsx` — 股票选择器容器
- `frontend/src/components/stock/StockCard.tsx` — 单个股票卡片
- `frontend/src/components/chat/ChatPanel.tsx` — 对话界面（替换 QueryPanel）
- `frontend/src/components/chat/ResultCard.tsx` — 结构化结果展示

**修改：**
- `app/polygon/client.py` — 新增 `fetch_ticker_details()` 获取 logo
- `app/api/models/schemas.py` — 新增 `StockQuote`、`StockQuotesResponse` schema
- `app/api/routes/analyze.py` — 统一 SSE 事件类型（`status` → `progress`）
- `app/api/routes/__init__.py` — 注册 stocks router
- `app/api/main.py` — 注册 stocks router
- `frontend/src/lib/types.ts` — 新增 `StockInfo`、`StockQuotesResponse` 类型
- `frontend/src/lib/api.ts` — 新增 `getStockQuotes()` 方法
- `frontend/src/app/page.tsx` — 重构为三区域布局
- `frontend/src/components/query/QueryPanel.tsx` — 删除（功能迁移到 ChatPanel）

---
## Task 1: 后端 — 新增 StockQuote Schema

**Files:**
- Modify: `app/api/models/schemas.py`

- [ ] **Step 1: 在 schemas.py 末尾新增两个 model**

```python
class StockQuote(BaseModel):
    symbol: str
    name: str
    price: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    logo: Optional[str] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None

class StockQuotesResponse(BaseModel):
    quotes: List[StockQuote]
```

- [ ] **Step 2: 验证 Python 语法无误**

```bash
cd /home/wcqqq21/finance-agent
python -c "from app.api.models.schemas import StockQuote, StockQuotesResponse; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/api/models/schemas.py
git commit -m "feat: add StockQuote and StockQuotesResponse schemas"
```

---

## Task 2: 后端 — Polygon 新增 fetch_ticker_details()

**Files:**
- Modify: `app/polygon/client.py`

- [ ] **Step 1: 在 client.py 末尾新增 logo 缓存 dict 和函数**

```python
# Logo cache (symbol -> logo_url), TTL not enforced — logos rarely change
_LOGO_CACHE: Dict[str, Optional[str]] = {}


def fetch_ticker_details(ticker: str) -> Optional[str]:
    """Fetch logo URL for a ticker from Polygon.io /v3/reference/tickers.

    Returns the logo URL string, or None if unavailable.
    Results are cached in-process for the lifetime of the server.
    """
    if ticker in _LOGO_CACHE:
        return _LOGO_CACHE[ticker]

    try:
        rate_limit()
        url = f"{BASE_URL}/v3/reference/tickers/{ticker}"
        resp = _http_get(url)
        data = resp.json()
        branding = data.get("results", {}).get("branding", {})
        logo_url = branding.get("logo_url")
        # Polygon returns SVG URLs; append API key for authenticated access
        if logo_url:
            api_key = _get_api_key()
            logo_url = f"{logo_url}?apiKey={api_key}"
        _LOGO_CACHE[ticker] = logo_url
        logger.info(f"Fetched logo for {ticker}: {logo_url}")
        return logo_url
    except Exception as exc:
        logger.warning(f"Failed to fetch logo for {ticker}: {exc}")
        _LOGO_CACHE[ticker] = None
        return None
```

- [ ] **Step 2: 验证导入无误**

```bash
python -c "from app.polygon.client import fetch_ticker_details; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/polygon/client.py
git commit -m "feat: add fetch_ticker_details() for logo fetching with in-process cache"
```

---

## Task 3: 后端 — 新增 /api/stocks/quotes 端点

**Files:**
- Create: `app/api/routes/stocks.py`

- [ ] **Step 1: 创建 stocks.py**

```python
from fastapi import APIRouter
from datetime import datetime, timezone
import asyncio
import logging

from ..models.schemas import StockQuote, StockQuotesResponse

logger = logging.getLogger(__name__)
router = APIRouter()

MAGNIFICENT_SEVEN = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.",
    "NVDA": "NVIDIA Corporation",
    "META": "Meta Platforms Inc.",
    "TSLA": "Tesla Inc.",
}


async def _fetch_single_quote(symbol: str) -> StockQuote:
    """Fetch quote for a single symbol, returning error field on failure."""
    import os
    from app.mcp_client.finance_client import _call_get_us_stock_quote_async
    from app.polygon.client import fetch_ticker_details

    url = os.environ.get("MCP_MARKET_DATA_URL", "http://127.0.0.1:8000/mcp")
    name = MAGNIFICENT_SEVEN.get(symbol, symbol)

    try:
        data = await _call_get_us_stock_quote_async(symbol, url)
        logo = await asyncio.to_thread(fetch_ticker_details, symbol)
        return StockQuote(
            symbol=symbol,
            name=name,
            price=data.get("price"),
            change=data.get("change"),
            change_percent=data.get("change_percent"),
            logo=logo,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as exc:
        logger.warning(f"Failed to fetch quote for {symbol}: {exc}")
        return StockQuote(symbol=symbol, name=name, error=str(exc))


@router.get("/stocks/quotes", response_model=StockQuotesResponse)
async def get_stock_quotes(symbols: str = "AAPL,MSFT,GOOGL,AMZN,NVDA,META,TSLA"):
    """Fetch real-time quotes for a comma-separated list of symbols."""
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    quotes = await asyncio.gather(*[_fetch_single_quote(s) for s in symbol_list])
    return StockQuotesResponse(quotes=list(quotes))
```

- [ ] **Step 2: 验证语法**

```bash
python -c "from app.api.routes.stocks import router; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/api/routes/stocks.py
git commit -m "feat: add /api/stocks/quotes endpoint with parallel fetching"
```

---
## Task 4: 后端 — 统一 SSE 事件类型

**Files:**
- Modify: `app/api/routes/analyze.py`

- [ ] **Step 1: 将所有 `'status'` 事件类型改为 `'progress'`**

在 `run_analysis_stream()` 中，将：
```python
yield f"data: {json.dumps({'type': 'status', 'message': '...'})}\n\n"
```
全部改为：
```python
yield f"data: {json.dumps({'type': 'progress', 'message': '...'})}\n\n"
```

同时更新 docstring 中的事件类型说明，移除 `status`，保留 `progress`、`result`、`error`。

- [ ] **Step 2: 验证**

```bash
python -c "from app.api.routes.analyze import router; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/api/routes/analyze.py
git commit -m "fix: standardize SSE event type from 'status' to 'progress'"
```

---

## Task 5: 后端 — 注册 stocks router

**Files:**
- Modify: `app/api/routes/__init__.py`
- Modify: `app/api/main.py`

- [ ] **Step 1: 查看 `app/api/routes/__init__.py` 和 `app/api/main.py` 当前内容**

```bash
cat app/api/routes/__init__.py
cat app/api/main.py
```

- [ ] **Step 2: 在 main.py 中注册 stocks router**

参照现有 router 注册方式，添加：
```python
from app.api.routes.stocks import router as stocks_router
app.include_router(stocks_router, prefix="/api")
```

- [ ] **Step 3: 启动后端验证端点存在**

```bash
curl http://localhost:8080/api/stocks/quotes 2>/dev/null | python -m json.tool | head -20
```
Expected: JSON 响应（即使 MCP 未启动也应返回带 error 字段的结构）

- [ ] **Step 4: Commit**

```bash
git add app/api/routes/__init__.py app/api/main.py
git commit -m "feat: register stocks router in FastAPI app"
```

---

## Task 6: 前端 — 新增类型定义

**Files:**
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: 在 types.ts 末尾新增类型**

```typescript
export interface StockInfo {
  symbol: string;
  name: string;
  logo?: string;
  price?: number;
  change?: number;
  changePercent?: number;
  timestamp?: string;
  error?: string;
}

export interface StockQuotesResponse {
  quotes: StockInfo[];
}
```

- [ ] **Step 2: 将 SSEEvent.type 中的 `'status'` 移除**

```typescript
// 改前
export interface SSEEvent {
  type: 'status' | 'progress' | 'result' | 'error';
  ...
}

// 改后
export interface SSEEvent {
  type: 'progress' | 'result' | 'error';
  ...
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/types.ts
git commit -m "feat: add StockInfo and StockQuotesResponse types, remove status SSE type"
```

---

## Task 7: 前端 — api.ts 新增 getStockQuotes()

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: 在 import 中添加新类型**

```typescript
import type {
  ...,
  StockQuotesResponse,
} from './types';
```

- [ ] **Step 2: 在 api 对象中新增方法**

```typescript
// Get stock quotes for given symbols
getStockQuotes: (symbols: string[]) =>
  fetchAPI<StockQuotesResponse>(
    `/api/stocks/quotes?symbols=${symbols.join(',')}`
  ),
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: add getStockQuotes() to API client"
```

---
## Task 8: 前端 — StockCard 组件

**Files:**
- Create: `frontend/src/components/stock/StockCard.tsx`

- [ ] **Step 1: 创建 StockCard.tsx**

```tsx
'use client';

import Image from 'next/image';
import { cn } from '@/lib/utils';
import type { StockInfo } from '@/lib/types';

interface StockCardProps {
  stock: StockInfo;
  selected: boolean;
  onClick: () => void;
}

export function StockCard({ stock, selected, onClick }: StockCardProps) {
  const isPositive = (stock.change ?? 0) >= 0;
  const changeColor = stock.change === undefined
    ? 'text-muted-foreground'
    : isPositive ? 'text-green-500' : 'text-red-500';
  const changeIcon = isPositive ? '↑' : '↓';

  const formattedPrice = stock.price !== undefined
    ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(stock.price)
    : '--';

  const formattedChange = stock.changePercent !== undefined
    ? `${changeIcon} ${Math.abs(stock.changePercent).toFixed(2)}%`
    : '--';

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-2 p-2 rounded-lg border text-left transition-all',
        'hover:shadow-md hover:bg-accent/50',
        selected
          ? 'border-primary bg-accent/30 shadow-sm'
          : 'border-border bg-card'
      )}
    >
      {/* Logo */}
      <div className="w-8 h-8 rounded-full overflow-hidden flex-shrink-0 bg-muted flex items-center justify-center">
        {stock.logo ? (
          <Image
            src={stock.logo}
            alt={stock.symbol}
            width={32}
            height={32}
            className="object-contain"
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        ) : (
          <span className="text-xs font-bold text-muted-foreground">
            {stock.symbol.slice(0, 2)}
          </span>
        )}
      </div>

      {/* Symbol + Price */}
      <div className="flex-1 min-w-0">
        <div className="font-semibold text-sm leading-tight">{stock.symbol}</div>
        <div className="text-xs text-muted-foreground truncate">{formattedPrice}</div>
      </div>

      {/* Change */}
      <div className={cn('text-xs font-medium flex-shrink-0', changeColor)}>
        {formattedChange}
      </div>
    </button>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/stock/StockCard.tsx
git commit -m "feat: add StockCard component with logo, price, and change display"
```

---

## Task 9: 前端 — StockSelector 组件

**Files:**
- Create: `frontend/src/components/stock/StockSelector.tsx`

- [ ] **Step 1: 创建 StockSelector.tsx**

```tsx
'use client';

import { useState, useEffect, useCallback } from 'react';
import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { StockCard } from './StockCard';
import { api } from '@/lib/api';
import type { StockInfo } from '@/lib/types';

const SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA'];
const REFRESH_INTERVAL = 60000;

interface StockSelectorProps {
  selectedStock: string | null;
  onStockSelect: (symbol: string) => void;
}

export function StockSelector({ selectedStock, onStockSelect }: StockSelectorProps) {
  const [stocks, setStocks] = useState<StockInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchQuotes = useCallback(async (isManual = false) => {
    if (isManual) setRefreshing(true);
    try {
      const data = await api.getStockQuotes(SYMBOLS);
      setStocks(data.quotes);
    } catch (err) {
      console.error('Failed to fetch stock quotes:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchQuotes();

    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchQuotes();
      }
    }, REFRESH_INTERVAL);

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') fetchQuotes();
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [fetchQuotes]);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          Magnificent Seven
        </h2>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={() => fetchQuotes(true)}
          disabled={refreshing}
        >
          <RefreshCw className={`h-3 w-3 ${refreshing ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-1.5">
        {loading
          ? SYMBOLS.map((s) => (
              <Skeleton key={s} className="h-12 w-full rounded-lg" />
            ))
          : stocks.map((stock) => (
              <StockCard
                key={stock.symbol}
                stock={stock}
                selected={selectedStock === stock.symbol}
                onClick={() => onStockSelect(stock.symbol)}
              />
            ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/stock/StockSelector.tsx
git commit -m "feat: add StockSelector with auto-refresh and visibility-aware polling"
```

---
## Task 10: 前端 — ResultCard 组件

**Files:**
- Create: `frontend/src/components/chat/ResultCard.tsx`

- [ ] **Step 1: 创建 ResultCard.tsx**

```tsx
'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface ResultCardProps {
  symbol: string;
  query: string;
  progress: string[];
  result: Record<string, unknown> | null;
  isAnalyzing: boolean;
}

function CollapsibleSection({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border rounded-md overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium bg-muted/50 hover:bg-muted transition-colors"
      >
        {title}
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>
      {open && <div className="px-3 py-2 text-sm">{children}</div>}
    </div>
  );
}

export function ResultCard({ symbol, query, progress, result, isAnalyzing }: ResultCardProps) {
  return (
    <Card className="flex-1 overflow-hidden flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <CardTitle className="text-base">{symbol}</CardTitle>
          {isAnalyzing && (
            <Badge variant="secondary" className="text-xs animate-pulse">
              Analyzing...
            </Badge>
          )}
        </div>
        <p className="text-xs text-muted-foreground truncate">{query}</p>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto space-y-2">
        {/* Progress */}
        {progress.length > 0 && (
          <div className="space-y-1">
            {progress.map((msg, i) => (
              <p key={i} className="text-xs text-muted-foreground flex items-start gap-1">
                <span className="text-primary mt-0.5">•</span>
                {msg}
              </p>
            ))}
          </div>
        )}

        {/* Structured result */}
        {result && (
          <div className="space-y-2 pt-1">
            {result.quant_analysis && (
              <CollapsibleSection title="Technical Analysis" defaultOpen>
                <pre className="text-xs whitespace-pre-wrap break-words">
                  {JSON.stringify(result.quant_analysis, null, 2)}
                </pre>
              </CollapsibleSection>
            )}
            {result.news_sentiment && (
              <CollapsibleSection title="News Summary">
                <pre className="text-xs whitespace-pre-wrap break-words">
                  {JSON.stringify(result.news_sentiment, null, 2)}
                </pre>
              </CollapsibleSection>
            )}
            {result.social_sentiment && (
              <CollapsibleSection title="Social Sentiment">
                <pre className="text-xs whitespace-pre-wrap break-words">
                  {JSON.stringify(result.social_sentiment, null, 2)}
                </pre>
              </CollapsibleSection>
            )}
            {result.final_decision && (
              <CollapsibleSection title="Recommendation" defaultOpen>
                <p className="text-sm">{String(result.final_decision)}</p>
              </CollapsibleSection>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/chat/ResultCard.tsx
git commit -m "feat: add ResultCard with collapsible analysis sections"
```

---

## Task 11: 前端 — ChatPanel 组件

**Files:**
- Create: `frontend/src/components/chat/ChatPanel.tsx`

- [ ] **Step 1: 创建 ChatPanel.tsx**

```tsx
'use client';

import { useState, useRef } from 'react';
import { Send } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ResultCard } from './ResultCard';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import type { SSEEvent } from '@/lib/types';

interface ChatPanelProps {
  selectedStock: string | null;
}

export function ChatPanel({ selectedStock }: ChatPanelProps) {
  const [query, setQuery] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState<string[]>([]);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [submittedSymbol, setSubmittedSymbol] = useState('');
  const eventSourceRef = useRef<EventSource | null>(null);
  const { toast } = useToast();

  const placeholder = selectedStock
    ? `Ask about ${selectedStock}... (e.g., technical analysis, recent news)`
    : 'Select a stock to start analysis';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStock || !query.trim() || isAnalyzing) return;

    // Close any existing connection
    eventSourceRef.current?.close();

    const fullQuery = `${query.trim()} ${selectedStock}`;
    setSubmittedQuery(query.trim());
    setSubmittedSymbol(selectedStock);
    setProgress([]);
    setResult(null);
    setIsAnalyzing(true);

    const es = api.createAnalyzeStream(fullQuery);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data);
        if (data.type === 'progress' && data.message) {
          setProgress((prev) => [...prev, data.message!]);
        } else if (data.type === 'result' && data.data) {
          setResult(data.data as Record<string, unknown>);
          es.close();
          setIsAnalyzing(false);
        } else if (data.type === 'error') {
          toast({ title: 'Analysis Error', description: data.message, variant: 'destructive' });
          es.close();
          setIsAnalyzing(false);
        }
      } catch (err) {
        console.error('Failed to parse SSE event:', err);
      }
    };

    es.onerror = () => {
      toast({ title: 'Connection Error', description: 'Lost connection to server', variant: 'destructive' });
      es.close();
      setIsAnalyzing(false);
    };

    setQuery('');
  };

  return (
    <div className="h-full flex flex-col p-4 gap-3">
      <div>
        <h2 className="text-lg font-semibold">Analysis Chat</h2>
        <p className="text-xs text-muted-foreground">
          {selectedStock ? `Analyzing ${selectedStock}` : 'Select a stock from the left panel'}
        </p>
      </div>

      {/* Result area */}
      {(progress.length > 0 || result) && (
        <ResultCard
          symbol={submittedSymbol}
          query={submittedQuery}
          progress={progress}
          result={result}
          isAnalyzing={isAnalyzing}
        />
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex gap-2 mt-auto">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          disabled={!selectedStock || isAnalyzing}
          className="flex-1 text-sm"
        />
        <Button
          type="submit"
          size="icon"
          disabled={!selectedStock || !query.trim() || isAnalyzing}
        >
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/chat/ChatPanel.tsx
git commit -m "feat: add ChatPanel with SSE streaming and result display"
```

---
## Task 12: 前端 — 重构 HomePage 布局

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: 将 page.tsx 改为 'use client' 并重构布局**

```tsx
'use client';

import { useState } from 'react';
import { StockSelector } from '@/components/stock/StockSelector';
import { ChatPanel } from '@/components/chat/ChatPanel';

export default function Home() {
  const [selectedStock, setSelectedStock] = useState<string | null>(null);

  return (
    <div className="flex gap-4 h-[calc(100vh-8rem)]">
      {/* Left panel */}
      <div className="flex-1 flex flex-col gap-4 overflow-hidden">
        {/* Top: Stock selector (40% height) */}
        <div className="h-[40%] overflow-y-auto">
          <StockSelector
            selectedStock={selectedStock}
            onStockSelect={setSelectedStock}
          />
        </div>

        {/* Bottom: K-line chart placeholder (60% height) */}
        <div className="flex-1 border rounded-lg flex items-center justify-center text-muted-foreground text-sm">
          {selectedStock
            ? `${selectedStock} K-Line Chart (coming soon)`
            : 'Select a stock to view chart'}
        </div>
      </div>

      {/* Right panel: Chat */}
      <div className="w-[35%] border-l overflow-hidden flex flex-col">
        <ChatPanel selectedStock={selectedStock} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat: refactor HomePage with StockSelector and ChatPanel layout"
```

---

## Task 13: 清理旧组件

**Files:**
- Delete: `frontend/src/components/query/QueryPanel.tsx`

- [ ] **Step 1: 删除旧的 QueryPanel**

```bash
rm frontend/src/components/query/QueryPanel.tsx
rmdir frontend/src/components/query 2>/dev/null || true
```

- [ ] **Step 2: 确认没有其他文件引用 QueryPanel**

```bash
grep -r "QueryPanel" frontend/src --include="*.tsx" --include="*.ts"
```
Expected: 无输出

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove deprecated QueryPanel component"
```

---

## Verification

完成所有 Task 后，执行以下验证：

1. 启动后端：`uvicorn app.api.main:app --port 8080`
2. 启动前端：`cd frontend && pnpm dev`
3. 访问 `http://localhost:3000`
4. 确认左侧显示七姐妹股票卡片（2列紧凑布局）
5. 点击一个股票，确认卡片高亮选中
6. 确认右侧输入框占位符变为 `Ask about AAPL...`
7. 输入问题并提交，确认进度消息实时显示
8. 确认分析完成后结果卡片展开
9. 确认 60 秒后股票价格自动刷新
10. 确认导航栏中没有 Query 链接
