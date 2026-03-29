# Volume Chart Design Spec

**Date:** 2026-03-29
**Status:** Draft
**Scope:** `frontend/src/components/chart/KLineChart.tsx` only

---

## Overview

Add a synchronized volume histogram below the existing K-line candlestick chart. The volume bars share the same chart instance, X-axis, and crosshair as the main price chart — no separate DOM elements or event synchronization code required.

---

## Architecture

**Single change point:** `KLineChart.tsx` — the chart `useEffect` block only.

No new files, no new components, no new props.

### Why single chart instance

`lightweight-charts` v5 supports multiple price scales on one chart. Assigning a `HistogramSeries` to a custom `priceScaleId` places it in its own vertical region while sharing the time axis natively. This gives:

- Zero-latency crosshair sync (same canvas)
- Native scroll/zoom sync (same time scale)
- Single resize handler (already present)

---

## Implementation Details

### 1. Main price scale margins

Add `scaleMargins` to the candlestick series options so the K-line area occupies the top ~75% and leaves room for volume below:

```ts
chart.addSeries(CandlestickSeries, {
  upColor: '#22c55e',
  downColor: '#ef4444',
  wickUpColor: '#22c55e',
  wickDownColor: '#ef4444',
  priceScaleId: 'right',
  scaleMargins: {
    top: 0.1,
    bottom: 0.25,
  },
});
```

### 2. Volume series registration

```ts
import { HistogramSeries } from 'lightweight-charts';

const volumeSeries = chart.addSeries(HistogramSeries, {
  priceScaleId: 'volume',
  priceFormat: { type: 'volume' },
});

chart.priceScale('volume').applyOptions({
  scaleMargins: {
    top: 0.8,   // volume area starts at 80% from top
    bottom: 0,
  },
});
```

### 3. Data mapping

Reuse the same `ohlcData` loop that builds `formattedData`. Build a parallel `volumeData` array:

```ts
const volumeData = ohlcData.map((d) => {
  const time = isIntradayData
    ? Math.floor(new Date(d.date).getTime() / 1000) as any
    : d.date.split('T')[0] as any;
  return {
    time,
    value: d.volume,
    color: d.close >= d.open
      ? 'rgba(34, 197, 94, 0.6)'   // green, matches upColor
      : 'rgba(239, 68, 68, 0.6)',  // red, matches downColor
  };
});

volumeSeries.setData(volumeData);
```

Alpha 0.6 keeps bars visually lighter than the candles above.

### 4. Tooltip / crosshair volume display

The existing `subscribeCrosshairMove` callback (if present) or a new one reads both series from `param.seriesData`:

```ts
chart.subscribeCrosshairMove((param) => {
  if (!param.point || !param.seriesData) return;
  const volData = param.seriesData.get(volumeSeries) as { value: number } | undefined;
  // update tooltip DOM with volData?.value
});
```

Display the raw volume value formatted as `1.23K` / `1.23M` — `lightweight-charts` handles this automatically via `priceFormat: { type: 'volume' }` on the series.

---

## Visual Spec

| Region | Height share | Price scale |
|--------|-------------|-------------|
| K-line (candlestick) | ~75–80% | `right` |
| Volume (histogram) | ~20–25% | `volume` (custom) |

- Volume bars are green (rgba 0.6) when `close >= open`, red (rgba 0.6) otherwise
- Y-axis for volume starts at 0, scales independently from price
- Crosshair spans both regions simultaneously (native behavior)
- Scroll and zoom affect both regions simultaneously (native behavior)
- Volume Y-axis auto-scales so the tallest visible bar fills the volume region

---

## What Is Not Changing

- No new files
- No new props on `KLineChartProps`
- No changes to data fetching (`fetchData`, API calls)
- No changes to `TimeRangeSelector`, `AssetSelector`, or any other component
- No changes to the visible range logic

---

## Acceptance Criteria

1. Volume bars appear below the K-line chart with correct proportions (~20% height)
2. Each bar color matches the corresponding candle (green/red)
3. Crosshair moves across both regions simultaneously
4. Scrolling and zooming keeps both regions in sync
5. Volume value is readable in the tooltip/crosshair label area
6. No regression on existing candlestick behavior (colors, time range, resize)
