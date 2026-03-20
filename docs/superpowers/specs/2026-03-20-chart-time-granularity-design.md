---
name: Chart Time Granularity Redesign
description: Change K-line chart from time-span view to time-granularity view with aggregated OHLC data
type: feature
---

# K线图时间粒度重构设计文档

## 1. 概述

### 1.1 目标
将K线图的时间维度从"时间跨度"模式改为"时间粒度"模式：
- **当前**: 按钮显示 1M/3M/6M/1Y/5Y，每根K线代表1天，显示该时间跨度内的所有日K线
- **目标**: 按钮显示 D/W/M/Y，每根K线代表对应的时间粒度（1天/1周/1月/1年），显示聚合后的OHLC数据

### 1.2 用户价值
- 更灵活的时间维度分析：用户可以快速切换不同粒度查看价格走势
- 更清晰的长期趋势：周线/月线/年线能更好地展示长期趋势，减少噪音
- 保持交互性：用户仍可通过鼠标滚轮缩放和拖拽查看更多历史数据

## 2. 详细设计

### 2.1 类型定义变更

**frontend/src/lib/types.ts**
```typescript
// 修改前
export type TimeRange = '1M' | '3M' | '6M' | '1Y' | '5Y';

// 修改后
export type TimeRange = 'D' | 'W' | 'M' | 'Y';
```

### 2.2 后端 API 设计

#### 2.2.1 API 端点
```
GET /stocks/{symbol}/ohlc
```

#### 2.2.2 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `symbol` | string | 是 | - | 股票代码（路径参数） |
| `start` | string | 否 | 5年前 | 开始日期 (YYYY-MM-DD) |
| `end` | string | 否 | 今天 | 结束日期 (YYYY-MM-DD) |
| `interval` | string | 否 | `day` | 时间粒度: `day`, `week`, `month`, `year` |

#### 2.2.3 响应格式
```json
{
  "symbol": "AAPL",
  "data": [
    {
      "date": "2024-01-01",
      "open": 150.0,
      "high": 155.0,
      "low": 148.0,
      "close": 153.0,
      "volume": 50000000
    }
  ]
}
```

#### 2.2.4 聚合逻辑

**Week (周线)**
- 分组: 按 ISO 周（周一到周日）
- `open`: 该周第一个交易日的开盘价
- `high`: 该周内的最高价
- `low`: 该周内的最低价
- `close`: 该周最后一个交易日的收盘价
- `volume`: 该周总成交量
- `date`: 该周的周一日期

**Month (月线)**
- 分组: 按自然月
- `open`: 该月第一个交易日的开盘价
- `high`: 该月内的最高价
- `low`: 该月内的最低价
- `close`: 该月最后一个交易日的收盘价
- `volume`: 该月总成交量
- `date`: 该月第一天日期 (YYYY-MM-01)

**Year (年线)**
- 分组: 按自然年
- `open`: 该年第一个交易日的开盘价
- `high`: 该年内的最高价
- `low`: 该年内的最低价
- `close`: 该年最后一个交易日的收盘价
- `volume`: 该年总成交量
- `date`: 该年第一天日期 (YYYY-01-01)

### 2.3 后端实现

#### 2.3.1 数据库查询函数

**app/database.py** - 新增函数

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
    conn = get_conn()

    if interval == 'day':
        # 直接返回每日数据，无需聚合
        query = """
            SELECT date, open, high, low, close, volume
            FROM ohlc
            WHERE symbol = ? AND date >= ? AND date <= ?
            ORDER BY date ASC
        """
        params = (symbol.upper(), start, end)

    elif interval == 'week':
        # 按 ISO 周聚合（周一到周日）
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

    elif interval == 'month':
        # 按月聚合
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
        # 按年聚合
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

    else:
        conn.close()
        raise ValueError(f"Invalid interval: {interval}")

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]
```

#### 2.3.2 API 路由修改

**app/api/routes/ohlc.py** - 修改现有端点

```python
@router.get("/{symbol}/ohlc", response_model=OHLCResponse)
def get_stock_ohlc(
    symbol: str,
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    interval: str = Query("day", description="Time granularity: day, week, month, year"),
):
    """Get OHLC data for a stock symbol with optional time aggregation."""
    # Validate interval
    valid_intervals = ["day", "week", "month", "year"]
    if interval not in valid_intervals:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid interval. Must be one of: {', '.join(valid_intervals)}"
        )

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

    # Query database with aggregation
    try:
        data = get_ohlc_aggregated(symbol, start, end, interval)
        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"No OHLC data found for {symbol}"
            )

        return OHLCResponse(
            symbol=symbol.upper(),
            data=[OHLCRecord(**record) for record in data]
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch OHLC for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Database error")
```

### 2.4 前端实现

#### 2.4.1 类型定义

**frontend/src/lib/types.ts**

```typescript
// 修改 TimeRange 类型
export type TimeRange = 'D' | 'W' | 'M' | 'Y';
```

#### 2.4.2 TimeRangeSelector 组件

**frontend/src/components/chart/TimeRangeSelector.tsx**

```typescript
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

#### 2.4.3 KLineChart 组件

**frontend/src/components/chart/KLineChart.tsx**

主要修改点：

1. **时间窗口计算函数**

```typescript
function calculateDateRange(range: TimeRange): { start: string; end: string } {
  const end = new Date();
  const start = new Date();

  switch (range) {
    case 'D':
      // Day: 显示最近3个月的每日数据
      start.setMonth(start.getMonth() - 3);
      break;
    case 'W':
      // Week: 显示最近1年的每周数据
      start.setFullYear(start.getFullYear() - 1);
      break;
    case 'M':
      // Month: 显示最近3年的每月数据
      start.setFullYear(start.getFullYear() - 3);
      break;
    case 'Y':
      // Year: 显示所有可用的年度数据（5年）
      start.setFullYear(start.getFullYear() - 5);
      break;
  }

  return {
    start: start.toISOString().split('T')[0],
    end: end.toISOString().split('T')[0],
  };
}
```

2. **API 调用修改**

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

    // 映射前端 TimeRange 到后端 interval 参数
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
      intervalMap[timeRange]  // 新增 interval 参数
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

3. **默认值修改**

```typescript
// 将默认时间范围从 '3M' 改为 'W'
const [timeRange, setTimeRange] = useState<TimeRange>('W');
```

#### 2.4.4 API 客户端

**frontend/src/lib/api.ts**

```typescript
export const api = {
  // 修改 getOHLC 函数签名，增加 interval 参数
  async getOHLC(
    symbol: string,
    start: string,
    end: string,
    interval: string = 'day'  // 新增参数，默认值 'day'
  ): Promise<OHLCResponse> {
    const params = new URLSearchParams({
      start,
      end,
      interval,  // 传递 interval 参数
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

  // ... 其他 API 方法保持不变
};
```

## 3. 实现步骤

### 3.1 后端实现
1. 在 `app/database.py` 中添加 `get_ohlc_aggregated()` 函数
2. 修改 `app/api/routes/ohlc.py` 中的 `get_stock_ohlc()` 端点
3. 编写单元测试验证聚合逻辑

### 3.2 前端实现
1. 修改 `frontend/src/lib/types.ts` 中的 `TimeRange` 类型
2. 更新 `frontend/src/components/chart/TimeRangeSelector.tsx` 组件
3. 修改 `frontend/src/components/chart/KLineChart.tsx` 组件
4. 更新 `frontend/src/lib/api.ts` 中的 API 调用

### 3.3 测试验证
1. 后端单元测试：验证各个 interval 的聚合逻辑
2. 前端集成测试：验证按钮切换和数据展示
3. 手动测试：验证图表交互（缩放、拖拽）

## 4. 向后兼容性

### 4.1 API 兼容性
- `interval` 参数为可选，默认值为 `day`
- 现有调用方不传 `interval` 时，行为与之前完全一致
- 不影响其他可能调用此 API 的服务

### 4.2 前端兼容性
- 修改了 `TimeRange` 类型定义，需要全局搜索确保没有其他地方使用旧值
- `api.getOHLC()` 增加了可选参数，现有调用仍然有效

## 5. 边界情况处理

### 5.1 数据不足
- 如果某个时间段内没有交易数据（如周末、节假日），该时间段不会出现在结果中
- 前端图表会自动处理数据缺失，不会显示空白K线

### 5.2 日期边界
- Week: 使用 ISO 8601 标准（周一为一周的开始）
- Month: 使用自然月（1日到月末）
- Year: 使用自然年（1月1日到12月31日）

### 5.3 性能考虑
- Day 模式：直接查询，无聚合开销
- Week/Month/Year 模式：使用子查询获取 open/close，可能略慢但数据量小
- 建议：如果性能成为问题，可以考虑添加物化视图或缓存

## 6. 未来扩展

### 6.1 可能的增强
- 添加更多时间粒度（如 5分钟、15分钟、1小时）
- 支持自定义时间窗口
- 添加技术指标叠加（MA、MACD等）

### 6.2 数据预聚合
- 如果查询性能成为瓶颈，可以考虑：
  - 定期预计算周/月/年数据并存储
  - 使用 SQLite 的物化视图（需要扩展）
  - 迁移到支持物化视图的数据库（如 PostgreSQL）

## 7. 风险与缓解

### 7.1 SQL 查询性能
- **风险**: 子查询可能在大数据集上变慢
- **缓解**:
  - 当前数据量（5年日线）较小，性能影响可控
  - 已有 `idx_ohlc_symbol_date` 索引支持查询
  - 如需优化，可以改用窗口函数或预聚合

### 7.2 前端类型变更
- **风险**: `TimeRange` 类型变更可能影响其他组件
- **缓解**:
  - 使用 TypeScript 编译检查
  - 全局搜索 `TimeRange` 确保所有使用点都已更新

### 7.3 用户习惯变化
- **风险**: 用户可能习惯了旧的时间跨度模式
- **缓解**:
  - 新设计更符合金融图表的标准做法
  - 保留缩放和拖拽功能，用户仍可查看任意时间范围

## 8. 总结

本设计通过在现有 API 上增加可选的 `interval` 参数，实现了从时间跨度到时间粒度的平滑过渡。设计保持了向后兼容性，同时为用户提供了更灵活的数据分析视角。实现相对简单，主要工作集中在 SQL 聚合逻辑和前端组件更新上。
