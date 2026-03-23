---
name: Crypto K-Line Timezone Adaptation
description: Frontend timezone adaptation for crypto K-line charts - display UTC data in user's local timezone
type: design
date: 2026-03-23
---

# Crypto K-Line Chart Timezone Adaptation Design

## Problem Statement

The crypto K-line chart currently displays times in UTC, but users expect to see times in their local timezone. The backend stores and transmits all timestamps in UTC (ISO 8601 format with +00:00), which is the correct approach. The frontend needs to adapt these UTC timestamps to display in the user's browser timezone automatically.

## Requirements

1. Display all chart times in the user's browser's local timezone
2. Do not modify backend code or API responses
3. Maintain data integrity - backend continues to use UTC
4. Provide visual feedback to users about which timezone is being displayed
5. Handle both intraday data (15M, 1H, 4H) and daily+ data correctly

## Design Decision: Frontend-Only Timezone Conversion

### Approach

**Backend**: Continue returning UTC timestamps in ISO 8601 format (e.g., `2026-03-23T08:00:00+00:00`)

**Frontend**:
- Convert UTC ISO strings to Unix timestamps (seconds)
- Let `lightweight-charts` automatically render times in browser's local timezone
- Add timezone indicator UI to show current timezone to users

### Why This Approach

1. **Industry Best Practice**: "Backend stores/transmits absolute UTC time, frontend adapts to local timezone" is the gold standard for global financial applications
2. **Clean Data**: Backend data is already properly aligned to UTC (+00:00), which is the result of careful timezone handling in Python scripts
3. **Browser Native Support**: JavaScript `Date` object and `lightweight-charts` handle timezone conversion automatically
4. **No DST Issues**: Avoids manual timezone offset calculations that break during daylight saving time transitions
5. **Simple & Reliable**: Minimal code changes, leverages built-in browser capabilities

## Implementation Details

### 1. Data Conversion Layer

**Location**: `frontend/src/components/chart/KLineChart.tsx`

**Current State**:
- For intraday data (15M, 1H, 4H): converts ISO string to Unix timestamp
- For daily+ data: extracts YYYY-MM-DD string

**Changes Needed**:
- Verify Unix timestamp conversion is correct: `Math.floor(new Date(isoString).getTime() / 1000)`
- The `Date` constructor automatically parses ISO 8601 strings and converts to local time
- Division by 1000 converts milliseconds to seconds (required by lightweight-charts)

**Code Example**:
```typescript
// Current implementation (lines 211-221)
const formattedData: CandlestickData[] = ohlcData.map((d) => {
  if (isIntradayData) {
    // For intraday: convert ISO string to Unix timestamp (seconds)
    // new Date() automatically handles timezone conversion
    const time = Math.floor(new Date(d.date).getTime() / 1000);
    return { time: time as any, open: d.open, high: d.high, low: d.low, close: d.close };
  } else {
    // For daily+: extract YYYY-MM-DD part (timezone-agnostic)
    const time = d.date.split('T')[0];
    return { time: time as any, open: d.open, high: d.high, low: d.low, close: d.close };
  }
});
```

**Status**: ✅ Current implementation is already correct for timezone conversion

### 2. Chart Localization Configuration

**Location**: `frontend/src/components/chart/KLineChart.tsx` (chart creation, lines 174-196)

**Changes Needed**:
Add custom time formatter to display local time in tooltips/crosshair.

**Code Changes**:
```typescript
const chart = createChart(chartContainerRef.current, {
  width: chartContainerRef.current.clientWidth,
  height: 400,
  localization: {
    locale: 'en-US',
    // Custom time formatter for tooltips and crosshair
    timeFormatter: (timestamp: number) => {
      // timestamp is Unix seconds, convert to milliseconds
      const date = new Date(timestamp * 1000);
      // Format as local time string
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    },
  },
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
    timeVisible: true,  // ✅ Already enabled - shows time on X-axis
    secondsVisible: false, // Don't show seconds for minute-level data
  },
  rightPriceScale: {
    borderColor: '#334155',
  },
});
```

### 3. Timezone Indicator UI Component

**Location**: `frontend/src/components/chart/KLineChart.tsx`

**Purpose**: Display current timezone to users for clarity (e.g., "UTC+8" or "Asia/Shanghai")

**Implementation**:
```typescript
// Add helper function to get timezone info
function getTimezoneInfo(): { name: string; offset: string } {
  const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const offset = -new Date().getTimezoneOffset() / 60;
  const offsetStr = `UTC${offset >= 0 ? '+' : ''}${offset}`;
  return { name: timeZone, offset: offsetStr };
}

// In component body
const [timezoneInfo] = useState(getTimezoneInfo());

// In JSX (add to chart header, line 333-343)
<div className="flex items-center justify-between mb-3">
  <div className="flex items-center gap-2">
    <h3 className="text-sm font-semibold">
      {selectedStock} - K-Line Chart
    </h3>
    <span className="text-xs text-muted-foreground">
      ({timezoneInfo.offset})
    </span>
  </div>
  <TimeRangeSelector
    value={timeRange}
    onChange={setTimeRange}
    disabled={loading}
    assetType={assetType}
  />
</div>
```

**Alternative (more detailed)**:
```typescript
<span className="text-xs text-muted-foreground" title={timezoneInfo.name}>
  时区: {timezoneInfo.offset}
</span>
```

## Files to Modify

1. **`frontend/src/components/chart/KLineChart.tsx`**
   - Add `timeFormatter` to chart localization config
   - Add timezone indicator UI component
   - Verify existing timestamp conversion logic

## Files NOT Modified

- Backend API endpoints (no changes)
- Database schema (no changes)
- Other frontend components (no changes)

## Testing Strategy

### Manual Testing
1. **Timezone Verification**:
   - Open chart in browser
   - Compare displayed time with system time
   - Verify times match local timezone

2. **Cross-Timezone Testing**:
   - Change system timezone
   - Refresh page
   - Verify chart updates to new timezone

3. **Data Integrity**:
   - Verify same data point shows different times in different timezones
   - Verify price data (OHLC) remains unchanged

### Edge Cases
1. **Daylight Saving Time**: Verify correct handling during DST transitions
2. **Timezone Boundaries**: Test with timezones that cross date boundaries (e.g., UTC+12, UTC-11)
3. **Intraday vs Daily Data**: Verify both data types display correctly

## Success Criteria

1. ✅ Chart displays times in user's browser timezone
2. ✅ Timezone indicator shows current timezone
3. ✅ No backend code changes
4. ✅ Tooltip/crosshair shows formatted local time
5. ✅ X-axis labels show local time for intraday data
6. ✅ Daily+ data continues to work correctly (date-only format)

## Trade-offs & Considerations

**Pros**:
- Simple, reliable implementation
- Leverages browser native capabilities
- No DST handling complexity
- Maintains clean UTC data in backend

**Cons**:
- Users in different timezones see different times (expected behavior)
- Cannot easily compare charts across timezones (mitigated by showing timezone indicator)

**Future Enhancements** (not in scope):
- Allow users to manually select timezone
- Show multiple timezone labels simultaneously
- Add UTC time in tooltip alongside local time

